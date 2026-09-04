#!/usr/bin/env python3
"""Couche 4 — les certificateurs sont-ils des indicateurs de qualite ?

Corrige une conclusion de la couche 1. Elle detectait les certificateurs en
cherchant la chaine 'halal' dans les tags, et annoncait 6,9 % de couverture,
d'ou la decision d'abandonner la question. Ce filtre ratait tous les
organismes nommes par leur mosquee ou leur association, dont AVS — A Votre
Service, le principal certificateur francais, dont le nom ne contient pas
'halal'. La couverture reelle est de 30,5 %.

Deux questions, dans cet ordre :
  1. la question est-elle exploitable — couverture, et separabilite d'avec la
     marque, qui etait le second motif d'abandon ;
  2. si oui, les certificateurs se distinguent-ils nutritionnellement, a
     composition egale, meme methode que les marques et les labels.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, charger, connexion, titre
from etape4_marques import GRAINE, N_SOLIDE, ic_mediane

N_MIN = 30
VARIABLES = [("nutriscore_score", "Nutri-Score en score continu", 1),
             ("sel", "sel pour 100 g", 1),
             ("ags", "AGS pour 100 g", 1),
             ("proteines", "proteines pour 100 g", -1)]


def main() -> int:
    cfg = charger("certificateurs.yaml")
    # Un organisme, plusieurs tags : la taxonomie OFF l'eclate en variantes.
    noms = {t: c["nom"] for c in cfg["certificateurs"] for t in c["tags"]}
    tags = "', '".join(noms)
    con = connexion()
    rng = np.random.default_rng(GRAINE)

    titre("1. La question est-elle exploitable ?")
    couv = con.execute(f"""
        SELECT count(*) FILTER (WHERE tag_halal) AS n_halal,
               count(*) FILTER (WHERE tag_halal AND len(list_filter(labels_tags,
                 x -> x IN ('{tags}'))) > 0) AS avec_certificateur
        FROM '{PERIMETRE}'""").df()
    n_h = int(couv.n_halal[0]); n_c = int(couv.avec_certificateur[0])
    print(f"  Couverture : {n_c} / {n_h} = {100 * n_c / n_h:.1f} % des produits "
          "halal portent un certificateur identifie.")
    print("  La couche 1 annoncait 6,9 % et abandonnait la question. Corrige.\n")

    # L'agregation se fait par ORGANISME, pas par tag : sinon un certificateur
    # eclate en variantes apparait plusieurs fois et parait plus petit qu'il
    # n'est.
    brut = con.execute(f"""
        SELECT lab, marque, count(*) AS n FROM (
          SELECT unnest(labels_tags) AS lab,
                 regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque
          FROM '{PERIMETRE}'
          WHERE brands_tags IS NOT NULL AND len(brands_tags) > 0)
        WHERE lab IN ('{tags}') GROUP BY lab, marque""").df()
    brut["certificateur"] = brut.lab.map(noms)
    # Un produit peut porter deux variantes du meme organisme : on compte les
    # couples organisme x marque une seule fois par produit, en prenant le max.
    par = (brut.groupby(["certificateur", "marque"])["n"].max().reset_index())
    sep = (par.groupby("certificateur")
           .agg(n_produits=("n", "sum"), n_marques=("marque", "nunique"),
                premiere=("n", "max")).reset_index())
    sep["pct_1re_marque"] = (100.0 * sep.premiere / sep.n_produits).round(1)
    sep = sep.sort_values("n_produits", ascending=False)
    print("  Separabilite d'avec la marque, second motif d'abandon :")
    print(sep[["certificateur", "n_produits", "n_marques",
               "pct_1re_marque"]].to_string(index=False))
    print("\n  Un certificateur dont une seule marque fait l'essentiel des")
    print("  produits n'est pas separable de cette marque.")
    sep.to_csv(SORTIES / "c_certificateurs_separabilite.csv", index=False)

    titre("2. Se distinguent-ils nutritionnellement, a composition egale ?")
    print("Ecart a la mediane de marche de la strate sous-categorie x espece,")
    print("meme methode que les marques et les labels. Negatif = mieux.\n")
    d = con.execute(f"""
        SELECT sous_categorie, espece, labels_tags, tag_halal,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               CASE WHEN salt_100g BETWEEN 0 AND 100 THEN salt_100g END AS sel,
               CASE WHEN saturated_fat_100g BETWEEN 0 AND 100
                    THEN saturated_fat_100g END AS ags,
               CASE WHEN proteins_100g BETWEEN 0 AND 100
                    THEN proteins_100g END AS proteines,
               nutriscore_score
        FROM '{PERIMETRE}' WHERE ({COMPLET})""").df()
    d["strate"] = d.sous_categorie + " / " + d.espece
    t = d.groupby("strate").size()
    d = d[d.strate.isin(t[t >= N_SOLIDE].index)].copy()
    for var, _, _ in VARIABLES:
        d["ecart_" + var] = d[var] - d.groupby("strate")[var].transform("median")

    d["certificateur"] = d.labels_tags.apply(
        lambda ls: next((noms[x] for x in ls if x in noms), None))
    halal = d[d.tag_halal].copy()
    halal["groupe"] = halal.certificateur.fillna("halal SANS certificateur")

    for var, libelle, sens in VARIABLES:
        lignes = []
        for g, sous in halal.groupby("groupe"):
            v = sous["ecart_" + var].dropna().to_numpy()
            if len(v) < N_MIN:
                continue
            ic = ic_mediane(v, rng)
            if ic is None:
                continue
            lignes.append({
                "groupe": g, "n": len(v),
                "ecart_median": round(sens * ic[0], 3),
                "ic95_bas": round(min(sens * ic[1], sens * ic[2]), 3),
                "ic95_haut": round(max(sens * ic[1], sens * ic[2]), 3),
                "strates": sous.strate.nunique(),
            })
        if not lignes:
            continue
        r = pd.DataFrame(lignes).sort_values("ecart_median")
        r["distingue_du_marche"] = np.where(
            (r.ic95_bas > 0) | (r.ic95_haut < 0), "oui", "non")
        print(f"  --- {libelle}")
        print(r.to_string(index=False))
        print()
        r.to_csv(SORTIES / f"c_certificateurs_{var}.csv", index=False)

    titre("La question de la couche 1, tranchee")
    print("Certifie vaut-il mieux que non certifie, DANS le bras halal ?")
    for var, libelle, sens in VARIABLES:
        a = halal.loc[halal.certificateur.notna(), "ecart_" + var].dropna()
        b = halal.loc[halal.certificateur.isna(), "ecart_" + var].dropna()
        if len(a) < N_MIN or len(b) < N_MIN:
            continue
        ia, ib = ic_mediane(a.to_numpy(), rng), ic_mediane(b.to_numpy(), rng)
        print(f"  {libelle:<32} certifie {sens*ia[0]:+.2f} "
              f"[{min(sens*ia[1],sens*ia[2]):+.2f} ; {max(sens*ia[1],sens*ia[2]):+.2f}]"
              f"   sans {sens*ib[0]:+.2f} "
              f"[{min(sens*ib[1],sens*ib[2]):+.2f} ; {max(sens*ib[1],sens*ib[2]):+.2f}]"
              f"   n={len(a)}/{len(b)}")

    comparaison_nationalite(halal, rng)
    comparaison_electronarcose(halal, rng)
    return 0

def comparaison_nationalite(halal, rng):
    """Les certificateurs francais font-ils mieux que les etrangers ?

    Critere de nationalite : le nom de l'organisme designe une institution
    francaise. Ce n'est pas une affirmation sur le siege social ni sur le lieu
    d'abattage, que ce depot ne connait pas.
    """
    nat = charger("certificateurs.yaml")["nationalite"]
    grp = {c: "certificateur francais" for c in nat["francais"]}
    grp.update({c: "certificateur etranger" for c in nat["etranger"]})
    h = halal.copy()
    h["nationalite"] = h.certificateur.map(grp)
    h.loc[h.certificateur.isna(), "nationalite"] = "sans certificateur"

    titre("Les certificateurs francais font-ils mieux que les etrangers ?")
    compo = (h[h.nationalite.notna()]
             .groupby("nationalite")
             .agg(produits=("certificateur", "size"),
                  organismes=("certificateur", "nunique")))
    print(compo.to_string())
    print()
    lignes = []
    for var, libelle, sens in VARIABLES:
        for g, sous in h.groupby("nationalite"):
            v = sous["ecart_" + var].dropna().to_numpy()
            if len(v) < N_MIN:
                print(f"  {libelle} / {g} : {len(v)} produits, sous le seuil "
                      f"de {N_MIN}. Non calcule.")
                continue
            ic = ic_mediane(v, rng)
            if ic is None:
                continue
            lignes.append({
                "variable": libelle, "groupe": g, "n": len(v),
                "ecart_median": round(sens * ic[0], 3),
                "ic95_bas": round(min(sens * ic[1], sens * ic[2]), 3),
                "ic95_haut": round(max(sens * ic[1], sens * ic[2]), 3),
            })
    if lignes:
        r = pd.DataFrame(lignes)
        print(r.to_string(index=False))
        r.to_csv(SORTIES / "c_nationalite.csv", index=False)

    # Un groupe si petit peut n'etre qu'une marque. Concentration, puis test
    # de sensibilite en retirant la marque dominante : si l'ecart s'effondre,
    # ce n'etait pas un effet de nationalite du certificateur.
    print("\n  Concentration par marque du groupe etranger :")
    etr = h[h.nationalite == "certificateur etranger"]
    print((etr.marque.value_counts(normalize=True) * 100).round(1)
          .head(5).to_string())
    dominante = etr.marque.value_counts().idxmax()
    print(f"\n  Sensibilite, Nutri-Score, en retirant « {dominante} » :")
    for lab, sous in [("etranger, tout", etr),
                      (f"etranger sans {dominante}",
                       etr[etr.marque != dominante]),
                      ("francais", h[h.nationalite == "certificateur francais"])]:
        v = sous["ecart_nutriscore_score"].dropna().to_numpy()
        ic = ic_mediane(v, rng) if len(v) >= 5 else None
        if ic is None:
            print(f"    {lab:<28} n={len(v)}, trop peu")
            continue
        alerte = "  SOUS LE SEUIL" if len(v) < N_MIN else ""
        print(f"    {lab:<28} n={len(v):>4}  {ic[0]:+.1f} "
              f"[{ic[1]:+.1f} ; {ic[2]:+.1f}]{alerte}")
    return h


def comparaison_electronarcose(halal, rng):
    """Compare les certificateurs selon un regroupement DECLARE, pas etabli.

    Le regroupement vient du commanditaire de l'etude. Ce depot ne dispose
    d'aucune donnee sur les pratiques d'abattage : il applique le decoupage
    fourni et n'en garantit pas l'exactitude.
    """
    e = charger("electronarcose.yaml")
    grp = {}
    for c in e["sans_electronarcose"]:
        grp[c] = "sans electronarcose (declare)"
    for c in e["avec_electronarcose"]:
        grp[c] = "avec electronarcose (declare)"
    halal = halal.copy()
    halal["groupe_e"] = halal.certificateur.map(grp)
    halal.loc[halal.certificateur.isna(), "groupe_e"] = "sans certificateur"

    titre("Electronarcose : regroupement DECLARE par le commanditaire")
    print("Ce depot n'etablit PAS quels organismes pratiquent l'electronarcose.")
    print("Open Food Facts n'en dit rien. La classification est fournie, non")
    print("verifiee, et toute publication doit citer les cahiers des charges")
    print("des organismes, pas ce fichier.\n")
    print("  Composition des groupes :")
    print(halal.groupby("groupe_e").certificateur.nunique().to_string())
    print()
    lignes = []
    for var, libelle, sens in VARIABLES:
        for g, sous in halal.groupby("groupe_e"):
            v = sous["ecart_" + var].dropna().to_numpy()
            if len(v) < N_MIN:
                continue
            ic = ic_mediane(v, rng)
            if ic is None:
                continue
            lignes.append({
                "variable": libelle, "groupe": g, "n": len(v),
                "ecart_median": round(sens * ic[0], 3),
                "ic95_bas": round(min(sens * ic[1], sens * ic[2]), 3),
                "ic95_haut": round(max(sens * ic[1], sens * ic[2]), 3),
                "marques": sous.groupby("certificateur").size().size,
            })
    r = pd.DataFrame(lignes)
    print(r.to_string(index=False))
    r.to_csv(SORTIES / "c_electronarcose.csv", index=False)
    print("\n  LIMITE DECISIVE : ces groupes ne sont pas separables de la")
    print("  marque. L'ARGML tire 78 % de ses produits d'une seule marque,")
    print("  Achahada 67 % de trois marques. Un ecart entre groupes peut etre")
    print("  la recette d'une marque, pas une consequence du mode d'abattage.")
    print("  Aucun mecanisme connu ne relie l'electronarcose au sel ou aux")
    print("  acides gras satures d'une recette industrielle.")


if __name__ == "__main__":
    sys.exit(main())
