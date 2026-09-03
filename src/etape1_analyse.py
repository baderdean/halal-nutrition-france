#!/usr/bin/env python3
"""Etape 1d — comptages de faisabilite et comparaison brute.

Produit les CSV versionnes de sorties/ et sorties/chiffres_cles.json.
Aucune redaction ici : le rapport est assemble par etape1_rapport.py.

Comparaison de couche 1 : deux variables seulement, sel pour 100 g et
Nutri-Score en grade. Aucun ajustement, aucun appariement (specs).
"""

from __future__ import annotations

import json
import sys

import numpy as np

from commun import (COMPLET, PERIMETRE, SORTIES, charger, connexion, echec,
                    titre)

BORNES = {
    "salt_100g": 100.0, "saturated_fat_100g": 100.0, "fat_100g": 100.0,
    "sugars_100g": 100.0, "proteins_100g": 100.0, "carbohydrates_100g": 100.0,
    "energy_kcal_100g": 900.0,
}
SEUIL_REGLE_30 = 30
GRAINE_BOOTSTRAP = 20260903
N_BOOTSTRAP = 4000


def vue(con) -> None:
    """Vue d'analyse : valeurs hors bornes physiques mises a NULL, lignes gardees.

    AGENTS.md : les lignes fautives sortent des statistiques nutritionnelles,
    jamais du denombrement du perimetre.
    """
    bornees = ", ".join(
        f"CASE WHEN {c} BETWEEN 0 AND {v} THEN {c} END AS {c}"
        for c, v in BORNES.items()
    )
    autres = [
        "code", "product_name", "brands", "brands_tags", "categories_tags",
        "labels_tags", "additives_tags", "additives_n", "nova_group",
        "nutriscore_grade", "nutriscore_score", "sous_categorie", "bras",
        "tag_halal", "tags_halal_bruts", "fiber_100g", "sodium_100g",
        "completeness", "image_url", "image_ingredients_url",
        "image_nutrition_url",
    ]
    con.execute(f"""
        CREATE VIEW p AS
        SELECT {', '.join(autres)}, {bornees},
               ({COMPLET}) AS complet
        FROM (SELECT *, {', '.join(f'{c} AS {c}_src' for c in BORNES)}
              FROM '{PERIMETRE}')
    """)


def ecrire(df, nom: str) -> None:
    chemin = SORTIES / nom
    df.to_csv(chemin, index=False)
    print(f"  -> {chemin.name}  ({len(df)} lignes)")


def bootstrap_diff_medianes(a, b, rng):
    """IC 95 % percentile sur la difference de medianes (halal - temoin)."""
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
    if len(a) < 10 or len(b) < 10:
        return None
    d = np.empty(N_BOOTSTRAP)
    for i in range(N_BOOTSTRAP):
        d[i] = (np.median(rng.choice(a, len(a), replace=True))
                - np.median(rng.choice(b, len(b), replace=True)))
    return float(np.median(a) - np.median(b)), float(np.percentile(d, 2.5)), \
        float(np.percentile(d, 97.5))


