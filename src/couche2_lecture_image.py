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

Fournisseur : API compatible OpenAI, configuree dans config/lecture_image.yaml.
Par defaut la passerelle OpenCode Zen et le modele MiniMax M3.

Le script appelle une API payante. Il ne fait rien sans --preflight ou
--executer.

Usage :
  python3 src/couche2_lecture_image.py                 # estimation, 0 appel
  python3 src/couche2_lecture_image.py --preflight     # 1 appel, go/no-go
  python3 src/couche2_lecture_image.py --executer --max 20
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time

from openai import OpenAI

from commun import PERIMETRE, SORTIES, charger, connexion, echec, titre

# L'export plat pointe des images en 400 px sur le grand cote. Un logo de
# certificateur y occupe quelques dizaines de pixels ; le module de vision de
# M3 accepte jusqu'a 2016 px. OFF sert d'autres tailles au meme chemin.
# NON VERIFIE : l'hote images etait injoignable depuis l'environnement de
# developpement. La colonne `taille_demandee` du CSV permet de comparer les
# taux de lecture entre les deux et de trancher sur donnees.
TAILLES = {"full": ".full.jpg", "800": ".800.jpg", "400": ".400.jpg"}

CHAMPS = ["estampille_halal", "certificateur_texte", "certificateur_logo",
          "confiance", "lisibilite"]

CONSIGNE = """Tu examines la photo d'un emballage de produit carne vendu en France.

Reponds UNIQUEMENT par un objet JSON, sans texte autour, sans bloc de code,
avec exactement ces cinq cles :

{
  "estampille_halal": "oui" | "non" | "illisible",
  "certificateur_texte": "nom de l'organisme certificateur EXACTEMENT tel qu'ecrit sur l'emballage, chaine vide si aucun nom lisible",
  "certificateur_logo": "description litterale du logo de certification s'il y en a un sans nom lisible, chaine vide sinon",
  "confiance": "haute" | "moyenne" | "basse",
  "lisibilite": "nette" | "floue" | "trop_petite" | "zone_absente"
}

Rapporte uniquement ce que tu vois. Les regles suivantes priment sur toute
envie de fournir une reponse utile :

- Si tu ne lis pas un nom, renvoie une chaine vide. Ne devine jamais un nom
  d'organisme a partir d'un logo partiellement visible, d'une couleur, d'une
  calligraphie arabe ou de la marque du produit.
- Ne deduis pas l'estampille halal de la marque, du type de viande, de la
  presence de texte arabe ou de l'absence de porc. Seule une mention ou un
  logo explicite compte.
- Si la zone est trop petite ou floue pour etre lue, dis-le par le champ
  lisibilite plutot que de proposer une lecture incertaine.
- "zone_absente" si la face photographiee ne montre pas la zone ou figurerait
  une estampille.

Une reponse "illisible" correctement rapportee vaut mieux qu'une lecture
plausible mais fausse. Une erreur ici se propage a toute la gamme d'une marque,
parce que toutes ses references partagent le meme emballage."""


def client_et_conf(args):
    conf = charger("lecture_image.yaml")
    if args.modele:
        conf["modele"] = args.modele
    cle = os.environ.get(conf["variable_env_cle"])
    if not cle:
        echec(f"{conf['variable_env_cle']} absente de l'environnement.")
    return OpenAI(api_key=cle, base_url=conf["base_url"], timeout=120.0), conf


def message(url: str, conf: dict, params_minimax: bool) -> list:
    img = {"type": "image_url", "image_url": {"url": url}}
    if params_minimax:
        img["image_url"].update(conf.get("params_minimax", {}))
    return [{"role": "user", "content": [img, {"type": "text",
                                               "text": CONSIGNE}]}]


def extraire_json(texte: str) -> dict:
    """Parse defensif. Le mode JSON strict n'est pas garanti par la passerelle."""
    t = texte.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    raise ValueError(f"reponse non parsable : {texte[:200]}")


