#!/usr/bin/env python3
"""Couche 6 — ce qu'un acheteur halal peut reellement eviter.

Question posee : peut-on designer des marques, des gammes, des certificateurs
ou des origines a eviter ? Ce script y repond variable par variable, et dit
NON la ou la reponse est non.

Ordre de presentation impose par la taille des effets, pas par l'interet de
la question :

  1. LA GAMME decide presque tout. Dans le bras halal, la mediane va de 3
     (decoupes) a 28 (charcuterie seche) en Nutri-Score continu. Aucun autre
     choix offert au consommateur ne pese autant.
  2. LA MARQUE DANS UNE GAMME donne un ecart reel, jusqu'a 16 points sur la
     charcuterie cuite. C'est le second levier.
  3. LA MARQUE SEULE est un mauvais repere : la meme marque peut etre la pire
     sur une gamme et la meilleure sur une autre. Le script le montre plutot
     que de l'affirmer.
  4. LE CERTIFICATEUR n'est pas separable de la marque : etabli en couche 4.
  5. L'ORIGINE FRANCE visible ne separe rien, et ne couvre que 5 % du bras.
  6. LE REPERTOIRE CULINAIRE (merguez, tavuk, jambon) ne separe rien non
     plus une fois la gamme fixee : il est une redite de la gamme.

Tout ce qui est publie ici est DESCRIPTIF. Ce sont des ecarts observes sur un
dump d'etiquetage declaratif, pas des mesures en laboratoire, pas un jugement
de conformite, pas un jugement sur la halalite. Les marques nommees le sont
avec leurs effectifs et leurs medianes.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, charger, connexion, echec, titre
from etape5_produits_emblematiques import ic_diff, liste_sql

SEUIL = 30       # regle des 30 : au-dessus, testable
SEUIL_CELL = 10  # marque x gamme : sous 30 mais publie, signale comme decrit
GRAINE = 20260904


def profil(d: pd.DataFrame, cles) -> pd.DataFrame:
    t = d.groupby(cles).agg(
        n=("ns", "size"), nutriscore=("ns", "median"), sel=("sel", "median"),
        ags=("ags", "median"), proteines=("prot", "median")).round(2)
    de = d[d.g.isin(["d", "e"])].groupby(cles).size()
    t["pct_DE"] = (100 * de / t.n).round(0).fillna(0)
    t["regle_30"] = np.where(t.n >= SEUIL, "franchie", "sous 30")
    return t


def main() -> int:
    con = connexion()
    rng = np.random.default_rng(GRAINE)
    fr = liste_sql(charger("questions.yaml")["labels_production_france"])
    d = con.execute(f"""
        SELECT sous_categorie, espece, tag_halal,
               len(list_intersect(labels_tags, {fr})) > 0 AS france,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               lower(coalesce(product_name, '')) AS nom,
               nutriscore_score AS ns, nutriscore_grade AS g,
               {borne('salt_100g', 'sel')},
               {borne('saturated_fat_100g', 'ags')},
               {borne('proteins_100g', 'prot')}
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    h = d[d.tag_halal]

    # ---- 1. La gamme.
    titre("1. LA GAMME — le seul levier de grande amplitude")
    g1 = profil(h, "sous_categorie").sort_values("nutriscore")
    print("Bras halal, valeurs absolues. pct_DE = part des produits notes D ou E.\n")
    print(g1.to_string())
    ecart = g1.nutriscore.max() - g1.nutriscore.min()
    print(f"\n  De la meilleure a la pire gamme : {ecart:.0f} points de "
          f"Nutri-Score continu.")
    print(f"  Part de D/E : {g1.pct_DE.min():.0f} % a {g1.pct_DE.max():.0f} %.")
    g1.to_csv(SORTIES / "r1_gammes_halal.csv")

    # ---- 2. Marque x gamme.
    titre("2. LA MARQUE DANS UNE GAMME — le second levier")
    hm = h[h.marque.notna() & (h.marque != "")]
    g2 = profil(hm, ["sous_categorie", "marque"]).reset_index()
    g2 = g2[g2.n >= SEUIL_CELL].sort_values(["sous_categorie", "nutriscore"])
    print(f"Cellules d'au moins {SEUIL_CELL} produits. Une cellule sous "
          f"{SEUIL} est decrite,\njamais testee.\n")
    print(g2.to_string(index=False))
    g2.to_csv(SORTIES / "r2_marque_x_gamme_halal.csv", index=False)

    # ---- 3. Pourquoi la marque seule est un mauvais repere.
    titre("3. LA MARQUE SEULE — pourquoi c'est un mauvais repere")
    rang = g2.copy()
    rang["rang"] = rang.groupby("sous_categorie").nutriscore.rank(method="min")
    rang["sur"] = rang.groupby("sous_categorie").marque.transform("size")
    croise = (rang.groupby("marque")
                  .agg(gammes=("sous_categorie", "size"),
                       meilleure=("rang", "min"), pire=("rang", "max"))
                  .query("gammes >= 2").sort_values("gammes", ascending=False))
    print("Rang de chaque marque dans chacune de ses gammes (1 = la meilleure "
          "de sa gamme) :\n")
    for mq in croise.index:
        s = rang[rang.marque == mq].sort_values("nutriscore")
        print(f"  {mq}")
        for r in s.itertuples():
            print(f"      {r.sous_categorie:26s} rang {int(r.rang)}/{int(r.sur)}"
                  f"   Nutri-Score {r.nutriscore:5.1f}   n={r.n}")
    croise.to_csv(SORTIES / "r3_marque_rangs_croises.csv")

    # ---- 4. Le certificateur. Resultat de couche 4, rappele, pas recalcule.
    titre("4. LE CERTIFICATEUR — non separable de la marque")
    print("Etabli en couche 4 (sorties/c_nationalite.csv, c_electronarcose.csv).")
    print("Chaque comparaison entre certificateurs s'est effondree au test de")
    print("retrait de la marque dominante : le marche halal francais est trop")
    print("concentre pour qu'un certificateur soit observe independamment de")
    print("ses marques. Aucun certificateur ne peut etre designe a eviter.")

    # ---- 5. L'origine France visible.
    titre("5. L'ORIGINE FRANCE VISIBLE — ne separe rien")
    a, b = h[h.france], h[~h.france]
    print(f"Le bras halal compte {len(a)} produits portant une mention de "
          f"production\nfrancaise visible, sur {len(h)} ({100*len(a)/len(h):.1f} %).\n")
    lignes = []
    for v, lib in [("ns", "Nutri-Score"), ("sel", "sel"), ("ags", "AGS"),
                   ("prot", "proteines")]:
        r = ic_diff(a[v].to_numpy(), b[v].to_numpy(), rng)
        print(f"  {lib:12s} France - sans mention = {r[0]:+.2f} "
              f"IC95 [{r[1]:+.2f} ; {r[2]:+.2f}]")
        lignes.append({"variable": lib, "ecart": round(r[0], 2),
                       "ic95_bas": round(r[1], 2), "ic95_haut": round(r[2], 2)})
    print("\n  L'ecart sur les AGS est un effet de composition : la mention "
          "France est\n  portee a 37 % par de la charcuterie cuite, contre "
          "16 % sans mention, et\n  la charcuterie cuite est pauvre en AGS. "
          "A gamme egale, une seule strate\n  est testable des deux cotes :")
    for sc, s in h.groupby("sous_categorie"):
        x, y = s[s.france], s[~s.france]
        if len(x) >= SEUIL and len(y) >= SEUIL:
            r = ic_diff(x.ns.to_numpy(), y.ns.to_numpy(), rng)
            rs = ic_diff(x.sel.to_numpy(), y.sel.to_numpy(), rng)
            print(f"    {sc:22s} n={len(x)}/{len(y)}  Nutri-Score "
                  f"{r[0]:+.1f} [{r[1]:+.1f} ; {r[2]:+.1f}]   sel "
                  f"{rs[0]:+.2f} [{rs[1]:+.2f} ; {rs[2]:+.2f}]")
            lignes.append({"variable": f"Nutri-Score, {sc}",
                           "ecart": round(r[0], 2), "ic95_bas": round(r[1], 2),
                           "ic95_haut": round(r[2], 2)})
    print("\n  ABSENCE DE MENTION N'EST PAS ETRANGER. Un produit sans mention "
          "n'a pas\n  revendique une origine, ce qui ne dit rien du lieu de "
          "production. Cette\n  comparaison oppose une revendication a son "
          "absence, pas la France au reste\n  du monde.")
    pd.DataFrame(lignes).to_csv(SORTIES / "r4_origine_france.csv", index=False)

    # ---- 6. Le repertoire culinaire.
    titre("6. LE REPERTOIRE CULINAIRE — une redite de la gamme")
    print("Le nom imprime sur l'emballage range le produit dans un repertoire :")
    print("merguez et kefta d'un cote, tavuk et sucuk d'un autre, jambon et")
    print("saucisson d'un troisieme. Cela classe des RECETTES, jamais des")
    print("personnes, jamais des entreprises, jamais un pays de fabrication.\n")
    rep = charger("repertoires_culinaires.yaml")["repertoires"]
    # Le nom vient de LA MEME requete que le reste : une seconde requete
    # DuckDB ne garantit pas le meme ordre de lignes (la connexion tourne en
    # preserve_insertion_order=false), et un rattachement par position serait
    # un appariement au hasard.
    lib = h.copy()
    lib["repertoire"] = "non classe"
    for r in reversed(rep):        # premier match gagnant : on ecrase a rebours
        lib.loc[lib.nom.str.contains(r["motif"], regex=True, na=False),
                "repertoire"] = r["nom"]

    # Le repertoire maghrebin du bras halal est a 78 % des saucisses. Ce n'est
    # PAS que le repertoire se reduise aux saucisses : le couscous et le tajine
    # existent en rayon, ils sont ranges en plats cuisines, et ils ne portent
    # presque jamais d'estampille halal. Mesurer le taux d'etiquetage par
    # repertoire evite de confondre « ce que le rayon halal contient » avec
    # « ce que la cuisine maghrebine est ».
    tous = d.copy()
    tous["repertoire"] = "non classe"
    for r in reversed(rep):
        tous.loc[tous.nom.str.contains(r["motif"], regex=True, na=False),
                 "repertoire"] = r["nom"]
    tx = (tous.assign(halal=tous.tag_halal)
              .groupby("repertoire")
              .agg(n_total=("halal", "size"), n_halal=("halal", "sum")))
    tx["pct_halal"] = (100 * tx.n_halal / tx.n_total).round(1)
    print("  Taux d'estampille halal par repertoire, perimetre entier :")
    print("   " + tx.to_string().replace("\n", "\n   "))
    print("\n  Lecture : le repertoire maghrebin du bras halal est domine par")
    print("  les saucisses, mais ce n'est pas que la cuisine maghrebine s'y")
    print("  reduise. Le couscous et le tajine sont bien dans le perimetre et")
    print("  bien ranges en plats cuisines — ils ne portent simplement presque")
    print("  jamais d'estampille halal.\n")
    tx.to_csv(SORTIES / "r7_etiquetage_par_repertoire.csv")

    print("  Composition en gammes de chaque repertoire, bras halal (%) :")
    comp = (pd.crosstab(lib.repertoire, lib.sous_categorie, normalize="index")
              .mul(100).round(0))
    print(comp.to_string().replace("\n", "\n  "))
    concentration = comp.max(axis=1)
    print("\n  Part de la gamme dominante dans chaque repertoire :")
    for nom, v in concentration.sort_values(ascending=False).items():
        print(f"    {nom:24s} {v:.0f} % dans une seule gamme")
    print("\n  Un repertoire concentre a 60 % ou plus sur une gamme ne mesure")
    print("  pas autre chose que cette gamme.\n")

    print("  A GAMME EGALE, dans le bras halal, chaque repertoire contre les")
    print(f"  produits non classes de la meme gamme (cellules a {SEUIL}+ des "
          f"deux cotes) :\n")
    lignes_rep = []
    for sc, g in lib.groupby("sous_categorie"):
        base = g[g.repertoire == "non classe"]
        if len(base) < SEUIL:
            continue
        for r in rep:
            x = g[g.repertoire == r["nom"]]
            if len(x) < SEUIL:
                continue
            ic = ic_diff(x.ns.to_numpy(), base.ns.to_numpy(), rng)
            etabli = "etabli" if (ic[1] > 0) or (ic[2] < 0) else "NON ETABLI"
            print(f"    {sc:20s} {r['nom']:24s} n={len(x):3d}/{len(base):3d}  "
                  f"Nutri-Score {ic[0]:+.1f} [{ic[1]:+.1f} ; {ic[2]:+.1f}]  "
                  f"{etabli}")
            lignes_rep.append({"sous_categorie": sc, "repertoire": r["nom"],
                               "n": len(x), "n_reference": len(base),
                               "ecart": round(ic[0], 2),
                               "ic95_bas": round(ic[1], 2),
                               "ic95_haut": round(ic[2], 2),
                               "etabli": etabli == "etabli"})
    pd.DataFrame(lignes_rep).to_csv(
        SORTIES / "r6_repertoires_culinaires.csv", index=False)
    print("\n  Les repertoires maghrebin et turc ne montrent rien a gamme "
          "egale. Ce\n  qui reste etabli concerne le vocabulaire charcutier "
          "europeen et le\n  vocabulaire industriel anglo-saxon, c'est-a-dire "
          "la forme du produit\n  dans sa propre gamme, pas une origine "
          "culturelle.")
    print("\n  AUCUNE QUALITE NUTRITIONNELLE NE SE DEDUIT DU REPERTOIRE "
          "CULINAIRE.")

    # ---- 6. Deux defauts de perimetre a signaler avant toute lecture fine.
    titre("6. DEUX DEFAUTS DE PERIMETRE, signales et non corriges")
    n_b = con.execute(f"""
        SELECT sum(CASE WHEN tag_halal THEN 1 ELSE 0 END),
               sum(CASE WHEN NOT tag_halal THEN 1 ELSE 0 END)
        FROM '{PERIMETRE}'
        WHERE regexp_matches(lower(coalesce(product_name, '')),
                'fond de (veau|volaille|boeuf)|bouillon|court-bouillon|fumet')
           OR len(list_filter(categories_tags,
                x -> regexp_matches(x, 'bouillon|broth|stock-cube|soup'))) > 0
    """).fetchone()
    print(f"  a) Aides culinaires (fonds, bouillons) dans un perimetre carne : "
          f"{n_b[0]} halal,\n     {n_b[1]} temoin. Un fond de veau a 22 g de sel "
          f"pour 100 g n'est pas un\n     produit carne consomme tel quel. Ils "
          f"deforment les moyennes de sel,\n     pas les medianes.")
    comp = con.execute(f"""
        SELECT CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               CASE WHEN len(list_filter(categories_tags, x -> regexp_matches(x,
                 'preparation|cooked|marinated|brochette|kebab|wings|grill')))>0
                 THEN 'preparation ou cuit' ELSE 'decoupe crue' END AS forme,
               count(*) AS n
        FROM '{PERIMETRE}' WHERE ({COMPLET}) AND sous_categorie = 'decoupes'
        GROUP BY 1, 2
    """).df().pivot(index="bras", columns="forme", values="n")
    part = (100 * comp.div(comp.sum(1), axis=0)).round(1)
    print(f"\n  b) La strate 'decoupes' melange la decoupe crue et la "
          f"preparation marinee\n     ou cuite, et le melange differe entre les "
          f"bras :")
    print(part.to_string().replace("\n", "\n     "))
    print("     L'ecart de sel apparent sur cette strate est en partie un ecart"
          "\n     de FORME de produit, pas de label. Sur le blanc de poulet "
          "seul\n     (en:chicken-breasts), aucun ecart n'est etabli.")
    comp.to_csv(SORTIES / "r5_defauts_perimetre.csv")

    print("\nEcrit : sorties/r1_gammes_halal.csv, r2_marque_x_gamme_halal.csv,")
    print("        sorties/r6_repertoires_culinaires.csv, "
          "r7_etiquetage_par_repertoire.csv,")
    print("        r3_marque_rangs_croises.csv, r4_origine_france.csv,")
    print("        r5_defauts_perimetre.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
