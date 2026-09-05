#!/usr/bin/env python3
"""Couche 10 — l'estampille sanitaire, ou le fabricant enfin observable.

Toute cette etude bute sur le meme obstacle : ce qu'on mesure entre bras est
peut-etre le fabricant et non le label. Le controle du fabricant n'existait
jusqu'ici que dans UNE cellule (Fleury Michon, jambon de poulet).

L'estampille sanitaire ovale imprimee sur l'emballage identifie l'ETABLISSEMENT
agree, pas la marque. Une usine qui fabrique pour dix marques porte le meme
code sur les dix. C'est donc l'identifiant de fabricant que l'etude cherchait,
et il est VISIBLE PAR LE CONSOMMATEUR, ce que la marque de distributeur ne dit
jamais.

DEUX FORMATS, UN SEUL UTILISABLE.

  `fr-56-222-002-ec` et ses variantes etrangeres identifient un
  ETABLISSEMENT. 19 535 produits, 1 803 codes. Utilisable.

  `emb-56222` est l'ancien code d'emballage : il designe une COMMUNE, pas une
  usine. Plusieurs sites d'une meme commune s'y confondent. 6 832 produits,
  ecartes. Les fusionner avec les premiers attribuerait a un site la
  production d'un autre.

Ce que ce script produit nomme des SITES INDUSTRIELS REELS. Un site mal classe
le serait sur les recettes que ses donneurs d'ordre lui commandent, pas sur
son propre travail : un fabricant a facon execute un cahier des charges. Le
classement est donc accompagne, comme celui des certificateurs, d'un test de
retrait de la marque dominante.
"""

from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd

from commun import (COMPLET, PERIMETRE, SORTIES, borne, connexion, titre)
from etape5_produits_emblematiques import ic_diff

SEUIL = 30
SEUIL_DESC = 10      # publie mais jamais teste
GRAINE = 20260904

# Un identifiant d'ETABLISSEMENT se termine par le suffixe d'agrement et
# porte un numero de site. L'ancien `emb-ddddd` n'en a pas : c'est une commune.
MOTIF_ETABLISSEMENT = re.compile(r"^[a-z]{2}-.+-(ec|ue|ce)$")


def utilisable(code: str) -> bool:
    return bool(MOTIF_ETABLISSEMENT.match(code)) and not code.startswith("emb-")


def normaliser_etablissement(code: str) -> str:
    """Retire le suffixe d'agrement, qui n'identifie pas le site.

    `fr-14-752-020-ec` et `fr-14-752-020-ue` sont le MEME etablissement : EC
    et UE sont deux redactions de la meme mention d'agrement europeen, la
    seconde ayant remplace la premiere. Les garder distincts scinde un site
    en deux et divise ses effectifs.
    """
    return re.sub(r"-(ec|ue|ce)$", "", code)


