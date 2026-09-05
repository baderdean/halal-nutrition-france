#!/usr/bin/env python3
"""Couche 8 — prix au kilo, via Open Prices.

Le prix est la variable manquante de toute cette etude. Sans lui, on ne peut
pas distinguer « le halal est moins bon » de « le halal est vendu sur un
segment de prix plus bas », qui est l'explication la plus banale et la moins
testee. Open Prices est le projet de releves de prix d'Open Food Facts,
alimente par des contributeurs, sous licence ODbL comme le reste.

DEUX MODES, parce que l'environnement de developpement ne joint pas
prices.openfoodfacts.org (CONNECT 403 de la politique de sortie reseau) alors
que le runner GitHub le joint :

  --collecte  tourne sur le runner. Sonde les points d'entree candidats, puis
              telecharge et ecrit donnees_prix/prix_open_prices.csv, qui est
              commite dans le depot. Aucune analyse.
  (defaut)    tourne partout. Lit le CSV commite, l'apparie au perimetre par
              code-barres, et compare le prix au kilo.

CE QU'IL FAUT ATTENDRE. Open Prices est un releve BENEVOLE : la couverture
sera faible et surtout NON ALEATOIRE. Un contributeur photographie ce qu'il
achete, dans les magasins ou il va. La couverture est donc mesuree et publiee
par bras AVANT toute comparaison, comme en couche 7, et la regle des 30
s'applique cellule par cellule. Une couverture trop faible donne un resultat
« non testable », pas un resultat nul.

UN PRIX RELEVE N'EST PAS UN PRIX DE MARCHE. Il vaut pour un magasin, un jour,
parfois en promotion. Les releves marques comme remises sont exclus par
defaut : une promotion ne dit rien du positionnement d'une gamme.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

from commun import (COMPLET, PERIMETRE, RACINE, SORTIES, borne, connexion,
                    echec, titre)
from etape5_produits_emblematiques import ic_diff

PRIX = RACINE / "donnees_prix" / "prix_open_prices.csv"
JOURNAL = RACINE / "donnees_prix" / "collecte.json"
SEUIL = 30
GRAINE = 20260904

# Points d'entree candidats, essayes dans l'ordre. Le service a change de
# forme plusieurs fois ; plutot que d'en deviner un et d'echouer en silence,
# on les sonde tous et on publie ce qui repond.
# Sonde du 2026-09-05 depuis un runner GitHub : les quatre points de dump
# repondent 404, l'API paginee et /status repondent 200. La collecte passe
# donc par l'API. La liste est conservee : si un dump apparait, la sonde le
# verra sans qu'on ait a y penser.
CANDIDATS_DUMP = [
    "https://prices.openfoodfacts.org/data/dump/prices.csv.gz",
    "https://prices.openfoodfacts.org/data/prices.csv.gz",
    "https://prices.openfoodfacts.org/data/dump/prices.jsonl.gz",
    "https://openfoodfacts-ds.s3.eu-west-3.amazonaws.com/open_prices.csv.gz",
]
API = "https://prices.openfoodfacts.org/api/v1/prices"
UA = "halal-nutrition-france/1.0 (etude academique; contact via depot GitHub)"


def http(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json"})
    return urllib.request.urlopen(req, timeout=timeout)


# Le run du 2026-09-05 a bute sur un PLAFOND DE PAGINATION : l'API annonce
# 307 196 releves mais renvoie 400 des la page 501, soit 50 000 releves au
# plus. Une collecte par numero de page ne peut donc pas etre exhaustive, et
# conclure « couverture insuffisante » sur 16 % de la base serait un faux
# resultat negatif. Ces parametres sont sondes pour trouver un parcours par
# CLE (keyset) qui ne depend pas du numero de page.
SONDES_PAGINATION = [
    ("plafond de page", f"{API}?size=1&page=501"),
    ("tri par id", f"{API}?size=1&order_by=id"),
    ("tri par -id", f"{API}?size=1&order_by=-id"),
    ("filtre id__gte", f"{API}?size=1&id__gte=1000&order_by=id"),
    ("filtre id__gt", f"{API}?size=1&id__gt=1000&order_by=id"),
    ("filtre created__gte", f"{API}?size=1&created__gte=2025-01-01"),
    ("filtre date__gte", f"{API}?size=1&date__gte=2025-01-01"),
    ("taille 1000", f"{API}?size=1000"),
    # Le balayage complet bute sur le decalage profond : la page 300 met
    # plusieurs secondes. Or on ne veut pas la base entiere, seulement les
    # 90 337 codes du perimetre. Si le service accepte une LISTE de codes,
    # 900 requetes ciblees remplacent 308 pages de plus en plus lentes.
    ("liste product_code__in",
     f"{API}?size=10&product_code__in=3263670455014,3263670790214"),
    ("liste code__in",
     f"{API}?size=10&code__in=3263670455014,3263670790214"),
    ("code unique",
     f"{API}?size=10&product_code=3263670455014"),
]


def sonder() -> None:
    """Publie ce qui repond depuis cette machine, sans rien conclure."""
    titre("Sonde des points d'entree Open Prices")
    for url in CANDIDATS_DUMP + [f"{API}?size=1", f"{API.rsplit('/', 1)[0]}/status"]:
        try:
            with http(url, timeout=30) as r:
                tete = r.read(200)
                print(f"  {r.status}  {url}")
                print(f"        {tete[:120]!r}")
        except urllib.error.HTTPError as e:
            print(f"  {e.code}  {url}  ({e.reason})")
        except Exception as e:                       # noqa: BLE001
            print(f"  ---  {url}  ({type(e).__name__}: {e})")

    titre("Sonde du parcours : depasser le plafond de 500 pages")
    for nom, url in SONDES_PAGINATION:
        try:
            with http(url, timeout=30) as r:
                d = json.loads(r.read())
                items = d.get("items", [])
                ids = [i.get("id") for i in items[:2]]
                print(f"  {r.status}  {nom:22s} total={d.get('total')} "
                      f"ids={ids}")
        except urllib.error.HTTPError as e:
            print(f"  {e.code}  {nom:22s} ({e.reason})")
        except Exception as e:                       # noqa: BLE001
            print(f"  ---  {nom:22s} ({type(e).__name__}: {e})")


def code_barres(releve: dict) -> str | None:
    """Le code peut etre au premier niveau ou sous l'objet produit.

    La sonde a montre la forme {"id":..,"product":{"code":"154151..."}}. Se
    fier au seul champ de premier niveau ferait rejeter tous les releves en
    silence, ce qui ressemblerait a « Open Prices ne couvre pas nos produits ».
    """
    c = releve.get("product_code")
    if not c:
        prod = releve.get("product") or {}
        c = prod.get("code") if isinstance(prod, dict) else None
    return str(c) if c else None


def codes_du_perimetre() -> set[str]:
    """Les codes a retenir. Sans ce filtre on commiterait tout Open Prices."""
    con = connexion()
    return set(con.execute(
        f"SELECT DISTINCT code FROM '{PERIMETRE}'").df().code.astype(str))


def mois(depuis: str = "2023-01") -> list[tuple[str, str]]:
    """Fenetres mensuelles de `depuis` a aujourd'hui, bornes incluses."""
    an, m = (int(x) for x in depuis.split("-"))
    fin = time.gmtime()
    out = []
    while (an, m) <= (fin.tm_year, fin.tm_mon):
        an2, m2 = (an + 1, 1) if m == 12 else (an, m + 1)
        out.append((f"{an:04d}-{m:02d}-01", f"{an2:04d}-{m2:02d}-01"))
        an, m = an2, m2
    return out


