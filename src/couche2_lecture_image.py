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

Fournisseurs : API compatible OpenAI, listes DANS L'ORDRE dans
config/lecture_image.yaml. Le premier qui passe l'appel de verification
emporte tout le lot ; on ne panache pas deux fournisseurs dans un meme jeu de
lectures, leurs taux d'erreur different.

Le script appelle une API payante. Il ne fait rien sans --preflight ou
--executer.

Usage :
  python3 src/couche2_lecture_image.py                 # estimation, 0 appel
  python3 src/couche2_lecture_image.py --preflight     # go/no-go, 1 appel
  python3 src/couche2_lecture_image.py --executer --max 20
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import json
import os
import re
import sys
import time
import urllib.request

from openai import OpenAI

from commun import PERIMETRE, SORTIES, charger, connexion, echec, titre

# L'export plat pointe des images en 400 px sur le grand cote. Un logo de
# certificateur y occupe quelques dizaines de pixels. Le .full.jpg existe et
# repond en HTTP 200 (verifie sur le runner) ; le .800.jpg n'existe pas.
TAILLES = {"full": ".full.jpg", "400": ".400.jpg"}

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


# --------------------------------------------------------------- fournisseurs

def fournisseurs(conf, filtre=None, modele=None):
    """Fournisseurs configures, resolus contre l'environnement.

    Un fournisseur dont la cle manque est ecarte AVEC SON MOTIF, pas en
    silence : une variable d'environnement oubliee ne doit pas ressembler a un
    fournisseur qui ne fonctionne pas.
    """
    out = []
    for brut_f in conf["fournisseurs"]:
        f = dict(brut_f)
        if filtre and f["nom"] != filtre:
            continue
        if modele:
            f["modele"] = modele
        brut = os.environ.get(f["env_cle"], "")
        # Un secret colle dans l'interface GitHub garde l'espace ou le saut de
        # ligne final. httpx refuse alors l'en-tete Authorization, et l'echec
        # remonte en APIConnectionError, qui ne ressemble en rien a un probleme
        # de cle. On nettoie, et on le signale : la source doit etre corrigee.
        f["cle"] = brut.strip()
        f["blancs"] = len(brut) - len(f["cle"])
        f["indisponible"] = ""
        if not f["cle"]:
            f["indisponible"] = f"{f['env_cle']} absente de l'environnement"
        if "env_compte" in f:
            compte = os.environ.get(f["env_compte"], "").strip()
            if not compte:
                f["indisponible"] = (f"{f['env_compte']} absente de "
                                     "l'environnement")
            else:
                f["base_url"] = f["base_url"].replace(
                    "{" + f["env_compte"] + "}", compte)
        out.append(f)
    if not out:
        echec(f"aucun fournisseur {filtre!r} dans config/lecture_image.yaml.")
    return out


def client_pour(f):
    return OpenAI(api_key=f["cle"], base_url=f["base_url"], timeout=180.0)


def cout(f, entree: int, sortie: int) -> float:
    return (entree * (f.get("tarif_entree_par_million") or 0.0)
            + sortie * (f.get("tarif_sortie_par_million") or 0.0)) / 1e6


# ------------------------------------------------------------------- appel

def contenu_image(url: str, f: dict, conf: dict, params_minimax: bool) -> dict:
    """Bloc image du message.

    `url` laisse le fournisseur aller chercher l'image lui-meme. `base64` la
    telecharge ici : une dependance de moins, et le runner joint
    images.openfoodfacts.org.
    """
    if f.get("image") == "base64":
        req = urllib.request.Request(
            url, headers={"User-Agent": "halal-nutrition-france/couche2"})
        with urllib.request.urlopen(req, timeout=60) as r:
            octets = r.read()
            mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
        return {"type": "image_url",
                "image_url": {"url": f"data:{mime};base64,"
                                     f"{base64.b64encode(octets).decode('ascii')}"}}
    bloc = {"type": "image_url", "image_url": {"url": url}}
    if params_minimax:
        bloc["image_url"].update(conf.get("params_minimax", {}))
    return bloc


def extraire_json(texte: str) -> dict:
    """Parse defensif : le mode JSON strict n'est garanti par aucune passerelle."""
    t = re.sub(r"^```(?:json)?|```$", "", texte.strip(),
               flags=re.MULTILINE).strip()
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


def appeler(client, f, conf, url, params_minimax, json_mode=True):
    kw = {"model": f["modele"], "max_tokens": 512,
          "messages": [{"role": "user", "content": [
              contenu_image(url, f, conf, params_minimax),
              {"type": "text", "text": CONSIGNE}]}]}
    if json_mode:
        kw["response_format"] = {"type": "json_object"}
    try:
        return client.chat.completions.create(**kw)
    except Exception as e:  # noqa: BLE001
        # response_format n'est garanti par aucune de ces passerelles : une
        # seule nouvelle tentative sans lui, puis on laisse remonter.
        if json_mode and any(m in str(e).lower() for m in
                             ("response_format", "unsupported", "invalid",
                              "unrecognized", "not supported")):
            return appeler(client, f, conf, url, params_minimax,
                           json_mode=False)
        raise


