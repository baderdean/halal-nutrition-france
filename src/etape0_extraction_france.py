#!/usr/bin/env python3
"""Etape 0 — materialisation du sous-ensemble France du dump.

Une seule lecture du dump complet (~12 Go decompresses). Filtre unique :
`en:france` dans countries_tags. Ce filtre n'est pas un choix d'analyse,
il est fixe par les specs de l'etude.

Sortie : data/france.parquet. Toutes les etapes suivantes lisent ce fichier,
jamais le dump. Le perimetre carne, lui, est applique ensuite a partir de
config/perimetre.yaml (liste figee, issue des categories observees).
"""

from __future__ import annotations

import json
import sys
import time

from commun import (DONNEES, SORTIES, charger, connexion, echec, liste,
                    sha256, titre)

FRANCE = DONNEES / "france.parquet"

# Colonnes racine conservees. Tout ce qui sert aux couches 1 a 3.
COLONNES_TEXTE = [
    "code", "product_name", "generic_name", "quantity", "serving_size",
    "brands", "brands_tags", "brand_owner", "categories_tags", "labels_tags",
    "countries_tags", "ingredients_text", "ingredients_tags",
    "ingredients_analysis_tags", "additives_tags", "states_tags",
    "nutrient_levels_tags", "pnns_groups_1", "pnns_groups_2",
    "main_category", "nutriscore_grade", "image_url",
    "image_ingredients_url", "image_nutrition_url", "no_nutrition_data",
]
COLONNES_NUM = [
    ("additives_n", "additives_n"),
    ("nutriscore_score", "nutriscore_score"),
    ("nova_group", "nova_group"),
    ("completeness", "completeness"),
    ("last_modified_t", "last_modified_t"),
    ("unique_scans_n", "unique_scans_n"),
    ("product_quantity", "product_quantity"),
]
NUTRIMENTS = [
    "energy-kj", "energy-kcal", "fat", "saturated-fat", "trans-fat",
    "carbohydrates", "sugars", "fiber", "proteins", "salt", "sodium",
    "fruits-vegetables-legumes", "collagen-meat-protein-ratio",
]

# Colonnes a decouper en listes de tags.
TAGS = [
    "categories_tags", "labels_tags", "countries_tags", "ingredients_tags",
    "ingredients_analysis_tags", "additives_tags", "brands_tags",
    "states_tags", "nutrient_levels_tags",
]


def main() -> None:
    src = charger("source.yaml")
    dump = DONNEES / src["fichier_local"]
    if not dump.exists():
        echec(f"dump absent : {dump}. Lance d'abord `make source`.")

    titre("ETAPE 0 — extraction du sous-ensemble France")
    print(f"  dump      : {dump}")
    print(f"  taille    : {dump.stat().st_size} octets")
    attendu = src.get("taille_octets")
    if attendu and dump.stat().st_size != attendu:
        echec(
            f"taille du dump inattendue ({dump.stat().st_size} != {attendu}). "
            "Le dump a change : mets a jour config/source.yaml par une issue, "
            "ne modifie pas la requete."
        )

    print("  sha256    : calcul en cours...", flush=True)
    h = sha256(dump)
    print(f"              {h}")
    if src.get("sha256") and src["sha256"] != h:
        echec("sha256 du dump different de config/source.yaml.")

    con = connexion()
    lecture = (
        f"read_csv('{dump}', delim='\\t', header=true, quote='', escape='', "
        "all_varchar=true, strict_mode=false, null_padding=true, "
        "ignore_errors=false, parallel=true)"
    )

    select = []
    for c in COLONNES_TEXTE:
        if c in TAGS:
            select.append(f'{liste(chr(34) + c + chr(34))} AS {c}')
        else:
            select.append(f'nullif("{c}", \'\') AS {c.replace("-", "_")}')
    for src_col, alias in COLONNES_NUM:
        select.append(f'TRY_CAST("{src_col}" AS DOUBLE) AS {alias}')
    for n in NUTRIMENTS:
        select.append(
            f'TRY_CAST("{n}_100g" AS DOUBLE) AS {n.replace("-", "_")}_100g'
        )

    sql = f"""
    COPY (
      SELECT {', '.join(select)}
      FROM {lecture}
      WHERE countries_tags IS NOT NULL
        AND list_contains(
              list_transform(string_split(countries_tags, ','), x -> trim(x)),
              'en:france')
    ) TO '{FRANCE}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """
    t0 = time.time()
    print("  lecture du dump (une passe, plusieurs minutes)...", flush=True)
    con.execute(sql)
    n = con.execute(f"SELECT count(*) FROM '{FRANCE}'").fetchone()[0]
    print(f"  {n} produits France ecrits en {time.time() - t0:.0f}s")
    print(f"  -> {FRANCE} ({FRANCE.stat().st_size / 1e6:.0f} Mo)")

    if n < 100_000:
        echec(
            f"seulement {n} produits France. Le filtre pays ou le parsing du "
            "dump est casse. Echec bruyant plutot que perimetre tronque."
        )

    SORTIES.mkdir(exist_ok=True)
    with open(SORTIES / "source_figee.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "url": src["url"],
                "date_dump": src["date_dump"],
                "taille_octets": dump.stat().st_size,
                "sha256": h,
                "n_produits_france": n,
            },
            f, indent=2, ensure_ascii=False,
        )


if __name__ == "__main__":
    sys.exit(main())