def appeler(client, conf, url, params_minimax, json_mode=True):
    kw = {"model": conf["modele"], "max_tokens": 512,
          "messages": message(url, conf, params_minimax)}
    if json_mode:
        kw["response_format"] = {"type": "json_object"}
    try:
        return client.chat.completions.create(**kw)
    except Exception as e:  # noqa: BLE001
        # response_format n'est pas garanti sur cette passerelle : une seule
        # nouvelle tentative sans lui, puis on laisse remonter.
        if json_mode and any(m in str(e).lower() for m in
                             ("response_format", "unsupported", "invalid",
                              "unrecognized")):
            return appeler(client, conf, url, params_minimax, json_mode=False)
        raise


def cibles(con, limite, par_marque):
    """Echantillon a lire, tire PAR MARQUE et par bras, pas par produit.

    Une marque partage un design d'emballage : lire dix references de la meme
    marque ne mesure pas dix fois la lecture, cela mesure une fois le design
    et neuf fois la meme erreur eventuelle.
    """
    df = con.execute(f"""
        SELECT code, product_name, brands,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque_tag,
               bras, sous_categorie, tag_halal, image_url
        FROM '{PERIMETRE}'
        WHERE image_url IS NOT NULL AND brands_tags IS NOT NULL
          AND len(brands_tags) > 0
        QUALIFY row_number() OVER (
            PARTITION BY regexp_replace(brands_tags[1], '^[a-z]{{2}}:', ''), bras
            ORDER BY code) <= {par_marque}
        ORDER BY marque_tag, bras, code
    """).df()
    return df.head(limite) if limite else df


def lire_une(client, conf, ligne, taille, params_minimax) -> dict:
    url = ligne.image_url
    if taille != "400":
        url = url.replace(".400.jpg", TAILLES[taille])
    base = {c: "" for c in CHAMPS}
    base.update({"erreur": "", "tokens_entree": 0, "tokens_sortie": 0})
    try:
        r = appeler(client, conf, url, params_minimax)
        lu = extraire_json(r.choices[0].message.content or "")
        base.update({c: str(lu.get(c, "")) for c in CHAMPS})
        if r.usage:
            base["tokens_entree"] = r.usage.prompt_tokens or 0
            base["tokens_sortie"] = r.usage.completion_tokens or 0
    except Exception as e:  # noqa: BLE001 - l'echec est une donnee, pas un arret
        base["erreur"] = f"{type(e).__name__}: {e}"[:300]
    base.update({"code": ligne.code, "marque_tag": ligne.marque_tag,
                 "brands": ligne.brands, "bras": ligne.bras,
                 "tag_halal": ligne.tag_halal,
                 "sous_categorie": ligne.sous_categorie,
                 "url_lue": url, "taille_demandee": taille})
    return base


def cout(conf, e: int, s: int) -> float:
    return (e * conf["tarif_entree_par_million"]
            + s * conf["tarif_sortie_par_million"]) / 1e6


