#!/usr/bin/env python3
"""Etape 1a — amorce : quelles categories carnees existent reellement.

Sortie destinee a l'humain qui fige `config/perimetre.yaml`. Les graines de
`config/graines.yaml` servent uniquement a amorcer la decouverte ; c'est la
liste observee ici, et elle seule, qui doit etre figee.

Ne produit aucun resultat d'etude.
"""

from __future__ import annotations

import sys

from commun import DONNEES, charger, connexion, echec, titre

FRANCE = DONNEES / "france.parquet"


def main() -> None:
    if not FRANCE.exists():
        echec(f"{FRANCE} absent. Lance d'abord etape0_extraction_france.py.")
    g = charger("graines.yaml")
    con = connexion()
    f = f"'{FRANCE}'"
    graines = ", ".join(f"'{c}'" for c in g["graines_categories"])

    titre("A1 — volumetrie brute France")
    print(con.execute(f"""
        SELECT count(*) AS n_france,
               sum(CASE WHEN list_contains(labels_tags,'en:halal')
                        THEN 1 ELSE 0 END) AS n_tag_halal,
               sum(CASE WHEN len(list_filter(labels_tags, x -> x LIKE '%halal%'))>0
                        THEN 1 ELSE 0 END) AS n_label_halal_large
        FROM {f}
    """).df().to_string(index=False))

    titre("A2 — categories les plus frequentes chez les produits tagues halal")
    print("Base de la liste figee. 80 lignes, a trier a la main.\n")
    print(con.execute(f"""
        SELECT cat, count(*) AS n,
               sum(CASE WHEN energy_kcal_100g IS NOT NULL
                         AND saturated_fat_100g IS NOT NULL
                         AND sugars_100g IS NOT NULL
                         AND salt_100g IS NOT NULL
                         AND proteins_100g IS NOT NULL THEN 1 ELSE 0 END) AS n_complet
        FROM (SELECT unnest(categories_tags) AS cat, * FROM {f}
              WHERE list_contains(labels_tags,'en:halal'))
        GROUP BY cat ORDER BY n DESC LIMIT 80
    """).df().to_string(index=False))

    titre("A3 — categories atteintes par les graines, hors halal")
    print("Sert a reperer les categories carnees absentes de A2.\n")
    print(con.execute(f"""
        SELECT cat, count(*) AS n
        FROM (SELECT unnest(categories_tags) AS cat FROM {f}
              WHERE len(list_intersect(categories_tags, [{graines}])) > 0
                AND NOT list_contains(labels_tags,'en:halal'))
        GROUP BY cat HAVING n >= 50 ORDER BY n DESC LIMIT 120
    """).df().to_string(index=False))

    titre("A4 — labels contenant 'halal' (variantes et certificateurs)")
    print(con.execute(f"""
        SELECT tag, count(*) AS n
        FROM (SELECT unnest(labels_tags) AS tag FROM {f})
        WHERE tag LIKE '%halal%'
        GROUP BY tag ORDER BY n DESC LIMIT 40
    """).df().to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
