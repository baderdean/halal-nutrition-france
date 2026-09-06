#!/usr/bin/env python3
"""Couche 19 — un seuil nutritionnel est-il tenable, et sur quoi l'ancrer ?

QUESTION POSEE. Peut-on refuser une gamme au-dessous d'une note minimale, au
motif que la charcuterie est classee cancerogene et que ces produits ne sont
pas de consommation exceptionnelle ?

CE QUE CE DEPOT PEUT REPONDRE, ET CE QU'IL NE PEUT PAS.

  MESURABLE ICI
    - la structure de l'OFFRE : quelles gammes le rayon halal propose, en
      part, comparee au reste du marche ;
    - la FAISABILITE d'un seuil : quelle part du marche l'atteint deja. Un
      seuil que personne n'atteint est une petition ; un seuil que le reste
      du marche atteint deja est un rattrapage.

  HORS DE PORTEE
    - la FREQUENCE de consommation. Ce depot ne contient aucune donnee de
      consommation. « Ces produits sont manges souvent » est une hypothese
      sur les gens, et rien ici ne la teste. La composition de l'offre n'est
      pas la frequence des achats.
    - le DANGER d'un produit. Un Nutri-Score est un indicateur COMPARATIF de
      composition, pas un verdict sanitaire sur une reference. Le risque
      documente porte sur des quantites consommees dans la duree, jamais sur
      un code-barres.
    - toute qualification religieuse. Ce depot ne dit pas ce qui est tayyib.

AUCUNE LIGNE DE CE FICHIER NE FIXE DE SEUIL. Le script simule des seuils pour
montrer ce qu'ils excluraient de part et d'autre. Choisir le seuil est une
decision de norme, elle appartient a qui ecrit la norme.
"""

from __future__ import annotations

import sys

import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, connexion, titre

SEUILS_SEL = (1.5, 2.0, 2.5, 3.0)
SEUILS_NOTE = ("a", "b", "c")
TRANSFORMEES = {"charcuterie_cuite", "charcuterie_seche", "saucisses",
                "panes", "plats_cuisines", "rillettes_pates_mousses",
                "foie_gras", "preparations_marinees"}


