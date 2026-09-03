#!/usr/bin/env python3
"""
POC — Etape 0 de l'etude "qualite nutritionnelle des produits carnes halal
industriels en France".

Ce script ne produit AUCUN resultat d'etude. Il produit une decision de
faisabilite : quelles strates ont assez d'effectifs, quelles variables
discriminent, quel est le taux de sous-etiquetage du tag halal.

Source : dump Open Food Facts au format Parquet, publie sous Open Database
License (contenus sous Database Contents License).
  https://huggingface.co/datasets/openfoodfacts/product-database
Fichier : food.parquet (~2.8 Go)

Dependances :
  pip install duckdb pandas pyarrow

Usage :
  python poc_etape0_halal.py schema      # etape 0a : inspecter le schema
  python poc_etape0_halal.py extraire    # etape 0b : materialiser le perimetre
  python poc_etape0_halal.py compter     # etape 0c : sortir les comptages

L'etape 'extraire' peut prendre plusieurs minutes en lecture distante.
Si le reseau est lent, telecharge food.parquet une fois et pointe SOURCE
sur le chemin local.
"""

import sys
import textwrap

import duckdb

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

SOURCE = (
    "https://huggingface.co/datasets/openfoodfacts/product-database"
    "/resolve/main/food.parquet"
)
# Alternative locale, plus rapide si tu relances souvent :
# SOURCE = "./food.parquet"

PERIMETRE = "./perimetre_carne_fr.parquet"

# Graines de recherche. Elles servent a AMORCER la decouverte, pas a definir
# le perimetre final. Le script imprime ensuite les tags reellement presents,
# c'est cette liste empirique qui doit etre figee dans le pre-enregistrement.
GRAINES_CATEGORIES = [
    "en:meats",
    "en:meat-based-products",
    "en:prepared-meats",
    "en:poultry",
    "en:sausages",
    "en:nuggets",
    "en:cordons-bleus",
    "en:hams",
    "en:meals",
]

# Tag parent halal dans la taxonomie OFF. Les certificateurs sont des tags
# ENFANTS ; on ne les code pas en dur, on les decouvre (voir compter()).
TAG_HALAL = "en:halal"

# Nutriments a extraire depuis la colonne imbriquee `nutriments`.
NUTRIMENTS = [
    "energy-kcal",
    "fat",
    "saturated-fat",
    "carbohydrates",
    "sugars",
    "fiber",
    "proteins",
    "salt",
    "sodium",
]

# Colonnes souhaitees au niveau racine. Le script ne garde que celles qui
# existent reellement dans le dump (le schema bouge d'une version a l'autre).
COLONNES_SOUHAITEES = [
    "code",
    "product_name",
    "brands",
    "brands_tags",
    "categories_tags",
    "labels_tags",
    "countries_tags",
    "ingredients_text",
    "ingredients_tags",
    "additives_n",
    "additives_tags",
    "nova_group",
    "nutriscore_grade",
    "nutriscore_score",
    "nutriscore",          # struct 2021/2023 selon version
    "nutriments",
    "quantity",
    "completeness",
    "last_modified_t",
    "images",
]


def connexion():
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("SET enable_progress_bar = true;")
    return con


def titre(txt):
    print("\n" + "=" * 78)
    print(txt)
    print("=" * 78)


# --------------------------------------------------------------------------
# Etape 0a — schema
# --------------------------------------------------------------------------

def schema():
    """Imprime le schema du dump.

    A LIRE AVANT TOUT. Trois points a verifier a la main :
      1. le nom exact de la colonne Nutri-Score 2023 (elle a change de place
         entre versions : parfois `nutriscore` struct, parfois colonnes plates)
      2. la structure de `nutriments` (liste de structs : quels champs ?)
      3. la structure de `product_name` (liste {lang, text} ou chaine simple ?)
    Le reste du script suppose une liste de structs pour `nutriments` avec un
    champ `name` et un champ "100g". Corrige NUTRI_EXPR si ce n'est pas le cas.
    """
    con = connexion()
    titre("SCHEMA DU DUMP")
    df = con.execute(f"DESCRIBE SELECT * FROM '{SOURCE}'").df()
    for _, r in df.iterrows():
        print(f"  {r['column_name']:<38} {r['column_type']}")

    titre("ECHANTILLON : 1 produit halal francais, colonnes cles")
    try:
        ech = con.execute(f"""
            SELECT code, brands, labels_tags, categories_tags, nutriments
            FROM '{SOURCE}'
            WHERE list_contains(countries_tags, 'en:france')
              AND list_contains(labels_tags, '{TAG_HALAL}')
            LIMIT 1
        """).df()
        for col in ech.columns:
            print(f"\n--- {col} ---")
            print(textwrap.shorten(str(ech[col].iloc[0]), 1200))
    except Exception as e:
        print(f"  Echec : {e}")
        print("  -> adapte les noms de colonnes d'apres le DESCRIBE ci-dessus.")