def main() -> int:
    SORTIES.mkdir(exist_ok=True)
    con = connexion()
    vue(con)
    p = charger("perimetre.yaml")
    libelles = {sc["nom"]: sc["libelle"] for sc in p["sous_categories"]}
    cles = {}

    # ---------------------------------------------------------------- D0
    titre("D0 — volumetrie du perimetre")
    d0 = con.execute("""
        SELECT count(*) AS n_perimetre,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) AS n_halal,
               sum(CASE WHEN NOT tag_halal THEN 1 ELSE 0 END) AS n_temoin,
               sum(CASE WHEN complet THEN 1 ELSE 0 END) AS n_complet,
               sum(CASE WHEN tag_halal AND complet THEN 1 ELSE 0 END)
                   AS n_halal_complet,
               sum(CASE WHEN NOT tag_halal AND complet THEN 1 ELSE 0 END)
                   AS n_temoin_complet
        FROM p
    """).df()
    print(d0.to_string(index=False))
    cles["volumetrie"] = d0.iloc[0].astype("int64").to_dict()
    ecrire(d0, "d0_volumetrie.csv")

    # ---------------------------------------------------------------- D1
    titre("D1 — categories OFF les plus frequentes cote halal (descriptif)")
    print("Un produit porte plusieurs categories : les lignes ne s'additionnent pas.\n")
    d1 = con.execute("""
        SELECT cat AS categorie_off, count(*) AS n_halal
        FROM (SELECT unnest(categories_tags) AS cat FROM p WHERE tag_halal)
        GROUP BY cat ORDER BY n_halal DESC LIMIT 50
    """).df()
    print(d1.head(20).to_string(index=False))
    ecrire(d1, "d1_categories_halal.csv")

    # ---------------------------------------------------------------- D2
    titre("D2 — effectifs par sous-categorie x bras x completude")
    print(f"Regle des {SEUIL_REGLE_30} : une strate sous ce seuil de produits")
    print("complets sort de l'analyse principale.\n")
    d2 = con.execute(f"""
        SELECT sous_categorie,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) AS halal,
               sum(CASE WHEN tag_halal AND complet THEN 1 ELSE 0 END)
                   AS halal_complet,
               sum(CASE WHEN NOT tag_halal THEN 1 ELSE 0 END) AS temoin,
               sum(CASE WHEN NOT tag_halal AND complet THEN 1 ELSE 0 END)
                   AS temoin_complet
        FROM p GROUP BY sous_categorie ORDER BY halal_complet DESC
    """).df()
    d2["regle_30"] = np.where(
        (d2.halal_complet >= SEUIL_REGLE_30) & (d2.temoin_complet >= SEUIL_REGLE_30),
        "franchie", "NON franchie")
    d2["libelle"] = d2.sous_categorie.map(libelles)
    print(d2.to_string(index=False))
    ecrire(d2, "d2_effectifs_strates.csv")
    cles["strates_retenues"] = d2.loc[d2.regle_30 == "franchie",
                                      "sous_categorie"].tolist()
    cles["strates_ecartees"] = d2.loc[d2.regle_30 != "franchie",
                                      "sous_categorie"].tolist()

    # ---------------------------------------------------------------- D3
    titre("D3 — distribution du Nutri-Score par bras")
    d3 = con.execute("""
        SELECT upper(nutriscore_grade) AS grade,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) AS halal,
               sum(CASE WHEN NOT tag_halal THEN 1 ELSE 0 END) AS temoin
        FROM p WHERE nutriscore_grade IS NOT NULL
          AND upper(nutriscore_grade) IN ('A','B','C','D','E')
        GROUP BY 1 ORDER BY 1
    """).df()
    for c in ("halal", "temoin"):
        d3[f"pct_{c}"] = (100.0 * d3[c] / d3[c].sum()).round(1)
    print(d3.to_string(index=False))
    ecrire(d3, "d3_nutriscore_par_bras.csv")
    de = d3[d3.grade.isin(["D", "E"])]
    cles["nutriscore"] = {
        "n_note_halal": int(d3.halal.sum()),
        "n_note_temoin": int(d3.temoin.sum()),
        "pct_DE_halal": round(float(de.pct_halal.sum()), 1),
        "pct_DE_temoin": round(float(de.pct_temoin.sum()), 1),
    }
    cles["nutriscore"]["sature"] = (
        cles["nutriscore"]["pct_DE_halal"] > 80.0
        and cles["nutriscore"]["pct_DE_temoin"] > 80.0
    )

    titre("D3bis — dispersion INTRA-halal du sel, par sous-categorie")
    d3b = con.execute(f"""
        SELECT sous_categorie, count(*) AS n,
               round(median(salt_100g), 2) AS sel_median,
               round(quantile_cont(salt_100g, 0.10), 2) AS sel_p10,
               round(quantile_cont(salt_100g, 0.90), 2) AS sel_p90,
               round(quantile_cont(salt_100g, 0.90)
                     - quantile_cont(salt_100g, 0.10), 2) AS ecart_interdecile,
               round(median(saturated_fat_100g), 2) AS ags_median
        FROM p WHERE tag_halal AND salt_100g IS NOT NULL
        GROUP BY 1 HAVING n >= {SEUIL_REGLE_30} ORDER BY n DESC
    """).df()
    print(d3b.to_string(index=False))
    ecrire(d3b, "d3bis_dispersion_intra_halal.csv")

    # ---------------------------------------------------------------- D4
    titre("D4 — taux de tag halal par marque (mesure des faux negatifs)")
    # Cle marque : premier tag normalise par OFF, prefixe de langue retire
    # (OFF emet tantot 'carrefour', tantot 'xx:carrefour'). `brands` en clair
    # contient des variantes d'accent et de casse qui eclatent une meme marque.
    # Ce regroupement reste mecanique : la table marque -> statut construite a
    # la main est un livrable de couche 2.
    d4 = con.execute("""
        SELECT regexp_replace(brands_tags[1], '^[a-z]{2}:', '') AS marque_tag, any_value(brands) AS marque_affichee,
               count(*) AS n_produits,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) AS n_tagues,
               round(100.0 * sum(CASE WHEN tag_halal THEN 1 ELSE 0 END)
                     / count(*), 1) AS pct_tague
        FROM p WHERE brands_tags IS NOT NULL AND len(brands_tags) > 0
        GROUP BY 1 HAVING sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) >= 5
        ORDER BY n_produits DESC LIMIT 60
    """).df()
    print(d4.head(25).to_string(index=False))
    ecrire(d4, "d4_taux_tag_par_marque.csv")
    # Borne BASSE des faux negatifs : marques dont la gamme carnee est
    # manifestement halal (>= 80 % de produits tagues) mais dont quelques
    # references ne portent pas le tag. Ces references sont dans le temoin.
    # Borne basse seulement : les marques generalistes a gamme halal partielle
    # (Carrefour, Fleury Michon) ne sont pas identifiables ainsi. Le taux reel
    # se mesure sur photo d'emballage, couche 2.
    spec = d4[(d4.pct_tague >= 80) & (d4.pct_tague < 100)]
    n_specialistes = int((d4.pct_tague >= 80).sum())
    n_faux_neg = int((spec.n_produits - spec.n_tagues).sum()) if len(spec) else 0
    n_prod_spec = int(d4.loc[d4.pct_tague >= 80, "n_produits"].sum())
    cles["sous_etiquetage"] = {
        "n_marques_examinees": int(len(d4)),
        "n_marques_specialistes_halal": n_specialistes,
        "n_produits_chez_specialistes": n_prod_spec,
        "faux_negatifs_borne_basse": n_faux_neg,
        "taux_faux_negatifs_borne_basse_pct":
            round(100.0 * n_faux_neg / n_prod_spec, 2) if n_prod_spec else None,
    }

    # ---------------------------------------------------------------- D5
    titre("D5 — certificateurs : effectifs et marques distinctes")
    d5 = con.execute(f"""
        SELECT tag AS certificateur, count(*) AS n_produits,
               count(DISTINCT brands) AS n_marques
        FROM (SELECT unnest(tags_halal_bruts) AS tag, brands FROM p)
        WHERE tag <> '{p['tag_traitement']}'
        GROUP BY tag ORDER BY n_produits DESC
    """).df()
    print(d5.to_string(index=False))
    ecrire(d5, "d5_certificateurs.csv")
    n_halal = int(cles["volumetrie"]["n_halal"])
    couverts = int(con.execute(f"""
        SELECT count(*) FROM p
        WHERE tag_halal AND len(list_filter(tags_halal_bruts,
              x -> x <> '{p['tag_traitement']}')) > 0
    """).fetchone()[0])
    cles["certificateurs"] = {
        "n_certificateurs_distincts": int(len(d5)),
        "n_produits_halal_avec_certificateur": couverts,
        "pct_halal_avec_certificateur": round(100.0 * couverts / n_halal, 1),
        "n_certificateurs_au_dela_de_2_marques":
            int((d5.n_marques > 2).sum()) if len(d5) else 0,
        "n_certificateurs_30_produits":
            int((d5.n_produits >= SEUIL_REGLE_30).sum()) if len(d5) else 0,
    }
    # Verdict. La couverture prime : un certificateur renseigne sur 7 % des
    # produits halal n'est pas une variable, quelle que soit sa separabilite.
    # Attention : plusieurs tags designent le meme organisme sous des
    # orthographes differentes (variantes fr:/en: de la SFCVH). Le regroupement
    # manuel des variantes est un travail de couche 2 ; ici on compte les tags
    # bruts, ce qui SURESTIME le nombre d'organismes distincts.
    cov = cles["certificateurs"]["pct_halal_avec_certificateur"]
    if cov < 50.0:
        verdict = "inexploitable_couverture"
    elif cles["certificateurs"]["n_certificateurs_30_produits"] >= 2 and \
            cles["certificateurs"]["n_certificateurs_au_dela_de_2_marques"] >= 2:
        verdict = "potentiellement_separable"
    else:
        verdict = "inseparable_de_la_marque"
    cles["certificateurs"]["verdict"] = verdict

    # ---------------------------------------------------------------- D6
    titre("D6 — additifs les plus frequents (bornage de la grille Yuka)")
    d6 = con.execute("""
        SELECT add AS additif, count(*) AS n,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) AS dont_halal
        FROM (SELECT unnest(additives_tags) AS add, tag_halal FROM p)
        GROUP BY add ORDER BY n DESC
    """).df()
    print(d6.head(25).to_string(index=False))
    ecrire(d6, "d6_additifs.csv")
    cles["additifs"] = {
        "n_codes_distincts": int(len(d6)),
        "n_codes_couvrant_99pct": int(
            (d6.n.cumsum() / d6.n.sum() <= 0.99).sum() + 1) if len(d6) else 0,
    }

    # ---------------------------------------------------------------- D7
    titre("D7 — NOVA par bras")
    d7 = con.execute("""
        SELECT CAST(nova_group AS INT) AS nova,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) AS halal,
               sum(CASE WHEN NOT tag_halal THEN 1 ELSE 0 END) AS temoin
        FROM p WHERE nova_group IS NOT NULL GROUP BY 1 ORDER BY 1
    """).df()
    for c in ("halal", "temoin"):
        d7[f"pct_{c}"] = (100.0 * d7[c] / d7[c].sum()).round(1)
    print(d7.to_string(index=False))
    ecrire(d7, "d7_nova.csv")
    cles["nova4"] = {
        "pct_halal": float(d7.loc[d7.nova == 4, "pct_halal"].sum()),
        "pct_temoin": float(d7.loc[d7.nova == 4, "pct_temoin"].sum()),
        "n_note_halal": int(d7.halal.sum()), "n_note_temoin": int(d7.temoin.sum()),
    }

    # ---------------------------------------------------------------- D8
    titre("D8 — couverture photo (voie de recuperation du certificateur)")
    print("Le certificateur est imprime sur l'emballage. Si la photo existe,")
    print("la question du certificateur n'est pas close par la seule absence")
    print("de tag : elle est renvoyee a la lecture d'image, couche 2.\n")
    d8 = con.execute("""
        SELECT bras, count(*) AS n,
               round(100.0 * sum(CASE WHEN image_url IS NOT NULL
                                      THEN 1 ELSE 0 END) / count(*), 1)
                   AS pct_photo_face,
               round(100.0 * sum(CASE WHEN image_ingredients_url IS NOT NULL
                                      THEN 1 ELSE 0 END) / count(*), 1)
                   AS pct_photo_ingredients,
               round(100.0 * sum(CASE WHEN image_url IS NOT NULL
                                       OR image_ingredients_url IS NOT NULL
                                       OR image_nutrition_url IS NOT NULL
                                      THEN 1 ELSE 0 END) / count(*), 1)
                   AS pct_au_moins_une
        FROM p GROUP BY 1 ORDER BY 1
    """).df()
    print(d8.to_string(index=False))
    ecrire(d8, "d8_couverture_image.csv")
    cles["couverture_image"] = d8.set_index("bras").to_dict(orient="index")

    # ------------------------------------------------------- comparaison C1
    titre("C1 — comparaison brute du sel pour 100 g, halal vs temoin")
    print("Aucun ajustement, aucun appariement. Strates sous la regle des 30")
    print("sont affichees mais marquees non testables.\n")
    rng = np.random.default_rng(GRAINE_BOOTSTRAP)
    sel = con.execute("""
        SELECT sous_categorie, bras, salt_100g
        FROM p WHERE salt_100g IS NOT NULL AND complet
    """).df()

    lignes = []
    for sc in list(d2.sous_categorie) + ["_ensemble_"]:
        sous = sel if sc == "_ensemble_" else sel[sel.sous_categorie == sc]
        a = sous.loc[sous.bras == "halal", "salt_100g"].to_numpy()
        b = sous.loc[sous.bras == "temoin", "salt_100g"].to_numpy()
        if len(a) == 0 or len(b) == 0:
            continue
        ic = bootstrap_diff_medianes(a, b, rng)
        lignes.append({
            "sous_categorie": sc,
            "n_halal": len(a), "n_temoin": len(b),
            "sel_median_halal": round(float(np.median(a)), 2),
            "sel_q1_halal": round(float(np.percentile(a, 25)), 2),
            "sel_q3_halal": round(float(np.percentile(a, 75)), 2),
            "sel_median_temoin": round(float(np.median(b)), 2),
            "sel_q1_temoin": round(float(np.percentile(b, 25)), 2),
            "sel_q3_temoin": round(float(np.percentile(b, 75)), 2),
            "diff_medianes": round(ic[0], 3) if ic else None,
            "ic95_bas": round(ic[1], 3) if ic else None,
            "ic95_haut": round(ic[2], 3) if ic else None,
            "testable_regle_30": bool(len(a) >= SEUIL_REGLE_30
                                      and len(b) >= SEUIL_REGLE_30),
        })
    import pandas as pd
    c1 = pd.DataFrame(lignes)
    print(c1.to_string(index=False))
    ecrire(c1, "c1_comparaison_sel.csv")
    ens = c1[c1.sous_categorie == "_ensemble_"].iloc[0].to_dict()
    cles["sel_ensemble"] = {k: (None if v is None or (isinstance(v, float)
                                and np.isnan(v)) else v)
                            for k, v in ens.items()}
    testables = c1[(c1.testable_regle_30) & (c1.sous_categorie != "_ensemble_")]
    cles["sel_strates"] = {
        "n_testables": int(len(testables)),
        "n_ic_excluant_zero": int(((testables.ic95_bas > 0)
                                   | (testables.ic95_haut < 0)).sum()),
        "n_halal_plus_sale": int((testables.diff_medianes > 0).sum()),
    }

    titre("C2 — Nutri-Score par sous-categorie et par bras")
    c2 = con.execute("""
        SELECT sous_categorie, bras, count(*) AS n_note,
               round(100.0 * sum(CASE WHEN upper(nutriscore_grade) IN ('D','E')
                                      THEN 1 ELSE 0 END) / count(*), 1) AS pct_DE,
               round(avg(nutriscore_score), 2) AS score_moyen,
               round(median(nutriscore_score), 1) AS score_median
        FROM p WHERE nutriscore_grade IS NOT NULL
          AND upper(nutriscore_grade) IN ('A','B','C','D','E')
        GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    print(c2.to_string(index=False))
    ecrire(c2, "c2_nutriscore_par_strate.csv")

    # Rapport dispersion interne / ecart entre bras. Chiffre le constat le plus
    # actionnable de la couche : ce qui separe deux produits halal entre eux
    # contre ce qui separe les deux bras.
    disp = d3b.set_index("sous_categorie")["ecart_interdecile"]
    comp = c1s = c1[c1.sous_categorie != "_ensemble_"].set_index("sous_categorie")
    ratios = (disp / comp["diff_medianes"].abs()).dropna()
    cles["dispersion_vs_ecart"] = {
        "n_strates": int(len(ratios)),
        "ratio_min": round(float(ratios.min()), 1),
        "ratio_max": round(float(ratios.max()), 1),
        "ratio_median": round(float(ratios.median()), 1),
        "n_strates_dispersion_dominante": int((ratios > 1).sum()),
        "par_strate": {k_: round(float(v_), 1) for k_, v_ in ratios.items()},
    }
    ecrire(ratios.rename("ratio_interdecile_sur_ecart").reset_index(),
           "c4_dispersion_vs_ecart.csv")

    titre("C3 — transformation (NOVA 4) par sous-categorie et par bras")
    print("Diagnostic de confusion : si le bras halal est plus transforme A")
    print("SOUS-CATEGORIE EGALE, l'ecart de sel suit la transformation autant")
    print("que le label. Question tranchee par l'appariement, couche 3.\n")
    c3 = con.execute("""
        SELECT sous_categorie, bras, count(*) AS n_nova,
               round(100.0 * sum(CASE WHEN nova_group = 4 THEN 1 ELSE 0 END)
                     / count(*), 1) AS pct_nova4
        FROM p WHERE nova_group IS NOT NULL GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    print(c3.to_string(index=False))
    ecrire(c3, "c3_transformation_par_strate.csv")
    pivot = c3.pivot(index="sous_categorie", columns="bras", values="pct_nova4")
    cles["transformation"] = {
        "n_strates_halal_plus_transforme":
            int((pivot["halal"] > pivot["temoin"]).sum()),
        "n_strates_comparees": int(len(pivot)),
        "ecart_median_points_nova4":
            round(float((pivot["halal"] - pivot["temoin"]).median()), 1),
    }

    with open(SORTIES / "chiffres_cles.json", "w", encoding="utf-8") as f:
        json.dump(cles, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  -> chiffres_cles.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
