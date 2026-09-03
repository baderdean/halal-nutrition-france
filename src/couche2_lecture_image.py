#!/usr/bin/env python3
"""Couche 2 — lecture des emballages : estampille halal et certificateur.

Repond a deux questions, dans cet ordre de priorite :
  1. le produit porte-t-il une estampille halal visible ? C'est la mesure du
     taux de faux negatifs du tag, qui commande l'amplitude de tous les ecarts
     de la couche 1.
  2. quel organisme certificateur est lisible sur l'emballage ? Le tag OFF ne
     le renseigne que pour 6,9 % des produits halal.

CE SCRIPT NE PRODUIT PAS UNE VARIABLE D'ANALYSE. Il produit une lecture
machine, dont le taux d'erreur doit etre mesure par src/couche2_validation.py
contre un double codage humain en aveugle. Tant que ce taux n'existe pas, la
lecture est descriptive et n'entre dans aucun modele (AGENTS.md).

Le script coute de l'argent : il appelle l'API Anthropic. Il tourne a vide par
defaut et n'emet aucun appel sans --executer.

Usage :
  python3 src/couche2_lecture_image.py                  # estimation seule
  python3 src/couche2_lecture_image.py --executer --max 200
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import time

import anthropic

from commun import PERIMETRE, SORTIES, connexion, echec, titre

# Modele par defaut : le plus petit modele de vision de la gamme. Ce choix
# n'est pas un acquis, c'est une hypothese que src/couche2_validation.py doit
# confirmer ou infirmer sur un taux d'erreur mesure.
MODELE_DEFAUT = "claude-haiku-4-5"

# L'export plat pointe des images en 400 px sur le grand cote. Un logo de
# certificateur y occupe quelques dizaines de pixels. OFF sert d'autres tailles
# au meme chemin ; on tente la plus grande et on retombe sur 400 si elle
# echoue. NON VERIFIE a la redaction : l'hote images etait injoignable depuis
# l'environnement de developpement. La colonne `taille_demandee` du CSV de
# sortie permet de comparer les taux de lecture entre les deux.
TAILLES = {"full": ".full.jpg", "400": ".400.jpg"}

SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["estampille_halal", "certificateur_texte",
                     "certificateur_logo", "confiance", "lisibilite"],
        "properties": {
            "estampille_halal": {
                "type": "string",
                "enum": ["oui", "non", "illisible"],
                "description": "Une mention ou un logo halal est-il visible ?",
            },
            "certificateur_texte": {
                "type": "string",
                "description": "Nom de l'organisme certificateur EXACTEMENT tel "
                               "qu'ecrit sur l'emballage. Chaine vide si aucun "
                               "nom n'est lisible. Ne jamais completer ni "
                               "corriger un nom partiellement lisible.",
            },
            "certificateur_logo": {
                "type": "string",
                "description": "Description litterale du logo de certification "
                               "s'il y en a un mais qu'aucun nom n'est lisible. "
                               "Chaine vide sinon.",
            },
            "confiance": {
                "type": "string",
                "enum": ["haute", "moyenne", "basse"],
            },
            "lisibilite": {
                "type": "string",
                "enum": ["nette", "floue", "trop_petite", "zone_absente"],
                "description": "zone_absente si la face photographiee ne montre "
                               "pas la zone ou figurerait une estampille.",
            },
        },
    },
}

CONSIGNE = """Tu examines la photo d'un emballage de produit carne vendu en France.

Rapporte UNIQUEMENT ce que tu vois sur l'image. Les regles suivantes priment
sur toute envie de fournir une reponse utile :

- Si tu ne lis pas un nom, renvoie une chaine vide. Ne devine jamais un nom
  d'organisme a partir d'un logo partiellement visible, d'une couleur, d'une
  calligraphie arabe ou de la marque du produit.
- Ne deduis pas l'estampille halal de la marque, du type de viande, du texte
  arabe ou de l'absence de porc. Seule une mention ou un logo explicite compte.
- Si la zone est trop petite ou floue pour etre lue, dis-le par le champ
  lisibilite plutot que de proposer une lecture incertaine.
