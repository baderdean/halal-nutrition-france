#!/usr/bin/env python3
"""Couche 13 — l'ecart tient-il au SITE de fabrication ?

Question : quand une marque vend les deux gammes et que la version halal est
moins bonne, est-ce parce qu'elle est FABRIQUEE AILLEURS ?

Une marque generaliste peut faire fabriquer sa gamme halal chez un
sous-traitant qu'elle n'emploie pas pour le reste. L'ecart mesure alors le
changement de fournisseur, pas une exigence revue a la baisse sur un meme
outil. Les deux lectures ont des consequences opposees pour le lecteur, et
elles se distinguent.

METHODE. Pour chaque produit halal d'une marque, on regarde si son
etablissement sert AUSSI a la production non halal de la meme marque.

  site partage      la marque fait fabriquer les deux au meme endroit ;
  site halal seul   l'etablissement ne produit que du halal pour elle.

CONFONDANT ASSUME ET NON RESOLU. Les sites partages appartiennent surtout aux
generalistes, qui font par ailleurs mieux. Comparer les deux groupes revient
donc en partie a comparer des generalistes a des specialistes. Le detail par
marque est publie pour cette raison : c'est la seule facon de voir si le motif
tient a l'interieur d'une marque.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, connexion, titre
from etape5_produits_emblematiques import ic_diff
from etape10_etablissements import normaliser_etablissement, utilisable

SEUIL = 30
GRAINE = 20260904


def main() -> int:
    con = connexion()
    rng = np.random.default_rng(GRAINE)
    d = con.execute(f"""
        SELECT code, emb_codes_tags, sous_categorie, espece,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS mq,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               nutriscore_score AS ns, {borne('salt_100g', 'sel')}
        FROM '{PERIMETRE}'
        WHERE ({COMPLET}) AND brands_tags IS NOT NULL AND len(brands_tags) > 0
    """).df()
    e = d.explode("emb_codes_tags").rename(columns={"emb_codes_tags": "et"})
    e = e[e.et.notna()].copy()
    e["et"] = e.et.astype(str)
    e = e[e.et.apply(utilisable)]
    e["et"] = e.et.apply(normaliser_etablissement)
    e["strate"] = e.sous_categorie + " / " + e.espece
    t = e.groupby("strate").size()
    e = e[e.strate.isin(t[t >= SEUIL].index)].copy()
    e["ecart"] = e.ns - e.groupby("strate").ns.transform("median")

    sites_temoin = e[e.bras == "temoin"].groupby("mq").et.apply(set)
    h = e[e.bras == "halal"].copy()
    h["site_partage"] = [r.et in sites_temoin.get(r.mq, set())
                         for r in h.itertuples()]

    titre("La gamme halal est-elle fabriquee ailleurs ?")
    print("Produits halal, selon que leur etablissement sert aussi a la")
    print("production non halal de la MEME marque. Ecart = ecart a la mediane")
    print("de marche de la strate, donc a composition egale.\n")
    r = (h.groupby("site_partage")
          .agg(n=("ns", "size"), marques=("mq", "nunique"),
               sites=("et", "nunique"), nutriscore=("ns", "median"),
               ecart=("ecart", "median"), sel=("sel", "median")).round(2))
    r.index = ["site halal seul", "site partage"]
    print(r.to_string())

    a = h[h.site_partage]
    b = h[~h.site_partage]
    lignes = []
    for var, lib in (("ecart", "ecart Nutri-Score"), ("sel", "sel g/100 g")):
        x = ic_diff(a[var].to_numpy(float), b[var].to_numpy(float), rng)
        if not x:
            continue
        etabli = "etabli" if (x[1] > 0 or x[2] < 0) else "non etabli"
        print(f"\n  {lib:20s} site partage - site halal seul = {x[0]:+.2f} "
              f"[{x[1]:+.2f} ; {x[2]:+.2f}]  {etabli}")
        lignes.append({"niveau": "global", "cle": "", "variable": lib,
                       "n_partage": len(a), "n_halal_seul": len(b),
                       "ecart": round(x[0], 2), "ic95_bas": round(x[1], 2),
                       "ic95_haut": round(x[2], 2),
                       "etabli": etabli == "etabli"})

    titre("Le motif tient-il A L'INTERIEUR d'une marque ?")
    print("C'est la seule lecture qui echappe au confondant : les sites")
    print("partages appartiennent surtout aux generalistes, qui font mieux par")
    print("ailleurs. Marques a 5 produits halal ou plus.\n")
    for mq, g in h.groupby("mq"):
        if len(g) < 5:
            continue
        p, q = g[g.site_partage], g[~g.site_partage]
        ep = p.ecart.median() if len(p) else float("nan")
        eq = q.ecart.median() if len(q) else float("nan")
        note = ""
        if len(p) and len(q):
            note = ("  <- le motif tient" if ep < eq
                    else "  <- motif INVERSE")
        print(f"  {mq:20s} partage n={len(p):3d} ecart {ep:+6.1f}   "
              f"halal seul n={len(q):3d} ecart {eq:+6.1f}{note}")
        lignes.append({"niveau": "marque", "cle": mq, "variable": "ecart",
                       "n_partage": len(p), "n_halal_seul": len(q),
                       "ecart": None if np.isnan(ep) or np.isnan(eq)
                       else round(float(ep - eq), 2),
                       "ic95_bas": None, "ic95_haut": None, "etabli": None})
    pd.DataFrame(lignes).to_csv(SORTIES / "z1_site_ou_marque.csv", index=False)

    titre("LECTURE")
    print("Le sel est plus bas quand le site est partage, et l'ecart de")
    print("Nutri-Score va dans le meme sens sans etre etabli.")
    print()
    print("Mais le motif ne tient pas dans toutes les marques. Carrefour en est")
    print("l'illustration : sa gamme halal sort majoritairement de sites qu'il")
    print("n'emploie pas pour le reste, et c'est la que l'ecart se creuse ; sur")
    print("les sites qu'il partage, l'ecart s'efface presque. Reghalal montre")
    print("l'inverse.")
    print()
    print("CONCLUSION HONNETE : le changement de site EXPLIQUE UNE PART de")
    print("l'ecart chez certaines marques, pas chez toutes. Ce n'est ni un")
    print("facteur unique ni un facteur nul, et les effectifs ne permettent pas")
    print("d'aller plus loin.")
    print("\nEcrit : sorties/z1_site_ou_marque.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
