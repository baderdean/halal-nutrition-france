#!/usr/bin/env python3
"""Couche 2 — diagnostic reseau et API, a lancer sur le runner.

L'environnement de developpement de ce depot ne joint ni les passerelles de
modeles ni images.openfoodfacts.org. Ce script etablit sur le runner ce qui
repond et ce qui ne repond pas, avant d'accuser le mauvais coupable.

N'imprime JAMAIS une cle : uniquement sa longueur et son prefixe de 4 signes.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from commun import charger, titre

IMAGE_TEST = ("https://images.openfoodfacts.org/images/products/"
              "590/566/864/0597/front_fr.13")


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
            return (f"HTTP {r.status}  {r.headers.get('Content-Type', '?')}  "
                    f"{r.headers.get('Content-Length', '?')} octets")
    except urllib.error.HTTPError as e:
        extrait = e.read(300).decode("utf-8", "replace").replace("\n", " ")
        return f"HTTP {e.code}  {extrait[:200]}"
    except Exception as e:  # noqa: BLE001
        return f"ECHEC {type(e).__name__}: {e}"


def main() -> int:
    conf = charger("lecture_image.yaml")

    for f in conf["fournisseurs"]:
        titre(f"DIAGNOSTIC — {f['nom']} / {f['modele']}")
        brut = os.environ.get(f["env_cle"], "")
        cle = brut.strip()
        print(f"  variable cle   : {f['env_cle']}")
        print(f"  longueur brute : {len(brut)}   nette : {len(cle)}")
        print(f"  prefixe        : {cle[:4] + '...' if cle else '(vide)'}")
        if cle != brut:
            print("  BLANCS PARASITES en debut ou fin. httpx refuse un en-tete")
            print("  Authorization qui en contient, et l'echec remonte en")
            print("  erreur de connexion. A corriger a la source du secret.")

        base = f["base_url"]
        if "env_compte" in f:
            compte = os.environ.get(f["env_compte"], "").strip()
            print(f"  variable compte: {f['env_compte']} "
                  f"({'presente' if compte else 'ABSENTE'})")
            if not compte:
                print("  -> sonde impossible sans identifiant de compte.")
                continue
            base = base.replace("{" + f["env_compte"] + "}", compte)
        if not cle:
            print("  -> sonde impossible sans cle.")
            continue

        print(f"  base_url       : {base}")
        print(f"    /models            {sonde(base + '/models', cle)}")
        charge = json.dumps({
            "model": f["modele"], "max_tokens": 16,
            "messages": [{"role": "user", "content": "ping"}],
        }).encode()
        print(f"    /chat/completions  "
              f"{sonde(base + '/chat/completions', cle, 'POST', charge)}")

    titre("DIAGNOSTIC — images Open Food Facts")
    for suffixe in (".400.jpg", ".full.jpg"):
        print(f"  {suffixe:<10} {sonde(IMAGE_TEST + suffixe)}")
    print("\n  Une image qui ne repond pas ici invalide toute la voie de la")
    print("  couche 2, independamment de la passerelle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