- Une reponse "illisible" correctement rapportee vaut mieux qu'une lecture
  plausible mais fausse. Une erreur ici se propage a toute la gamme d'une
  marque, parce que toutes ses references partagent le meme emballage."""


def cibles(con, limite: int | None, par_marque: int):
    """Echantillon a lire.

    Tire PAR MARQUE, pas par produit. Une marque partage un design d'emballage :
    lire dix references de la meme marque ne mesure pas dix fois la lecture,
    cela mesure une fois le design et neuf fois la meme erreur eventuelle.
    """
    sql = f"""
        SELECT code, product_name, brands,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque_tag,
               bras, sous_categorie, image_url, image_ingredients_url
        FROM '{PERIMETRE}'
        WHERE image_url IS NOT NULL AND brands_tags IS NOT NULL
          AND len(brands_tags) > 0
        QUALIFY row_number() OVER (
            PARTITION BY regexp_replace(brands_tags[1], '^[a-z]{{2}}:', ''), bras
            ORDER BY code) <= {par_marque}
        ORDER BY marque_tag, bras, code
    """
    df = con.execute(sql).df()
    return df.head(limite) if limite else df


def lire_une(client, modele: str, ligne, taille: str) -> dict:
    url = ligne.image_url
    if taille != "400":
        url = url.replace(".400.jpg", TAILLES[taille])
    try:
        r = client.messages.create(
            model=modele,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "url", "url": url}},
                    {"type": "text", "text": CONSIGNE},
                ],
            }],
            output_config={"format": SCHEMA},
        )
        texte = next((b.text for b in r.content if b.type == "text"), "{}")
        lu = json.loads(texte)
        lu["erreur"] = ""
        lu["tokens_entree"] = r.usage.input_tokens
        lu["tokens_sortie"] = r.usage.output_tokens
    except Exception as e:  # noqa: BLE001 - l'echec est une donnee, pas un arret
        lu = {"estampille_halal": "", "certificateur_texte": "",
              "certificateur_logo": "", "confiance": "", "lisibilite": "",
              "erreur": f"{type(e).__name__}: {e}"[:300],
              "tokens_entree": 0, "tokens_sortie": 0}
    lu.update({"code": ligne.code, "marque_tag": ligne.marque_tag,
               "brands": ligne.brands, "bras": ligne.bras,
               "sous_categorie": ligne.sous_categorie,
               "url_lue": url, "taille_demandee": taille})
    return lu


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--executer", action="store_true",
                    help="emet reellement les appels API (payant)")
    ap.add_argument("--modele", default=MODELE_DEFAUT)
    ap.add_argument("--max", type=int, default=None, dest="limite")
    ap.add_argument("--par-marque", type=int, default=3,
                    help="references lues par marque et par bras")
    ap.add_argument("--taille", choices=list(TAILLES), default="full")
    ap.add_argument("--concurrence", type=int, default=8)
    args = ap.parse_args()

    con = connexion()
    df = cibles(con, args.limite, args.par_marque)
    titre("COUCHE 2 — lecture des emballages")
    print(f"  modele        : {args.modele}")
    print(f"  taille image  : {args.taille}")
    print(f"  produits      : {len(df)}  "
          f"({df.marque_tag.nunique()} marques, "
          f"{(df.bras == 'halal').sum()} halal / "
          f"{(df.bras == 'temoin').sum()} temoin)")

    if not args.executer:
        print("\n  MODE ESTIMATION — aucun appel emis, aucun euro depense.")
        print("  Relance avec --executer pour lancer la lecture.")
        print("\n  Le cout depend de la resolution reelle servie par Open Food")
        print("  Facts, inconnue a la redaction de ce script. Le premier run")
        print("  reel doit se faire avec --max 20 : le CSV de sortie porte le")
        print("  compte de tokens par image, qui donne le cout au produit et")
        print("  permet d'extrapoler avant d'engager le lot complet.")
        return 0

    if not (os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        echec("ni ANTHROPIC_API_KEY ni ANTHROPIC_AUTH_TOKEN dans "
              "l'environnement.")

    client = anthropic.Anthropic()
    t0 = time.time()
    resultats = []
    with cf.ThreadPoolExecutor(max_workers=args.concurrence) as ex:
        futurs = [ex.submit(lire_une, client, args.modele, l, args.taille)
                  for l in df.itertuples()]
        for i, f in enumerate(cf.as_completed(futurs), 1):
            resultats.append(f.result())
            if i % 25 == 0:
                print(f"    {i}/{len(futurs)}", flush=True)

    import pandas as pd
    out = pd.DataFrame(resultats)
    SORTIES.mkdir(exist_ok=True)
    chemin = SORTIES / "couche2_lecture_image.csv"
    out.to_csv(chemin, index=False)

    n_err = int((out.erreur != "").sum())
    print(f"\n  {len(out)} lectures en {time.time() - t0:.0f}s, "
          f"{n_err} echecs techniques")
    print(f"  tokens entree : {int(out.tokens_entree.sum())}")
    print(f"  -> {chemin}")

    ok = out[out.erreur == ""]
    if len(ok):
        print("\n  Repartition lisibilite (diagnostic de la resolution) :")
        print(ok.lisibilite.value_counts().to_string())
        print("\n  Estampille halal lue, par bras :")
        print(ok.groupby(["bras", "estampille_halal"]).size().to_string())

    # Fichier d'ENTREE a remplir par un humain, en aveugle. Les specs exigent
    # que le double codage soit un fichier d'entree du depot, pas une sortie
    # generee : ce CSV ne contient donc aucune lecture machine.
    modele_humain = df[["code", "brands", "bras", "image_url"]].copy()
    for col in ("h_estampille_halal", "h_certificateur", "h_lisibilite",
                "h_commentaire"):
        modele_humain[col] = ""
    cible = SORTIES / "double_codage_a_remplir.csv"
    modele_humain.to_csv(cible, index=False)
    print(f"\n  -> {cible}")
    print("     A remplir a la main, en aveugle, SANS consulter "
          "couche2_lecture_image.csv,")
    print("     puis a deposer dans donnees_humaines/double_codage.csv "
          "(fichier d'entree du depot).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
