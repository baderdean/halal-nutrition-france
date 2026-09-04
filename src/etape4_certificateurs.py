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
    noms = {c["tag"]: c["nom"] for c in cfg["certificateurs"]}
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

    sep = con.execute(f"""
        SELECT lab AS tag, count(*) AS n_produits,
               count(DISTINCT marque) AS n_marques,
               round(100.0 * max(part) , 1) AS pct_1re_marque
        FROM (
          SELECT lab, marque, count(*) OVER (PARTITION BY lab) AS tot,
                 count(*) OVER (PARTITION BY lab, marque)::DOUBLE
                   / count(*) OVER (PARTITION BY lab) AS part
          FROM (SELECT unnest(labels_tags) AS lab,
                       regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque
                FROM '{PERIMETRE}'
                WHERE brands_tags IS NOT NULL AND len(brands_tags) > 0))
        WHERE lab IN ('{tags}')
        GROUP BY lab ORDER BY n_produits DESC""").df()
    sep["certificateur"] = sep.tag.map(noms)
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
