#!/usr/bin/env python3
"""Etape 0 — recuperation et verification du dump source.

Telecharge le fichier decrit par config/source.yaml s'il est absent, puis
verifie taille et sha256. Un ecart arrete le pipeline : le dump Open Food Facts
est republie chaque jour, et une etude figee ne doit pas changer de base
sous elle sans que quelqu'un l'ait decide.

Pour figer un nouveau dump : lance avec --figer, verifie les effectifs, puis
regenere config/effectifs_attendus.yaml.
"""

from __future__ import annotations

import argparse
import subprocess
import sys

import yaml

from commun import CONFIG, DONNEES, charger, echec, sha256, titre


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figer", action="store_true",
                    help="ecrit taille et sha256 observes dans config/source.yaml")
    args = ap.parse_args()

    src = charger("source.yaml")
    DONNEES.mkdir(parents=True, exist_ok=True)
    cible = DONNEES / src["fichier_local"]

    titre("ETAPE 0 — source")
    # Sans version_id, l'URL rend le dump du jour : le bucket est versionne
    # et l'objet ecrase quotidiennement. Le sha256 detecte la substitution,
    # version_id l'evite.
    url = src["url"]
    if src.get("version_id"):
        url += f"?versionId={src['version_id']}"
    else:
        print("  [ATTENTION] config/source.yaml sans version_id : le dump "
              "telecharge sera\n  celui du jour, pas celui de l'etude.")
    if not cible.exists():
        print(f"  telechargement de {url}")
        r = subprocess.run(
            ["curl", "-sSL", "--fail", "--retry", "4", "--retry-delay", "2",
             "-o", str(cible), url]
        )
        if r.returncode != 0:
            echec(f"telechargement echoue (curl {r.returncode}).")
    else:
        print(f"  deja present : {cible}")

    taille = cible.stat().st_size
    print(f"  taille : {taille} octets")
    print("  sha256 : calcul...", flush=True)
    h = sha256(cible)
    print(f"           {h}")

    if args.figer:
        src["taille_octets"] = taille
        src["sha256"] = h
        # Reecriture ciblee pour conserver les commentaires du YAML.
        texte = (CONFIG / "source.yaml").read_text(encoding="utf-8")
        for cle, val in (("taille_octets", taille), ("sha256", h)):
            lignes = []
            for l in texte.splitlines():
                if l.startswith(f"{cle}:"):
                    reste = l.split("#", 1)
                    suffixe = f"  #{reste[1]}" if len(reste) > 1 else ""
                    l = f"{cle}: {val}{suffixe}"
                lignes.append(l)
            texte = "\n".join(lignes) + "\n"
        (CONFIG / "source.yaml").write_text(texte, encoding="utf-8")
        print("  -> config/source.yaml mis a jour")
        return 0

    ecarts = []
    if src.get("taille_octets") and src["taille_octets"] != taille:
        ecarts.append(f"taille {taille} != {src['taille_octets']}")
    if src.get("sha256") and src["sha256"] != h:
        ecarts.append("sha256 different")
    if ecarts:
        echec(
            "le dump ne correspond pas a config/source.yaml : "
            + " ; ".join(ecarts)
            + ".\n    Le dump OFF est republie quotidiennement. Pour figer la "
            "nouvelle version :\n      python3 src/etape0_source.py --figer\n"
            "    puis rejouer le pipeline et regenerer les effectifs attendus."
        )
    print("  source conforme a config/source.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
