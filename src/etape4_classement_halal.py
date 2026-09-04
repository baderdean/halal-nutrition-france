#!/usr/bin/env python3
"""Couche 4 — classement des MARQUES HALAL, et d'elles seules.

Le classement des 398 marques marque « gamme_halal = oui » des la premiere
reference halal du catalogue. Carrefour y figure avec 61 produits halal sur
2 868, soit 2 % : c'est un distributeur qui vend du halal, pas une marque
halal. Son rang y est fixe par les 98 % restants.

Le classement publie ici compare les marques sur leurs SEULS PRODUITS HALAL.
Les ecarts viennent de m_halal_*.csv, qui n'agrege que le bras halal : la
ligne « Fleury Michon » y porte sur ses 70 produits halal, pas sur ses 1 015
produits. C'est la seule comparaison qui reponde a « qui fait le mieux dans
le halal ».

Deux populations, deux questions, et le script publie les deux :

  MARQUES FAISANT DU HALAL   toute marque ayant une gamme halal reelle,
                             specialiste ou generaliste. Repond a « chez qui
                             le produit halal est-il le meilleur ».
  MARQUES HALAL              les seules dont le halal est le coeur du
                             catalogue. Repond a « quelles marques halal sont
                             les meilleures ».

Elles sont distinguees par trois criteres qu'il ne faut pas confondre.

  QUI FAIT DU HALAL
    au moins 5 produits tagues halal : il y a une gamme a examiner, pas une
    reference isolee.

  QUI EST UNE MARQUE HALAL
    en plus, au moins 50 % du catalogue carne tague halal : le halal est le
    coeur du catalogue, pas un rayon d'appoint.

    Ce second seuil n'est pas arbitraire. Sur les 42 marques que D4 examine,
    les taux se repartissent en deux paquets separes par un vide : 57,1 %
    puis 26,3 %, soit un saut de 30,8 points, trois fois le plus grand ecart
    suivant. Le seuil tombe dans ce vide : le deplacer n'importe ou entre
    27 % et 57 % ne changerait le classement d'aucune marque.

  QUI EST ESTIMABLE
    15 produits halal a nutrition complete (N_MIN de etape4_marques.py), la
    regle des 30 au-dessus. Une marque halal sous ce seuil est publiee a part
    avec son effectif : la taire ferait du classement un portrait des seuls
    gros volumes, alors que le rayon halal francais compte une majorite de
    petites marques.

Les ecarts proviennent du classement du BRAS HALAL (m_halal_*.csv), calcule
sur les seuls produits du bras. Aucun recalcul statistique ici.

Le tag halal est une DECLARATION d'etiquetage. Ce classement nomme des
entreprises reelles et ne dit rien de la halalite, de la conformite ni de la
qualite sanitaire d'aucun produit.
"""

from __future__ import annotations

import sys

import pandas as pd

from commun import SORTIES, echec, titre
from etape4_classement_complet import intervalles_de_rang, separabilite

BRAS_HALAL = SORTIES / "m_halal_nutriscore_score.csv"
PROFILS = SORTIES / "d4_taux_tag_par_marque.csv"

SEUIL_GAMME = 5       # produits tagues halal : une gamme, pas une reference
SEUIL_PART = 50.0     # % du catalogue carne tague halal (tombe dans le vide)
SEUIL_ESTIME = 15     # produits halal a nutrition complete pour estimer


def marques_halal(d4: pd.DataFrame) -> pd.DataFrame:
    return d4[(d4.n_tagues >= SEUIL_GAMME) & (d4.pct_tague >= SEUIL_PART)].copy()


def controle_du_vide(d4: pd.DataFrame) -> tuple[float, float, float]:
    """Verifie que le seuil tombe bien dans un vide de la distribution.

    Si un futur dump comble ce vide, le seuil redevient arbitraire et doit
    etre rediscute. L'assertion le fera savoir plutot que de le masquer.
    """
    v = sorted(d4[d4.n_tagues >= SEUIL_GAMME].pct_tague.dropna(), reverse=True)
    sauts = [(v[i] - v[i + 1], v[i + 1], v[i]) for i in range(len(v) - 1)]
    saut, bas, haut = max(sauts)
    if not bas < SEUIL_PART < haut:
        echec(f"Le seuil de {SEUIL_PART} % ne tombe plus dans le plus grand "
              f"vide de la distribution ([{bas} ; {haut}]). Le choix du seuil "
              f"doit etre rediscute avant de publier ce classement.")
    return saut, bas, haut


def _table(rows) -> list:
    l = ["| rang | rangs possibles | marque | n halal | % catalogue | ecart | "
         "IC 95 % | strates |",
         "|---:|:---:|:---|---:|---:|---:|:---:|---:|"]
    for r in rows.itertuples():
        l.append(f"| {r.rang} | {r.rang_min}-{r.rang_max} | {r.marque_affichee} "
                 f"| {r.n}{'' if r.regle_30 == 'franchie' else ' *'} "
                 f"| {r.pct_tague:.0f} | {r.ecart_median:+.1f} "
                 f"| [{r.ic95_bas:+.1f} ; {r.ic95_haut:+.1f}] "
                 f"| {r.strates_couvertes} |")
    return l