# --------------------------------------------------------------------------
# Etape 0b — extraction du perimetre
# --------------------------------------------------------------------------

def expr_nutriments():
    """Extraction des nutriments depuis la colonne imbriquee.

    Suppose : nutriments = LIST(STRUCT(name VARCHAR, "100g" DOUBLE, ...)).
    L'indexation [1] d'une liste vide renvoie NULL en DuckDB, donc pas besoin
    de garde. Verifie avec `schema` avant de faire confiance a cette expression.
    """
    out = []
    for n in NUTRIMENTS:
        alias = n.replace("-", "_") + "_100g"
        out.append(
            f"""(list_filter(nutriments, x -> x.name = '{n}'))[1]."100g" AS {alias}"""
        )
    return ",\n        ".join(out)


def extraire():
    con = connexion()

    dispo = set(
        con.execute(f"DESCRIBE SELECT * FROM '{SOURCE}'").df()["column_name"]
    )
    gardees = [c for c in COLONNES_SOUHAITEES if c in dispo]
    manquantes = [c for c in COLONNES_SOUHAITEES if c not in dispo]
    if manquantes:
        print(f"[avertissement] colonnes absentes du dump : {manquantes}")

    cats = ", ".join(f"'{c}'" for c in GRAINES_CATEGORIES)
    cols = ", ".join(gardees)

    # Filtre large volontairement : mieux vaut ratisser puis affiner sur la
    # base des tags reellement observes que de figer un perimetre a l'aveugle.
    sql = f"""
    COPY (
      SELECT
        {cols},
        {expr_nutriments()},
        list_contains(labels_tags, '{TAG_HALAL}') AS tag_halal,
        list_filter(labels_tags, x -> x LIKE '%halal%') AS tags_halal_bruts
      FROM '{SOURCE}'
      WHERE list_contains(countries_tags, 'en:france')
        AND (
             len(list_intersect(categories_tags, [{cats}])) > 0
          OR list_contains(labels_tags, '{TAG_HALAL}')
        )
    ) TO '{PERIMETRE}' (FORMAT PARQUET);
    """
    titre("EXTRACTION DU PERIMETRE (France x carne, filtre large)")
    con.execute(sql)
    n = con.execute(f"SELECT count(*) FROM '{PERIMETRE}'").fetchone()[0]
    print(f"  {n} produits ecrits dans {PERIMETRE}")


# --------------------------------------------------------------------------
# Etape 0c — comptages de decision
# --------------------------------------------------------------------------

COMPLET = (
    "energy_kcal_100g IS NOT NULL AND saturated_fat_100g IS NOT NULL "
    "AND sugars_100g IS NOT NULL AND salt_100g IS NOT NULL "
    "AND proteins_100g IS NOT NULL"
)


