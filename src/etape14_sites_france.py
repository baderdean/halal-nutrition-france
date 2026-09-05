#!/usr/bin/env python3
"""Couche 14 — classer les sites de production francais.

L'estampille sanitaire ovale porte un code de la forme FR 56.222.002 CE :
pays, DEPARTEMENT, code INSEE de la COMMUNE, numero d'ordre de
l'etablissement dans cette commune. La geographie se lit donc sans aucune
source externe.

Ce que le code ne donne PAS : le nom de l'entreprise. Il faut pour cela le
registre officiel des etablissements agrees, publie par le ministere de
l'Agriculture. Cet hote est refuse par la politique de sortie reseau de
l'environnement de developpement ; `--registre` le telecharge depuis un
runner GitHub, comme la couche 8 le fait pour les prix.

TROIS AVERTISSEMENTS AVANT DE CLASSER UN SITE.

  1. Un site est juge sur les recettes que ses DONNEURS D'ORDRE lui
     commandent. Un faconnier execute un cahier des charges. Le classement
     porte donc sur ce qui sort du site, pas sur son savoir-faire, et le
     retrait de la marque dominante mesure la part qui tient a un seul client.

  2. La couche 10 a etabli que le CRENEAU pese plus que le savoir-faire :
     72,5 % de la variance brute contre 30,4 % a strate fixee. Le classement
     est donc calcule sur l'ecart a la mediane de la strate, jamais sur le
     Nutri-Score brut.

  3. Sur le HALAL en particulier, la couche 10 a mesure une dispersion INTRA
     site plus grande que dans le temoin (7,82 contre 5,55) et un pouvoir
     explicatif du site plus faible (0,168 contre 0,304). Classer un site sur
     sa seule production halal est donc mal fonde, et le script le refuse
     au-dela d'un simple affichage descriptif.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, connexion, titre
from etape10_etablissements import normaliser_etablissement, utilisable
from etape8_prix import spearman_boot
from etape4_classement_complet import MOTIF_MER_MARQUE

GRAINE = 20260904
SEUIL = 30
SEUIL_DESC = 10
TIRAGES = 2000
# FR 56.222.002 : departement sur 2, commune INSEE sur 3, etablissement sur 3.
MOTIF_FR = re.compile(r"^fr-(\d{2})-(\d{3})-(\d{3})$")


# --- Registre officiel des etablissements agrees ------------------------------
#
# Le code d'agrement ne nomme personne. Le ministere de l'Agriculture publie
# la liste des etablissements agrees au titre du reglement (CE) 853/2004 :
# numero d'agrement, raison sociale, commune, activites. C'est la seule
# source qui transforme `fr-56-222-002` en une entreprise.
#
# Cet hote est refuse par la politique de sortie reseau de l'environnement de
# developpement (CONNECT 403). La sonde tourne donc sur un runner GitHub, et
# elle ne telecharge rien : elle publie ce qui repond et sous quel format,
# pour que le telechargement soit ecrit ensuite sur des faits et non sur une
# devinette d'URL. La couche 8 a coute deux heures pour avoir saute cette
# etape.
UA = "halal-nutrition-france/1.0 (etude nutritionnelle, contact via le depot)"
# Le premier passage (run 33989454409) a etabli deux faits.
#   1. La DGAL publie ses listes officielles en .txt brut sous
#      fichiers-publics.agriculture.gouv.fr/dgal/ListesOfficielles/.
#   2. Les requetes generiques ramenaient l'alimentation animale, les
#      escargots et l'entreposage, jamais la viande. La requete contenant
#      « 853/2004 » ne ramenait rien : la barre oblique cassait la recherche.
# Les requetes ci-dessous visent les listes de produits d'origine animale.
# Le deuxieme passage (run 33989901558) a trouve les jeux qui correspondent
# exactement aux sous-categories du perimetre — produits a base de viande,
# preparations de viandes, viandes hachees — mais l'API de RECHERCHE n'expose
# pas les ressources de tous les jeux. D'ou un second temps : rappeler chaque
# jeu par son identifiant, ce qui rend la liste complete de ses fichiers.
MOTIF_VIANDE = re.compile(
    r"viande|abattoir|charcuterie|volaille|gibier|boyaux|preparations de",
    re.IGNORECASE)

RECHERCHES = [
    "https://www.data.gouv.fr/api/1/datasets/?q=%C3%A9tablissements+agr%C3%A9%C3%A9s+viande&page_size=10",
    "https://www.data.gouv.fr/api/1/datasets/?q=%C3%A9tablissements+agr%C3%A9%C3%A9s+produits+origine+animale&page_size=10",
    "https://www.data.gouv.fr/api/1/datasets/?q=liste+%C3%A9tablissements+agr%C3%A9%C3%A9s+CE+abattoir&page_size=10",
    "https://www.data.gouv.fr/api/1/datasets/?q=agr%C3%A9%C3%A9s+CE+charcuterie+preparations+de+viandes&page_size=10",
    "https://www.data.gouv.fr/api/1/datasets/?q=%C3%A9tablissements+agr%C3%A9%C3%A9s&page_size=20",
]


def _http(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


def sonder_registre() -> int:
    """Publie ce qui repond, sans rien telecharger ni rien conclure."""
    titre("Sonde du registre des etablissements agrees")
    print("Ne telecharge rien. Publie les jeux de donnees qui repondent et")
    print("l'URL de leurs ressources, pour ecrire ensuite le telechargement")
    print("sur des faits.\n")
    trouve, jeux_viande = [], {}
    for url in RECHERCHES:
        print(f"  --- {url}")
        try:
            with _http(url, timeout=45) as r:
                d = json.loads(r.read())
        except urllib.error.HTTPError as e:
            print(f"      {e.code} ({e.reason})")
            continue
        except Exception as e:                          # noqa: BLE001
            print(f"      --- ({type(e).__name__}: {e})")
            continue
        for jeu in d.get("data", []):
            org = (jeu.get("organization") or {}).get("name", "?")
            if MOTIF_VIANDE.search(jeu.get("title") or ""):
                jeux_viande[jeu.get("id")] = jeu.get("title")
            print(f"      [{jeu.get('id')}] {jeu.get('title')}  ({org})")
            for res in jeu.get("resources", [])[:6]:
                print(f"          {res.get('format'):>6} "
                      f"{res.get('filesize')} o  {res.get('title')}")
                print(f"          {res.get('url')}")
                trouve.append({"jeu": jeu.get("title"), "org": org,
                               "format": res.get("format"),
                               "titre": res.get("title"),
                               "url": res.get("url")})
    if jeux_viande:
        print("\n  --- Second temps : les jeux dont le titre parle de viande,")
        print("      rappeles un par un pour obtenir leurs fichiers.")
        for jid, titre_jeu in sorted(jeux_viande.items()):
            url = f"https://www.data.gouv.fr/api/1/datasets/{jid}/"
            try:
                with _http(url, timeout=45) as r:
                    d = json.loads(r.read())
            except urllib.error.HTTPError as e:
                print(f"      {e.code} {jid} ({e.reason})")
                continue
            except Exception as e:                      # noqa: BLE001
                print(f"      --- {jid} ({type(e).__name__}: {e})")
                continue
            print(f"\n      [{jid}] {titre_jeu}")
            for res in d.get("resources", []):
                print(f"          {str(res.get('format')):>6}  "
                      f"{res.get('title')}")
                print(f"          {res.get('url')}")
                trouve.append({"jeu": titre_jeu, "org": "DGAL",
                               "format": res.get("format"),
                               "titre": res.get("title"),
                               "url": res.get("url")})

    if trouve:
        pd.DataFrame(trouve).drop_duplicates(subset=["url"]).sort_values(
            ["jeu", "url"]).to_csv(SORTIES / "s4_sonde_registre.csv",
                                   index=False)
        print(f"\n  {len(trouve)} ressources listees dans "
              "sorties/s4_sonde_registre.csv.")
        print("  RIEN n'est encore telecharge : le choix de la ressource se")
        print("  fait a la lecture de ce fichier, pas ici.")
    else:
        print("\n  Aucune ressource. Soit l'hote est refuse depuis cette")
        print("  machine, soit la recherche est mal formulee. Dans les deux")
        print("  cas, ne pas deviner une URL : relancer la sonde.")
    return 0


def recuperer_registre() -> int:
    titre("Telechargement du registre des etablissements agrees")
    print("Pas encore ecrit. La sonde (--sonder-registre) doit d'abord tourner")
    print("sur un runner GitHub et dire quelle ressource existe, sous quel")
    print("format et a quelle URL. Ecrire ce telechargement avant est la")
    print("meme erreur que la couche 8 a payee deux fois.")
    return 1


def decoder(code: str) -> dict | None:
    m = MOTIF_FR.match(code)
    if not m:
        return None
    dep, com, num = m.groups()
    return {"departement": dep, "insee": f"{dep}{com}", "numero": num}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sonder-registre", action="store_true",
                    dest="sonder_registre",
                    help="cherche le registre des agrements, sans rien "
                         "telecharger (runner GitHub)")
    ap.add_argument("--registre", action="store_true",
                    help="telecharge le registre des agrements (runner GitHub)")
    a = ap.parse_args()
    if a.sonder_registre:
        return sonder_registre()
    if a.registre:
        return recuperer_registre()

    con = connexion()
    d = con.execute(f"""
        SELECT code, emb_codes_tags, sous_categorie, espece,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               (list_contains(categories_tags, 'en:seafood')
                OR list_contains(categories_tags, 'en:fishes')
                OR list_contains(categories_tags, 'en:canned-fishes')
                OR list_contains(categories_tags, 'en:fish-fillets')) AS mer,
               nutriscore_score AS ns, {borne('salt_100g', 'sel')}
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    e = d.explode("emb_codes_tags").rename(columns={"emb_codes_tags": "et"})
    e = e[e.et.notna()].copy()
    e["et"] = e.et.astype(str)
    # brands_tags peut etre vide : on garde la ligne, avec une marque
    # nommee explicitement inconnue plutot qu'un vide silencieux.
    e["marque"] = [str(x) if x is not None and x == x and str(x) != ""
                   else "inconnue" for x in e.marque]
    e = e[e.et.apply(utilisable)]
    e["et"] = e.et.apply(normaliser_etablissement)

    titre("Decodage geographique des estampilles")
    dec = e.et.apply(decoder)
    e["departement"] = [x["departement"] if x else None for x in dec]
    e["insee"] = [x["insee"] if x else None for x in dec]
    fr = e[e.departement.notna()].copy()
    print(f"  {e.et.nunique()} etablissements, dont {fr.et.nunique()} francais")
    print(f"  au format decodable, dans {fr.departement.nunique()} departements.")
    print("\n  Le code donne le departement et la commune. Il ne donne PAS le")
    print("  nom de l'entreprise : cela demande le registre des agrements.")

    fr["strate"] = fr.sous_categorie + " / " + fr.espece
    t = fr.groupby("strate").size()
    fr = fr[fr.strate.isin(t[t >= SEUIL].index)].copy()
    fr["ecart"] = fr.ns - fr.groupby("strate").ns.transform("median")

    titre("Classement des sites francais, a composition egale")
    print("Ecart a la mediane de marche de la strate. Negatif = mieux que le")
    print("marche sur le meme type de produit.\n")
    lignes = []
    for et, g in fr.groupby("et"):
        if len(g) < SEUIL_DESC:
            continue
        med = float(g.ecart.median())
        if np.isnan(med):
            continue
        dom = (g.marque.value_counts()
                .rename_axis("m").reset_index(name="k")
                .sort_values(["k", "m"], ascending=[False, True]))
        premiere = dom.m.iloc[0]
        sans = g[g.marque != premiere] if len(dom) > 1 else g.iloc[0:0]
        lignes.append({
            "etablissement": et, "departement": g.departement.iloc[0],
            "insee": g.insee.iloc[0], "n": len(g),
            "n_marques": int(g.marque.nunique()),
            "n_halal": int((g.bras == "halal").sum()),
            "ecart_median": round(med, 1),
            "sel_median": round(float(g.sel.median()), 2),
            "marque_dominante": premiere,
            "part_dominante_pct": round(100.0 * dom.k.iloc[0] / len(g), 1),
            "part_mer_pct": round(100.0 * float(g.mer.mean()), 1),
            "ecart_sans_dominante": (round(float(sans.ecart.median()), 1)
                                     if len(sans) >= SEUIL_DESC else None),
            "regle_30": "franchie" if len(g) >= SEUIL else "sous 30",
        })
    t14 = pd.DataFrame(lignes).sort_values("ecart_median")
    # Meme defaut connu que le classement des marques : des residus de la mer
    # survivent a l'exclusion composee du perimetre. Un site dont le premier
    # client porte un nom de la mer est signale, pas retire : le retirer sans
    # verification produit par produit serait un jugement sur un nom.
    # Deux temoins independants : la categorie saisie sur le produit (un fait
    # de la base) et le nom du premier client (un indice, faillible dans les
    # deux sens). Un site est signale si l'un des deux se declenche.
    t14["alerte_mer"] = (
        (t14.part_mer_pct > 0)
        | t14.marque_dominante.str.contains(MOTIF_MER_MARQUE, regex=True,
                                            na=False))
    cols = ["etablissement", "departement", "n", "n_marques", "n_halal",
            "ecart_median", "sel_median", "marque_dominante",
            "part_dominante_pct", "ecart_sans_dominante", "regle_30",
            "part_mer_pct", "alerte_mer"]
    print("  --- 15 meilleurs, classement brut")
    print(t14.head(15)[cols].to_string(index=False))
    print("\n  --- 15 derniers, classement brut")
    print(t14.tail(15)[cols].to_string(index=False))
    t14.to_csv(SORTIES / "s1_sites_france.csv", index=False)
    print(f"\n  {len(t14)} sites classes, dont "
          f"{int((t14.regle_30 == 'franchie').sum())} au-dessus de 30 produits.")
    print("  `ecart_sans_dominante` mesure ce qui reste quand on retire le")
    print("  premier client du site : un ecart qui s'y effondre etait celui")
    print("  d'une marque, pas d'une usine.")
    n_mer = int(t14.alerte_mer.sum())
    if n_mer:
        print(f"\n  [ALERTE] {n_mer} sites sortent au moins un produit de la "
              f"mer, dont\n  {int(t14.head(15).alerte_mer.sum())} dans les 15 "
              "premiers du classement brut. L'etude porte sur les\n  produits "
              "carnes : le haut du classement BRUT n'est pas publiable. Le "
              "conserve\n  quand meme en CSV permet de verifier, plutot que "
              "de faire disparaitre.")

    pub = t14[(t14.regle_30 == "franchie") & (~t14.alerte_mer)]
    titre("Le meme classement, publiable")
    print("Sites d'au moins 30 produits, sans produit de la mer. C'est la")
    print("seule version de ce tableau qui peut sortir du depot.\n")
    print("  --- 10 meilleurs")
    print(pub.head(10)[cols].to_string(index=False))
    print("\n  --- 10 derniers")
    print(pub.tail(10)[cols].to_string(index=False))
    pub.to_csv(SORTIES / "s1b_sites_france_publiable.csv", index=False)
    print(f"\n  {len(pub)} sites. Etendue des ecarts medians : "
          f"{pub.ecart_median.min():+.1f} a {pub.ecart_median.max():+.1f} "
          "points de\n  Nutri-Score a composition egale.")

    # Un site qui sort beaucoup de halal est-il plus haut ou plus bas dans ce
    # classement ? Correlation de rang, IC par bootstrap sur les SITES.
    rho, bas, haut = spearman_boot(pub.n_halal, pub.ecart_median,
                                   np.random.default_rng(GRAINE),
                                   n_boot=TIRAGES)
    print(f"\n  Correlation de rang entre le nombre de produits halal d'un "
          f"site et\n  son ecart : rho = {rho:+.2f} [{bas:+.2f} ; {haut:+.2f}] "
          f"sur {len(pub)} sites.")
    print("  Un rho positif dont l'IC exclut zero dit que les sites qui sortent")
    print("  beaucoup de halal sont classes plus bas. Il ne dit PAS pourquoi :")
    print("  ces sites appartiennent a des specialistes et fabriquent leur")
    print("  propre recette. Le site et la marque n'y sont pas separables.")
    print(f"\n  A LIRE AVEC PRUDENCE : {int((pub.n_halal > 0).sum())} sites "
          f"sur {len(pub)} sortent au moins un produit\n  halal, et seulement "
          f"{int((pub.n_halal >= 10).sum())} en sortent au moins dix. La "
          "variable est nulle presque\n  partout : la correlation repose sur "
          "cette poignee, et son IC frole zero.")
    pd.DataFrame([{"n_sites": len(pub), "rho": round(rho, 3),
                   "ic95_bas": round(bas, 3), "ic95_haut": round(haut, 3),
                   "tirages": TIRAGES, "graine": GRAINE}]).to_csv(
        SORTIES / "s1c_correlation_halal_rang.csv", index=False)

    titre("Par departement — des effectifs plus solides")
    dep = (fr.groupby("departement")
             .agg(n=("ns", "size"), sites=("et", "nunique"),
                  marques=("marque", "nunique"),
                  n_halal=("bras", lambda x: int((x == "halal").sum())),
                  ecart_median=("ecart", "median"),
                  sel=("sel", "median")).round(2))
    dep = dep[dep.n >= SEUIL].sort_values("ecart_median")
    print(dep.to_string())
    dep.to_csv(SORTIES / "s2_departements.csv")

    titre("ET SUR LE HALAL ?")
    h = fr[fr.bras == "halal"]
    hs = (h.groupby("et").agg(n=("ns", "size"),
                              n_marques=("marque", "nunique"),
                              ecart_median=("ecart", "median"),
                              sel=("sel", "median")).round(2))
    hs = hs[hs.n >= SEUIL_DESC].sort_values("ecart_median")
    print(f"{len(hs)} sites francais ont au moins {SEUIL_DESC} produits halal.\n")
    print(hs.to_string())
    hs.to_csv(SORTIES / "s3_sites_halal.csv")
    print("\n  DESCRIPTIF, PAS UN CLASSEMENT. La couche 10 a montre que sur le")
    print("  halal la dispersion INTRA site depasse celle du temoin (7,82")
    print("  contre 5,55) et que le site explique moins (0,168 contre 0,304).")
    print("  Un site n'a donc pas de « niveau » halal stable, et le designer")
    print("  bon ou mauvais eleve sur cette base serait mal fonde.")

    print("\nEcrit : sorties/s1_sites_france.csv,")
    print("        s1b_sites_france_publiable.csv, s2_departements.csv,")
    print("        s3_sites_halal.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
