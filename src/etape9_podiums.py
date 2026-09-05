#!/usr/bin/env python3
"""Couche 9 — produits nommes : candidats, pas palmares.

Un podium par code-barres est ce que le lecteur retient. C'est aussi ce qui
engage le plus : nommer un article commercial precis comme le pire de son
rayon est une mise en cause publique, et une erreur de comparaison y devient
une accusation fausse.

CE QUE CE SCRIPT PRODUIT EST UNE LISTE DE CANDIDATS A VERIFIER, PAS UN
PALMARES PUBLIABLE. Trois obstacles l'imposent, tous constates sur ces
donnees :

  1. Le comparateur doit etre le meme aliment. Les categories Open Food Facts
     ne le garantissent pas : « Allumettes de poulet fumees » portait
     en:chicken-breasts et se retrouvait compare a du filet cru a 0,15 g de
     sel. Corrige dans config/produits_emblematiques.yaml, mais rien ne dit
     que le cas etait unique.

  2. Certains produits sont SOUS-TAGGUES et rien dans leurs categories ne
     revele leur forme. Un « Blanc de dinde » a 2,90 g de sel n'est pas une
     decoupe crue, quoi qu'en disent ses tags. La regle de plausibilite de
     forme, declaree en config, les ecarte et les publie a part.

  3. Un produit est UNE observation. Il n'a pas d'intervalle de confiance. On
     publie donc son PERCENTILE dans la distribution du comparateur, qui dit
     ou il se situe, et jamais un test.

Les valeurs sont DECLAREES par le fabricant, pas dosees en laboratoire. Une
valeur aberrante est plus souvent une erreur de saisie qu'un produit
extraordinaire, et c'est au premier chef vrai des extremes que ce script
remonte.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import (COMPLET, PERIMETRE, SORTIES, borne, charger, connexion,
                    titre)
from etape5_produits_emblematiques import expr_produit, liste_sql

import re


def normaliser(nom: str) -> str:
    """Cle d'appariement d'un nom de produit.

    Retire le mot « halal », les grammages et les articles : « Blanc de Dinde
    Fume Halal » et « Blanc de dinde fume » doivent tomber sur la meme cle.
    C'est volontairement grossier ; la coincidence de la marque, de la gamme
    et de l'espece fait le reste du travail.
    """
    s = str(nom).lower()
    s = re.sub(r"\bhalal\b|\d+\s*g\b|\ble\b|\bla\b|\bles\b|\bde\b|\bdu\b",
               " ", s)
    return re.sub(r"[^a-z]+", " ", s).strip()

SEUIL_REF = 30      # effectif minimal du comparateur
N_PODIUM = 10

# Plafond de VRAISEMBLANCE du sel pour un produit nomme.
#
# Les bornes de commun.py (15 g) protegent les medianes ; elles sont trop
# larges pour un palmares, ou une seule ligne fausse est une accusation. La
# charcuterie la plus salee du marche plafonne vers 6 g. Au-dela, la valeur
# est une erreur de saisie du contributeur, et le premier tirage l'a montre :
# un cordon bleu a 12 g, et un « Blanc de poulet - 25 % de sel » de Fleury
# Michon a 13,8 g, qui annonce donc l'inverse de ce qu'il affiche.
#
# Ces produits ne sont pas ecartes en silence : ils sont publies a part.
SEL_INVRAISEMBLABLE = 6.0


def main() -> int:
    cfg = charger("produits_emblematiques.yaml")
    q = charger("questions.yaml")
    libelles = {p["nom"]: p["libelle"] for p in cfg["produits"]}
    regles = cfg.get("plausibilite_forme", {})
    con = connexion()

    d = con.execute(f"""
        SELECT code, product_name AS nom, brands AS marque,
               {expr_produit(cfg)} AS produit, espece,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               nutriscore_score AS ns, nutriscore_grade AS grade,
               {borne('salt_100g', 'sel')},
               {borne('proteins_100g', 'proteines')}
        FROM '{PERIMETRE}'
        WHERE ({COMPLET}) AND nutriscore_score IS NOT NULL
          AND NOT (tag_halal AND len(list_intersect(labels_tags,
                   {liste_sql(q['labels_kasher'])})) > 0)
    """).df()
    d = d[d.produit.notna() & (d.produit != "plat_a_base_de_jambon")]

    # ---- Regle de plausibilite de forme, declaree en config.
    titre("Produits dont la forme contredit leur categorie")
    ecartes = []
    for nom, r in regles.items():
        m = (d.produit.isin(r["produits"])
             & (d.sel > r["sel_max_g_100g"]))
        if m.any():
            print(f"  Regle « {nom} » : {int(m.sum())} produits ecartes "
                  f"(sel > {r['sel_max_g_100g']} g/100 g).")
            e = d[m].copy()
            e["regle"] = nom
            ecartes.append(e)
        d = d[~m]
    if ecartes:
        e = pd.concat(ecartes)
        print(f"\n  Dont, cote halal, {int((e.bras == 'halal').sum())} :")
        print(e[e.bras == "halal"][["code", "nom", "marque", "produit", "sel"]]
              .head(12).to_string(index=False))
        e.to_csv(SORTIES / "v0_forme_incoherente.csv", index=False)
        print("\n  Ce n'est pas un jugement sur ces produits : c'est le constat")
        print("  que leur categorie Open Food Facts ne decrit pas ce qu'ils")
        print("  sont. Ils ne peuvent pas etre compares a leur categorie.")

    # ---- Comparateur : meme produit, meme espece, bras temoin, 30 au moins.
    t = d[d.bras == "temoin"]
    ref = (t.groupby(["produit", "espece"])
             .agg(n_ref=("ns", "size"), ns_ref=("ns", "median"),
                  sel_ref=("sel", "median"),
                  proteines_ref=("proteines", "median")).reset_index())
    ref = ref[ref.n_ref >= SEUIL_REF]
    h = d[d.bras == "halal"].merge(ref, on=["produit", "espece"])
    h["ecart"] = h.ns - h.ns_ref

    # Percentile : la place du produit DANS la distribution du comparateur.
    dist = {(p, e): g.ns.to_numpy()
            for (p, e), g in t.groupby(["produit", "espece"])}
    h["percentile"] = [
        round(100.0 * float((dist[(p, e)] < v).mean()), 1)
        for p, e, v in zip(h.produit, h.espece, h.ns)]

    # ---- Valeurs invraisemblables : ecartees du palmares, publiees a part.
    faux = h[h.sel > SEL_INVRAISEMBLABLE]
    if len(faux):
        titre(f"Valeurs de sel invraisemblables : {len(faux)} produits")
        print(f"Au-dela de {SEL_INVRAISEMBLABLE} g/100 g, c'est une erreur de "
              f"saisie et non un\nproduit. Ces lignes sortent du palmares.\n")
        print(faux[["code", "nom", "marque", "sel", "ns"]].to_string(index=False))
        faux.to_csv(SORTIES / "v3_sel_invraisemblable.csv", index=False)
        h = h[h.sel <= SEL_INVRAISEMBLABLE]

    titre(f"Comparaisons possibles : {len(h)} produits halal")
    print(f"Comparateur : meme produit emblematique, meme espece, bras temoin,")
    print(f"au moins {SEUIL_REF} produits. Le percentile dit la place du produit")
    print("halal dans cette distribution : 100 = pire que tous les temoins.\n")
    print(h.groupby(["produit", "espece"]).size().to_string())

    cols = ["code", "nom", "marque", "produit", "espece", "grade", "ns",
            "ns_ref", "ecart", "percentile", "sel", "sel_ref", "proteines",
            "proteines_ref", "n_ref"]

    titre(f"CANDIDATS — les {N_PODIUM} plus eloignes vers le HAUT (moins bons)")
    pires = h.nlargest(N_PODIUM, "ecart")
    print(pires[cols].to_string(index=False))
    pires.to_csv(SORTIES / "v1_candidats_pires.csv", index=False)

    titre(f"CANDIDATS — les {N_PODIUM} plus eloignes vers le BAS (meilleurs)")
    meilleurs = h.nsmallest(N_PODIUM, "ecart")
    print(meilleurs[cols].to_string(index=False))
    meilleurs.to_csv(SORTIES / "v2_candidats_meilleurs.csv", index=False)

    # ---- LA comparaison defendable : paires appariees par nom et marque.
    titre("PAIRES APPARIEES — meme marque, meme nom, meme gamme, meme espece")
    print("C'est la seule comparaison au niveau du code-barres qui ne dependent")
    print("pas de la qualite des categories : le fabricant vend le meme produit")
    print("en deux versions, et son nom le dit. Le nom est normalise — casse,")
    print("accents, grammages et le mot « halal » retires — puis on exige que")
    print("marque, gamme et espece coincident aussi.\n")

    tout = con.execute(f"""
        SELECT code, coalesce(product_name, '') AS nom,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS mq,
               sous_categorie, espece,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               nutriscore_score AS ns, nutriscore_grade AS grade,
               {borne('salt_100g', 'sel')},
               {borne('proteins_100g', 'proteines')}
        FROM '{PERIMETRE}'
        WHERE ({COMPLET}) AND nutriscore_score IS NOT NULL
          AND brands_tags IS NOT NULL AND len(brands_tags) > 0
    """).df()
    # Le meme filtre que pour le palmares : sans lui, le « Blanc de poulet
    # -25 % de sel » de Fleury Michon saisi a 13,8 g tire la mediane de sa
    # paire et fabrique un ecart de 10 points qui n'existe pas.
    n_av = len(tout)
    tout = tout[tout.sel.isna() | (tout.sel <= SEL_INVRAISEMBLABLE)]
    print(f"  {n_av - len(tout)} produits ecartes pour sel invraisemblable.")
    tout["cle"] = [normaliser(x) for x in tout.nom]
    tout = tout[tout.cle.str.len() > 8]
    n_bras = tout.groupby(["mq", "cle", "sous_categorie", "espece"]).bras.nunique()
    paires = n_bras[n_bras > 1].reset_index()[
        ["mq", "cle", "sous_categorie", "espece"]]
    m = tout.merge(paires, on=["mq", "cle", "sous_categorie", "espece"])
    print(f"  {len(paires)} paires, {len(m)} produits.\n")

    lignes = []
    for (mq, cle, sc, esp), g in m.groupby(["mq", "cle", "sous_categorie",
                                            "espece"]):
        a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
        # Mediane de chaque cote : une marque peut avoir plusieurs references
        # du meme produit, ce sont des conditionnements, pas des recettes.
        ecart = float(a.ns.median() - b.ns.median())
        dp = float(a.proteines.median() - b.proteines.median())
        lignes.append({
            "marque": mq, "produit": cle, "gamme": sc, "espece": esp,
            "n_halal": len(a), "n_temoin": len(b),
            "code_halal": a.sort_values("ns").iloc[-1].code,
            "code_temoin": b.sort_values("ns").iloc[0].code,
            "ns_halal": float(a.ns.median()), "ns_temoin": float(b.ns.median()),
            "ecart": ecart,
            "sel_halal": float(a.sel.median()), "sel_temoin": float(b.sel.median()),
            "prot_halal": float(a.proteines.median()),
            "prot_temoin": float(b.proteines.median()),
            # Meme nom mais 5 g de proteines d'ecart : ce ne sont pas deux
            # versions d'une meme recette, c'est un homonyme.
            "meme_recette": abs(dp) <= 5.0,
        })
    t9 = pd.DataFrame(lignes).sort_values("ecart", ascending=False)
    t9.to_csv(SORTIES / "v4_paires_appariees.csv", index=False)

    sures = t9[t9.meme_recette]
    cols9 = ["marque", "produit", "gamme", "espece", "n_halal", "n_temoin",
             "ns_halal", "ns_temoin", "ecart", "sel_halal", "sel_temoin"]
    print("  --- Paires ou le halal est MOINS BON (ecart positif)")
    print(sures[sures.ecart > 0][cols9].to_string(index=False))
    print("\n  --- Paires IDENTIQUES ou le halal est MEILLEUR")
    print(sures[sures.ecart <= 0][cols9].to_string(index=False))
    ecartees9 = t9[~t9.meme_recette]
    if len(ecartees9):
        print(f"\n  --- {len(ecartees9)} paires ecartees : meme nom mais plus de")
        print("      5 g de proteines d'ecart, donc pas la meme recette.")
        print(ecartees9[cols9 + ["prot_halal", "prot_temoin"]].to_string(
            index=False))

    n_ident = int((sures.ecart == 0).sum())
    print(f"\n  Sur {len(sures)} paires comparables, {n_ident} sont IDENTIQUES,")
    print(f"  {int((sures.ecart > 0).sum())} defavorables au halal et "
          f"{int((sures.ecart < 0).sum())} favorables.")

    titre("AVANT DE NOMMER UN SEUL DE CES PRODUITS")
    print("Chaque ligne demande trois verifications qu'aucun script ne fait :")
    print("  1. le produit est-il bien l'aliment que sa categorie annonce ;")
    print("  2. le comparateur est-il le meme aliment ;")
    print("  3. la valeur nutritionnelle est-elle plausible, ou est-ce une")
    print("     erreur de saisie du contributeur.")
    print("\nUn extreme est plus souvent une erreur de saisie qu'un produit")
    print("extraordinaire. Publier cette liste telle quelle reviendrait a")
    print("accuser des articles nommes sur la foi d'une base collaborative.")

    print("\nEcrit : sorties/v0_forme_incoherente.csv, v1_candidats_pires.csv,")
    print("        v2_candidats_meilleurs.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