def markdown(tous, t, reste, ecartees, mh, saut, bas, haut) -> str:
    couvert, hors = int(t.n_tagues.sum()), int(reste.n_tagues.sum())
    l = [
        "# Classement des marques halal — Nutri-Score, a composition egale",
        "",
        "Ecart a la mediane de marche de la strate (sous-categorie x espece),",
        "calcule sur les **seuls produits halal** de la marque.",
        "**Negatif = meilleur que le marche sur le meme type de produit.**",
        "",
        f"## Toutes les marques faisant du halal ({len(tous)})",
        "",
        f"Au moins {SEUIL_GAMME} produits tagues halal, specialistes et "
        "generalistes ensemble.",
        "`rang_min`-`rang_max` est l'intervalle de rangs compatible avec les",
        "donnees (IC 95 % disjoints, critere conservateur) : cet ordre ne se lit",
        "pas rang par rang.",
        "",
    ] + _table(tous) + [
        "",
        "Les generalistes de ce tableau ("
        + " ; ".join(tous[tous.type != "marque halal"].marque_affichee)
        + ") sont mesures sur leurs produits",
        "halal uniquement, comme toutes les autres lignes.",
        "",
        f"## Restreint aux {len(t)} marques halal",
        "",
        f"Une marque halal a au moins {SEUIL_GAMME} produits tagues halal et au "
        f"moins {SEUIL_PART:.0f} % de son",
        "catalogue carne tague halal. Le second seuil tombe dans un vide de la",
        f"distribution — {saut:.1f} points separent {bas} % de {haut} %, trois "
        "fois le plus grand",
        f"ecart suivant : tout seuil entre {bas} % et {haut} % donne le meme "
        "resultat.",
        "",
        f"{len(mh)} marques halal au total. Ecartees comme non halal malgre "
        f"{SEUIL_GAMME} produits",
        "halal ou plus : " + ", ".join(
            f"{r.marque_affichee} ({r.pct_tague} %)"
            for r in ecartees.itertuples()) + ".",
        "",
    ] + _table(t) + [
        "",
        "`*` effectif sous 30 : ligne descriptive, non testable.",
        "",
        f"Aucune n'est meilleure que la mediane de marche de ses strates : le",
        f"meilleur ecart est {t.ecart_median.min():+.1f}.",
        "",
        f"## Les {len(reste)} marques halal que ce classement ne couvre pas",
        "",
        f"Elles ont {SEUIL_GAMME} a {SEUIL_ESTIME - 1} produits halal : une "
        "gamme reelle, pas de quoi porter",
        "une mediane. Les omettre ferait de ce classement un portrait des seuls",
        "gros volumes.",
        "",
        "| marque | produits | dont halal | % catalogue |",
        "|:---|---:|---:|---:|",
    ]
    for r in reste.itertuples():
        l.append(f"| {r.marque_affichee} | {r.n_produits} | {int(r.n_tagues)} "
                 f"| {r.pct_tague:.0f} |")
    l += [
        "",
        f"Le classement couvre {couvert} produits halal sur {couvert + hors} "
        f"({100 * couvert / (couvert + hors):.0f} %) mais",
        f"{len(t)} marques sur {len(mh)} ({100 * len(t) / len(mh):.0f} %) : les "
        "marques absentes sont petites, pas",
        "negligeables.",
        "",
        "---",
        "",
        "Le tag halal est une **declaration d'etiquetage**. Ce classement nomme",
        "des entreprises reelles et ne dit rien de la halalite, de la conformite",
        "ni de la qualite sanitaire d'aucun produit.",
    ]
    return "\n".join(l) + "\n"