def main() -> int:
    con = connexion()
    d = con.execute(f"""
        SELECT product_name, tag_halal, sous_categorie, espece,
               nutriscore_score AS ns, nutriscore_grade AS note,
               {borne('salt_100g', 'sel')}
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    d["bras"] = ["halal" if x else "temoin" for x in d.tag_halal]

    titre("La structure de l'offre, gamme par gamme")
    print("Part de chaque gamme dans son propre bras. Ce n'est PAS ce que les")
    print("gens mangent : c'est ce que le rayon propose. La frequence de")
    print("consommation n'est nulle part dans ce depot.\n")
    p = (d.pivot_table(index="sous_categorie", columns="bras",
                       values="ns", aggfunc="size").fillna(0))
    for b in ("halal", "temoin"):
        p[f"pct_{b}"] = (100 * p[b] / p[b].sum()).round(1)
    p["ecart_points"] = (p.pct_halal - p.pct_temoin).round(1)
    p = p.sort_values("pct_halal", ascending=False)
    print(p[["halal", "temoin", "pct_halal", "pct_temoin",
             "ecart_points"]].to_string())
    p.to_csv(SORTIES / "j1_structure_offre.csv")
    for b in ("halal", "temoin"):
        tot = p[b].sum()
        tr = p.loc[p.index.isin(TRANSFORMEES), b].sum()
        print(f"\n  {b:7s} : {tr:.0f} produits transformes sur {tot:.0f}, "
              f"soit {100 * tr / tot:.1f} %")
    print("\n  L'ecart sur le total transforme est faible. Ce qui bouge, ce")
    print("  sont les gammes : les panes pesent quatre fois plus dans le")
    print("  rayon halal, les plats cuisines et les decoupes deux fois moins.")
    print("  Un consommateur qui s'en tient au rayon halal rencontre plus de")
    print("  produits panes et moins de viande a cuisiner. C'est un fait")
    print("  d'OFFRE, et il ne dit pas ce qui finit dans les assiettes.")

    titre("Un seuil serait-il tenable ? Ce que le marche atteint deja")
    print("Un seuil que personne n'atteint est une petition. Un seuil que le")
    print("reste du marche atteint deja est un rattrapage. La difference se")
    print("mesure, et elle se mesure gamme par gamme.\n")
    lignes = []
    for (sc, esp), g in d.groupby(["sous_categorie", "espece"]):
        h, t = g[g.bras == "halal"], g[g.bras == "temoin"]
        if len(h) < 30 or len(t) < 30:
            continue
        for s in SEUILS_SEL:
            lignes.append({"gamme": f"{sc} / {esp}", "critere": f"sel <= {s} g",
                           "n_halal": len(h), "n_temoin": len(t),
                           "pct_halal": round(100 * (h.sel <= s).mean(), 1),
                           "pct_temoin": round(100 * (t.sel <= s).mean(), 1)})
        for lettre in SEUILS_NOTE:
            ok = list("abcde")[:list("abcde").index(lettre) + 1]
            lignes.append({"gamme": f"{sc} / {esp}",
                           "critere": f"Nutri-Score {lettre.upper()} ou mieux",
                           "n_halal": len(h), "n_temoin": len(t),
                           "pct_halal": round(100 * h.note.isin(ok).mean(), 1),
                           "pct_temoin": round(100 * t.note.isin(ok).mean(), 1)})
    s19 = pd.DataFrame(lignes)
    s19["ecart_points"] = (s19.pct_temoin - s19.pct_halal).round(1)
    s19 = s19.sort_values(["gamme", "critere"])
    s19.to_csv(SORTIES / "j2_faisabilite_seuils.csv", index=False)
    print(f"  {s19.gamme.nunique()} gammes ou les deux bras depassent 30 "
          "produits.\n")
    for gamme, g in s19.groupby("gamme"):
        print(f"  --- {gamme}  (halal {g.n_halal.iloc[0]}, "
              f"temoin {g.n_temoin.iloc[0]})")
        print(g[["critere", "pct_halal", "pct_temoin",
                 "ecart_points"]].to_string(index=False))
        print()
    print("  LECTURE. Un critere dont la colonne temoin est haute et la")
    print("  colonne halal basse est un seuil DEJA ATTEINT par le reste du")
    print("  marche sur la meme gamme. Il ne demande aucune technologie")
    print("  nouvelle : il demande la meme recette.")
    print("\n  CE QUE CE TABLEAU NE FIXE PAS : le seuil. Aucune ligne de ce")
    print("  depot ne dit ou le mettre. C'est une decision de norme, et elle")
    print("  appartient a qui ecrit la norme.")

    # --- Un critere « sel eleve ET note C ou pire » deconseille-t-il des
    # PRODUITS, ou redit-il simplement la GAMME ?
    titre("Le critere « sel eleve + note C ou pire » : que selectionne-t-il ?")
    print("Un critere n'aide un lecteur que s'il DISTINGUE a l'interieur d'une")
    print("gamme. S'il retient 80 % d'une gamme et 1 % d'une autre, il ne")
    print("deconseille pas des produits : il deconseille une gamme, ce que les")
    print("reperes publics font deja.\n")
    d = d[d.note.notna() & d.sel.notna()].copy()
    lignes = []
    for s_ in SEUILS_SEL:
        for b in ("halal", "temoin"):
            g = d[d.bras == b]
            f_ = (g.sel >= s_) & (g.note.isin(["c", "d", "e"]))
            lignes.append({"critere": f"sel >= {s_} g et note C ou pire",
                           "bras": b, "n": len(g),
                           "pct_retenu": round(100 * f_.mean(), 1)})
    ct = pd.DataFrame(lignes)
    print(ct.pivot(index="critere", columns="bras",
                   values="pct_retenu").to_string())
    ct.to_csv(SORTIES / "j3_critere_selection.csv", index=False)

    h = d[d.bras == "halal"].copy()
    h["retenu"] = (h.sel >= 2.5) & (h.note.isin(["c", "d", "e"]))
    par = (h.groupby("sous_categorie")
             .agg(n=("retenu", "size"), pct=("retenu", "mean")))
    par["pct"] = (100 * par.pct).round(1)
    par = par[par.n >= 30].sort_values("pct", ascending=False)
    print("\n  Au seuil de 2,5 g, part du bras halal retenue par gamme :")
    print(par.to_string())
    par.to_csv(SORTIES / "j4_critere_par_gamme.csv")
    print("\n  De 80,8 % en charcuterie sechee a 0,7 % en panes. Le critere")
    print("  est un DETECTEUR DE GAMME avant d'etre un detecteur de produit.")
    print("  Pour aider a choisir DANS une gamme, il faut un seuil interne a")
    print("  la gamme, pas un seuil general.")

    # --- L'arithmetique de la portion, seule facon honnete de dire « eleve ».
    titre("Ce que « sel eleve » veut dire, en portion")
    print("Reperes publics, cites et non produits par cette etude :")
    print("  - moins de 5 g de sel par jour pour un adulte (OMS, repris par le")
    print("    PNNS) ;")
    print("  - au plus 150 g de charcuterie par semaine, soit environ 25 g par")
    print("    jour (PNNS, Sante publique France).")
    print("\nCes deux reperes se combinent en une arithmetique verifiable, qui")
    print("ne conseille rien et ne diagnostique personne :\n")
    ch = h[h.sous_categorie.isin(["charcuterie_cuite", "charcuterie_seche"])]
    for gamme, g in ch.groupby("sous_categorie"):
        for q, lib in ((0.5, "median"), (0.9, "9e decile")):
            sel = float(g.sel.quantile(q))
            print(f"  {gamme:20s} {lib:10s} {sel:.2f} g/100 g  ->  une portion "
                  f"PNNS de 25 g\n  {'':32s} apporte {sel * 0.25:.2f} g de sel, "
                  f"soit {100 * sel * 0.25 / 5:.0f} % du maximum quotidien.")
    print("\n  A quoi cela sert. « Sel eleve » est un jugement ; « cette")
    print("  portion couvre un quart du maximum quotidien » est un fait que")
    print("  le lecteur peut verifier sur l'emballage et rapporter au reste de")
    print("  sa journee. Ce depot publie le fait, pas le jugement.")

    print("\nEcrit : sorties/j1_structure_offre.csv, j2_faisabilite_seuils.csv,")
    print("        j3_critere_selection.csv, j4_critere_par_gamme.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
