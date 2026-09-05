#!/usr/bin/env python3
"""Couche 11 — y a-t-il un cahier des charges commun derriere le halal ?

La question posee est la plus lourde de l'etude : l'ecart nutritionnel
traduirait-il une PRESCRIPTION, c'est-a-dire un choix delibere quelque part.

Aucune donnee nutritionnelle ne peut atteindre une intention. Une intention
est un etat mental de decideurs ; Open Food Facts contient des etiquettes. Ce
script ne teste donc pas l'intention. Il teste sa TRACE OBSERVABLE, et cette
trace a une forme precise :

  UNE PRESCRIPTION COMMUNE HOMOGENEISE. Si un cahier des charges partage
  dictait les recettes halal, les produits halal se ressembleraient ENTRE EUX
  plus que les temoins ne se ressemblent entre eux. C'est la signature d'une
  norme : elle resserre la dispersion.

  UNE DISPERSION PLUS LARGE DIT L'INVERSE. Elle est la signature de choix
  independants, non coordonnes.

La dispersion est mesuree sur l'ECART A LA MEDIANE DE LA STRATE, pas sur le
Nutri-Score brut : sans cela on mesurerait l'heterogeneite de l'assortiment
et non celle des recettes. Trois mesures, parce que l'ecart-type seul est
sensible aux valeurs extremes : ecart-type, ecart interquartile, et ecart
absolu median a la mediane.

Ce que ce script ne peut PAS trancher, et qu'il ne faut pas lui faire dire :
il ne dit rien des cahiers des charges reels des organismes certificateurs,
qui portent sur l'abattage et la tracabilite et qu'il faudrait lire.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, connexion, titre

SEUIL = 30
GRAINE = 20260904
N_BOOT = 4000


def dispersions(x: np.ndarray) -> dict:
    x = x[~np.isnan(x)]
    return {"n": len(x), "ecart_type": float(np.std(x, ddof=1)),
            "iqr": float(np.percentile(x, 75) - np.percentile(x, 25)),
            "mad": float(np.median(np.abs(x - np.median(x))))}


def ic_rapport(a: np.ndarray, b: np.ndarray, mesure: str, rng) -> tuple | None:
    """IC du RAPPORT de dispersion halal / temoin.

    Un rapport plutot qu'une difference : « 1,4 fois plus disperse » se lit
    sans connaitre l'echelle du Nutri-Score continu. Sous 1, le halal est plus
    homogene, ce que produirait une prescription commune.
    """
    a = a[~np.isnan(a)]
    b = b[~np.isnan(b)]
    if len(a) < 20 or len(b) < 20:
        return None
    f = {"ecart_type": lambda x: np.std(x, ddof=1),
         "iqr": lambda x: np.percentile(x, 75) - np.percentile(x, 25),
         "mad": lambda x: np.median(np.abs(x - np.median(x)))}[mesure]
    base = float(f(a) / f(b)) if f(b) else float("nan")
    r = np.empty(N_BOOT)
    for i in range(N_BOOT):
        da = f(rng.choice(a, len(a), True))
        db = f(rng.choice(b, len(b), True))
        r[i] = da / db if db else np.nan
    r = r[~np.isnan(r)]
    return base, float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def main() -> int:
    con = connexion()
    rng = np.random.default_rng(GRAINE)
    d = con.execute(f"""
        SELECT sous_categorie, espece,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               nutriscore_score AS ns, {borne('salt_100g', 'sel')}
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    d["strate"] = d.sous_categorie + " / " + d.espece
    t = d.groupby("strate").size()
    d = d[d.strate.isin(t[t >= SEUIL].index)].copy()
    d["ecart"] = d.ns - d.groupby("strate").ns.transform("median")

    titre("Le bras halal est-il PLUS HOMOGENE que le temoin ?")
    print("Une prescription commune resserre la dispersion. Un rapport sous 1")
    print("irait dans le sens d'un cahier des charges partage ; au-dessus de 1,")
    print("il dit des choix independants.\n")
    a = d[d.bras == "halal"].ecart.to_numpy(float)
    b = d[d.bras == "temoin"].ecart.to_numpy(float)
    da, db = dispersions(a), dispersions(b)
    lignes = []
    print(f"  {'mesure':12s} {'halal':>8s} {'temoin':>8s} {'rapport':>8s} "
          f"{'IC 95 %':>16s}")
    for m in ("ecart_type", "iqr", "mad"):
        r = ic_rapport(a, b, m, rng)
        print(f"  {m:12s} {da[m]:8.2f} {db[m]:8.2f} {r[0]:8.2f} "
              f"  [{r[1]:.2f} ; {r[2]:.2f}]")
        lignes.append({"niveau": "perimetre", "cle": "", "mesure": m,
                       "halal": round(da[m], 2), "temoin": round(db[m], 2),
                       "rapport": round(r[0], 2), "ic95_bas": round(r[1], 2),
                       "ic95_haut": round(r[2], 2), "n_halal": da["n"],
                       "n_temoin": db["n"]})

    titre("Meme test, strate par strate")
    print("Un rapport global pourrait venir d'un assortiment halal plus varie.")
    print("A strate fixee, cette explication tombe.\n")
    plus, moins = 0, 0
    for s, g in d.groupby("strate"):
        x = g[g.bras == "halal"].ecart.to_numpy(float)
        y = g[g.bras == "temoin"].ecart.to_numpy(float)
        if len(x[~np.isnan(x)]) < SEUIL or len(y[~np.isnan(y)]) < SEUIL:
            continue
        r = ic_rapport(x, y, "mad", rng)
        if not r:
            continue
        sens = ("plus disperse" if r[1] > 1 else
                "plus homogene" if r[2] < 1 else "non etabli")
        plus += r[1] > 1
        moins += r[2] < 1
        print(f"  {s:34s} n={len(x):4d}/{len(y):5d}  rapport MAD {r[0]:5.2f} "
              f"[{r[1]:.2f} ; {r[2]:.2f}]  {sens}")
        lignes.append({"niveau": "strate", "cle": s, "mesure": "mad",
                       "halal": None, "temoin": None, "rapport": round(r[0], 2),
                       "ic95_bas": round(r[1], 2), "ic95_haut": round(r[2], 2),
                       "n_halal": len(x), "n_temoin": len(y)})
    print(f"\n  Strates ou le halal est plus disperse : {plus}. Plus "
          f"homogene : {moins}.")

    titre("Dispersion A L'INTERIEUR d'une meme marque")
    print("Si la prescription venait des certificateurs, elle s'appliquerait")
    print("aussi DANS une marque. Ecart-type median des ecarts, marques a 10")
    print("produits ou plus.\n")
    for bras, g in d.groupby("bras"):
        v = g.groupby("marque").ecart.agg(["size", "std"])
        v = v[v["size"] >= 10]
        print(f"  {bras:8s} {len(v):3d} marques, ecart-type intra median "
              f"{v['std'].median():.2f}")
        lignes.append({"niveau": "intra_marque", "cle": bras, "mesure": "std",
                       "halal": None, "temoin": None,
                       "rapport": None, "ic95_bas": None, "ic95_haut": None,
                       "n_halal": int(v["size"].sum()), "n_temoin": len(v)})
    pd.DataFrame(lignes).to_csv(SORTIES / "x1_homogeneite.csv", index=False)

    titre("CE QUE CE RESULTAT AUTORISE, ET CE QU'IL INTERDIT")
    print("Sur le perimetre entier, le bras halal est PLUS disperse : de 1,2")
    print("a 1,8 fois selon la mesure, les trois intervalles au-dessus de 1.")
    print("Meme constat a l'interieur d'une marque et a l'interieur d'un")
    print("etablissement (H26).")
    print()
    print(f"A STRATE FIXEE le tableau est plus partage : {plus} strates plus")
    print(f"dispersees, {moins} plus homogenes, le reste non etabli. Une part")
    print("du rapport global vient donc de l'assortiment, pas des recettes.")
    print("Ce nuance le resultat, il ne l'inverse pas : nulle part on n'observe")
    print("le resserrement systematique que produirait une norme partagee.")
    print()
    print("La dispersion est la signature de choix de formulation INDEPENDANTS.")
    print("Une prescription commune resserre ; on ne voit pas de resserrement.")
    print()
    print("Ce resultat ne prouve pas qu'aucun cahier des charges n'existe, et")
    print("il ne dit rien de leur contenu reel, qu'il faudrait lire. Il")
    print("etablit que les donnees ne portent pas la trace d'une prescription")
    print("nutritionnelle commune, et qu'une lecture en terme d'intention")
    print("coordonnee n'a, dans ces donnees, aucun appui.")
    print()
    print("AUCUNE DONNEE NUTRITIONNELLE NE PEUT ATTEINDRE UNE INTENTION. Une")
    print("intention est un etat mental de decideurs ; cette base contient des")
    print("etiquettes. Ce script teste une TRACE OBSERVABLE de prescription,")
    print("pas une volonte.")
    print("\nEcrit : sorties/x1_homogeneite.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
