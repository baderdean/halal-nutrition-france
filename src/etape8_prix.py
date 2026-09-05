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


def collecte_keyset(max_lots: int, taille: int) -> list[dict]:
    """Parcours par identifiant croissant, insensible au plafond de pages.

    Chaque lot demande les releves d'identifiant strictement superieur au
    dernier vu, toujours en page 1. Le plafond de 500 pages ne s'applique
    donc jamais. Si l'identifiant n'avance pas d'un lot a l'autre, le filtre
    n'est pas honore par le service : on s'arrete plutot que de boucler sur
    la meme page en croyant collecter.
    """
    lignes, dernier, lot = [], 0, 0
    while lot < max_lots:
        url = f"{API}?size={taille}&order_by=id&id__gt={dernier}"
        try:
            with http(url) as r:
                d = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    429 apres id {dernier}, pause 30 s")
                time.sleep(30)
                continue
            print(f"    {e.code} apres id {dernier} : arret du parcours keyset")
            return lignes
        items = d.get("items", [])
        if not items:
            print(f"    fin du parcours a l'id {dernier}")
            break
        ids = [i.get("id") for i in items if i.get("id") is not None]
        if not ids or max(ids) <= dernier:
            print(f"    [ECHEC] l'identifiant n'avance pas (dernier={dernier}) :"
                  f"\n    le filtre id__gt n'est pas honore. Arret.")
            return lignes
        lignes.extend(items)
        dernier = max(ids)
        lot += 1
        if lot % 25 == 0 or lot == 1:
            print(f"    lot {lot} : cumul {len(lignes)} / {d.get('total')} "
                  f"(id {dernier})", flush=True)
        time.sleep(0.15)
    return lignes


def collecte_api(max_pages: int, taille: int) -> list[dict]:
    """Pagination par numero de page. Plafonnee a 500 pages par le service :
    ne sert que de repli si le parcours par identifiant echoue."""
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
    titre("Couche 8 — prix au kilo")
    print(f"{len(p)} releves de prix charges.")
    if JOURNAL.exists():
        j = json.loads(JOURNAL.read_text(encoding="utf-8"))
        print(f"  Collecte du {j['date_collecte']} : {j['releves_collectes']} "
              f"releves aspires\n  sur {j['total_annonce_par_api']} annonces "
              f"par l'API, dont {j['releves_du_perimetre']} dans le\n  "
              f"perimetre carne.")
        if not j.get("collecte_complete"):
            print("  [ATTENTION] COLLECTE INCOMPLETE. Une couverture faible "
                  "ci-dessous ne\n  prouve alors rien : elle peut venir de la "
                  "collecte et non du terrain.")
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

    titre("Prix au kilo, a gamme egale")
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
    print("\nEcrit : sorties/u0_couverture_prix.csv, u1_prix_par_gamme.csv")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collecte", action="store_true",
                    help="telecharge depuis Open Prices (runner GitHub)")
    ap.add_argument("--sonder", action="store_true",
                    help="teste les points d'entree sans rien telecharger")
    ap.add_argument("--max-pages", type=int, default=4000)
    ap.add_argument("--taille-page", type=int, default=100)
    a = ap.parse_args()

    if a.sonder:
        sonder()
        return 0
    if a.collecte:
        sonder()
        titre("Collecte par l'API paginee")
        titre("Collecte, parcours par identifiant")
        lignes = collecte_keyset(a.max_pages, a.taille_page)
        # Repli : mieux vaut 50 000 releves declares incomplets que zero.
        if len(lignes) < 50000:
            titre("Repli sur la pagination par numero de page")
            print("Le parcours par identifiant n'a pas abouti. La pagination")
            print("classique est PLAFONNEE a 500 pages par le service : ce qui")
            print("suit sera un echantillon, pas la base entiere, et la couche")
            print("8 doit le declarer comme tel.")
            secours = collecte_api(min(a.max_pages, 500), a.taille_page)
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
        }, indent=2) + "\n", encoding="utf-8")
        print(f"  -> {JOURNAL}")
        return 0
    return analyser()


if __name__ == "__main__":
    sys.exit(main())
