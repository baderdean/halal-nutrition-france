#!/usr/bin/env python3
"""Couche 2 — taux d'erreur de la lecture d'image, contre double codage humain.

La lecture machine n'est pas une variable d'analyse tant que ce script n'a pas
tourne. Il compare sorties/couche2_lecture_image.csv a
donnees_humaines/double_codage.csv, rempli a la main EN AVEUGLE par un humain.

Sort en erreur si le taux depasse le seuil : la variable est alors declassee en
descriptive, et le pipeline le dit au lieu de continuer (AGENTS.md, critere
d'acceptation de la couche 2).
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from commun import RACINE, SORTIES, echec, titre

HUMAIN = RACINE / "donnees_humaines" / "double_codage.csv"
MACHINE = SORTIES / "couche2_lecture_image.csv"
SEUIL_DEFAUT = 0.10
N_MIN = 200          # exigence des specs pour le parseur viande, reprise ici


def wilson(k: int, n: int, z: float = 1.96):
    """IC 95 % de Wilson. Preferable a l'IC normal sur des taux proches de 0."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - m), min(1.0, c + m))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seuil", type=float, default=SEUIL_DEFAUT)
    ap.add_argument("--n-min", type=int, default=N_MIN)
    args = ap.parse_args()

    if not HUMAIN.exists():
        echec(
            f"{HUMAIN} absent.\n"
            "    Le double codage humain est un fichier d'ENTREE du depot, pas "
            "une sortie generee.\n"
            "    Remplir sorties/double_codage_a_remplir.csv a la main, en "
            "aveugle, et le deposer la."
        )
    if not MACHINE.exists():
        echec(f"{MACHINE} absent. Lance d'abord couche2_lecture_image.py.")

    h = pd.read_csv(HUMAIN, dtype={"code": str})
    m = pd.read_csv(MACHINE, dtype={"code": str})
    j = h.merge(m, on="code", suffixes=("_h", "_m"))

    titre("COUCHE 2 — taux d'erreur de la lecture d'image")
    print(f"  produits doublement codes : {len(j)}")
    if len(j) < args.n_min:
        echec(
            f"seulement {len(j)} produits doublement codes, minimum "
            f"{args.n_min}. Un taux d'erreur sur un echantillon plus petit "
            "n'est pas publiable. Completer le double codage."
        )

    lignes = []
    for nom, col_h, col_m in [
        ("estampille halal", "h_estampille_halal", "estampille_halal"),
        ("certificateur", "h_certificateur", "certificateur_texte"),
    ]:
        v = j[[col_h, col_m]].fillna("").astype(str)
        v = v.apply(lambda s: s.str.strip().str.lower())
        # Le certificateur se compare sur la presence d'un nom, pas sur son
        # orthographe : la normalisation des variantes est un travail humain
        # (config a construire), pas une correction automatique.
        if nom == "certificateur":
            v = (v != "").astype(int).astype(str)
        d = (v[col_h] != v[col_m])
        k, n = int(d.sum()), len(v)
        bas, haut = wilson(k, n)
        lignes.append({"variable": nom, "n": n, "desaccords": k,
                       "taux_erreur": round(k / n, 4),
                       "ic95_bas": round(bas, 4), "ic95_haut": round(haut, 4),
                       "verdict": "utilisable" if k / n <= args.seuil
                                  else "DECLASSEE en descriptive"})
    res = pd.DataFrame(lignes)
    print()
    print(res.to_string(index=False))
    res.to_csv(SORTIES / "couche2_taux_erreur.csv", index=False)
    print(f"\n  -> {SORTIES / 'couche2_taux_erreur.csv'}")

    # Erreur correlee a la marque : le risque specifique de cette lecture.
    if "marque_tag" in j.columns:
        v = j[["h_estampille_halal", "estampille_halal"]].fillna("").astype(str)
        j["_faux"] = (v.iloc[:, 0].str.strip().str.lower()
                      != v.iloc[:, 1].str.strip().str.lower())
        par_marque = j.groupby("marque_tag")["_faux"].agg(["sum", "count"])
        concentrees = par_marque[(par_marque["sum"] >= 2)]
        print(f"\n  Marques concentrant au moins 2 desaccords : "
              f"{len(concentrees)}")
        if len(concentrees):
            print("  Une erreur groupee sur une marque n'est pas du bruit : "
                  "elle suit\n  le design d'emballage et se propage a toute "
                  "la gamme.")
            print(concentrees.sort_values("sum", ascending=False)
                  .head(15).to_string())

    mauvais = res[res.verdict != "utilisable"]
    if len(mauvais):
        echec(
            "taux d'erreur au-dessus du seuil pour : "
            + ", ".join(mauvais.variable)
            + f" (seuil {args.seuil:.0%}).\n"
            "    Ces variables sont declassees en descriptives. Elles "
            "n'entrent dans aucun modele\n    et ne portent aucune conclusion "
            "de l'article. Le rapport doit le dire."
        )
    print("\n  Lecture d'image utilisable, sous reserve du taux publie "
          "ci-dessus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