def collecte_fenetres(taille: int, max_pages_fenetre: int = 400) -> list[dict]:
    """Parcours par FENETRES DE DATES, pour contourner le plafond de pages.

    La sonde du 2026-09-05 a etabli trois choses :
      - la page 501 est refusee (400), quel que soit `size` ;
      - `id__gte` et `id__gt` sont IGNORES : id__gte=1000 renvoie l'id 1.
        Un parcours par cle sur l'identifiant est donc impossible ;
      - `date__gte` est honore (307 197 releves au total, 236 431 depuis
        2025-01-01) et `size=1000` est accepte.

    On decoupe donc par mois. Chaque mois tient tres en dessous du plafond,
    et les releves sont dedupliques par identifiant : si `date__lte` n'etait
    pas honore, les fenetres se recouvriraient sans fausser le resultat, au
    prix d'un peu de temps.
    """
    vus, lignes = set(), []
    for debut, fin in mois():
        page = 1
        while page <= max_pages_fenetre:
            url = (f"{API}?size={taille}&page={page}"
                   f"&date__gte={debut}&date__lt={fin}")
            try:
                with http(url) as r:
                    d = json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f"    429 sur {debut}, pause 30 s")
                    time.sleep(30)
                    continue
                print(f"    {e.code} sur {debut} page {page} : fenetre "
                      f"abandonnee")
                break
            items = d.get("items", [])
            if not items:
                break
            neufs = [i for i in items if i.get("id") not in vus]
            vus.update(i.get("id") for i in items)
            lignes.extend(neufs)
            page += 1
            time.sleep(0.1)
        print(f"    {debut} : cumul {len(lignes)}", flush=True)
    return lignes