def lire_une(client, f, conf, ligne, taille, params_minimax) -> dict:
    url = ligne.image_url
    if taille != "400":
        url = url.replace(".400.jpg", TAILLES[taille])
    base = {c: "" for c in CHAMPS}
    base.update({"erreur": "", "tokens_entree": 0, "tokens_sortie": 0})
    try:
        r = appeler(client, f, conf, url, params_minimax)
        lu = extraire_json(r.choices[0].message.content or "")
        base.update({c: str(lu.get(c, "")) for c in CHAMPS})
        if r.usage:
            base["tokens_entree"] = r.usage.prompt_tokens or 0
            base["tokens_sortie"] = r.usage.completion_tokens or 0
    except Exception as e:  # noqa: BLE001 - l'echec est une donnee, pas un arret
        # APIConnectionError se resume a "Connection error." et masque la cause
        # httpx : sans elle on ne distingue pas le DNS, le TLS, un refus de
        # connexion et un en-tete mal forme.
        cause = getattr(e, "__cause__", None)
        detail = f" | cause: {type(cause).__name__}: {cause}" if cause else ""
        base["erreur"] = f"{type(e).__name__}: {e}{detail}"[:400]
    base.update({"code": ligne.code, "marque_tag": ligne.marque_tag,
                 "brands": ligne.brands, "bras": ligne.bras,
                 "tag_halal": ligne.tag_halal,
                 "sous_categorie": ligne.sous_categorie,
                 "url_lue": url, "taille_demandee": taille,
                 "fournisseur": f["nom"], "modele": f["modele"]})
    return base


def diagnostiquer(erreur: str) -> str:
    e = erreur.lower()
    if "illegal header" in e:
        return ("En-tete Authorization mal forme : la cle contient un blanc. "
                "Corriger la valeur du secret.")
    if "credit" in e or "balance" in e or "quota" in e or "402" in e:
        return ("Compte sans credit. La cle est valide, le fournisseur refuse "
                "de servir. Approvisionner, ou passer au fournisseur suivant.")
    if "model agreement" in e or "community license" in e or "must submit" in e:
        return ("Le modele exige l'acceptation prealable de sa licence, une "
                "fois par compte.\n     C'est un engagement juridique : il "
                "revient au titulaire du compte de le prendre,\n     pas au "
                "script. Voir --accepter-licence, ou changer de modele.")
    if "auth" in e or "401" in e or "403" in e:
        return "Cle refusee. Verifier sa valeur et ses droits."
    if "image" in e or "modality" in e or "content" in e or "vision" in e:
        return ("Le fournisseur ne relaie pas l'image jusqu'au modele. "
                "En changer dans config/lecture_image.yaml, pas contourner.")
    return "Lancer src/couche2_diagnostic.py pour separer reseau et API."


# --------------------------------------------------------------- preflight

def preflight(conf, df, args, verbeux=True):
    """Un appel par fournisseur, dans l'ordre, jusqu'au premier qui passe.

    Tranche la question qui conditionne tout le reste : le fournisseur relaie-
    t-il l'image jusqu'au modele ? Une passerelle qui l'ignore repond quand
    meme, a partir du seul texte de la consigne, et rien dans le CSV ne le
    signalerait.
    """
    ligne = next(df[df.bras == "halal"].itertuples())
    for f in fournisseurs(conf, args.fournisseur, args.modele):
        if verbeux:
            titre(f"PREFLIGHT — {f['nom']} / {f['modele']}")
            print(f"  base_url : {f['base_url']}")
        if f["indisponible"]:
            print(f"  ECARTE : {f['indisponible']}")
            continue
        if f["blancs"]:
            print(f"  [avertissement] {f['env_cle']} contient {f['blancs']} "
                  "blanc(s) en debut ou fin. Nettoye ici, a corriger a la "
                  "source : Settings -> Secrets and variables -> Actions.")
        r = lire_une(client_pour(f), f, conf, ligne, args.taille,
                     args.params_minimax)
        if verbeux:
            print(f"  produit : {ligne.code}  {ligne.brands}")
            print(f"  url     : {r['url_lue']}")
            for c in CHAMPS:
                print(f"    {c:<22} {r[c]!r}")
            print(f"    {'tokens entree':<22} {r['tokens_entree']}")
            print(f"    {'cout de cet appel':<22} "
                  f"${cout(f, r['tokens_entree'], r['tokens_sortie']):.5f}")
        if r["erreur"]:
            print(f"\n  ECHEC : {r['erreur']}")
            print(f"  -> {diagnostiquer(r['erreur'])}")
            continue
        # Une image analysee coute des centaines de tokens. Sous ce seuil,
        # le fournisseur a repondu sans la regarder : la sortie serait inventee.
        if r["tokens_entree"] and r["tokens_entree"] < 200:
            print(f"\n  REFUS : {r['tokens_entree']} tokens d'entree seulement.")
            print("  Le fournisseur a repondu sans analyser l'image. Le lot")
            print("  produirait des lectures inventees.")
            continue
        print(f"\n  {f['nom']} valide. Image relayee et facturee.")
        return f
    return None