def main() -> int:
    for chemin in (BRAS_HALAL, PROFILS):
        if not chemin.exists():
            echec(f"{chemin} absent. Lancer d'abord la couche 4.")
    d4 = pd.read_csv(PROFILS)
    saut, bas, haut = controle_du_vide(d4)
    mh = marques_halal(d4)

    titre("Qui est une marque halal")
    print(f"Criteres : au moins {SEUIL_GAMME} produits tagues halal ET au "
          f"moins {SEUIL_PART:.0f} % du\ncatalogue carne tague halal.\n")
    print(f"  {len(mh)} marques halal sur les {len(d4)} que D4 examine.")
    print(f"  Le seuil de {SEUIL_PART:.0f} % tombe dans le vide de la "
          f"distribution : {saut:.1f} points\n  separent {bas} % de {haut} %. "
          f"Tout seuil entre {bas} % et {haut} % donne le meme\n  resultat.\n")
    ecartees = d4[(d4.n_tagues >= SEUIL_GAMME)
                  & (d4.pct_tague < SEUIL_PART)].sort_values(
                      "pct_tague", ascending=False)
    print(f"  Ecartees comme non halal malgre {SEUIL_GAMME} produits halal ou "
          f"plus :")
    print("  " + ", ".join(f"{r.marque_affichee} ({r.pct_tague} %)"
                           for r in ecartees.itertuples()) + ".")

    # ---- 1. Toutes les marques faisant du halal, sur leurs produits halal.
    brut = (pd.read_csv(BRAS_HALAL)
              .merge(d4[["marque_tag", "marque_affichee", "n_produits",
                         "n_tagues", "pct_tague"]], left_on="marque",
                     right_on="marque_tag", how="left")
              .drop(columns=["marque_tag"]))
    orphelines = brut[brut.n_tagues.isna()]
    if len(orphelines):
        echec("Marque classee sur le bras halal et absente de D4 : "
              + ", ".join(orphelines.marque))
    brut["type"] = ["marque halal" if p >= SEUIL_PART
                    else "generaliste faisant du halal" for p in brut.pct_tague]
    colonnes = ["rang", "rang_min", "rang_max", "marque_affichee", "type", "n",
                "n_tagues", "pct_tague", "ecart_median", "ic95_bas",
                "ic95_haut", "regle_30", "strates_couvertes"]

    tous = intervalles_de_rang(
        brut.sort_values("ecart_median").reset_index(drop=True))
    titre(f"Les {len(tous)} marques faisant du halal, sur leurs produits halal")
    print("Ecart a la mediane de marche de la strate (sous-categorie x espece),")
    print("calcule sur les SEULS produits halal de la marque. Negatif = mieux")
    print("que le marche sur le meme type de produit.\n")
    sep, total = separabilite(tous)
    print(f"  Paires separees (IC 95 % disjoints) : {sep} sur {total} "
          f"({100 * sep / total:.0f} %).\n")
    print(tous[colonnes].to_string(index=False))
    tous[colonnes + ["marque"]].to_csv(
        SORTIES / "classement_halal_toutes_marques.csv", index=False)

    # ---- 2. Restreint aux marques dont le halal est le coeur du catalogue.
    t = intervalles_de_rang(
        brut[brut.marque.isin(mh.marque_tag)]
        .sort_values("ecart_median").reset_index(drop=True))
    titre(f"Restreint aux {len(t)} marques halal")
    print("Meme mesure, sans les generalistes dont le halal est un rayon "
          "d'appoint.\n")
    sep, total = separabilite(t)
    print(f"  Paires separees : {sep} sur {total} "
          f"({100 * sep / total:.0f} %).")
    print(f"  Aucune n'est meilleure que la mediane de marche de ses strates : "
          f"le\n  meilleur ecart est {t.ecart_median.min():+.1f}.\n")
    print(t[colonnes].to_string(index=False))
    t[colonnes + ["marque"]].to_csv(
        SORTIES / "classement_marques_halal.csv", index=False)

    # ---- 3. Marques halal non estimables. Les taire biaiserait le portrait.
    reste = mh[~mh.marque_tag.isin(t.marque)].sort_values(
        "n_tagues", ascending=False)
    titre(f"Marques halal non classees, faute d'effectif : {len(reste)}")
    print(f"Elles ont {SEUIL_GAMME} a {SEUIL_ESTIME - 1} produits halal : une "
          f"gamme reelle, mais pas de quoi\nporter une mediane et un "
          f"intervalle. Elles sont publiees pour ce qu'elles\nsont, une part "
          f"du rayon que ce classement ne couvre pas.\n")
    print(reste[["marque_affichee", "n_produits", "n_tagues",
                 "pct_tague"]].to_string(index=False))
    reste.to_csv(SORTIES / "marques_halal_non_estimables.csv", index=False)
    couvert, hors = int(t.n_tagues.sum()), int(reste.n_tagues.sum())
    print(f"\n  Produits halal couverts par le classement : {couvert} sur "
          f"{couvert + hors} ({100 * couvert / (couvert + hors):.0f} %).")
    print(f"  Marques halal couvertes : {len(t)} sur {len(mh)} "
          f"({100 * len(t) / len(mh):.0f} %).")
    print("  Le classement couvre donc l'essentiel des PRODUITS et une "
          "minorite des\n  MARQUES : les marques absentes sont petites, pas "
          "negligeables.")

    (SORTIES / "classement_marques_halal.md").write_text(
        markdown(tous, t, reste, ecartees, mh, saut, bas, haut),
        encoding="utf-8")
    print("\nEcrit : sorties/classement_halal_toutes_marques.csv,")
    print("        sorties/classement_marques_halal.{csv,md},")
    print("        sorties/marques_halal_non_estimables.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
