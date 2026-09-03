"""Fonctions partagees par les etapes de la couche 1.

Aucune logique d'analyse ici : chemins, connexion DuckDB, expressions SQL
reutilisees. Toute regle de fond vit dans AGENTS.md et config/.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys

import duckdb
import yaml

RACINE = pathlib.Path(__file__).resolve().parent.parent
CONFIG = RACINE / "config"
SORTIES = RACINE / "sorties"
DONNEES = pathlib.Path(os.environ.get("HNF_DATA", RACINE / "data"))

PERIMETRE = DONNEES / "perimetre_carne_fr.parquet"


def charger(nom: str) -> dict:
    with open(CONFIG / nom, encoding="utf-8") as f:
        return yaml.safe_load(f)


def connexion(memoire_go: int = 10) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{memoire_go}GB';")
    con.execute(f"SET temp_directory='{DONNEES / 'duckdb_tmp'}';")
    con.execute("SET preserve_insertion_order=false;")
    return con


def titre(txt: str) -> None:
    print("\n" + "=" * 78, flush=True)
    print(txt, flush=True)
    print("=" * 78, flush=True)


def echec(message: str) -> None:
    """Arret bruyant. AGENTS.md interdit de degrader silencieusement."""
    print(f"\n[ECHEC] {message}", file=sys.stderr, flush=True)
    sys.exit(2)


def sha256(chemin: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 22), b""):
            h.update(bloc)
    return h.hexdigest()


def revision_git() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RACINE, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "inconnue"


# --- expressions SQL reutilisees -------------------------------------------

# Les tags sont des chaines separees par des virgules dans l'export plat.
def liste(colonne: str) -> str:
    return (
        f"CASE WHEN {colonne} IS NULL OR {colonne} = '' THEN []::VARCHAR[] "
        f"ELSE list_transform(string_split({colonne}, ','), x -> trim(x)) END"
    )


# Completude nutritionnelle : les cinq champs necessaires a toute comparaison
# nutritionnelle de la couche 1 et au FSAm-NPS des couches suivantes.
COMPLET = (
    "energy_kcal_100g IS NOT NULL AND saturated_fat_100g IS NOT NULL "
    "AND sugars_100g IS NOT NULL AND salt_100g IS NOT NULL "
    "AND proteins_100g IS NOT NULL"
)
