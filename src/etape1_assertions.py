#!/usr/bin/env python3
"""Etape 1c — assertions bloquantes.

AGENTS.md : ecart hors tolerance = arret, pas d'avertissement. Ce module
s'execute AVANT la production du rapport. S'il echoue, aucun chiffre ne sort.

`--figer` reecrit config/effectifs_attendus.yaml a partir du run courant.
A n'utiliser que quand un changement d'effectifs est volontaire et documente.
"""

from __future__ import annotations

import argparse
import sys

import yaml

from commun import (CONFIG, PERIMETRE, SORTIES, charger, connexion, echec,
                    titre)

# Bornes physiques. Au-dela, la valeur est une erreur de saisie, pas un aliment.
BORNES = {
    "salt_100g": 100.0,
    "saturated_fat_100g": 100.0,
    "fat_100g": 100.0,
    "sugars_100g": 100.0,
    "proteins_100g": 100.0,
    "carbohydrates_100g": 100.0,
    "energy_kcal_100g": 900.0,
}
CLAUSE_BORNES = " OR ".join(f"{c} > {v}" for c, v in BORNES.items()) + \
    " OR " + " OR ".join(f"{c} < 0" for c in BORNES)


def effectifs(con) -> dict:
    lignes = con.execute(f"""
        SELECT sous_categorie, bras, count(*) AS n
        FROM '{PERIMETRE}' GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchall()
    d = {}
    for sc, bras, n in lignes:
        d.setdefault(sc, {})[bras] = int(n)
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figer", action="store_true")
    args = ap.parse_args()

    con = connexion()
    titre("ETAPE 1c — assertions bloquantes")
    echecs = []

    # A1 — integrite de ligne
    n_total, n_sans_code, n_sans_sc, n_sans_bras, n_sans_cat = con.execute(f"""
        SELECT count(*),
               sum(CASE WHEN code IS NULL OR code='' THEN 1 ELSE 0 END),
               sum(CASE WHEN sous_categorie IS NULL THEN 1 ELSE 0 END),
               sum(CASE WHEN bras IS NULL THEN 1 ELSE 0 END),
               sum(CASE WHEN categories_tags IS NULL OR len(categories_tags)=0
                        THEN 1 ELSE 0 END)
        FROM '{PERIMETRE}'
    """).fetchone()
    print(f"  A1 lignes                       : {n_total}")
    for nom, v in [("sans code", n_sans_code), ("sans sous-categorie", n_sans_sc),
                   ("sans bras", n_sans_bras), ("sans categorie", n_sans_cat)]:
        if v:
            echecs.append(f"A1 : {v} lignes {nom}")
    print("  A1 code / categorie / statut    : OK" if not echecs else "  A1 : ECHEC")

    # A2 — somme des bras
    h, t = con.execute(f"""
        SELECT sum(CASE WHEN bras='halal' THEN 1 ELSE 0 END),
               sum(CASE WHEN bras='temoin' THEN 1 ELSE 0 END)
        FROM '{PERIMETRE}'
    """).fetchone()
    print(f"  A2 halal + temoin = total       : {h} + {t} = {h + t} / {n_total}")
    if h + t != n_total:
        echecs.append(f"A2 : {h} + {t} != {n_total}")

    # A3 — unicite du code produit
    n_dup = con.execute(f"""
        SELECT count(*) FROM (SELECT code FROM '{PERIMETRE}'
                              GROUP BY code HAVING count(*) > 1)
    """).fetchone()[0]
    print(f"  A3 codes dupliques              : {n_dup}")
    if n_dup:
        echecs.append(f"A3 : {n_dup} codes produits dupliques")

    # A4 — une et une seule sous-categorie par produit (verifie l'exclusivite)
    n_sc = con.execute(
        f"SELECT count(DISTINCT sous_categorie) FROM '{PERIMETRE}'").fetchone()[0]
    attendu_sc = len(charger("perimetre.yaml")["sous_categories"])
    print(f"  A4 sous-categories peuplees     : {n_sc} / {attendu_sc} declarees")
    if n_sc > attendu_sc:
        echecs.append("A4 : sous-categorie inconnue dans le jeu final")

    # A5 — valeurs hors bornes physiques (comptees, pas supprimees)
    n_aberrant = con.execute(
        f"SELECT count(*) FROM '{PERIMETRE}' WHERE {CLAUSE_BORNES}").fetchone()[0]
    pct = 100.0 * n_aberrant / n_total if n_total else 0.0
    print(f"  A5 valeurs hors bornes physiques: {n_aberrant} ({pct:.2f} %)")
    if pct > 1.0:
        echecs.append(
            f"A5 : {pct:.2f} % de lignes hors bornes physiques (> 1 %). "
            "Parsing numerique suspect."
        )

    # A7 — coherence espece / label. Un produit certifie halal ne peut pas
    # etre du porc : chaque cas est soit une erreur de tag OFF, soit une
    # erreur de ma derivation d'espece. Les deux meritent d'etre vues.
    n_porc_halal = con.execute(f"""
        SELECT count(*) FROM '{PERIMETRE}' WHERE tag_halal AND espece = 'porc'
    """).fetchone()[0]
    n_halal = con.execute(
        f"SELECT count(*) FROM '{PERIMETRE}' WHERE tag_halal").fetchone()[0]
    pct_ph = 100.0 * n_porc_halal / n_halal if n_halal else 0.0
    print(f"  A7 halal classes porc            : {n_porc_halal} ({pct_ph:.2f} %)")
    # La liste est publiee, pas seulement comptee : l'inspection montre qu'elle
    # melange deux causes, des erreurs de taxonomie OFF (saucissons de boeuf
    # ranges sous porc) et de vraies erreurs de tag halal (andouillettes de
    # Troyes taguees halal). Le seuil est a 2 % : au-dela, c'est la derivation
    # d'espece qui est cassee, pas la base.
    con.execute(f"""
        COPY (SELECT code, product_name, brands, sous_categorie
              FROM '{PERIMETRE}' WHERE tag_halal AND espece = 'porc')
        TO '{SORTIES / "a7_halal_classes_porc.csv"}' (HEADER, DELIMITER ',')
    """)
    if pct_ph > 2.0:
        echecs.append(
            f"A7 : {pct_ph:.2f} % des produits halal sont classes porc "
            "(> 2 %). Soit la derivation d'espece attrape des FORMES de "
            "produit au lieu de l'espece, soit le tag halal est errone."
        )

    # A6 — effectifs attendus
    obs = effectifs(con)
    if args.figer:
        (CONFIG / "effectifs_attendus.yaml").write_text(
            "# Effectifs de reference, figes depuis un run valide.\n"
            "# Regenere par : python3 src/etape1_assertions.py --figer\n"
            "# Un ecart hors tolerance arrete le pipeline (AGENTS.md).\n"
            "# La tolerance couvre la derive quotidienne du dump OFF, pas un\n"
            "# changement de perimetre ou de code.\n"
            + yaml.safe_dump(
                {"tolerance_relative": 0.15, "effectifs": obs},
                allow_unicode=True, sort_keys=True),
            encoding="utf-8")
        print("  A6 effectifs figes dans config/effectifs_attendus.yaml")
    else:
        ref = charger("effectifs_attendus.yaml")
        tol = ref["tolerance_relative"]
        for sc, bras_ref in ref["effectifs"].items():
            for bras, n_ref in bras_ref.items():
                n_obs = obs.get(sc, {}).get(bras)
                if n_obs is None:
                    echecs.append(f"A6 : strate absente {sc}/{bras}")
                    continue
                if abs(n_obs - n_ref) > tol * n_ref:
                    echecs.append(
                        f"A6 : {sc}/{bras} = {n_obs}, attendu {n_ref} "
                        f"+/- {tol:.0%}"
                    )
        print(f"  A6 effectifs vs reference       : "
              f"{'OK' if not any(e.startswith('A6') for e in echecs) else 'ECHEC'}")

    if echecs:
        echec("assertions non satisfaites :\n    - " + "\n    - ".join(echecs))
    print("\n  Toutes les assertions passent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
