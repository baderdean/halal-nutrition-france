#!/usr/bin/env python3
"""Couche 12 — l'effort nutritionnel est-il moindre sur les gammes halal ?

L'hypothese n'est PAS que la norme halal degrade un produit. Elle est que,
dans le cahier des charges d'une MARQUE, la dimension nutritionnelle pese
moins quand la gamme est halal. C'est une hypothese sur la posture d'un
industriel, pas sur une norme religieuse, et elle laisse une trace mesurable.

Un fabricant qui travaille la nutrition le dit sur le paquet : il affiche le
Nutri-Score, revendique un sel reduit, une absence d'additifs. Ces mentions
sont volontaires et coutent une reformulation, ou au moins un engagement.
Leur frequence mesure un effort declare.

POURQUOI UNE SECONDE LISTE. On compte les mentions nutritionnelles : 10 % des
produits halal en portent, 22 % des non halal. Une objection evidente
ruinerait ce chiffre : et si les fiches halal etaient simplement MOINS
REMPLIES ? L'ecart ne dirait alors rien de la nutrition.

Pour departager, une seconde liste de mentions sans rapport avec la
nutrition : sans gluten, sans huile de palme, sans OGM. Memes paquets, memes
contributeurs.

  halal aussi bas sur cette seconde liste
      -> les fiches halal sont moins remplies, on n'apprend rien ;
  halal a niveau egal ou superieur sur cette seconde liste, mais plus bas sur
  la nutrition
      -> ce qui manque est specifiquement nutritionnel.

Ce que ce script ne peut pas faire : lire un cahier des charges. Il mesure ce
qui est imprime, pas ce qui est decide. Une mention absente peut signifier un
produit non reformule, ou un produit reformule dont on n'a pas juge utile de
le dire.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, charger, connexion, titre
from etape5_produits_emblematiques import liste_sql
from etape7_additifs_transformation import newcombe

SEUIL = 30
SEUIL_MARQUE = 20


def main() -> int:
    con = connexion()
    fam = charger("allegations.yaml")["familles"]
    cols = ", ".join(
        f"len(list_intersect(labels_tags, {liste_sql(f['codes'])})) > 0 "
        f"AS {f['nom']}" for f in fam)
    d = con.execute(f"""
        SELECT sous_categorie, espece,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               {cols}
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    noms = [f["nom"] for f in fam]
    lib = {f["nom"]: f["libelle"] for f in fam}

    titre("1. PREVALENCE DES ALLEGATIONS, perimetre entier")
    print("Difference de proportion halal - temoin, IC 95 % de Newcombe.\n")
    lignes = []
    for n in noms:
        a, b = d[d.bras == "halal"], d[d.bras == "temoin"]
        k1, k2 = int(a[n].sum()), int(b[n].sum())
        r = newcombe(k1, len(a), k2, len(b))
        etabli = "etabli" if (r[1] > 0 or r[2] < 0) else "non etabli"
        print(f"  {lib[n]:42s} halal {100*k1/len(a):5.2f} %  temoin "
              f"{100*k2/len(b):5.2f} %   ecart {100*r[0]:+6.2f} pts "
              f"[{100*r[1]:+6.2f} ; {100*r[2]:+6.2f}]  {etabli}")
        lignes.append({"niveau": "perimetre", "cle": "", "famille": n,
                       "pct_halal": round(100 * k1 / len(a), 2),
                       "pct_temoin": round(100 * k2 / len(b), 2),
                       "ecart_points": round(100 * r[0], 2),
                       "ic95_bas": round(100 * r[1], 2),
                       "ic95_haut": round(100 * r[2], 2),
                       "n_halal": len(a), "n_temoin": len(b),
                       "etabli": etabli == "etabli"})

    titre("2. A GAMME EGALE")
    print("La composition du bras halal pourrait suffire a expliquer l'ecart :")
    print("la charcuterie porte moins de Nutri-Score que les plats cuisines.\n")
    for n in noms:
        print(f"  --- {lib[n]}")
        for sc, g in d.groupby("sous_categorie"):
            a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
            if len(a) < SEUIL or len(b) < SEUIL:
                continue
            k1, k2 = int(a[n].sum()), int(b[n].sum())
            r = newcombe(k1, len(a), k2, len(b))
            etabli = "etabli" if (r[1] > 0 or r[2] < 0) else "non etabli"
            print(f"      {sc:24s} halal {100*k1/len(a):5.2f} %  temoin "
                  f"{100*k2/len(b):5.2f} %   ecart {100*r[0]:+6.2f} pts "
                  f"[{100*r[1]:+6.2f} ; {100*r[2]:+6.2f}]  {etabli}")
            lignes.append({"niveau": "gamme", "cle": sc, "famille": n,
                           "pct_halal": round(100 * k1 / len(a), 2),
                           "pct_temoin": round(100 * k2 / len(b), 2),
                           "ecart_points": round(100 * r[0], 2),
                           "ic95_bas": round(100 * r[1], 2),
                           "ic95_haut": round(100 * r[2], 2),
                           "n_halal": len(a), "n_temoin": len(b),
                           "etabli": etabli == "etabli"})
        print()

    titre("3. DANS UNE MEME MARQUE — le test de la posture")
    print("Le meme industriel, deux gammes. Si la nutrition pese moins sur la")
    print("gamme halal, c'est ici que cela se voit, et le fabricant ne peut")
    print("plus servir d'explication.\n")
    for n in noms:
        print(f"  --- {lib[n]}")
        trouve = False
        for mq, g in d.groupby("marque"):
            a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
            if len(a) < SEUIL_MARQUE or len(b) < SEUIL_MARQUE:
                continue
            k1, k2 = int(a[n].sum()), int(b[n].sum())
            r = newcombe(k1, len(a), k2, len(b))
            etabli = "etabli" if (r[1] > 0 or r[2] < 0) else "non etabli"
            trouve = True
            print(f"      {mq:22s} n={len(a):4d}/{len(b):5d}  halal "
                  f"{100*k1/len(a):5.1f} %  temoin {100*k2/len(b):5.1f} %   "
                  f"ecart {100*r[0]:+6.1f} pts "
                  f"[{100*r[1]:+6.1f} ; {100*r[2]:+6.1f}]  {etabli}")
            lignes.append({"niveau": "marque", "cle": mq, "famille": n,
                           "pct_halal": round(100 * k1 / len(a), 2),
                           "pct_temoin": round(100 * k2 / len(b), 2),
                           "ecart_points": round(100 * r[0], 2),
                           "ic95_bas": round(100 * r[1], 2),
                           "ic95_haut": round(100 * r[2], 2),
                           "n_halal": len(a), "n_temoin": len(b),
                           "etabli": etabli == "etabli"})
        if not trouve:
            print(f"      Aucune marque n'atteint {SEUIL_MARQUE} produits des "
                  f"deux cotes.")
        print()
    pd.DataFrame(lignes).to_csv(SORTIES / "y1_allegations.csv", index=False)

    titre("LECTURE — l'ecart nutritionnel excede-t-il l'ecart general ?")
    print("Les fiches halal peuvent etre un peu moins remplies sur TOUT. Ce")
    print("qui compte est donc l'ECART ENTRE LES DEUX ECARTS : le deficit")
    print("nutritionnel depasse-t-il le deficit general ? Bootstrap sur les")
    print("produits.\n")
    rng = np.random.default_rng(20260904)
    a, b = d[d.bras == "halal"], d[d.bras == "temoin"]
    ea = a.effort_nutritionnel.to_numpy(bool)
    eb = b.effort_nutritionnel.to_numpy(bool)
    aa = a.autres_revendications.to_numpy(bool)
    ab = b.autres_revendications.to_numpy(bool)

    def dd(ia, ib):
        return ((ea[ia].mean() - eb[ib].mean())
                - (aa[ia].mean() - ab[ib].mean()))

    base = dd(np.arange(len(a)), np.arange(len(b)))
    boot = np.array([dd(rng.integers(0, len(a), len(a)),
                        rng.integers(0, len(b), len(b))) for _ in range(4000)])
    bas, haut = np.percentile(boot, [2.5, 97.5])
    per = pd.DataFrame(lignes)
    per = per[per.niveau == "perimetre"].set_index("famille")
    print(f"  Effort nutritionnel      {per.loc['effort_nutritionnel'].ecart_points:+7.2f} points "
          f"[{per.loc['effort_nutritionnel'].ic95_bas:+.2f} ; "
          f"{per.loc['effort_nutritionnel'].ic95_haut:+.2f}]")
    print(f"  Autres revendications    {per.loc['autres_revendications'].ecart_points:+7.2f} points "
          f"[{per.loc['autres_revendications'].ic95_bas:+.2f} ; "
          f"{per.loc['autres_revendications'].ic95_haut:+.2f}]")
    print(f"  DIFFERENCE des deux      {100*base:+7.2f} points "
          f"[{100*bas:+.2f} ; {100*haut:+.2f}]")
    lignes.append({"niveau": "difference_des_ecarts", "cle": "", "famille": "",
                   "pct_halal": None, "pct_temoin": None,
                   "ecart_points": round(100 * base, 2),
                   "ic95_bas": round(100 * bas, 2),
                   "ic95_haut": round(100 * haut, 2),
                   "n_halal": len(a), "n_temoin": len(b),
                   "etabli": bool(haut < 0 or bas > 0)})
    print()
    if haut < 0:
        print("  Le recul de l'effort nutritionnel EXCEDE le recul general.")
        print("  L'ecart ne s'explique donc pas par un emballage globalement")
        print("  moins documente : ces gammes revendiquent, mais moins la")
        print("  nutrition.")
    elif bas > 0:
        print("  L'effort nutritionnel recule MOINS que le reste. Le motif")
        print("  attendu n'est pas observe.")
    else:
        print("  La difference n'est pas etablie : les deux familles reculent")
        print("  d'autant, et rien ne distingue la nutrition du reste.")

    g = pd.DataFrame(lignes)
    g = g[(g.niveau == "gamme") & g.etabli]
    ne = int((g[g.famille == "effort_nutritionnel"].ecart_points < 0).sum())
    na = int((g[g.famille == "autres_revendications"].ecart_points < 0).sum())
    print(f"\n  A gamme egale : le recul de l'effort nutritionnel est etabli")
    print(f"  dans {ne} gammes, celui des autres revendications dans {na}.")
    print("  Sur les plats cuisines et les preparations marinees, la gamme")
    print("  halal revendique DAVANTAGE sur la famille temoin et MOINS sur la")
    print("  nutrition : c'est la le motif le plus net.")
    pd.DataFrame(lignes).to_csv(SORTIES / "y1_allegations.csv", index=False)
    print("\nEcrit : sorties/y1_allegations.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