# ------------------------------------------------------------------- cibles

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


def accepter_licence(conf, args) -> int:
    """Envoie le prompt 'agree' exige par certains modeles avant tout usage.

    C'est l'acceptation d'un contrat de licence, pas une formalite technique.
    Le script ne la fait JAMAIS de lui-meme : elle n'a lieu que sur ce drapeau
    explicite, et le texte affiche les licences concernees avant d'envoyer.
    """
    reussites = 0
    for f in fournisseurs(conf, args.fournisseur, args.modele):
        if f["indisponible"]:
            print(f"  {f['nom']} ECARTE : {f['indisponible']}")
            continue
        titre(f"ACCEPTATION DE LICENCE — {f['nom']} / {f['modele']}")
        print("  Envoi du prompt 'agree' au modele. Cela engage le titulaire du")
        print("  compte a respecter la licence communautaire du modele et sa")
        print("  politique d'usage acceptable, dont les URL figurent dans le")
        print("  message d'erreur du fournisseur.")
        try:
            r = client_pour(f).chat.completions.create(
                model=f["modele"], max_tokens=16,
                messages=[{"role": "user", "content": "agree"}])
            print(f"  Reponse : {r.choices[0].message.content!r}")
            print("  Licence acceptee pour ce compte. Relancer le preflight.")
            reussites += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ECHEC : {type(e).__name__}: {e}"[:400])
            print(f"  -> {diagnostiquer(str(e))}")
            continue
    if not reussites:
        print("\n  Aucune licence acceptee.")
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--executer", action="store_true")
    ap.add_argument("--fournisseur", default=None,
                    help="force un fournisseur au lieu de l'ordre configure")
    ap.add_argument("--modele", default=None,
                    help="remplace le modele du fournisseur retenu")
    ap.add_argument("--accepter-licence", action="store_true",
                    help="envoie 'agree' au modele pour accepter sa licence")
    ap.add_argument("--max", type=int, default=None, dest="limite")
    ap.add_argument("--par-marque", type=int, default=3)
    ap.add_argument("--taille", choices=list(TAILLES), default="full")
    ap.add_argument("--params-minimax", action="store_true")
    ap.add_argument("--concurrence", type=int, default=6)
    args = ap.parse_args()

    conf = charger("lecture_image.yaml")
    con = connexion()
    df = cibles(con, args.limite, args.par_marque)
    titre("COUCHE 2 — lecture des emballages")
    print(f"  produits : {len(df)}  ({df.marque_tag.nunique()} marques, "
          f"{(df.bras == 'halal').sum()} halal / "
          f"{(df.bras == 'temoin').sum()} temoin)")
    print("  fournisseurs, dans l'ordre :")
    for f in fournisseurs(conf, args.fournisseur, args.modele):
        etat = f["indisponible"] or "cle presente"
        print(f"    {f['nom']:<24} {f['modele']:<42} {etat}")

    if args.accepter_licence:
        return accepter_licence(conf, args)

    if not (args.preflight or args.executer):
        print("\n  MODE ESTIMATION — aucun appel emis, aucun euro depense.")
        print("  Le cout par image est inconnu tant que --preflight n'a pas")
        print("  tourne. Enchainement : --preflight, puis --executer --max 20,")
        print("  puis le lot complet une fois le cout reel connu.")
        return 0

    retenu = preflight(conf, df, args)
    if retenu is None:
        echec("aucun fournisseur ne passe le preflight. Le lot ne part pas : "
              "mieux vaut zero lecture qu'un CSV de lectures inventees.")
    if args.preflight:
        return 0

    t0 = time.time()
    client = client_pour(retenu)
    resultats = []
    with cf.ThreadPoolExecutor(max_workers=args.concurrence) as ex:
        futurs = [ex.submit(lire_une, client, retenu, conf, l, args.taille,
                            args.params_minimax) for l in df.itertuples()]
        for i, fut in enumerate(cf.as_completed(futurs), 1):
            resultats.append(fut.result())
            if i % 25 == 0:
                print(f"    {i}/{len(futurs)}", flush=True)

    import pandas as pd
    out = pd.DataFrame(resultats)
    SORTIES.mkdir(exist_ok=True)
    chemin = SORTIES / "couche2_lecture_image.csv"
    out.to_csv(chemin, index=False)

    n_err = int((out.erreur != "").sum())
    te, ts = int(out.tokens_entree.sum()), int(out.tokens_sortie.sum())
    titre("RESULTAT")
    print(f"  fournisseur : {retenu['nom']} / {retenu['modele']}")
    print(f"  {len(out)} lectures en {time.time() - t0:.0f}s, "
          f"{n_err} echecs techniques")
    print(f"  tokens : {te} entree / {ts} sortie")
    print(f"  cout   : ${cout(retenu, te, ts):.4f}  "
          f"(${cout(retenu, te, ts) / max(len(out), 1):.5f} par produit)")
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
            print("  le taux d'erreur de CE fournisseur contre un codage humain.")

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
