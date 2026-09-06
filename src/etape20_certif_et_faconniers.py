#!/usr/bin/env python3
"""Couche 20 — deux comparaisons que le rayon suggere et que personne n'a faites.

  1. Un produit CERTIFIE est-il mieux compose qu'un produit halal sans
     certificateur identifie ?
  2. Un faconnier EXCLUSIVEMENT halal fait-il moins bien, sur son halal, qu'un
     faconnier generaliste ?

Les deux comparaisons portent sur l'ecart a la mediane de marche de la strate
(sous-categorie x espece), et leurs IC sont calcules par bootstrap de
grappes : sur les MARQUES pour la premiere, sur les SITES pour la seconde.
Grouper par produit supposerait que deux references d'une meme marque, ou
deux produits d'une meme usine, sont deux observations independantes.

UN PIEGE PROPRE A LA PREMIERE QUESTION, ET IL EST DECISIF. « Sans
certificateur » ne veut pas dire « non certifie ». Open Food Facts enregistre
ce qu'un contributeur a saisi : un produit sans tag d'organisme peut porter
un certificateur parfaitement lisible sur son emballage. La couche 2, qui a
lu des emballages en image, a trouve 26 organismes distincts la ou les tags
de la base n'en identifient que 13. Le groupe « sans certificateur » est donc
un melange de produits reellement non certifies et de produits dont le
certificateur n'a pas ete saisi, dans une proportion inconnue.

Cela ne casse pas la mesure, cela casse son INTERPRETATION CAUSALE : un ecart
nul entre les deux groupes est compatible avec « la certification ne change
rien » comme avec « les deux groupes contiennent les memes produits ».
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, charger, connexion, \
    titre

GRAINE = 20260904
TIRAGES = 4000
SEUIL = 30
SEUIL_SITE = 5        # produits halal pour qu'un site entre dans la comparaison
PART_EXCLUSIF = 90.0  # % de la production du site qui est halal
PART_GENERALISTE = 50.0


def boot(a: list, b: list, rng) -> tuple:
    out = np.empty(TIRAGES)
    for i in range(TIRAGES):
        ia = rng.integers(0, len(a), len(a))
        ib = rng.integers(0, len(b), len(b))
        out[i] = (np.median(np.concatenate([a[j] for j in ia]))
                  - np.median(np.concatenate([b[j] for j in ib])))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def grappes(g: pd.DataFrame, cle: str, col: str) -> list:
    """Un paquet par groupe ; une ligne sans groupe fait son propre paquet."""
    # Cles TRIEES, et valeurs triees dans chaque paquet. Sans cela l'ordre
    # vient de DuckDB, qui ne preserve pas l'ordre d'insertion : les paquets
    # changent d'ordre d'une execution a l'autre et le bootstrap tire une
    # suite differente. Le resultat bougeait a la deuxieme decimale.
    p = [np.sort(g[g[cle] == k][col].to_numpy(float))
         for k in sorted(g[cle].dropna().unique())]
    p += [np.array([v]) for v in np.sort(g[g[cle].isna()][col].to_numpy(float))]
    return p


def dire(nom, a, b, col, unite, cle, rng):
    a2, b2 = a[a[col].notna()], b[b[col].notna()]
    lo, hi = boot(grappes(a2, cle, col), grappes(b2, cle, col), rng)
    pt = float(a2[col].median()) - float(b2[col].median())
    etabli = lo > 0 or hi < 0
    print(f"  {nom:38s} {pt:+6.2f} [{lo:+.2f} ; {hi:+.2f}] {unite:6s} "
          f"{'ETABLI' if etabli else 'NON ETABLI'}")
    return {"comparaison": nom, "mesure": col, "difference": round(pt, 2),
            "ic95_bas": round(lo, 2), "ic95_haut": round(hi, 2),
            "unite": unite, "etabli": bool(etabli),
            "n_groupes_a": len(grappes(a2, cle, col)),
            "n_groupes_b": len(grappes(b2, cle, col))}


def main() -> int:
    rng = np.random.default_rng(GRAINE)
    cfg = charger("certificateurs.yaml")
    tags = sorted({t for c in cfg["certificateurs"] for t in c["tags"]})
    con = connexion()

    strates = con.execute(f"""
        SELECT sous_categorie || ' / ' || espece AS strate,
               median(nutriscore_score) AS med_ns, median({borne('salt_100g')})
                 AS med_sel, count(*) AS n
        FROM '{PERIMETRE}' WHERE ({COMPLET}) AND nutriscore_score IS NOT NULL
        GROUP BY 1
    """).df()
    strates = strates[strates.n >= SEUIL]

    lst = "','".join(tags)
    d = con.execute(f"""
        SELECT code, sous_categorie, espece, tag_halal, emb_codes_tags,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               nutriscore_score AS ns, {borne('salt_100g', 'sel')},
               len(list_filter(labels_tags, x -> x IN ('{lst}'))) > 0
                 AS certifie
        FROM '{PERIMETRE}' WHERE ({COMPLET}) AND nutriscore_score IS NOT NULL
    """).df()
    d["strate"] = d.sous_categorie + " / " + d.espece
    d = d.merge(strates[["strate", "med_ns", "med_sel"]], on="strate")
    d["ecart"] = d.ns - d.med_ns
    d["ecart_sel"] = d.sel - d.med_sel

    # --- 1. Certifie contre non certifie, dans le bras halal.
    titre("1. Un produit certifie est-il mieux compose ?")
    h = d[d.tag_halal]
    t1 = h.groupby("certifie").agg(
        produits=("ecart", "size"), marques=("marque", "nunique"),
        ecart_median=("ecart", "median"), sel_median=("sel", "median")).round(2)
    t1.index = ["sans certificateur identifie", "avec certificateur identifie"]
    print(t1.to_string())
    print()
    lignes = [dire("certifie - non certifie", h[h.certifie], h[~h.certifie],
                   c, u, "marque", rng)
              for c, u in (("ecart", "pts"), ("ecart_sel", "g"))]
    print("\n  « SANS CERTIFICATEUR » NE VEUT PAS DIRE « NON CERTIFIE ». Open")
    print("  Food Facts enregistre ce qu'un contributeur a saisi. La couche 2,")
    print("  qui a lu des emballages en image, a trouve 26 organismes")
    print("  distincts la ou les tags de la base n'en identifient que 13 : le")
    print("  groupe « sans certificateur » melange des produits non certifies")
    print("  et des produits dont l'organisme n'a pas ete saisi, dans une")
    print("  proportion inconnue. Un ecart nul est donc compatible avec « la")
    print("  certification ne change rien » COMME avec « les deux groupes")
    print("  contiennent les memes produits ».")
    t1.to_csv(SORTIES / "k1_certifie_vs_non.csv")

    # --- 2. Faconnier exclusif halal contre faconnier generaliste.
    titre("2. Les faconniers exclusivement halal font-ils moins bien ?")
    e = d.explode("emb_codes_tags").rename(columns={"emb_codes_tags": "et"})
    e = e[e.et.notna()].copy()
    e["et"] = e.et.astype(str).str.replace(r"-(ec|ue|ce)$", "", regex=True)
    prof = e.groupby("et").agg(n_tot=("ecart", "size"),
                               n_hal=("tag_halal", "sum"))
    prof["part_halal"] = 100 * prof.n_hal / prof.n_tot
    hh = e[e.tag_halal].merge(prof, on="et")
    hh = hh[hh.n_hal >= SEUIL_SITE].copy()
    hh["profil"] = np.where(hh.part_halal >= PART_EXCLUSIF, "exclusif halal",
                            np.where(hh.part_halal <= PART_GENERALISTE,
                                     "generaliste", "mixte"))
    print(f"Sites d'au moins {SEUIL_SITE} produits halal. Un site est dit")
    print(f"EXCLUSIF au-dela de {PART_EXCLUSIF:.0f} % de production halal, "
          f"GENERALISTE\nen dessous de {PART_GENERALISTE:.0f} %. Entre les "
          "deux : mixte, publie mais pas teste.\n")
    t2 = hh.groupby("profil").agg(
        produits=("ecart", "size"), sites=("et", "nunique"),
        marques=("marque", "nunique"), ecart_median=("ecart", "median"),
        sel_median=("sel", "median")).round(2)
    print(t2.to_string())
    print()
    A = hh[hh.profil == "exclusif halal"]
    B = hh[hh.profil == "generaliste"]
    lignes += [dire("exclusif halal - generaliste", A, B, c, u, "et", rng)
               for c, u in (("ecart", "pts"), ("ecart_sel", "g"))]
    print("\n  Les points estimes vont dans le sens de la question, les")
    print(f"  intervalles ne l'etablissent pas : {A.et.nunique()} sites contre "
          f"{B.et.nunique()}, c'est la\n  precision reelle disponible. Et les "
          "sites MIXTES sont au-dessus des\n  deux autres, ce qu'une "
          "explication par l'exclusivite ne predit pas.")
    print("\n  CONFONDANT ASSUME. Un site exclusivement halal appartient")
    print("  presque toujours a un specialiste, un site generaliste a un")
    print("  industriel. Comparer les deux revient en partie a comparer des")
    print("  entreprises differentes, ce que H31 a deja mesure separement.")
    t2.to_csv(SORTIES / "k2_faconniers_profil.csv")
    pd.DataFrame(lignes).to_csv(SORTIES / "k3_differences.csv", index=False)

    print("\nEcrit : sorties/k1_certifie_vs_non.csv, k2_faconniers_profil.csv,")
    print("        k3_differences.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