def preflight(client, conf, df, args) -> int:
    """Un seul appel. Tranche la question qui conditionne tout le reste :
    la passerelle relaie-t-elle les images jusqu'au modele ?"""
    ligne = next(df[df.bras == "halal"].itertuples())
    titre("PREFLIGHT — un appel, une image")
    print(f"  modele : {conf['modele']}  via  {conf['base_url']}")
    r = lire_une(client, conf, ligne, args.taille, args.params_minimax)
    print(f"  produit : {ligne.code}  {ligne.brands}")
    print(f"  url     : {r['url_lue']}")
    print()
    for c in CHAMPS:
        print(f"    {c:<22} {r[c]!r}")
    print(f"    {'tokens entree':<22} {r['tokens_entree']}")
    print(f"    {'cout de cet appel':<22} "
          f"${cout(conf, r['tokens_entree'], r['tokens_sortie']):.5f}")
    if r["erreur"]:
        print(f"\n  ECHEC : {r['erreur']}")
        print("\n  Si l'erreur porte sur le type de contenu `image_url`, la")
        print("  passerelle ne relaie pas les images. Il faut alors changer de")
        print("  fournisseur dans config/lecture_image.yaml, pas contourner.")
        return 1
    if r["tokens_entree"] < 200:
        print("\n  AVERTISSEMENT : moins de 200 tokens en entree. Une image")
        print("  analysee en coute beaucoup plus. La passerelle a probablement")
        print("  ignore l'image et repondu sur le seul texte de la consigne.")
        print("  Ne PAS lancer le lot : la reponse ci-dessus serait inventee.")
        return 1
    print("\n  Image relayee et facturee. Le lot peut partir.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true",
                    help="un seul appel, verifie que la passerelle relaie l'image")
    ap.add_argument("--executer", action="store_true",
                    help="emet reellement le lot d'appels (payant)")
    ap.add_argument("--modele", default=None)
    ap.add_argument("--max", type=int, default=None, dest="limite")
    ap.add_argument("--par-marque", type=int, default=3)
    ap.add_argument("--taille", choices=list(TAILLES), default="full")
    ap.add_argument("--params-minimax", action="store_true",
                    help="envoie detail et max_long_side_pixel (non garantis)")
    ap.add_argument("--concurrence", type=int, default=6)
    args = ap.parse_args()

    con = connexion()
    df = cibles(con, args.limite, args.par_marque)
    titre("COUCHE 2 — lecture des emballages")
    print(f"  produits : {len(df)}  ({df.marque_tag.nunique()} marques, "
          f"{(df.bras == 'halal').sum()} halal / "
          f"{(df.bras == 'temoin').sum()} temoin)")

    if not (args.preflight or args.executer):
        conf = charger("lecture_image.yaml")
        print(f"  modele   : {conf['modele']} via {conf['base_url']}")
        print("\n  MODE ESTIMATION — aucun appel emis, aucun euro depense.")
        print("  Le cout depend du nombre de tokens qu'une image consomme chez")
        print("  ce fournisseur, inconnu tant que --preflight n'a pas tourne.")
        print("  Ordre de grandeur, si une image vaut ~1500 tokens d'entree :")
        for n in (20, len(df)):
            print(f"    {n:>6} produits  ~ ${cout(conf, n * 1500, n * 120):.2f}")
        print("\n  Enchainement : --preflight, puis --executer --max 20,")
        print("  puis le lot complet une fois le cout reel connu.")
        return 0

    client, conf = client_et_conf(args)
    if args.preflight:
        return preflight(client, conf, df, args)

    t0 = time.time()
    resultats = []
    with cf.ThreadPoolExecutor(max_workers=args.concurrence) as ex:
        futurs = [ex.submit(lire_une, client, conf, l, args.taille,
                            args.params_minimax) for l in df.itertuples()]
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
    te, ts = int(out.tokens_entree.sum()), int(out.tokens_sortie.sum())
    print(f"\n  {len(out)} lectures en {time.time() - t0:.0f}s, "
          f"{n_err} echecs techniques")
    print(f"  tokens : {te} entree / {ts} sortie")
    print(f"  cout   : ${cout(conf, te, ts):.4f}  "
          f"(${cout(conf, te, ts) / max(len(out), 1):.5f} par produit)")
    print(f"  -> {chemin}")

    ok = out[out.erreur == ""]
    if len(ok):
        print("\n  Lisibilite (diagnostic de la resolution servie) :")
        print(ok.lisibilite.value_counts().to_string())
        print("\n  Estampille halal lue, par bras :")
        print(ok.groupby(["bras", "estampille_halal"]).size().to_string())
        vus = ok[(ok.bras == "temoin") & (ok.estampille_halal == "oui")]
        if len(vus):
            print(f"\n  {len(vus)} produits du TEMOIN portent une estampille "
                  "halal lisible.")
            print("  C'est la mesure attendue des faux negatifs du tag. Elle ne")
            print("  vaut rien tant que src/couche2_validation.py n'a pas publie")
            print("  le taux d'erreur de cette lecture contre un codage humain.")

    # Fichier d'ENTREE a remplir par un humain, en aveugle. Les specs exigent
    # que le double codage soit un fichier d'entree du depot, pas une sortie
    # generee : ce CSV ne contient donc aucune lecture machine.
    gabarit = df[["code", "brands", "bras", "image_url"]].copy()
    for col in ("h_estampille_halal", "h_certificateur", "h_lisibilite",
                "h_commentaire"):
        gabarit[col] = ""
    cible = SORTIES / "double_codage_a_remplir.csv"
    gabarit.to_csv(cible, index=False)
    print(f"\n  -> {cible}")
    print("     A remplir a la main, en aveugle, SANS consulter")
    print("     couche2_lecture_image.csv, puis a deposer dans")
    print("     donnees_humaines/double_codage.csv (fichier d'entree du depot).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
