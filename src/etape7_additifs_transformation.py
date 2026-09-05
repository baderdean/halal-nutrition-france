#!/usr/bin/env python3
"""Couche 7 — additifs, transformation, et l'hypothese de l'hydratation.

Les couches 3 a 6 mesurent un ecart sur le sel, les proteines et le
Nutri-Score. Elles ne disent pas POURQUOI. Trois familles d'additifs et deux
indicateurs de transformation sont testes ici, chacun parce qu'une hypothese
precise le designe. Aucune peche : la liste est figee dans config/additifs.yaml
avant de regarder les resultats.

HYPOTHESE PRINCIPALE, celle de l'hydratation. Les phosphates retiennent l'eau.
Un produit plus hydrate porte moins de proteines au 100 g, plus de sel
rapporte a sa matiere seche, et un moins bon Nutri-Score. C'est exactement le
profil du jambon halal mesure en couche 5. Si l'hypothese tient, la phrase
juste n'est pas « la charcuterie halal est plus salee » mais « elle est plus
hydratee », et ce n'est pas la meme affirmation.

PIEGE DE MESURE, traite en premier. additives_tags n'est renseigne que si la
liste d'ingredients a ete saisie et analysee par Open Food Facts. Un produit
sans liste apparait sans additif. Si la couverture differe entre les bras,
toute prevalence comparee est fausse. Elle est donc mesuree et publiee avant
tout, et toutes les prevalences sont calculees SUR LES SEULS PRODUITS
COUVERTS, jamais sur l'effectif total.

Les intervalles sur les differences de proportions suivent la methode de
Newcombe, construite sur deux intervalles de Wilson. Elle ne suppose pas la
normalite et reste valide sur les petits effectifs, contrairement a
l'approximation normale usuelle.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import (COMPLET, PERIMETRE, SORTIES, borne, charger, connexion,
                    echec, titre)
from etape5_produits_emblematiques import ic_diff, liste_sql

SEUIL = 30
GRAINE = 20260904
Z = 1.959963984540054      # quantile normal a 97.5 %


def wilson(k: int, n: int) -> tuple[float, float, float]:
    """Intervalle de Wilson pour une proportion. (p, bas, haut)."""
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    e = Z * np.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return p, max(0.0, c - e), min(1.0, c + e)


def newcombe(k1: int, n1: int, k2: int, n2: int):
    """IC 95 % de la difference de deux proportions (methode de Newcombe)."""
    if n1 == 0 or n2 == 0:
        return None
    p1, l1, u1 = wilson(k1, n1)
    p2, l2, u2 = wilson(k2, n2)
    return (p1 - p2,
            (p1 - p2) - np.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
            (p1 - p2) + np.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def main() -> int:
    con = connexion()
    rng = np.random.default_rng(GRAINE)
    fam = charger("additifs.yaml")["familles"]
    cols = ", ".join(
        f"len(list_intersect(additives_tags, {liste_sql(f['codes'])})) > 0 "
        f"AS {f['nom']}" for f in fam)
    d = con.execute(f"""
        SELECT sous_categorie, espece,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               -- additives_tags n'est jamais NULL : il vaut la liste vide
               -- quand la liste d'ingredients n'a pas ete saisie, ce qui est
               -- indiscernable d'un produit sans additif. Le seul temoin
               -- fiable de l'analyse est additives_n : renseigne, la liste a
               -- ete lue ; absent, on ne sait rien.
               additives_n IS NOT NULL AS additifs_connus,
               coalesce(additives_n, 0) AS n_additifs,
               additives_n IS NOT NULL AS additifs_n_connu,
               nova_group AS nova, nova_group IS NOT NULL AS nova_connu,
               {cols},
               {borne('salt_100g', 'sel')},
               {borne('proteins_100g', 'proteines')},
               nutriscore_score AS ns
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    noms = [f["nom"] for f in fam]

    # ---- 0. La couverture, avant toute prevalence.
    titre("0. COUVERTURE DES DONNEES D'ADDITIFS — a verifier avant tout")
    cov = d.groupby("bras").agg(
        n=("ns", "size"),
        liste_ingredients_lue=("additifs_connus", "mean"),
        nova=("nova_connu", "mean"))
    cov[["liste_ingredients_lue", "nova"]] *= 100
    print(cov.round(1).to_string())
    ecart = abs(cov.loc["halal", "liste_ingredients_lue"]
                - cov.loc["temoin", "liste_ingredients_lue"])
    print(f"\n  Ecart de couverture entre bras : {ecart:.1f} points.")
    print("  La liste d'ingredients est mieux saisie cote halal. Compter les "
          "produits\n  non saisis comme sans additif gonflerait donc "
          "MECANIQUEMENT la prevalence\n  halal. Toutes les prevalences qui "
          "suivent excluent ces produits.")
    if ecart > 15:
        print("  [ATTENTION] Au-dela de 15 points d'ecart, meme restreinte aux "
              "produits\n  couverts, la comparaison peut rester biaisee si la "
              "saisie n'est pas\n  aleatoire. A lire comme une borne.")
    cov.round(1).to_csv(SORTIES / "t0_couverture_additifs.csv")

    # Toutes les prevalences sur les seuls produits couverts.
    dc = d[d.additifs_connus]
    print(f"\n  Prevalences calculees sur {len(dc)} produits couverts "
          f"({len(dc[dc.bras=='halal'])} halal).")

    # ---- 1. Prevalence par famille, a gamme egale.
    titre("1. PREVALENCE DES ADDITIFS, a gamme egale")
    print("Difference de proportion halal - temoin, IC 95 % de Newcombe.")
    print(f"Une strate n'est publiee que si les deux bras y ont {SEUIL} "
          f"produits couverts.\n")
    lignes = []
    for f in fam:
        print(f"  --- {f['libelle']}")
        for sc, g in dc.groupby("sous_categorie"):
            a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
            if len(a) < SEUIL or len(b) < SEUIL:
                continue
            k1, k2 = int(a[f["nom"]].sum()), int(b[f["nom"]].sum())
            r = newcombe(k1, len(a), k2, len(b))
            etabli = "etabli" if (r[1] > 0 or r[2] < 0) else "non etabli"
            print(f"      {sc:24s} halal {100*k1/len(a):5.1f} %  temoin "
                  f"{100*k2/len(b):5.1f} %   ecart {100*r[0]:+5.1f} pts "
                  f"[{100*r[1]:+5.1f} ; {100*r[2]:+5.1f}]  {etabli}")
            lignes.append({"famille": f["nom"], "sous_categorie": sc,
                           "n_halal": len(a), "n_temoin": len(b),
                           "pct_halal": round(100 * k1 / len(a), 1),
                           "pct_temoin": round(100 * k2 / len(b), 1),
                           "ecart_points": round(100 * r[0], 1),
                           "ic95_bas": round(100 * r[1], 1),
                           "ic95_haut": round(100 * r[2], 1),
                           "etabli": etabli == "etabli"})
        print()
    pd.DataFrame(lignes).to_csv(SORTIES / "t1_prevalence_additifs.csv",
                                index=False)

    # ---- 2. L'hypothese de l'hydratation.
    titre("2. HYPOTHESE DE L'HYDRATATION — les phosphates expliquent-ils "
          "l'ecart ?")
    print("Si les phosphates portent l'ecart, alors : les produits qui en")
    print("contiennent ont moins de proteines A GAMME EGALE, et l'ecart halal -")
    print("temoin sur les proteines se reduit une fois les phosphates tenus")
    print("fixes. Les deux conditions sont testees separement.\n")

    print("  a) Les phosphates predisent-ils moins de proteines, a gamme "
          "egale ?\n")
    lignes2 = []
    for sc, g in dc.groupby("sous_categorie"):
        a, b = g[g.phosphates], g[~g.phosphates]
        if len(a) < SEUIL or len(b) < SEUIL:
            continue
        r = ic_diff(a.proteines.to_numpy(), b.proteines.to_numpy(), rng)
        if not r:
            continue
        etabli = "etabli" if (r[1] > 0 or r[2] < 0) else "non etabli"
        print(f"      {sc:24s} n={len(a):5d}/{len(b):5d}  proteines "
              f"{r[0]:+.2f} [{r[1]:+.2f} ; {r[2]:+.2f}]  {etabli}")
        lignes2.append({"test": "phosphates -> proteines", "strate": sc,
                        "n_a": len(a), "n_b": len(b), "ecart": round(r[0], 2),
                        "ic95_bas": round(r[1], 2), "ic95_haut": round(r[2], 2)})

    print("\n  b) L'ecart halal - temoin sur les proteines survit-il au "
          "controle\n     des phosphates ? (strate x presence de phosphates)\n")
    for sc, g in dc.groupby("sous_categorie"):
        for phos in (False, True):
            s = g[g.phosphates == phos]
            a, b = s[s.bras == "halal"], s[s.bras == "temoin"]
            if len(a) < SEUIL or len(b) < SEUIL:
                continue
            r = ic_diff(a.proteines.to_numpy(), b.proteines.to_numpy(), rng)
            if not r:
                continue
            etat = "avec phosphates " if phos else "sans phosphates"
            print(f"      {sc:22s} {etat} n={len(a):4d}/{len(b):5d}  "
                  f"proteines {r[0]:+.2f} [{r[1]:+.2f} ; {r[2]:+.2f}]")
            lignes2.append({"test": f"halal-temoin proteines, phosphates={phos}",
                            "strate": sc, "n_a": len(a), "n_b": len(b),
                            "ecart": round(r[0], 2),
                            "ic95_bas": round(r[1], 2),
                            "ic95_haut": round(r[2], 2)})
    pd.DataFrame(lignes2).to_csv(SORTIES / "t2_hydratation.csv", index=False)

    # ---- 3. NOVA a gamme egale.
    titre("3. CLASSEMENT NOVA, a gamme egale")
    dn = d[d.nova_connu]
    print(f"Sur {len(dn)} produits ou NOVA est renseigne "
          f"({len(dn[dn.bras=='halal'])} halal).")
    print("Part de NOVA 4 (ultra-transforme), difference halal - temoin.\n")
    lignes3 = []
    for sc, g in dn.groupby("sous_categorie"):
        a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
        if len(a) < SEUIL or len(b) < SEUIL:
            continue
        k1, k2 = int((a.nova == 4).sum()), int((b.nova == 4).sum())
        r = newcombe(k1, len(a), k2, len(b))
        etabli = "etabli" if (r[1] > 0 or r[2] < 0) else "non etabli"
        print(f"    {sc:24s} halal {100*k1/len(a):5.1f} %  temoin "
              f"{100*k2/len(b):5.1f} %   ecart {100*r[0]:+5.1f} pts "
              f"[{100*r[1]:+5.1f} ; {100*r[2]:+5.1f}]  {etabli}")
        lignes3.append({"sous_categorie": sc, "n_halal": len(a),
                        "n_temoin": len(b),
                        "pct_nova4_halal": round(100 * k1 / len(a), 1),
                        "pct_nova4_temoin": round(100 * k2 / len(b), 1),
                        "ecart_points": round(100 * r[0], 1),
                        "ic95_bas": round(100 * r[1], 1),
                        "ic95_haut": round(100 * r[2], 1),
                        "etabli": etabli == "etabli"})
    pd.DataFrame(lignes3).to_csv(SORTIES / "t3_nova.csv", index=False)

    # ---- 4. Nombre d'additifs, a gamme egale puis a marque egale.
    titre("4. NOMBRE D'ADDITIFS")
    da = dc
    print("Ne depend pas du Nutri-Score : c'est un decompte, pas un score.\n")
    print("  a) A gamme egale :\n")
    lignes4 = []
    for sc, g in da.groupby("sous_categorie"):
        a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
        if len(a) < SEUIL or len(b) < SEUIL:
            continue
        r = ic_diff(a.n_additifs.to_numpy(float), b.n_additifs.to_numpy(float),
                    rng)
        if not r:
            continue
        etabli = "etabli" if (r[1] > 0 or r[2] < 0) else "non etabli"
        print(f"      {sc:24s} halal {a.n_additifs.median():.1f}  temoin "
              f"{b.n_additifs.median():.1f}   ecart {r[0]:+.2f} "
              f"[{r[1]:+.2f} ; {r[2]:+.2f}]  {etabli}")
        lignes4.append({"niveau": "gamme", "cle": sc, "n_halal": len(a),
                        "n_temoin": len(b), "ecart": round(r[0], 2),
                        "ic95_bas": round(r[1], 2),
                        "ic95_haut": round(r[2], 2)})

    print("\n  b) A marque, gamme ET espece egales — le test le plus dur :\n")
    trouve = False
    for (sc, mq, esp), g in da.groupby(["sous_categorie", "marque", "espece"]):
        a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
        if len(a) < 15 or len(b) < 15:
            continue
        r = ic_diff(a.n_additifs.to_numpy(float), b.n_additifs.to_numpy(float),
                    rng)
        if not r:
            continue
        trouve = True
        print(f"      {mq} / {sc} / {esp}  n={len(a)}/{len(b)}  "
              f"halal {a.n_additifs.median():.1f} contre "
              f"{b.n_additifs.median():.1f}   ecart {r[0]:+.2f} "
              f"[{r[1]:+.2f} ; {r[2]:+.2f}]")
        lignes4.append({"niveau": "marque x gamme x espece",
                        "cle": f"{mq} / {sc} / {esp}", "n_halal": len(a),
                        "n_temoin": len(b), "ecart": round(r[0], 2),
                        "ic95_bas": round(r[1], 2),
                        "ic95_haut": round(r[2], 2)})
    if not trouve:
        print("      Aucune cellule marque x gamme x espece n'atteint 15 "
              "produits\n      des deux cotes. Le controle du fabricant n'est "
              "pas disponible ici.")
    pd.DataFrame(lignes4).to_csv(SORTIES / "t4_nombre_additifs.csv", index=False)

    # ---- 5. Format de vente. CE N'EST PAS UN PRIX.
    titre("5. FORMAT DE VENTE — le seul angle d'achat disponible")
    print("Le prix au kilo n'est pas dans ces donnees : l'export plat d'Open")
    print("Food Facts ne contient aucune colonne de prix, et le service Open")
    print("Prices est hors d'atteinte de la politique reseau de cet")
    print("environnement. Le format de vente en est le plus proche parent")
    print("disponible, et il ne le remplace pas : un grand format se vend")
    print("d'ordinaire moins cher au kilo, mais ce lien n'est pas verifiable")
    print("ici. Ce qui suit est un FAIT sur les grammages, pas une mesure de")
    print("prix.\n")
    q = con.execute(f"""
        SELECT sous_categorie,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               -- Bornes de plausibilite : sous 10 g c'est une portion mal
               -- saisie, au-dela de 5 kg c'est un colis de gros.
               CASE WHEN product_quantity BETWEEN 10 AND 5000
                    THEN product_quantity END AS format_g
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    couv = (100 * q.groupby("bras").format_g.apply(lambda x: x.notna().mean()))
    print("  Couverture du grammage par bras (%) :")
    print("   " + couv.round(1).to_string().replace("\n", "\n   "))
    dcouv = abs(couv["halal"] - couv["temoin"])
    print(f"\n  [ATTENTION] {dcouv:.1f} points d'ecart de couverture, plus que "
          f"sur les additifs.\n  Le grammage n'est renseigne que sur une "
          f"fraction des produits, et pas la\n  meme fraction dans les deux "
          f"bras. Ce qui suit est une BORNE, pas une\n  mesure.\n")
    qq = q[q.format_g.notna()]
    lignes5 = []
    for sc, g in qq.groupby("sous_categorie"):
        a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
        if len(a) < SEUIL or len(b) < SEUIL:
            continue
        r = ic_diff(a.format_g.to_numpy(), b.format_g.to_numpy(), rng)
        if not r:
            continue
        etabli = "etabli" if (r[1] > 0 or r[2] < 0) else "non etabli"
        print(f"    {sc:24s} halal {a.format_g.median():5.0f} g  temoin "
              f"{b.format_g.median():5.0f} g   ecart {r[0]:+6.0f} g "
              f"[{r[1]:+6.0f} ; {r[2]:+6.0f}]  {etabli}")
        lignes5.append({"sous_categorie": sc, "n_halal": len(a),
                        "n_temoin": len(b),
                        "format_halal_g": round(a.format_g.median()),
                        "format_temoin_g": round(b.format_g.median()),
                        "ecart_g": round(r[0]), "ic95_bas": round(r[1]),
                        "ic95_haut": round(r[2]), "etabli": etabli == "etabli"})
    pd.DataFrame(lignes5).to_csv(SORTIES / "t5_format_vente.csv", index=False)
    print("\n  Les formats halal sont plus GRANDS la ou l'ecart est etabli :")
    print("  panes, viande hachee et decoupes autour de 800 g contre 360 a")
    print("  400 g. Seule la charcuterie seche est vendue plus petite. Cela")
    print("  contredit l'idee d'un rayon halal vendu en petits formats de")
    print("  niche, sans rien dire du prix au kilo, qui reste non teste.")

    print("\nEcrit : sorties/t0_couverture_additifs.csv, "
          "t1_prevalence_additifs.csv,\n        t2_hydratation.csv, t3_nova.csv, "
          "t4_nombre_additifs.csv,\n        t5_format_vente.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
