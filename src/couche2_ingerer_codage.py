#!/usr/bin/env python3
"""Couche 2 — ingestion du double codage humain.

Convertit le classeur rempli en CSV d'entree et separe DEUX variables que la
saisie a melangees, parce qu'elles ne mesurent pas la meme chose :

  source=image    l'estampille a ete lue sur la photo Open Food Facts.
                  Seules ces lignes sont comparables a la lecture machine.
  source=externe  l'estampille a ete etablie autrement (site du fabricant,
                  recherche en ligne), la photo ne la montrant pas.
                  Meilleure mesure du statut halal reel, mais hors de portee
                  d'un modele de vision : les compter dans un taux d'erreur
                  machine reviendrait a reprocher au modele de ne pas savoir
                  ce qui n'est pas sur l'image.

Produit aussi la mesure qui commande toute la couche 1 : le taux de faux
negatifs du tag `en:halal` dans le bras temoin.
"""

from __future__ import annotations

import math
import sys

import pandas as pd

from commun import PERIMETRE, RACINE, SORTIES, connexion, echec, titre

CLASSEUR = RACINE / "donnees_humaines" / "double_codage_rempli.xlsx"
CSV = RACINE / "donnees_humaines" / "double_codage.csv"
SUR_IMAGE = ("nette", "partiel", "floue", "trop_petite")


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - m), min(1.0, c + m)


def main() -> int:
    if not CLASSEUR.exists():
        echec(f"{CLASSEUR} absent.")
    d = pd.read_excel(CLASSEUR, sheet_name="Codage", dtype={"Code-barres": str})
    d.columns = ["n", "code", "marque", "lien", "h_estampille_halal",
                 "h_certificateur", "h_lisibilite", "h_commentaire"]
    d["code"] = d.code.astype(str).str.strip()
    for c in ("h_estampille_halal", "h_certificateur", "h_lisibilite",
              "h_commentaire"):
        d[c] = d[c].fillna("").astype(str).str.strip()

    # Origine de la lecture, deduite mecaniquement de la lisibilite saisie.
    d["source_lecture"] = "non_code"
    d.loc[d.h_lisibilite.isin(SUR_IMAGE), "source_lecture"] = "image"
    d.loc[d.h_lisibilite == "zone_absente", "source_lecture"] = "externe"

    d.drop(columns=["lien"]).to_csv(CSV, index=False)

    titre("INGESTION DU DOUBLE CODAGE HUMAIN")
    print(f"  {len(d)} lignes  ->  {CSV}")
    print("\n  Origine de la lecture :")
    print(d.source_lecture.value_counts().to_string())
    print("\n  Estampille saisie :")
    print(d.h_estampille_halal.value_counts().to_string())

    con = connexion()
    p = con.execute(
        f"SELECT code, bras, sous_categorie, brands FROM '{PERIMETRE}'").df()
    p["code"] = p.code.astype(str)
    j = d.merge(p, on="code", how="left")
    if j.bras.isna().any():
        echec(f"{int(j.bras.isna().sum())} codes du codage humain absents du "
              "perimetre. Le perimetre a change depuis le tirage.")

    titre("FAUX NEGATIFS DU TAG en:halal")
    print("Un produit du bras TEMOIN portant une estampille halal est un faux")
    print("negatif du tag. C'est la mesure qui borne l'amplitude de tous les")
    print("ecarts de la couche 1.\n")
    print(pd.crosstab(j.bras, j.h_estampille_halal, margins=True).to_string())

    lignes = []
    for bras, etiquette in [("temoin", "faux negatifs (temoin avec estampille)"),
                            ("halal", "tagues halal SANS estampille trouvee")]:
        sous = j[j.bras == bras]
        cible = "oui" if bras == "temoin" else "non"
        k, n = int((sous.h_estampille_halal == cible).sum()), len(sous)
        bas, haut = wilson(k, n)
        lignes.append({"bras": bras, "mesure": etiquette, "k": k, "n": n,
                       "taux_pct": round(100 * k / n, 1) if n else None,
                       "ic95_bas_pct": round(100 * bas, 1),
                       "ic95_haut_pct": round(100 * haut, 1)})
    res = pd.DataFrame(lignes)
    print()
    print(res.to_string(index=False))
    SORTIES.mkdir(exist_ok=True)
    res.to_csv(SORTIES / "couche2_faux_negatifs.csv", index=False)
    print(f"\n  -> {SORTIES / 'couche2_faux_negatifs.csv'}")

    titre("CE QUI RESTE HORS DE PORTEE")
    n_img = int((d.source_lecture == "image").sum())
    print(f"  Lignes lues sur l'image, comparables a la machine : {n_img}")
    print("  Minimum exige pour publier un taux d'erreur machine  : 200")
    if n_img < 200:
        print(f"  -> il en manque {200 - n_img}. Le taux d'erreur de la lecture")
        print("     automatique n'est PAS calculable, et la lecture machine")
        print("     reste descriptive.")

    titre("CERTIFICATEURS RELEVES A LA MAIN")
    cert = j[j.h_certificateur != ""]
    print(f"  {len(cert)} produits portent un certificateur identifie, contre")
    print("  165 pour le tag OFF sur tout le perimetre. Le releve manuel est")
    print("  radicalement plus riche que la taxonomie.")
    print("\n  Repartition par origine de la lecture :")
    print(cert.source_lecture.value_counts().to_string())
    cert.groupby("h_certificateur").size().sort_values(
        ascending=False).rename("n").to_csv(SORTIES / "couche2_certificateurs_humains.csv")
    print(f"\n  -> {SORTIES / 'couche2_certificateurs_humains.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
