#!/usr/bin/env python3
"""Couche 2 — diagnostic reseau et API, a lancer sur le runner.

L'environnement de developpement de ce depot ne joint ni la passerelle du
modele ni images.openfoodfacts.org. Ce script etablit sur le runner ce qui
repond et ce qui ne repond pas, avant d'accuser le mauvais coupable.

N'imprime JAMAIS la cle : uniquement sa longueur et son prefixe de 4 signes.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from commun import charger, titre




def sonde(url: str, cle: str | None = None, methode: str = "GET",
          corps: bytes | None = None) -> str:
    req = urllib.request.Request(url, data=corps, method=methode)
    req.add_header("User-Agent", "halal-nutrition-france/couche2")
    if cle:
        req.add_header("Authorization", f"Bearer {cle}")
    if corps:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            taille = r.headers.get("Content-Length", "?")
            ctype = r.headers.get("Content-Type", "?")
            return f"HTTP {r.status}  {ctype}  {taille} octets"
    except urllib.error.HTTPError as e:
        extrait = e.read(300).decode("utf-8", "replace").replace("\n", " ")
        return f"HTTP {e.code}  {extrait[:200]}"
    except Exception as e:  # noqa: BLE001
        return f"ECHEC {type(e).__name__}: {e}"


def main() -> int:
    conf = charger("lecture_image.yaml")
    brut = os.environ.get(conf["variable_env_cle"], "")
    cle = brut.strip()

    titre("DIAGNOSTIC — cle")
    print(f"  variable      : {conf['variable_env_cle']}")
    print(f"  presente      : {bool(cle)}")
    print(f"  longueur brute: {len(brut)}")
    print(f"  longueur nette: {len(cle)}")
    if cle != brut:
        print("  BLANCS PARASITES en debut ou fin. httpx refuse un en-tete")
        print("  Authorization qui en contient, et l'echec remonte en erreur")
        print("  de connexion. A corriger a la source du secret.")
    print(f"  prefixe       : {cle[:4] + '...' if cle else '(vide)'}")

    titre("DIAGNOSTIC — hotes candidats pour la passerelle")
    for base in CANDIDATS:
        print(f"\n  {base}")
        print(f"    /models          {sonde(base + '/models', cle)}")
        charge = json.dumps({
            "model": conf["modele"], "max_tokens": 16,
            "messages": [{"role": "user", "content": "ping"}],
        }).encode()
        print(f"    /chat/completions {sonde(base + '/chat/completions', cle, 'POST', charge)}")

    titre("DIAGNOSTIC — images Open Food Facts")
    exemple = ("https://images.openfoodfacts.org/images/products/"
               "590/566/864/0597/front_fr.13")
    for suffixe in (".400.jpg", ".800.jpg", ".full.jpg"):
        print(f"  {suffixe:<10} {sonde(exemple + suffixe)}")

    print("\n  Une image qui ne repond pas ici invalide toute la voie de la")
    print("  couche 2, independamment de la passerelle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
