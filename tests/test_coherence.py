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

    # Couche 8 : les choix offerts par l'Action doivent exister comme options
    # du script. Un renommage d'un cote seulement ne se verrait qu'au runtime,
    # apres la couche 1 complete sur le runner.
    wf8 = (RACINE / ".github" / "workflows" / "couche8-prix.yml").read_text()
    src8 = (RACINE / "src" / "etape8_prix.py").read_text()
    for option in ("--sonder", "--collecte", "--max-pages"):
        if option not in src8:
            echecs.append(f"etape8_prix.py : option {option} absente")
        if option not in wf8 and option != "--max-pages":
            echecs.append(f"workflow couche8 : {option} jamais appele")
    if "prices.openfoodfacts.org" not in src8:
        echecs.append("etape8_prix.py : hote Open Prices absent")

    # Chaque variable d'environnement attendue par la config doit etre injectee
    # par le workflow. Un secret renomme d'un cote et pas de l'autre ne se voit
    # autrement qu'au runtime, apres deux minutes de couche 1.
    for f in fournisseurs or []:
        for champ in ("env_cle", "env_compte"):
            var = f.get(champ)
            if var and var not in wf:
                echecs.append(
                    f"{f.get('nom')} : {champ}={var} n'est injecte nulle part "
                    "dans le workflow")

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
