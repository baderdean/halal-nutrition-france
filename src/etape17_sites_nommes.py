#!/usr/bin/env python3
"""Couche 17 — nommer les sites de production francais.

La couche 14 decode la geographie d'une estampille sans source externe, mais
bute sur le nom : `fr-56-222-002` designe un etablissement dans une commune,
pas une entreprise. Le registre des etablissements agrees de la DGAL fait ce
lien, par le numero d'agrement.

CE QUE CETTE COUCHE PRODUIT : un classement de SITES NOMMES, sur l'ecart de
leurs produits a la mediane de marche de leur strate.

CE QU'ELLE NE DIT PAS, ET QU'AUCUNE DE SES LIGNES N'AUTORISE A DIRE.

  1. Rien sur la HALALITE d'un produit, ni sur la conformite d'un site a une
     norme religieuse ou sanitaire. Le registre atteste un agrement
     sanitaire europeen, rien d'autre. Le tag halal est une declaration
     d'etiquetage.

  2. Rien sur le SAVOIR-FAIRE d'un site. Un faconnier execute le cahier des
     charges de ses donneurs d'ordre. Le classement porte sur ce qui sort du
     site, et la colonne `ecart_sans_dominante` mesure la part qui tient a un
     seul client : quand l'ecart s'y effondre, il etait celui d'une marque.

  3. Rien qui ressemble a une intention. Un ecart de composition n'est pas un
     choix, et AGENTS.md interdit toute formulation qui le suggererait.

TROIS PRECAUTIONS DE RAPPROCHEMENT, chacune mesuree et publiee.

  a. Le meme numero d'agrement porte parfois PLUSIEURS raisons sociales dans
     le registre — exploitants successifs, ou graphies differentes selon les
     listes. Ces sites sont marques `nom_ambigu` et leurs noms sont TOUS
     affiches. En choisir un serait inventer une attribution.

  b. Les fichiers de la DGAL ont des lignes de longueur variable : la colonne
     des activites y deborde en champs supplementaires. Le lecteur repere le
     numero d'agrement par sa FORME (dd.ddd.ddd) et lit les champs suivants
     par rapport a lui, ce qui resiste aux deux mises en page rencontrees.
     Les lignes qu'il ne peut pas lire sont comptees et publiees.

  c. Un site sans nom n'est pas retire : il reste au classement avec son code
     et la mention explicite qu'il n'a pas ete apparie.
"""

from __future__ import annotations

import csv
import re
import sys

import pandas as pd

from commun import RACINE, SORTIES, titre

REGISTRE = RACINE / "donnees_registre"
# La forme du numero d'agrement : departement, commune INSEE, ordre.
MOTIF_AGREMENT = re.compile(r"^\d{2}\.\d{3}\.\d{3}$")
# Champs lus a partir du numero d'agrement, dans cet ordre.
APRES = ["siret", "nom", "adresse", "cp", "commune"]


def lire_registre() -> tuple[pd.DataFrame, dict]:
    """Lit toutes les listes rapatriees. Position relative au numero."""
    lignes, rejets = [], {}
    for f in sorted(REGISTRE.glob("SSA*")):
        with open(f, encoding="utf-8") as fh:
            rows = list(csv.reader(fh))
        perdues = 0
        for row in rows[1:]:
            row = [c.strip() for c in row]
            i = next((k for k, c in enumerate(row)
                      if MOTIF_AGREMENT.match(c)), None)
            if i is None or len(row) < i + 1 + len(APRES):
                perdues += 1
                continue
            e = {"agrement": row[i], "source": f.name}
            for d, nom in enumerate(APRES, start=1):
                e[nom] = row[i + d]
            lignes.append(e)
        rejets[f.name] = perdues
    return pd.DataFrame(lignes), rejets


