#!/usr/bin/env python3
"""Couche 4 — les labels sont-ils des indicateurs de qualite nutritionnelle ?

Meme methode que le classement des marques, meme precaution : un label porte
sur des types de produits particuliers. Le Label Rouge est surtout sur de la
volaille, l'AOP surtout sur de la charcuterie seche. Comparer leurs porteurs
au rayon entier ne dirait rien.

Chaque produit est donc compare a la mediane de MARCHE de sa strate
sous-categorie x espece, puis on agrege par label. L'ecart mesure ce que les
produits portant ce label font de mieux ou de pire que le marche SUR LE MEME
TYPE DE PRODUIT.

Un produit porte plusieurs labels : les lignes ne s'additionnent pas, et
l'ecart d'un label est contamine par les labels qui l'accompagnent souvent.
Un label frequemment associe au bio heritera d'une partie de l'effet bio.
C'est une limite de methode, pas un detail : ce tableau classe des
ASSOCIATIONS, pas des effets causaux.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, connexion, titre
from etape4_marques import GRAINE, N_BOOT, N_SOLIDE, ic_mediane

N_MIN = 30          # un label sous 30 produits n'est pas classe
VARIABLES = [("nutriscore_score", "Nutri-Score en score continu", 1),
             ("sel", "sel pour 100 g", 1),
             ("proteines", "proteines pour 100 g", -1)]


def main() -> int:
    con = connexion()
    rng = np.random.default_rng(GRAINE)
    d = con.execute(f"""
        SELECT bras, sous_categorie, espece, labels_tags,
               {borne('salt_100g', 'sel')},
               {borne('proteins_100g', 'proteines')},
               nutriscore_score
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    d["strate"] = d.sous_categorie + " / " + d.espece
    tailles = d.groupby("strate").size()
    d = d[d.strate.isin(tailles[tailles >= N_SOLIDE].index)].copy()
    for var, _, _ in VARIABLES:
        d["ecart_" + var] = d[var] - d.groupby("strate")[var].transform("median")

    # Un produit porte plusieurs labels : on eclate, les lignes ne s'ajoutent pas.
    long = d.explode("labels_tags").rename(columns={"labels_tags": "label"})
    long = long[long.label.notna() & (long.label != "")]

    titre("Les labels sont-ils des indicateurs de qualite ?")
    print("Ecart a la mediane de marche de la strate sous-categorie x espece.")
    print("Negatif = mieux que le marche sur le meme type de produit.")
    print(f"Labels portes par moins de {N_MIN} produits non classes.\n")
    print("Un produit porte plusieurs labels : les lignes ne s'additionnent")
    print("pas, et l'ecart d'un label est contamine par ceux qui l'accompagnent.")
    print("Ce tableau classe des ASSOCIATIONS, pas des effets causaux.\n")

    for var, libelle, sens in VARIABLES:
        lignes = []
        for label, g in long.groupby("label"):
            v = g["ecart_" + var].dropna().to_numpy()
            if len(v) < N_MIN:
                continue
            ic = ic_mediane(v, rng)
            if ic is None:
                continue
            lignes.append({
                "label": label, "n": len(v),
                "ecart_median": round(sens * ic[0], 3),
                "ic95_bas": round(min(sens * ic[1], sens * ic[2]), 3),
                "ic95_haut": round(max(sens * ic[1], sens * ic[2]), 3),
                "strates": g.strate.nunique(),
                "pct_halal": round(100.0 * (g.bras == "halal").mean(), 1),
            })
        t = pd.DataFrame(lignes).sort_values("ecart_median")
        if not len(t):
            continue
        # Un intervalle qui contient zero ne distingue pas le label du marche.
        t["distingue_du_marche"] = np.where(
            (t.ic95_bas > 0) | (t.ic95_haut < 0), "oui", "non")
        print(f"  --- {libelle}  ({len(t)} labels classes)")
        print("  15 meilleurs :")
        print(t.head(15).to_string(index=False))
        print("\n  15 pires :")
        print(t.tail(15).to_string(index=False))
        n_nul = (t.distingue_du_marche == "non").sum()
        print(f"\n  {n_nul} labels sur {len(t)} ne se distinguent pas du marche "
              "(IC contenant zero).\n")
        t.to_csv(SORTIES / f"l_labels_{var}.csv", index=False)

    titre("Les labels qui nous interessent, cote a cote")
    cibles = ["en:halal", "en:kosher", "en:organic", "fr:ab-agriculture-biologique",
              "fr:label-rouge", "en:made-in-france", "fr:origine-france",
              "en:pdo", "en:pgi", "fr:igp", "en:nutriscore",
              "fr:elu-produit-de-l-annee", "en:no-preservatives",
              "en:no-artificial-flavors", "fr:saveurs-de-l-annee"]
    for var, libelle, sens in VARIABLES:
        f = SORTIES / f"l_labels_{var}.csv"
        if not f.exists():
            continue
        t = pd.read_csv(f)
        sel = t[t.label.isin(cibles)]
        if len(sel):
            print(f"  --- {libelle}")
            print(sel.to_string(index=False))
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