def collecte_par_codes(codes: list[str], lot: int = 250) -> list[dict] | None:
    """Interroge l'API par lots de codes-barres du perimetre.

    Evite le decalage profond : chaque requete est un filtre selectif, pas un
    saut de 300 000 lignes. Rend None si le service n'honore pas le filtre,
    ce qui se detecte en demandant deux codes precis et en verifiant que la
    reponse ne contient qu'eux — un filtre ignore renverrait toute la base et
    se lirait a tort comme une couverture excellente.
    """
    sonde = f"{API}?size=10&product_code__in={codes[0]},{codes[1]}"
    try:
        with http(sonde) as r:
            d = json.loads(r.read())
    except Exception as e:                           # noqa: BLE001
        print(f"  filtre par liste indisponible ({type(e).__name__}) : "
              f"repli sur le balayage")
        return None
    rendus = {code_barres(i) for i in d.get("items", [])}
    if not rendus or not rendus <= {codes[0], codes[1]}:
        print(f"  le filtre product_code__in n'est pas honore "
              f"(total={d.get('total')}) : repli sur le balayage")
        return None

    # Le controle a deux codes ne prouve rien sur un lot de 250 : une URL
    # longue peut faire tomber le filtre cote service sans le dire. On mesure
    # donc, lot par lot, la part des reponses qui appartient aux codes
    # demandes, et le journal de collecte la publie.
    lignes, dedans, recus_total = [], 0, 0
    for i in range(0, len(codes), lot):
        tranche = codes[i:i + lot]
        attendus = set(tranche)
        url = f"{API}?size=1000&product_code__in={','.join(tranche)}"
        try:
            with http(url) as r:
                recus = json.loads(r.read()).get("items", [])
            recus_total += len(recus)
            dedans += sum(1 for x in recus if code_barres(x) in attendus)
            lignes.extend(recus)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30)
                continue
            print(f"    {e.code} sur le lot {i // lot} : ignore")
        if (i // lot) % 20 == 0:
            print(f"    lot {i // lot} / {len(codes) // lot} : cumul "
                  f"{len(lignes)}", flush=True)
        time.sleep(0.05)
    taux = 100.0 * dedans / recus_total if recus_total else 0.0
    print(f"  Filtre honore sur {taux:.1f} % des reponses "
          f"({dedans} / {recus_total}).")
    if taux < 90:
        print("  [ATTENTION] Le filtre par liste n'a pas ete honore a cette "
              "taille de lot.\n  La collecte n'est donc PAS ciblee : c'est un "
              "balayage de la base, qu'il\n  faut declarer comme tel. Le "
              "filtrage sur le perimetre reste correct,\n  seule la "
              "description de la methode change.")
    globals()["_TAUX_FILTRE"] = round(taux, 1)
    return lignes


def collecte_api(max_pages: int, taille: int) -> list[dict]:
    """Pagination par numero de page. Voie principale.

    Le plafond du service porte sur le NUMERO de page (la page 501 est
    refusee), pas sur le decalage : a 1000 releves par page, les 307 197 de
    la base tiennent en 308 pages. C'est ce que la premiere collecte a rate
    en demandant 100 releves par page, ce qui butait a 50 000.
    """
    lignes, page = [], 1
    while page <= max_pages:
        url = f"{API}?size={taille}&page={page}"
        try:
            with http(url) as r:
                d = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    429 page {page}, pause 30 s")
                time.sleep(30)
                continue
            print(f"    {e.code} page {page} : arret")
            break
        items = d.get("items", d if isinstance(d, list) else [])
        if not items:
            break
        lignes.extend(items)
        total = d.get("total")
        if page == 1:
            print(f"    total annonce par l'API : {total}")
        print(f"    page {page} : {len(items)} releves, cumul {len(lignes)}",
              flush=True)
        page += 1
        if total and len(lignes) >= total:
            break
        time.sleep(0.2)
    return lignes


def ecrire(lignes: list[dict]) -> None:
    """Ne garde que les champs utiles. Aucune donnee personnelle de releveur."""
    champs = ["product_code", "price", "price_is_discounted", "price_without_discount",
              "currency", "price_per", "date", "location_osm_type",
              "location_osm_id", "category_tag"]
    PRIX.parent.mkdir(parents=True, exist_ok=True)
    with open(PRIX, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=champs, extrasaction="ignore")
        w.writeheader()
        garde = 0
        for l in lignes:
            code = code_barres(l)
            if not code:
                continue          # releve de produit en vrac, sans code-barres
            ligne = {c: l.get(c) for c in champs}
            ligne["product_code"] = code
            w.writerow(ligne)
            garde += 1
    print(f"  {garde} releves avec code-barres retenus sur {len(lignes)}.")
    print(f"  -> {PRIX} ({sum(1 for _ in open(PRIX)) - 1} lignes)")


def filtrer_perimetre(lignes: list[dict]) -> list[dict]:
    codes = codes_du_perimetre()
    print(f"  {len(codes)} codes-barres dans le perimetre carne.")
    gardees = [l for l in lignes if code_barres(l) in codes]
    print(f"  {len(gardees)} releves sur {len(lignes)} portent un produit du "
          f"perimetre.")
    return gardees


def analyser() -> int:
    if not PRIX.exists():
        echec(f"{PRIX} absent. Lancer d'abord le workflow couche8-prix "
              f"(mode --collecte sur un runner GitHub), qui commite ce fichier.")
    p = pd.read_csv(PRIX, dtype={"product_code": str})
    # La collecte ne deduplique pas : deux lots peuvent rendre le meme releve.
    # Deux releves reellement identiques (meme produit, meme prix, meme jour,
    # meme magasin) sont indiscernables d'un doublon technique, donc ecartes.
    # C'est conservateur : on perd quelques vrais doublons plutot que de
    # compter plusieurs fois le meme.
    avant_dedup = len(p)
    p = p.drop_duplicates()
    titre("Couche 8 — prix au kilo")
    if avant_dedup != len(p):
        print(f"{avant_dedup - len(p)} lignes identiques ecartees "
              f"(doublons de collecte indiscernables de vrais doublons).")
    print(f"{len(p)} releves de prix charges.")
    if JOURNAL.exists():
        j = json.loads(JOURNAL.read_text(encoding="utf-8"))
        print(f"  Collecte du {j['date_collecte']} : {j['releves_collectes']} "
              f"releves aspires\n  sur {j['total_annonce_par_api']} annonces "
              f"par l'API, dont {j['releves_du_perimetre']} dans le\n  "
              f"perimetre carne.")
        part = j.get("part_de_la_base_aspiree_pct")
        if part is not None:
            print(f"  Part de la base aspiree : {part} %.")
        taux = j.get("filtre_par_codes_honore_pct")
        if taux is not None and taux < 90:
            print(f"  Le filtre par codes n'a ete honore que sur {taux} % des "
                  f"reponses : la\n  collecte est un balayage de la base, pas "
                  f"une interrogation ciblee. Cela\n  ne biaise pas le "
                  f"resultat — le filtrage sur le perimetre se fait ensuite —\n"
                  f"  mais la methode n'est pas celle que le nom suggere.")
        if part is not None and part < 90:
            print("  [ATTENTION] Moins de 90 % de la base aspiree. Une "
                  "couverture faible\n  ci-dessous peut venir de la collecte "
                  "et non du terrain.")
    print()

    # Un prix en promotion ne dit rien du positionnement d'une gamme.
    avant = len(p)
    if "price_is_discounted" in p:
        p = p[p.price_is_discounted != True]  # noqa: E712
    print(f"  Releves en promotion ecartes : {avant - len(p)}.")
    p = p[p.currency.isin(["EUR"])] if "currency" in p else p
    print(f"  Releves en euros retenus : {len(p)}.")

    con = connexion()
    d = con.execute(f"""
        SELECT code, sous_categorie, espece,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               CASE WHEN product_quantity BETWEEN 10 AND 5000
                    THEN product_quantity END AS format_g,
               {borne('salt_100g', 'sel')},
               {borne('proteins_100g', 'proteines')},
               nutriscore_score AS ns
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()

    j = d.merge(p, left_on="code", right_on="product_code", how="inner")
    titre("Couverture — a lire avant tout resultat")
    cov = (j.groupby("bras").code.nunique()
             .to_frame("produits_avec_prix")
             .join(d.groupby("bras").code.nunique().to_frame("produits")))
    cov["couverture_pct"] = (100 * cov.produits_avec_prix / cov.produits).round(2)
    print(cov.to_string())
    cov.to_csv(SORTIES / "u0_couverture_prix.csv")
    if cov.produits_avec_prix.min() < SEUIL:
        print(f"\n  Un bras est sous {SEUIL} produits apparies : aucune "
              f"comparaison n'est\n  testable. Open Prices est un releve "
              f"benevole, sa couverture du rayon\n  halal est ce qu'elle est. "
              f"Resultat NON TESTABLE, ce qui n'est pas un\n  resultat nul.")
        return 0

    # Prix au kilo : le prix du pack rapporte au grammage FIGE du perimetre,
    # jamais au grammage renvoye par le service de prix, pour que la variable
    # vienne d'une source unique et versionnee.
    j = j[j.format_g.notna() & j.price.notna()].copy()
    j["prix_kg"] = j.price / (j.format_g / 1000.0)
    j = j[(j.prix_kg > 0.5) & (j.prix_kg < 200)]      # bornes de plausibilite
    print(f"\n  {len(j)} releves exploitables apres grammage et bornes.")

    # L'UNITE D'ANALYSE EST LE PRODUIT, PAS LE RELEVE.
    #
    # Un produit peut porter 68 releves de prix : autant de passages en
    # magasin, pas 68 produits. Comparer des releves donne le poids d'une
    # gamme aux articles les plus photographies et fait franchir la regle des
    # 30 a des cellules qui ne comptent que quinze produits. La premiere
    # version de cette couche faisait exactement cela, et trois de ses quatre
    # ecarts « etablis » ne survivent pas a la correction.
    j = (j.groupby(["code", "sous_categorie", "espece", "bras", "marque",
                    "ns", "sel", "proteines"], dropna=False)
           .prix_kg.median().reset_index())
    print(f"  {len(j)} PRODUITS distincts apres agregation des releves.")

    titre("Prix au kilo, a gamme egale (un point par produit)")
    rng = np.random.default_rng(GRAINE)
    lignes = []
    for sc, g in j.groupby("sous_categorie"):
        a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
        if len(a) < SEUIL or len(b) < SEUIL:
            continue
        r = ic_diff(a.prix_kg.to_numpy(), b.prix_kg.to_numpy(), rng)
        if not r:
            continue
        etabli = "etabli" if (r[1] > 0 or r[2] < 0) else "non etabli"
        print(f"  {sc:24s} halal {a.prix_kg.median():6.2f} EUR/kg  temoin "
              f"{b.prix_kg.median():6.2f}   ecart {r[0]:+6.2f} "
              f"[{r[1]:+6.2f} ; {r[2]:+6.2f}]  {etabli}")
        lignes.append({"sous_categorie": sc, "n_halal": len(a),
                       "n_temoin": len(b),
                       "prix_kg_halal": round(a.prix_kg.median(), 2),
                       "prix_kg_temoin": round(b.prix_kg.median(), 2),
                       "ecart": round(r[0], 2), "ic95_bas": round(r[1], 2),
                       "ic95_haut": round(r[2], 2),
                       "etabli": etabli == "etabli"})
    if not lignes:
        print("  Aucune gamme n'atteint le seuil des deux cotes.")
    pd.DataFrame(lignes).to_csv(SORTIES / "u1_prix_par_gamme.csv", index=False)
    # ---- Le prix explique-t-il l'ecart nutritionnel ?
    titre("Prix et nutrition cote a cote, sur les MEMES produits")
    print("L'explication la plus banale de l'ecart nutritionnel serait que le")
    print("halal se vend sur un segment de prix plus bas. Elle se teste en")
    print("mettant les deux ecarts en regard, sur les seuls produits qui ont")
    print("un prix. Un ecart de prix POSITIF avec un ecart de Nutri-Score")
    print("positif ruine l'explication : le produit est a la fois plus cher")
    print("et moins bon.\n")
    lignes2 = []
    for sc, g in j.groupby("sous_categorie"):
        a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
        if len(a) < SEUIL or len(b) < SEUIL:
            continue
        rp = ic_diff(a.prix_kg.to_numpy(), b.prix_kg.to_numpy(), rng)
        rn = ic_diff(a.ns.to_numpy(float), b.ns.to_numpy(float), rng)
        if not rp or not rn:
            continue
        # Le verdict se lit sur les INTERVALLES, pas sur le point : un ecart
        # de +0.0 dont l'intervalle contient zero ne dit ni mieux ni moins
        # bien, et le ranger d'un cote serait inventer un resultat.
        def sens(r, mieux_si_negatif=True):
            if r[1] > 0:
                return "plus cher" if not mieux_si_negatif else "moins bon"
            if r[2] < 0:
                return "moins cher" if not mieux_si_negatif else "meilleur"
            return "non etabli"

        vp = sens(rp, mieux_si_negatif=False)
        vn = sens(rn)
        verdict = f"{vp} / {vn}"
        print(f"  {sc:22s} prix {rp[0]:+6.2f} EUR/kg [{rp[1]:+.2f} ; {rp[2]:+.2f}]"
              f"   Nutri-Score {rn[0]:+5.1f} [{rn[1]:+.1f} ; {rn[2]:+.1f}]"
              f"   {verdict}")
        lignes2.append({"sous_categorie": sc, "n_halal": len(a),
                        "n_temoin": len(b),
                        "ecart_prix_kg": round(rp[0], 2),
                        "prix_ic95_bas": round(rp[1], 2),
                        "prix_ic95_haut": round(rp[2], 2),
                        "ecart_nutriscore": round(rn[0], 1),
                        "ns_ic95_bas": round(rn[1], 1),
                        "ns_ic95_haut": round(rn[2], 1),
                        "verdict": verdict})
    pd.DataFrame(lignes2).to_csv(SORTIES / "u2_prix_et_nutrition.csv",
                                 index=False)
    print("\n  Ces ecarts nutritionnels portent sur le SOUS-ENSEMBLE des")
    print("  produits ayant un prix releve, pas sur le perimetre entier : ils")
    print("  ne remplacent pas ceux des couches 3 et 6.")

    # ---- Q1 : dans un bras, le moins cher est-il le moins bon ?
    titre("Q1 — le moins cher est-il le moins bon, DANS un meme bras ?")
    print("Correlation de rang entre prix au kilo et Nutri-Score continu, a")
    print("gamme egale. Un rho POSITIF signifie que plus cher va avec MOINS")
    print("bon ; negatif, que plus cher va avec meilleur. IC par bootstrap.\n")
    lignes3 = []
    for sc, g in j.groupby("sous_categorie"):
        for bras in ("halal", "temoin"):
            sous = g[g.bras == bras]
            if len(sous) < SEUIL:
                continue
            r = spearman_boot(sous.prix_kg, sous.ns, rng)
            if not r:
                continue
            etabli = "etabli" if (r[1] > 0 or r[2] < 0) else "non etabli"
            print(f"  {sc:22s} {bras:7s} n={len(sous):4d}  rho {r[0]:+.3f} "
                  f"[{r[1]:+.3f} ; {r[2]:+.3f}]  {etabli}")
            lignes3.append({"sous_categorie": sc, "bras": bras, "n": len(sous),
                            "rho": round(r[0], 3), "ic95_bas": round(r[1], 3),
                            "ic95_haut": round(r[2], 3),
                            "etabli": etabli == "etabli"})
    pd.DataFrame(lignes3).to_csv(SORTIES / "u3_gradient_prix_qualite.csv",
                                 index=False)

    print("\n  Detail par tercile de prix, bras halal :\n")
    for sc, g in j.groupby("sous_categorie"):
        h = g[g.bras == "halal"]
        if len(h) < SEUIL:
            continue
        h = h.assign(bande=pd.qcut(h.prix_kg, 3,
                                   labels=["bas", "moyen", "haut"]))
        t = (h.groupby("bande", observed=True)
              .agg(n=("ns", "size"), prix_kg=("prix_kg", "median"),
                   nutriscore=("ns", "median"), sel=("sel", "median"),
                   proteines=("proteines", "median")).round(2))
        print(f"  {sc}")
        print("   " + t.to_string().replace("\n", "\n   "))
        t.to_csv(SORTIES / f"u4_terciles_halal_{sc}.csv")

    # ---- Q2 : a prix egal, le halal reste-t-il moins bon ?
    titre("Q2 — a PRIX EGAL, le halal reste-t-il moins bon ?")
    print("Terciles de prix calcules sur la gamme entiere, les deux bras")
    print("confondus, puis comparaison halal / temoin DANS chaque bande. Si")
    print("l'ecart disparait a prix egal, il etait un corollaire du prix ; s'il")
    print("survit, le prix ne l'explique pas.\n")
    lignes4 = []
    for sc, g in j.groupby("sous_categorie"):
        if (g.bras == "halal").sum() < SEUIL:
            continue
        g = g.assign(bande=pd.qcut(g.prix_kg, 3,
                                   labels=["bas", "moyen", "haut"]))
        print(f"  {sc}")
        for b in ["bas", "moyen", "haut"]:
            a = g[(g.bande == b) & (g.bras == "halal")]
            c = g[(g.bande == b) & (g.bras == "temoin")]
            if len(a) < SEUIL or len(c) < SEUIL:
                print(f"    bande {b:6s} n={len(a):3d}/{len(c):4d}  "
                      f"sous le seuil de {SEUIL} : decrit, jamais teste")
                lignes4.append({"sous_categorie": sc, "bande": b,
                                "n_halal": len(a), "n_temoin": len(c),
                                "testable": False})
                continue
            rn = ic_diff(a.ns.to_numpy(float), c.ns.to_numpy(float), rng)
            rs = ic_diff(a.sel.to_numpy(float), c.sel.to_numpy(float), rng)
            etabli = "etabli" if (rn[1] > 0 or rn[2] < 0) else "non etabli"
            print(f"    bande {b:6s} n={len(a):3d}/{len(c):4d}  prix halal "
                  f"{a.prix_kg.median():5.2f} contre {c.prix_kg.median():5.2f}"
                  f"   Nutri-Score {rn[0]:+.1f} [{rn[1]:+.1f} ; {rn[2]:+.1f}] "
                  f"{etabli}   sel {rs[0]:+.2f} [{rs[1]:+.2f} ; {rs[2]:+.2f}]")
            lignes4.append({"sous_categorie": sc, "bande": b,
                            "n_halal": len(a), "n_temoin": len(c),
                            "prix_halal": round(a.prix_kg.median(), 2),
                            "prix_temoin": round(c.prix_kg.median(), 2),
                            "ecart_nutriscore": round(rn[0], 1),
                            "ns_ic95_bas": round(rn[1], 1),
                            "ns_ic95_haut": round(rn[2], 1),
                            "ecart_sel": round(rs[0], 2),
                            "sel_ic95_bas": round(rs[1], 2),
                            "sel_ic95_haut": round(rs[2], 2),
                            "testable": True, "etabli": etabli == "etabli"})
    pd.DataFrame(lignes4).to_csv(SORTIES / "u5_a_prix_egal.csv", index=False)

    print("\nEcrit : sorties/u0_couverture_prix.csv, u1_prix_par_gamme.csv,")
    print("        u2_prix_et_nutrition.csv, u3_gradient_prix_qualite.csv,")
    print("        u4_terciles_halal_*.csv, u5_a_prix_egal.csv")
    return 0


def spearman_boot(x, y, rng, n_boot: int = 4000):
    """Correlation de rang de Spearman, avec IC 95 % par bootstrap.

    Le rang plutot que la valeur : la relation prix / qualite n'a aucune
    raison d'etre lineaire, et une poignee de produits de luxe suffirait a
    dicter un coefficient de Pearson.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    m = ~(np.isnan(x) | np.isnan(y))
    x, y = x[m], y[m]
    if len(x) < 10:
        return None

    def rho(a, b):
        ra = pd.Series(a).rank().to_numpy()
        rb = pd.Series(b).rank().to_numpy()
        return float(np.corrcoef(ra, rb)[0, 1])

    bs = np.empty(n_boot)
    for i in range(n_boot):
        k = rng.integers(0, len(x), len(x))
        bs[i] = rho(x[k], y[k])
    return rho(x, y), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collecte", action="store_true",
                    help="telecharge depuis Open Prices (runner GitHub)")
    ap.add_argument("--sonder", action="store_true",
                    help="teste les points d'entree sans rien telecharger")
    ap.add_argument("--max-pages", type=int, default=4000)
    ap.add_argument("--taille-page", type=int, default=1000)
    a = ap.parse_args()

    if a.sonder:
        sonder()
        return 0
    if a.collecte:
        sonder()
        titre("Collecte par l'API paginee")
        # Le plafond porte sur le NUMERO de page, pas sur le decalage : la
        # page 501 est refusee quelle que soit la taille. A 1000 releves par
        # page, les 307 197 de la base tiennent en 308 pages, sous le
        # plafond. C'est la solution simple, et j'ai perdu deux runs a
        # chercher plus complique — un parcours par identifiant, que le
        # service ignore, puis des fenetres mensuelles dont la borne
        # superieure n'est pas honoree, si bien qu'elles se recouvrent toutes.
        titre("Collecte ciblee sur les codes-barres du perimetre")
        codes = sorted(codes_du_perimetre())
        lignes = collecte_par_codes(codes) or []
        if not lignes:
            titre("Collecte par pagination, 1000 releves par page")
            lignes = collecte_api(min(a.max_pages, 500), a.taille_page)
        # Repli : si la base depassait un jour 500 000 releves, la pagination
        # ne suffirait plus et les fenetres mensuelles, elles, passent a
        # l'echelle. Lentes mais sans plafond.
        if lignes and len(lignes) < 300000:
            titre("Repli sur les fenetres mensuelles")
            print("La pagination n'a pas rendu la base entiere. Les fenetres")
            print("sont lentes — leur borne superieure n'est pas honoree, donc")
            print("elles se recouvrent — mais elles ne butent sur aucun plafond.")
            secours = collecte_fenetres(a.taille_page)
            if len(secours) > len(lignes):
                lignes = secours
        if not lignes:
            echec("aucun releve recupere. Voir la sonde ci-dessus.")
        titre("Filtrage sur le perimetre carne")
        gardees = filtrer_perimetre(lignes)
        ecrire(gardees)
        # Sans ce journal, une collecte tronquee et une collecte complete
        # rendent le meme CSV, et une couverture faible se lit a tort comme
        # une absence de prix plutot que comme une collecte partielle.
        total = None
        try:
            with http(f"{API}?size=1") as r:
                total = json.loads(r.read()).get("total")
        except Exception:                            # noqa: BLE001
            pass
        JOURNAL.write_text(json.dumps({
            "date_collecte": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_annonce_par_api": total,
            "releves_collectes": len(lignes),
            "releves_du_perimetre": len(gardees),
            "collecte_complete": bool(total and len(lignes) >= total),
            "part_de_la_base_aspiree_pct": (
                round(100.0 * len(lignes) / total, 1) if total else None),
            "filtre_par_codes_honore_pct": globals().get("_TAUX_FILTRE"),
            "taille_page": a.taille_page,
            "plafond_pages_du_service": 500,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"  -> {JOURNAL}")
        return 0
    return analyser()


if __name__ == "__main__":
    sys.exit(main())