def compter():
    con = connexion()
    p = f"'{PERIMETRE}'"

    # --- D1 : quelles categories existent vraiment cote halal ? -------------
    titre("D1 — Categories les plus frequentes parmi les produits tagues halal")
    print("Fige le perimetre final sur cette liste, pas sur les graines.\n")
    print(con.execute(f"""
        SELECT cat, count(*) AS n
        FROM (SELECT unnest(categories_tags) AS cat FROM {p} WHERE tag_halal)
        GROUP BY cat ORDER BY n DESC LIMIT 40
    """).df().to_string(index=False))

    # --- D2 : effectifs exploitables --------------------------------------
    titre("D2 — Effectifs par categorie x statut x completude nutritionnelle")
    print("REGLE : sous 30 produits complets dans une cellule, la strate sort")
    print("du plan d'analyse principal.\n")
    print(con.execute(f"""
        SELECT cat,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END)            AS halal,
               sum(CASE WHEN tag_halal AND complet THEN 1 ELSE 0 END) AS halal_complet,
               sum(CASE WHEN NOT tag_halal THEN 1 ELSE 0 END)         AS temoin,
               sum(CASE WHEN NOT tag_halal AND complet THEN 1 ELSE 0 END) AS temoin_complet
        FROM (
          SELECT unnest(categories_tags) AS cat, tag_halal, ({COMPLET}) AS complet
          FROM {p}
        )
        GROUP BY cat
        HAVING halal_complet >= 10
        ORDER BY halal_complet DESC LIMIT 30
    """).df().to_string(index=False))

    # --- D3 : saturation du Nutri-Score ------------------------------------
    titre("D3 — Distribution du Nutri-Score par statut")
    print("Si D et E ecrasent tout dans les deux groupes, la lettre ne")
    print("discrimine rien : bascule la couche editoriale sur sel et % viande.\n")
    print(con.execute(f"""
        SELECT nutriscore_grade,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) AS halal,
               sum(CASE WHEN NOT tag_halal THEN 1 ELSE 0 END) AS temoin
        FROM {p} WHERE nutriscore_grade IS NOT NULL
        GROUP BY nutriscore_grade ORDER BY nutriscore_grade
    """).df().to_string(index=False))

    titre("D3bis — Dispersion INTRA-halal (l'analyse actionnable)")
    print("Compare l'ecart-type et l'etendue interne a l'ecart moyen entre")
    print("groupes. Si la dispersion interne domine, c'est ton titre.\n")
    print(con.execute(f"""
        SELECT cat,
               count(*) AS n,
               round(median(salt_100g), 2)   AS sel_median,
               round(quantile_cont(salt_100g, 0.10), 2) AS sel_p10,
               round(quantile_cont(salt_100g, 0.90), 2) AS sel_p90,
               round(median(saturated_fat_100g), 2) AS ags_median
        FROM (
          SELECT unnest(categories_tags) AS cat, salt_100g, saturated_fat_100g
          FROM {p} WHERE tag_halal AND salt_100g IS NOT NULL
        )
        GROUP BY cat HAVING n >= 15 ORDER BY n DESC LIMIT 20
    """).df().to_string(index=False))

    # --- D4 : sous-etiquetage du tag halal ---------------------------------
    titre("D4 — Taux de tag halal par marque (mesure des faux negatifs)")
    print("Une marque halal specialisee affichant 40% de tag te donne ton taux")
    print("de faux negatifs dans le temoin. Audite ces marques sur photo.\n")
    print(con.execute(f"""
        SELECT brands,
               count(*) AS n_produits,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) AS n_tagues,
               round(100.0 * sum(CASE WHEN tag_halal THEN 1 ELSE 0 END)
                     / count(*), 1) AS pct_tague
        FROM {p} WHERE brands IS NOT NULL AND brands <> ''
        GROUP BY brands
        HAVING sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) >= 3
        ORDER BY n_produits DESC LIMIT 40
    """).df().to_string(index=False))

    # --- D5 : le certificateur est-il une variable ou un alias de marque ? --
    titre("D5 — Certificateurs : effectifs ET nombre de marques distinctes")
    print("Si chaque certificateur ne couvre qu'une ou deux marques, l'effet")
    print("certificateur n'est pas separable de l'effet marque. Abandonne")
    print("cette question et dis-le dans l'annexe.\n")
    print(con.execute(f"""
        SELECT tag AS certificateur,
               count(*) AS n_produits,
               count(DISTINCT brands) AS n_marques
        FROM (SELECT unnest(tags_halal_bruts) AS tag, brands FROM {p})
        WHERE tag <> '{TAG_HALAL}'
        GROUP BY tag ORDER BY n_produits DESC
    """).df().to_string(index=False))

    # --- D6 : additifs, la ou se joue le bloc Yuka -------------------------
    titre("D6 — Additifs les plus frequents (perimetre de la grille a relever)")
    print("Cette liste borne le travail de relevé manuel de la classification")
    print("Yuka. Si elle tient en 40 codes E, le recalcul est faisable.\n")
    print(con.execute(f"""
        SELECT add AS additif,
               count(*) AS n,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) AS dont_halal
        FROM (SELECT unnest(additives_tags) AS add, tag_halal FROM {p})
        GROUP BY add ORDER BY n DESC LIMIT 40
    """).df().to_string(index=False))

    titre("D7 — NOVA par statut (la variable qui porte la these transformation)")
    print(con.execute(f"""
        SELECT nova_group,
               sum(CASE WHEN tag_halal THEN 1 ELSE 0 END) AS halal,
               sum(CASE WHEN NOT tag_halal THEN 1 ELSE 0 END) AS temoin
        FROM {p} WHERE nova_group IS NOT NULL
        GROUP BY nova_group ORDER BY nova_group
    """).df().to_string(index=False))


# --------------------------------------------------------------------------

if __name__ == "__main__":
    etapes = {"schema": schema, "extraire": extraire, "compter": compter}
    if len(sys.argv) < 2 or sys.argv[1] not in etapes:
        print(__doc__)
        sys.exit(1)
    etapes[sys.argv[1]]()