def main() -> int:
    if not REGISTRE.exists() or not any(REGISTRE.glob("SSA*")):
        print("Registre absent. Le rapatrier d'abord :", file=sys.stderr)
        print("  workflow couche14-registre, etape « registre ».",
              file=sys.stderr)
        return 1

    titre("Le registre des etablissements agrees")
    r, rejets = lire_registre()
    perdues = sum(rejets.values())
    print(f"  {len(r)} lignes lues dans {len(rejets)} listes de la DGAL,")
    print(f"  {perdues} illisibles ({100 * perdues / (len(r) + perdues):.1f} %).")
    for f, n in sorted(rejets.items()):
        if n:
            print(f"      {n:>4} rejets  {f}")
    print(f"\n  {r.agrement.nunique()} numeros d'agrement distincts.")
    amb = r.groupby("agrement").nom.nunique()
    print(f"  {int((amb > 1).sum())} portent plus d'une raison sociale : "
          "exploitants\n  successifs, ou graphies differentes selon les "
          "listes. Aucun n'est\n  tranche ici.")

    # Une ligne par agrement : tous les noms, jamais le premier venu.
    reg = (r.groupby("agrement")
             .agg(nom=("nom", lambda x: " / ".join(sorted(set(x)))),
                  n_noms=("nom", "nunique"),
                  commune=("commune", lambda x: sorted(set(x))[0]),
                  cp=("cp", lambda x: sorted(set(x))[0]),
                  n_siret=("siret", "nunique"),
                  listes=("source", lambda x: len(set(x))))
             .reset_index())
    reg.to_csv(SORTIES / "h0_registre_agrements.csv", index=False)

    s = pd.read_csv(SORTIES / "s1_sites_france.csv")
    s["agrement"] = (s.etablissement.str.replace("^fr-", "", regex=True)
                                    .str.replace("-", "."))
    j = s.merge(reg, on="agrement", how="left")
    j["nom_ambigu"] = j.n_noms.fillna(0) > 1
    j["nom"] = j.nom.fillna("non apparie au registre")

    titre("Couverture du rapprochement")
    print(f"  {len(j)} sites classes par la couche 14,")
    print(f"  {int((j.n_noms.notna()).sum())} apparies au registre "
          f"({100 * j.n_noms.notna().mean():.1f} %).")
    print("\n  Un site non apparie reste au classement avec son code et la")
    print("  mention explicite. Le retirer ferait disparaitre precisement les")
    print("  etablissements que le registre documente le moins bien.")

    pub = j[(j.regle_30 == "franchie") & (~j.alerte_mer)].copy()
    pub = pub.sort_values(["ecart_median", "etablissement"])
    cols = ["etablissement", "nom", "commune", "departement", "n", "n_marques",
            "n_halal", "ecart_median", "sel_median", "marque_dominante",
            "part_dominante_pct", "ecart_sans_dominante", "nom_ambigu"]
    pub[cols].to_csv(SORTIES / "h1_sites_nommes.csv", index=False)
    j[cols].to_csv(SORTIES / "h2_sites_nommes_complet.csv", index=False)

    titre("Les sites francais, nommes")
    print("Sites d'au moins 30 produits, sans produit de la mer. Ecart a la")
    print("mediane de marche de la strate (sous-categorie x espece) : negatif")
    print("= mieux que le marche sur le meme type de produit.\n")
    print(f"  {len(pub)} sites, dont "
          f"{int((pub.nom == 'non apparie au registre').sum())} sans nom et "
          f"{int(pub.nom_ambigu.sum())} a raison sociale multiple.\n")
    aff = ["etablissement", "nom", "commune", "n", "n_halal", "ecart_median",
           "sel_median", "marque_dominante", "part_dominante_pct",
           "ecart_sans_dominante"]
    print("  --- 12 sites les mieux classes")
    print(pub.head(12)[aff].to_string(index=False))
    print("\n  --- 12 sites les moins bien classes")
    print(pub.tail(12)[aff].to_string(index=False))

    print("\n  A LIRE AVEC CHAQUE LIGNE. `ecart_sans_dominante` recalcule")
    print("  l'ecart apres retrait du premier client du site. Quand il")
    print("  s'effondre, l'ecart etait celui d'une MARQUE et non d'une usine.")
    bascule = pub[(pub.ecart_sans_dominante.notna())
                  & ((pub.ecart_sans_dominante - pub.ecart_median).abs() >= 5)]
    if len(bascule):
        print(f"\n  {len(bascule)} sites basculent d'au moins 5 points :")
        print(bascule[["etablissement", "nom", "marque_dominante",
                       "part_dominante_pct", "ecart_median",
                       "ecart_sans_dominante"]].to_string(index=False))
        bascule.to_csv(SORTIES / "h3_bascule_sans_dominante.csv", index=False)

    # --- Les sites qui sortent du halal, description seule.
    titre("Les sites qui sortent du halal")
    print("DESCRIPTIF, PAS UN CLASSEMENT. La couche 10 a mesure sur le halal")
    print("une dispersion INTRA site superieure a celle du temoin (7,82 contre")
    print("5,55) et un pouvoir explicatif du site plus faible (0,168 contre")
    print("0,304). Un site n'a donc pas de « niveau » halal stable.\n")
    h = j[j.n_halal >= 10].sort_values(["n_halal", "etablissement"],
                                       ascending=[False, True])
    if len(h):
        print(h[["etablissement", "nom", "commune", "n", "n_halal",
                 "n_marques", "ecart_median", "sel_median",
                 "marque_dominante"]].to_string(index=False))
        h.to_csv(SORTIES / "h4_sites_halal_nommes.csv", index=False)
    print("\n  Ces lignes disent QUI FABRIQUE, pas si un produit est halal ni")
    print("  si une entreprise respecte quoi que ce soit. Le registre atteste")
    print("  un agrement sanitaire europeen, rien d'autre.")

    print("\nEcrit : sorties/h0_registre_agrements.csv, h1_sites_nommes.csv,")
    print("        h2_sites_nommes_complet.csv, h3_bascule_sans_dominante.csv,")
    print("        h4_sites_halal_nommes.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
