#!/usr/bin/env python3
"""Coherence entre config/lecture_image.yaml et le code qui la lit.

Ce fichier existe a cause d'une panne reelle : une modification de la config
avait renomme les cles sans que le diagnostic suive, et l'ecart n'est apparu
qu'apres un run complet sur le runner, soit deux minutes de couche 1 pour
tomber sur un KeyError. Une verification qui coute 50 ms evite ca.

Lance par le workflow avant tout appel payant.
"""

from __future__ import annotations

import pathlib
import sys

import yaml

RACINE = pathlib.Path(__file__).resolve().parent.parent
CHAMPS_REQUIS = ("nom", "modele", "base_url", "env_cle", "image")
IMAGES_CONNUES = ("url", "base64")


def main() -> int:
    conf = yaml.safe_load((RACINE / "config" / "lecture_image.yaml").read_text())
    echecs = []

    fournisseurs = conf.get("fournisseurs")
    if not fournisseurs:
        echecs.append("aucun fournisseur declare")

    noms = set()
    for i, f in enumerate(fournisseurs or []):
        etiquette = f.get("nom", f"#{i}")
        for champ in CHAMPS_REQUIS:
            if champ not in f:
                echecs.append(f"{etiquette} : champ '{champ}' manquant")
        if f.get("image") not in IMAGES_CONNUES:
            echecs.append(f"{etiquette} : image={f.get('image')!r}, "
                          f"attendu l'un de {IMAGES_CONNUES}")
        if f.get("nom") in noms:
            echecs.append(f"{etiquette} : nom en double")
        noms.add(f.get("nom"))
        # Un placeholder dans l'URL doit avoir sa variable declaree.
        base = f.get("base_url", "")
        if "{" in base:
            compte = f.get("env_compte")
            if not compte or "{" + compte + "}" not in base:
                echecs.append(
                    f"{etiquette} : base_url contient un placeholder que "
                    "env_compte ne resout pas")

    # Le code ne doit plus reference l'ancienne config a fournisseur unique.
    for nom in ("couche2_lecture_image.py", "couche2_diagnostic.py"):
        src = (RACINE / "src" / nom).read_text()
        for obsolete in ("variable_env_cle", 'conf["modele"]', 'conf["base_url"]'):
            if obsolete in src:
                echecs.append(f"src/{nom} : reference obsolete {obsolete!r}")

    # Les choix de l'Action doivent correspondre aux fournisseurs declares.
    wf = (RACINE / ".github" / "workflows" / "couche2-images.yml").read_text()
    for nom in noms:
        if nom and f'"{nom}"' not in wf:
            echecs.append(f"workflow : {nom} absent des choix de fournisseur")

    if echecs:
        print("INCOHERENCES :", file=sys.stderr)
        for e in echecs:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"config coherente : {len(noms)} fournisseurs, "
          f"{', '.join(sorted(n for n in noms if n))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
