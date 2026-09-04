#!/usr/bin/env python3
"""Questions ouvertes apres la couche 1, toutes DESCRIPTIVES.

Q1  Les produits halal portant un label de production francais VISIBLE
    different-ils des autres produits halal ?
Q2  Le kasher, contrefactuel a contrainte rituelle comparable, se compare
    comment au halal et au temoin generique ?
Q3  Le foie gras, strate a halalite disputee : que contient-elle.

Aucune de ces trois questions n'est causale. Elles se heurtent au meme
confondant que la couche 1 : la marque et le degre de transformation. Elles
sont decrites, jamais testees, tant que l'appariement de la couche 3 n'a pas
eu lieu.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, charger, connexion, titre

SEUIL = 30
GRAINE = 20260904
N_BOOT = 4000


def liste_sql(tags):
    return "[" + ", ".join(f"'{t}'" for t in tags) + "]"


def ic_diff_medianes(a, b, rng):
    a = np.asarray(a, float); b = np.asarray(b, float)
    a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
    if len(a) < 10 or len(b) < 10:
        return None
    d = np.empty(N_BOOT)
    for i in range(N_BOOT):
        d[i] = (np.median(rng.choice(a, len(a), True))
                - np.median(rng.choice(b, len(b), True)))
    return (float(np.median(a) - np.median(b)),
            float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))


def decrire(df, groupe, valeur, rng, reference):
    """Mediane, quartiles et IC de la difference contre le groupe reference."""
    lignes = []
    ref = df.loc[df[groupe] == reference, valeur].dropna().to_numpy()
    for g, sous in df.groupby(groupe):
        v = sous[valeur].dropna().to_numpy()
        if not len(v):
            continue
        ic = None if g == reference else ic_diff_medianes(v, ref, rng)
        lignes.append({
            groupe: g, "n": len(v),
            "median": round(float(np.median(v)), 2),
            "q1": round(float(np.percentile(v, 25)), 2),
            "q3": round(float(np.percentile(v, 75)), 2),
            "diff_vs_" + reference: round(ic[0], 3) if ic else None,
            "ic95_bas": round(ic[1], 3) if ic else None,
            "ic95_haut": round(ic[2], 3) if ic else None,
            "regle_30": "franchie" if len(v) >= SEUIL else "NON franchie",
        })
    return pd.DataFrame(lignes).sort_values("n", ascending=False)


def main() -> int:
    q = charger("questions.yaml")
    con = connexion()
    rng = np.random.default_rng(GRAINE)
    p = f"'{PERIMETRE}'"
    fr = liste_sql(q["labels_production_france"])
    ks = liste_sql(q["labels_kasher"])

    con.execute(f"""
        CREATE VIEW v AS
        SELECT *,
          len(list_intersect(labels_tags, {fr})) > 0 AS france_visible,
          len(list_intersect(labels_tags, {ks})) > 0 AS kasher,
          CASE WHEN salt_100g BETWEEN 0 AND 100 THEN salt_100g END AS sel,
          CASE WHEN saturated_fat_100g BETWEEN 0 AND 100
               THEN saturated_fat_100g END AS ags,
          ({COMPLET}) AS complet
        FROM {p}
    """)

    # ------------------------------------------------------------------ Q1
    titre("Q1 — label de production francais VISIBLE, au sein du bras halal")
    print("Variable : le label que le client voit en rayon, pas l'origine des")
    print("ingredients ni le code d'emballage sanitaire.\n")
    d = con.execute("""
        SELECT CASE WHEN france_visible THEN 'halal_france_visible'
                    ELSE 'halal_sans_label_france' END AS groupe,
               sel, ags, nutriscore_score, nutriscore_grade, sous_categorie
        FROM v WHERE tag_halal AND complet
    """).df()
    print(f"  {len(d)} produits halal a donnees completes")
    print(d.groupe.value_counts().to_string())
    for var in ("sel", "ags"):
        t = decrire(d, "groupe", var, rng, "halal_sans_label_france")
        print(f"\n  --- {var} pour 100 g")
        print(t.to_string(index=False))
        t.to_csv(SORTIES / f"q1_france_visible_{var}.csv", index=False)

    # ------------------------------------------------------------------ Q2
    titre("Q2 — kasher, halal, temoin generique")
    print("Le kasher subit une contrainte d'abattage rituel comparable. C'est")
    print("un contrefactuel plus proche que le temoin generique.\n")
    n_deux = con.execute(
        "SELECT count(*) FROM v WHERE tag_halal AND kasher").fetchone()[0]
    print(f"  [declaration] {n_deux} produits portent les DEUX labels. Ils sont")
    print("  ecartes : ils n'appartiennent a aucun des trois bras.\n")
    d = con.execute("""
        SELECT CASE WHEN tag_halal THEN 'halal' WHEN kasher THEN 'kasher'
                    ELSE 'temoin' END AS bras3,
               sel, ags, nutriscore_score, sous_categorie
        FROM v WHERE complet AND NOT (tag_halal AND kasher)
    """).df()
    print(d.bras3.value_counts().to_string())
    for var in ("sel", "ags", "nutriscore_score"):
        t = decrire(d, "bras3", var, rng, "temoin")
        print(f"\n  --- {var}")
        print(t.to_string(index=False))
        t.to_csv(SORTIES / f"q2_kasher_{var}.csv", index=False)

    print("\n  --- effectifs kasher par sous-categorie (regle des 30)")
    e = (d[d.bras3 == "kasher"].groupby("sous_categorie").size()
         .rename("n").reset_index())
    e["regle_30"] = np.where(e.n >= SEUIL, "franchie", "NON franchie")
    print(e.sort_values("n", ascending=False).to_string(index=False))
    e.to_csv(SORTIES / "q2_kasher_effectifs.csv", index=False)

    titre("Q2bis — le kasher tient-il A SOUS-CATEGORIE EGALE ?")
    print("Un ecart global peut n'etre qu'un effet de composition. Cette table")
    print("le teste : si l'ecart disparait a sous-categorie egale, il venait du")
    print("panier de produits, pas du label.\n")
    med = d.pivot_table(index="sous_categorie", columns="bras3",
                        values="nutriscore_score", aggfunc="median")
    eff = d.pivot_table(index="sous_categorie", columns="bras3",
                        values="nutriscore_score", aggfunc="count")
    strat = med.round(1).join(eff, rsuffix="_n")
    print(strat.to_string())
    strat.to_csv(SORTIES / "q2bis_kasher_par_strate.csv")
    print("\n  Nutri-Score en SCORE continu : plus bas vaut mieux.")
    print("  Ne lire que les strates ou l'effectif kasher franchit la regle")
    print(f"  des {SEUIL}.")

    titre("Composition des trois bras, en % de chaque bras")
    print("Un ecart global se lit d'abord ici : deux bras qui n'ont pas le meme")
    print("panier de produits ne sont pas comparables sans appariement.\n")
    comp = (pd.crosstab(d.sous_categorie, d.bras3, normalize="columns")
            .mul(100).round(1))
    print(comp.to_string())
    comp.to_csv(SORTIES / "q2ter_composition_bras.csv")

    # ------------------------------------------------------------------ Q3
    titre("Q3 — foie gras, strate a halalite disputee")
    d3 = con.execute("""
        SELECT bras, count(*) n,
               sum(CASE WHEN complet THEN 1 ELSE 0 END) complet,
               round(median(sel), 2) sel_median, round(median(ags), 2) ags_median
        FROM v WHERE sous_categorie = 'foie_gras' GROUP BY 1
    """).df()
    print(d3.to_string(index=False))
    d3.to_csv(SORTIES / "q3_foie_gras.csv", index=False)
    print("\n  Cette strate ne portera aucune comparaison halal / temoin :")
    print("  le bras halal y est trop mince. Elle est decrite, pas testee.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