def main() -> int:
    con = connexion()
    rng = np.random.default_rng(GRAINE)
    d = con.execute(f"""
        SELECT code, emb_codes_tags, sous_categorie, espece,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               nutriscore_score AS ns,
               {borne('salt_100g', 'sel')},
               {borne('proteins_100g', 'proteines')}
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()

    # ---- 0. Couverture, avant tout resultat.
    titre("0. COUVERTURE DE L'ESTAMPILLE — a lire avant le reste")
    d["a_code"] = d.emb_codes_tags.apply(
        lambda x: bool(x is not None and len(x)))
    cov = d.groupby("bras").agg(n=("ns", "size"), avec=("a_code", "mean"))
    cov["avec"] = (100 * cov.avec).round(1)
    print(cov.to_string())
    print("\n  L'estampille est un fait d'emballage, mais sa SAISIE dans Open")
    print("  Food Facts est facultative. Un produit sans code n'est pas un")
    print("  produit sans usine : c'est un produit dont personne n'a saisi le")
    print("  code. Tout ce qui suit porte sur la fraction saisie.")
    cov.to_csv(SORTIES / "w0_couverture_estampille.csv")

    e = (d.explode("emb_codes_tags")
           .rename(columns={"emb_codes_tags": "etablissement"}))
    e = e[e.etablissement.notna()]
    avant = e.etablissement.nunique()
    e = e[e.etablissement.apply(utilisable)]
    e["etablissement"] = e.etablissement.apply(normaliser_etablissement)
    print(f"\n  Codes distincts : {avant}, dont {e.etablissement.nunique()} "
          f"identifient un etablissement.")
    print(f"  Produits rattaches a un etablissement : {e.code.nunique()}.")

    # ---- 1. Les usines qui fabriquent pour plusieurs marques.
    titre("1. LES USINES MULTI-MARQUES")
    print("Un etablissement qui porte plusieurs marques fabrique a facon. La")
    print("marque affichee en rayon ne dit alors pas qui produit.\n")
    u = (e.groupby("etablissement")
          .agg(n_produits=("code", "nunique"),
               n_marques=("marque", "nunique"),
               n_halal=("bras", lambda x: int((x == "halal").sum())),
               n_temoin=("bras", lambda x: int((x == "temoin").sum())))
          .reset_index())
    u = u[u.n_produits >= SEUIL_DESC].sort_values("n_marques", ascending=False)
    print(u.head(20).to_string(index=False))
    u.to_csv(SORTIES / "w1_usines_multimarques.csv", index=False)
    mixtes = u[(u.n_halal >= SEUIL_DESC) & (u.n_temoin >= SEUIL_DESC)]
    print(f"\n  {len(u)} etablissements a {SEUIL_DESC} produits ou plus.")
    print(f"  {len(mixtes)} en fabriquent des deux bras, halal et temoin.")

    # ---- 2. Le controle du fabricant, a l'echelle.
    titre("2. HALAL CONTRE TEMOIN, DANS UN MEME ETABLISSEMENT")
    print("C'est le controle que l'etude cherchait : meme site, meme outil,")
    print("souvent le meme cahier des charges. Compare a gamme egale, faute de")
    print("quoi l'ecart mesurerait l'assortiment du site.\n")
    lignes = []
    for (et, sc), g in e.groupby(["etablissement", "sous_categorie"]):
        a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
        if len(a) < SEUIL_DESC or len(b) < SEUIL_DESC:
            continue
        r = ic_diff(a.ns.to_numpy(float), b.ns.to_numpy(float), rng)
        if not r:
            continue
        testable = len(a) >= SEUIL and len(b) >= SEUIL
        etabli = ("etabli" if testable and (r[1] > 0 or r[2] < 0)
                  else "non etabli" if testable else "sous 30, decrit")
        rs = ic_diff(a.sel.to_numpy(float), b.sel.to_numpy(float), rng)
        print(f"  {et:20s} {sc:22s} n={len(a):3d}/{len(b):3d}  "
              f"Nutri-Score {r[0]:+5.1f} [{r[1]:+.1f} ; {r[2]:+.1f}]  {etabli}"
              + (f"   sel {rs[0]:+.2f}" if rs else ""))
        lignes.append({"etablissement": et, "sous_categorie": sc,
                       "n_halal": len(a), "n_temoin": len(b),
                       "ecart_nutriscore": round(r[0], 1),
                       "ic95_bas": round(r[1], 1), "ic95_haut": round(r[2], 1),
                       "ecart_sel": round(rs[0], 2) if rs else None,
                       "testable": testable, "etabli": etabli == "etabli"})
    if not lignes:
        print("  Aucune cellule n'atteint le seuil des deux cotes.")
    pd.DataFrame(lignes).to_csv(SORTIES / "w2_intra_etablissement.csv",
                                index=False)

    # ---- 3. Bons et mauvais eleves, a composition egale.
    titre("3. LES ETABLISSEMENTS, A COMPOSITION EGALE")
    print("Ecart de chaque produit a la mediane de marche de sa strate")
    print("(sous-categorie x espece), agrege en mediane par etablissement. Un")
    print("classement brut opposerait un site de charcuterie seche a un")
    print("atelier de decoupe, ce qui ne dit rien de leur travail.\n")
    e["strate"] = e.sous_categorie + " / " + e.espece
    tailles = e.groupby("strate").size()
    ev = e[e.strate.isin(tailles[tailles >= SEUIL].index)].copy()
    ev["ecart"] = ev.ns - ev.groupby("strate").ns.transform("median")
    lignes3 = []
    for et, g in ev.groupby("etablissement"):
        if len(g) < SEUIL_DESC:
            continue
        med = float(g.ecart.median())
        if np.isnan(med):
            continue
        dom = g.marque.value_counts()
        part = 100.0 * dom.iloc[0] / len(g) if len(dom) else 100.0
        # Retrait de la marque dominante : un site dont 80 % de la production
        # est une seule marque est juge sur cette marque.
        sans = g[g.marque != dom.index[0]] if len(dom) > 1 else g.iloc[0:0]
        lignes3.append({
            "etablissement": et, "n": len(g),
            "n_marques": int(g.marque.nunique()),
            "n_halal": int((g.bras == "halal").sum()),
            "ecart_median": round(med, 1),
            "marque_dominante": dom.index[0] if len(dom) else None,
            "part_dominante_pct": round(part, 1),
            "ecart_sans_dominante": (round(float(sans.ecart.median()), 1)
                                     if len(sans) >= SEUIL_DESC else None),
            "n_sans_dominante": len(sans),
            "regle_30": "franchie" if len(g) >= SEUIL else "sous 30",
        })
    t3 = pd.DataFrame(lignes3).sort_values("ecart_median")
    print("  --- Les 12 meilleurs eleves")
    print(t3.head(12).to_string(index=False))
    print("\n  --- Les 12 mauvais eleves")
    print(t3.tail(12).to_string(index=False))
    t3.to_csv(SORTIES / "w3_classement_etablissements.csv", index=False)
    print(f"\n  {len(t3)} etablissements classes, dont "
          f"{int((t3.regle_30 == 'franchie').sum())} au-dessus de 30 produits.")
    print("  La colonne `ecart_sans_dominante` est le garde-fou : un site dont")
    print("  la production est concentree sur une marque est juge sur cette")
    print("  marque, pas sur son savoir-faire.")

    print("\nEcrit : sorties/w0_couverture_estampille.csv, "
          "w1_usines_multimarques.csv,\n        w2_intra_etablissement.csv, "
          "w3_classement_etablissements.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
