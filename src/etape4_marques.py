#!/usr/bin/env python3
"""Couche 4 — classement des marques, a composition egale.

Un classement BRUT serait malhonnete : une marque qui ne vend que de la
charcuterie seche paraitrait catastrophique face a une marque de blancs de
poulet, sans qu'aucune des deux n'y soit pour quelque chose. Le rayon
n'oppose pas ces produits.

Methode. Pour chaque produit on calcule son ECART a la mediane de marche de
sa strate (sous-categorie x espece), toutes marques et tous bras confondus.
La strate est donc le point de comparaison, et l'ecart mesure ce que la
marque fait DE MIEUX OU DE PIRE que le marche sur ce type de produit precis.
On agrege ensuite par marque, en mediane, avec un intervalle par bootstrap.

Un ecart negatif est meilleur pour le sel, les AGS et le Nutri-Score en score
continu. Il est PIRE pour les proteines : le signe y est inverse a
l'affichage, pour que la lecture reste « negatif = moins bon ».

Ce classement nomme des entreprises reelles. Il n'a de sens qu'accompagne de
ses effectifs et de ses intervalles, et il ne dit rien de la halalite ni de
la conformite d'aucun produit.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, connexion, titre

N_MIN = 15          # sous ce seuil une marque n'est pas classee
N_SOLIDE = 30       # regle des 30 : au-dessus, la ligne est testable
N_BOOT = 2000
GRAINE = 20260904
VARIABLES = [("nutriscore_score", "Nutri-Score en score continu", 1),
             ("sel", "sel pour 100 g", 1),
             ("ags", "AGS pour 100 g", 1),
             ("proteines", "proteines pour 100 g", -1)]


def ic_mediane(x, rng):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 5:
        return None
    b = np.array([np.median(rng.choice(x, len(x), True)) for _ in range(N_BOOT)])
    return (float(np.median(x)), float(np.percentile(b, 2.5)),
            float(np.percentile(b, 97.5)))


def classer(d, var, sens, rng, bras=None):
    """Classement des marques sur l'ecart a la mediane de marche de la strate."""
    sous = d if bras is None else d[d.bras == bras]
    lignes = []
    for marque, g in sous.groupby("marque"):
        v = g["ecart_" + var].dropna().to_numpy()
        if len(v) < N_MIN:
            continue
        ic = ic_mediane(v, rng)
        if ic is None:
            continue
        lignes.append({
            "marque": marque, "n": len(v),
            # Le signe est applique AVANT le tri des bornes : l'inverser
            # ensuite mettait la borne basse au-dessus de la haute.
            "ecart_median": round(sens * ic[0], 3),
            "ic95_bas": round(min(sens * ic[1], sens * ic[2]), 3),
            "ic95_haut": round(max(sens * ic[1], sens * ic[2]), 3),
            "regle_30": "franchie" if len(v) >= N_SOLIDE else "sous 30",
            "strates_couvertes": g.strate.nunique(),
        })
    t = pd.DataFrame(lignes)
    return t.sort_values("ecart_median") if len(t) else t


def main() -> int:
    con = connexion()
    rng = np.random.default_rng(GRAINE)
    d = con.execute(f"""
        SELECT bras, sous_categorie, espece,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               any_value(brands) OVER (
                 PARTITION BY regexp_replace(brands_tags[1], '^[a-z]{{2}}:', ''))
                 AS marque_affichee,
               {borne('salt_100g', 'sel')},
               {borne('saturated_fat_100g', 'ags')},
               {borne('proteins_100g', 'proteines')},
               nutriscore_score
        FROM '{PERIMETRE}'
        WHERE ({COMPLET}) AND brands_tags IS NOT NULL AND len(brands_tags) > 0
    """).df()
    d["strate"] = d.sous_categorie + " / " + d.espece

    # Reference : la mediane de MARCHE de la strate, tous bras confondus.
    # Une strate trop petite ne fournit pas de reference fiable.
    tailles = d.groupby("strate").size()
    d = d[d.strate.isin(tailles[tailles >= N_SOLIDE].index)]
    for var, _, _ in VARIABLES:
        d["ecart_" + var] = d[var] - d.groupby("strate")[var].transform("median")

    titre("Classement des marques du bras HALAL, a composition egale")
    print("Ecart a la mediane de marche de chaque strate sous-categorie x")
    print("espece. Negatif = mieux que le marche sur le meme type de produit.")
    print(f"Marques a moins de {N_MIN} produits non classees ; celles sous "
          f"{N_SOLIDE}\nsont classees mais signalees.\n")
    for var, libelle, sens in VARIABLES:
        t = classer(d, var, sens, rng, bras="halal")
        if not len(t):
            print(f"  --- {libelle} : aucune marque ne franchit {N_MIN}\n")
            continue
        print(f"  --- {libelle}  (negatif = meilleur)")
        print(t.to_string(index=False))
        print()
        t.to_csv(SORTIES / f"m_halal_{var}.csv", index=False)

    titre("Meme classement, toutes marques du perimetre")
    print("Sert de reference : les marques halal se situent ou dans le rayon ?\n")
    t = classer(d, "nutriscore_score", 1, rng)
    if len(t):
        # « avec gamme halal » et non « halal » : Carrefour ou Fleury Michon
        # ont quelques references halal dans une gamme tres majoritairement
        # non halal. Les etiqueter halal serait faux.
        avec = set(d[d.bras == "halal"].marque)
        t["gamme_halal"] = np.where(t.marque.isin(avec), "oui", "non")
        print(f"  {len(t)} marques classees. Meilleures et pires 12 :")
        print(pd.concat([t.head(12), t.tail(12)]).to_string(index=False))
        t.to_csv(SORTIES / "m_toutes_nutriscore.csv", index=False)
        rang = t.reset_index(drop=True)
        rang["rang"] = rang.index + 1
        h = rang[rang.gamme_halal == "oui"]
        print(f"\n  Les {len(h)} marques disposant d'une gamme halal occupent "
              f"les rangs "
              f"{int(h.rang.min())} a {int(h.rang.max())} sur {len(rang)}, "
              f"rang median {int(h.rang.median())}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
