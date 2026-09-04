#!/usr/bin/env python3
"""Etape 1b — application du perimetre fige.

Lit data/france.parquet, applique config/perimetre.yaml, ecrit
data/perimetre_carne_fr.parquet. Aucun filtre en dur ici : tout vient du YAML.
"""

from __future__ import annotations

import sys

from commun import DONNEES, PERIMETRE, charger, connexion, echec, titre

FRANCE = DONNEES / "france.parquet"


def sql_liste(tags) -> str:
    return "[" + ", ".join(f"'{t}'" for t in tags) + "]"


def clause_perimetre(p: dict) -> str:
    """Predicat d'appartenance au perimetre, integralement issu du YAML."""
    cond = [f"len(list_intersect(categories_tags, {sql_liste(p['racines'])})) > 0"]
    if p.get("exclusions_categories"):
        cond.append(
            f"len(list_intersect(categories_tags, "
            f"{sql_liste(p['exclusions_categories'])})) = 0"
        )
    if p.get("exclusions_labels"):
        cond.append(
            f"len(list_intersect(labels_tags, "
            f"{sql_liste(p['exclusions_labels'])})) = 0"
        )
    if p.get("exclusion_mer"):
        m, v = p["exclusion_mer"]["motif_mer"], p["exclusion_mer"]["motif_viande"]
        # Sort si le produit porte une categorie PRODUIT de la mer et aucune
        # categorie PRODUIT carnee. Une categorie qui matche les deux motifs
        # est une categorie parente et ne compte pour aucun des deux.
        cond.append(
            f"NOT (len(list_filter(categories_tags, x -> regexp_matches(x, "
            f"'{m}') AND NOT regexp_matches(x, '{v}'))) > 0 "
            f"AND len(list_filter(categories_tags, x -> regexp_matches(x, "
            f"'{v}') AND NOT regexp_matches(x, '{m}'))) = 0)"
        )
    return " AND ".join(cond)


def expr_sous_categorie(p: dict) -> str:
    """Affectation ordonnee, premier match gagnant. Exactement une par produit."""
    morceaux = ["CASE"]
    residuel = None
    for sc in p["sous_categories"]:
        if not sc["tags"]:
            residuel = sc["nom"]
            continue
        morceaux.append(
            f"WHEN len(list_intersect(categories_tags, {sql_liste(sc['tags'])})) > 0 "
            f"THEN '{sc['nom']}'"
        )
    if residuel is None:
        echec("config/perimetre.yaml : aucune sous-categorie residuelle (tags: []).")
    morceaux.append(f"ELSE '{residuel}' END")
    return " ".join(morceaux)


def main() -> None:
    if not FRANCE.exists():
        echec(f"{FRANCE} absent. Lance d'abord etape0_extraction_france.py.")
    p = charger("perimetre.yaml")
    con = connexion()

    titre("ETAPE 1b — application du perimetre fige")
    sql = f"""
    COPY (
      SELECT *,
             {expr_sous_categorie(p)} AS sous_categorie,
             list_contains(labels_tags, '{p['tag_traitement']}') AS tag_halal,
             CASE WHEN list_contains(labels_tags, '{p['tag_traitement']}')
                  THEN 'halal' ELSE 'temoin' END AS bras,
             list_filter(labels_tags, x -> x LIKE '%halal%') AS tags_halal_bruts
      FROM '{FRANCE}'
      WHERE {clause_perimetre(p)}
      -- L'export plat OFF contient de rares doublons de code-barres (deux
      -- revisions du meme produit). On garde la revision la plus recente.
      -- Deduplication DECLAREE, comptee ci-dessous, pas un filtre silencieux.
      QUALIFY row_number() OVER (
        PARTITION BY code ORDER BY last_modified_t DESC NULLS LAST) = 1
    ) TO '{PERIMETRE}' (FORMAT PARQUET, COMPRESSION ZSTD);
    """
    n_brut = con.execute(f"""
        SELECT count(*) FROM '{FRANCE}' WHERE {clause_perimetre(p)}
    """).fetchone()[0]
    con.execute(sql)
    n, h, t = con.execute(f"""
        SELECT count(*), sum(CASE WHEN tag_halal THEN 1 ELSE 0 END),
               sum(CASE WHEN NOT tag_halal THEN 1 ELSE 0 END)
        FROM '{PERIMETRE}'
    """).fetchone()
    print(f"  lignes brutes du perimetre : {n_brut}")
    print(f"  doublons de code retires   : {n_brut - n}")
    print(f"  perimetre : {n} produits  |  halal {h}  |  temoin {t}")
    print(f"  -> {PERIMETRE}")
    if n == 0:
        echec("perimetre vide. Ne pas elargir le filtre : corriger la config.")


if __name__ == "__main__":
    sys.exit(main())
