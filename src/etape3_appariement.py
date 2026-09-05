#!/usr/bin/env python3
"""Couche 3 — appariement, et les deux estimands des specs.

L'ecart brut de la couche 1 est confondu avec la composition : le bras halal
compte 14,8 % de produits panes contre 3,1 % au temoin, et 91,3 % de NOVA 4
contre 73,3 %. Cette couche compare a composition egale.

Methode : appariement exact grossier (CEM). On stratifie, on compare DANS
chaque strate, puis on agrege en ponderant par l'effectif HALAL de la strate.
Cette ponderation donne l'effet moyen sur les traites (ATT) : la question
posee est « les produits halal seraient-ils differents s'ils n'etaient pas
halal », pas « le rayon entier serait-il different ».

Pas de score de propension : un appariement exact sur deux variables
observables se verifie a l'oeil, un modele de propension demande qu'on croie
a sa specification.

DEUX ESTIMANDS, rapportes separement et jamais melanges :

  E1  effet TOTAL du label, espece non ajustee. L'exclusion du porc est un
      MEDIATEUR assume : elle est une consequence du label, pas un biais.
      Stratification sur la seule sous-categorie.

  E2  effet DIRECT a espece et sous-categorie identiques, restreint aux
      strates ou le temoin existe hors porc. Repond a : a produit comparable,
      le label change-t-il quelque chose.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, connexion, titre

SEUIL = 30
GRAINE = 20260904
N_BOOT = 2000
VARIABLES = [("sel", "sel pour 100 g"), ("ags", "AGS pour 100 g"),
             ("proteines", "proteines pour 100 g"),
             ("nutriscore_score", "Nutri-Score en score continu")]


def diff_medianes_boot(a, b, rng):
    a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
    if len(a) < 10 or len(b) < 10:
        return None
    d = np.empty(N_BOOT)
    for i in range(N_BOOT):
        d[i] = (np.median(rng.choice(a, len(a), True))
                - np.median(rng.choice(b, len(b), True)))
    return float(np.median(a) - np.median(b)), d


def estimand(df, cles, var, rng, etiquette):
    """Difference par strate, puis agregat pondere par l'effectif halal."""
    lignes, contribs, poids = [], [], []
    for cle, sous in df.groupby(cles):
        a = sous.loc[sous.bras == "halal", var].dropna().to_numpy()
        b = sous.loc[sous.bras == "temoin", var].dropna().to_numpy()
        if len(a) < SEUIL or len(b) < SEUIL:
            continue
        r = diff_medianes_boot(a, b, rng)
        if r is None:
            continue
        d, tirages = r
        lignes.append({
            "strate": cle if isinstance(cle, str) else " / ".join(cle),
            "n_halal": len(a), "n_temoin": len(b),
            "median_halal": round(float(np.median(a)), 2),
            "median_temoin": round(float(np.median(b)), 2),
            "diff": round(d, 3),
            "ic95_bas": round(float(np.percentile(tirages, 2.5)), 3),
            "ic95_haut": round(float(np.percentile(tirages, 97.5)), 3),
        })
        contribs.append(tirages); poids.append(len(a))
    if not lignes:
        return pd.DataFrame(), None
    poids = np.array(poids, float); poids /= poids.sum()
    agrege = np.tensordot(poids, np.array(contribs), axes=1)
    point = float(np.dot(poids, [l["diff"] for l in lignes]))
    return pd.DataFrame(lignes), {
        "estimand": etiquette, "variable": var,
        "n_strates": len(lignes),
        "n_halal_apparies": int(sum(l["n_halal"] for l in lignes)),
        "diff_ponderee": round(point, 3),
        "ic95_bas": round(float(np.percentile(agrege, 2.5)), 3),
        "ic95_haut": round(float(np.percentile(agrege, 97.5)), 3),
    }


def main() -> int:
    con = connexion()
    rng = np.random.default_rng(GRAINE)
    d = con.execute(f"""
        SELECT bras, sous_categorie, espece,
          {borne('salt_100g', 'sel')},
          {borne('saturated_fat_100g', 'ags')},
          {borne('proteins_100g', 'proteines')},
          nutriscore_score
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()

    resume = []
    titre("E1 — effet TOTAL du label, espece non ajustee")
    print("L'exclusion du porc est un MEDIATEUR du label, pas un biais : elle")
    print("reste dans l'estimand. Stratification sur la sous-categorie seule.\n")
    for var, libelle in VARIABLES:
        t, ag = estimand(d, ["sous_categorie"], var, rng, "E1_total")
        if ag is None:
            continue
        resume.append(ag)
        print(f"  --- {libelle}")
        print(t.to_string(index=False))
        print(f"  AGREGE pondere par l'effectif halal : {ag['diff_ponderee']:+.3f} "
              f"IC95 [{ag['ic95_bas']:+.3f} ; {ag['ic95_haut']:+.3f}]\n")
        t.to_csv(SORTIES / f"e1_total_{var}.csv", index=False)

    titre("E2 — effet DIRECT, a espece ET sous-categorie identiques")
    print("Restreint aux strates ou le temoin existe hors porc : la question")
    print("est ce que le label change A PRODUIT COMPARABLE.\n")
    hors_porc = d[d.espece.isin(["poulet", "dinde", "boeuf", "agneau",
                                 "volaille_autre", "veau"])]
    for var, libelle in VARIABLES:
        t, ag = estimand(hors_porc, ["sous_categorie", "espece"], var, rng,
                         "E2_direct")
        if ag is None:
            continue
        resume.append(ag)
        print(f"  --- {libelle}")
        print(t.to_string(index=False))
        print(f"  AGREGE pondere par l'effectif halal : {ag['diff_ponderee']:+.3f} "
              f"IC95 [{ag['ic95_bas']:+.3f} ; {ag['ic95_haut']:+.3f}]\n")
        t.to_csv(SORTIES / f"e2_direct_{var}.csv", index=False)

    titre("LES DEUX ESTIMANDS COTE A COTE")
    print("E1 mesure ce que devient un produit quand il devient halal, en")
    print("laissant l'exclusion du porc jouer. E2 mesure ce qui reste une fois")
    print("l'espece et la forme du produit tenues fixes. Ils ne repondent pas")
    print("a la meme question et ne se comparent pas terme a terme.\n")
    r = pd.DataFrame(resume)
    print(r.to_string(index=False))
    r.to_csv(SORTIES / "e_estimands.csv", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
