#!/usr/bin/env python3
"""Couche 5 — quatre produits que le lecteur reconnait.

Les couches precedentes comparent des sous-categories. Personne n'achete une
sous-categorie. Ici on compare le jambon au jambon, le cordon bleu au cordon
bleu, le nugget au nugget, le saucisson au saucisson, entre trois bras :
halal, kasher, et ni l'un ni l'autre.

DEUX LECTURES, jamais melangees, pour la meme raison qu'en couche 3.

  RAYON     tous les produits du meme nom, especes confondues. C'est ce que
            le client voit dans le lineaire. Mais le jambon halal est de la
            volaille et le jambon temoin est majoritairement du porc : cette
            lecture mesure le label ET le changement d'espece qu'il impose.

  A ESPECE EGALE  jambon de dinde contre jambon de dinde. Isole ce que fait
            le label une fois l'espece fixee.

  A MARQUE ET ESPECE EGALES  le jambon de volaille halal de Fleury Michon
            contre le jambon de volaille non halal de Fleury Michon. Meme
            produit, meme espece, meme fabricant : ne reste que le label.
            Fixer l'espece y est indispensable : sans elle on compare le
            jambon de dinde halal de Fleury Michon a son jambon de porc. C'est le test le
            plus dur, et le seul qui separe l'effet du LABEL de l'effet du
            FABRICANT. Il n'est possible que la ou une marque vend les deux,
            ce qui est rare.

L'ecart entre ces lectures est le resultat, pas un defaut.

REGLE DES 30 : une cellule sous 30 produits complets est decrite, jamais
testee, et sa ligne le dit. Le bras kasher tombe sous ce seuil presque
partout : le kasher est un rayon de niche en France. Ne pas le tester n'est
pas l'ignorer, c'est refuser de conclure sur 2 produits.

Les definitions produit sont figees dans config/produits_emblematiques.yaml.
Aucun filtre en dur ici.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, charger, connexion, titre

SEUIL = 30          # regle des 30
SEUIL_MARQUE = 15   # intra-marque : sous ce seuil, decrit et jamais teste
GRAINE = 20260904
N_BOOT = 4000
VARIABLES = [("nutriscore_score", "Nutri-Score en score continu", "plus bas = mieux"),
             ("sel", "sel g/100 g", "plus bas = mieux"),
             ("ags", "AGS g/100 g", "plus bas = mieux"),
             ("proteines", "proteines g/100 g", "plus haut = mieux")]


def liste_sql(tags) -> str:
    return "[" + ", ".join(f"'{t}'" for t in tags) + "]"


def expr_produit(cfg: dict) -> str:
    """Affectation ordonnee, premier match gagnant."""
    m = ["CASE"]
    for p in cfg["produits"]:
        m.append(f"WHEN len(list_intersect(categories_tags, "
                 f"{liste_sql(p['tags'])})) > 0 THEN '{p['nom']}'")
    m.append("ELSE NULL END")
    return " ".join(m)


def ic_diff(a, b, rng):
    """IC 95 % percentile de la difference des medianes. None si trop peu."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
    if len(a) < 10 or len(b) < 10:
        return None
    d = np.empty(N_BOOT)
    for i in range(N_BOOT):
        d[i] = (np.median(rng.choice(a, len(a), True))
                - np.median(rng.choice(b, len(b), True)))
    return (float(np.median(a) - np.median(b)),
            float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))


def comparer(d: pd.DataFrame, var: str, rng, cles: list) -> pd.DataFrame:
    """Un bloc par cle : effectifs, medianes, ecarts au temoin."""
    lignes = []
    for cle, g in d.groupby(cles, dropna=False):
        cle = cle if isinstance(cle, tuple) else (cle,)
        ref = g[g.bras3 == "temoin"][var].dropna().to_numpy()
        for bras in ("halal", "kasher", "temoin"):
            v = g[g.bras3 == bras][var].dropna().to_numpy()
            ligne = dict(zip(cles, cle))
            ligne.update({"bras": bras, "n": len(v),
                          "mediane": round(float(np.median(v)), 2) if len(v) else None,
                          "regle_30": "franchie" if len(v) >= SEUIL else "sous 30"})
            if bras != "temoin" and len(v) and len(ref):
                ic = ic_diff(v, ref, rng)
                if ic:
                    ligne.update({"ecart_vs_temoin": round(ic[0], 2),
                                  "ic95_bas": round(ic[1], 2),
                                  "ic95_haut": round(ic[2], 2),
                                  # Un ecart sur une cellule sous 30 n'est pas
                                  # un resultat : il est calcule, jamais lu.
                                  "testable": (len(v) >= SEUIL
                                               and len(ref) >= SEUIL)})
            lignes.append(ligne)
    return pd.DataFrame(lignes)


def comparer_intra_marque(d: pd.DataFrame, var: str, rng) -> pd.DataFrame:
    """halal contre temoin a marque, produit ET espece identiques.

    Une marque qui vend les deux versions du meme produit tient constants son
    cahier des charges, ses fournisseurs et son positionnement prix. Ce qui
    reste entre les deux lignes est le label, et rien d'autre. C'est aussi la
    seule facon de savoir si un ecart mesure le label ou le fabricant.
    """
    lignes = []
    # L'espece est dans la cle : sans elle, la ligne compare le jambon de
    # dinde halal d'une marque a son jambon de porc, et l'ecart mesure
    # l'espece.
    for (prod, marque, esp), g in d.groupby(["produit", "marque", "espece"]):
        a = g[g.bras3 == "halal"][var].dropna().to_numpy()
        b = g[g.bras3 == "temoin"][var].dropna().to_numpy()
        if len(a) < 5 or len(b) < 5:
            continue
        ic = ic_diff(a, b, rng)
        lignes.append({
            "produit": prod, "marque": marque, "espece": esp,
            "n_halal": len(a), "n_temoin": len(b),
            "mediane_halal": round(float(np.median(a)), 2),
            "mediane_temoin": round(float(np.median(b)), 2),
            "ecart": round(ic[0], 2) if ic else None,
            "ic95_bas": round(ic[1], 2) if ic else None,
            "ic95_haut": round(ic[2], 2) if ic else None,
            "testable": len(a) >= SEUIL_MARQUE and len(b) >= SEUIL_MARQUE,
        })
    return pd.DataFrame(lignes).sort_values("n_halal", ascending=False)


def afficher(t: pd.DataFrame, cles: list) -> None:
    cols = cles + ["bras", "n", "mediane", "ecart_vs_temoin", "ic95_bas",
                   "ic95_haut", "regle_30", "testable"]
    cols = [c for c in cols if c in t.columns]
    print(t[cols].to_string(index=False, na_rep=""))


def rapport(eff, rayon, espece, intra, disp, libelles) -> str:
    """Le meme resultat, ecrit pour etre lu et non pour etre grep."""
    def bloc(t, cles):
        cols = cles + ["bras", "n", "mediane", "ecart_vs_temoin",
                       "ic95_bas", "ic95_haut"]
        l = ["| " + " | ".join(cols) + " |",
             "|" + "|".join([":--"] * len(cles)) + "|:--|--:|--:|--:|--:|--:|"]
        for r in t.itertuples():
            v = [str(getattr(r, c)) for c in cles]
            e = getattr(r, "ecart_vs_temoin", None)
            ok = getattr(r, "testable", False) is True
            l.append("| " + " | ".join(v)
                     + f" | {r.bras} | {r.n}{'' if r.n >= SEUIL else ' *'} "
                     + f"| {r.mediane} "
                     + (f"| {e:+.2f} | {r.ic95_bas:+.2f} | {r.ic95_haut:+.2f} |"
                        if ok and pd.notna(e) else "|  |  |  |"))
        return l

    l = [
        "# Quatre produits que le lecteur reconnait",
        "",
        "Jambon cuit, cordon bleu, nuggets, saucisson sec, compares entre halal,",
        "kasher et ni l'un ni l'autre. Le jambon SEC est ajoute parce que son",
        "absence du rayon halal est elle-meme un resultat.",
        "",
        "`n` suivi de `*` : moins de 30 produits, ligne decrite et jamais testee.",
        "Un ecart n'est affiche que si les deux cellules comparees franchissent 30.",
        "",
        "## Combien de produits, dans chaque bras",
        "",
        "| produit | halal | kasher | ni l'un ni l'autre |",
        "|:--|--:|--:|--:|",
    ]
    for i, r in eff.iterrows():
        l.append(f"| {libelles[i]} | {r.halal} | {r.kasher} | {r.temoin} |")
    l += [
        "",
        "Le kasher ne franchit 30 que sur le jambon cuit. Partout ailleurs il est",
        "decrit et jamais teste : conclure sur 1 ou 2 produits n'est pas conclure.",
        "",
        "## Lecture 1 — le rayon",
        "",
        "Especes confondues : ce que le client trouve sous ce nom. Cette lecture",
        "melange le label et le changement d'espece qu'il impose.",
        "",
    ] + bloc(rayon, ["produit"]) + [
        "",
        "## Lecture 2 — a espece egale",
        "",
        "Jambon de dinde contre jambon de dinde. Seules les cellules testables",
        "figurent ici.",
        "",
    ] + bloc(espece, ["produit", "espece"]) + [
        "",
        "## Lecture 3 — a marque et espece egales",
        "",
        "Le meme fabricant, le meme produit, la meme espece : ne reste que le",
        "label. Une seule cellule au monde le permet dans ces donnees.",
        "",
        "| produit | marque | espece | n halal | n temoin | mediane halal "
        "| mediane temoin | ecart | IC 95 % |",
        "|:--|:--|:--|--:|--:|--:|--:|--:|:-:|",
    ] + [
        f"| {r.produit} | {r.marque} | {r.espece} | {r.n_halal} | {r.n_temoin} "
        f"| {r.mediane_halal} | {r.mediane_temoin} | {r.ecart:+.2f} "
        f"| [{r.ic95_bas:+.2f} ; {r.ic95_haut:+.2f}] |"
        for r in intra.itertuples() if r.testable
    ] + [
        "",
        "## L'ecart entre fabricants, a l'interieur du bras halal",
        "",
        "| produit | marque | n | Nutri-Score | sel | proteines |",
        "|:--|:--|--:|--:|--:|--:|",
    ] + [
        f"| {r.produit} | {r.marque} | {r.n} | {r.nutriscore} | {r.sel} "
        f"| {r.proteines} |" for r in disp.itertuples()
    ] + [
        "",
        "---",
        "",
        "Le tag halal et le tag kasher sont des **declarations d'etiquetage**.",
        "Rien ici ne dit quoi que ce soit de la halalite, de la casherout, de la",
        "conformite ni de la qualite sanitaire d'aucun produit.",
    ]
    return "\n".join(l) + "\n"


def main() -> int:
    cfg = charger("produits_emblematiques.yaml")
    q = charger("questions.yaml")
    analyses = [p["nom"] for p in cfg["produits"] if p["analyse"]]
    libelles = {p["nom"]: p["libelle"] for p in cfg["produits"]}
    con = connexion()
    rng = np.random.default_rng(GRAINE)

    d = con.execute(f"""
        SELECT {expr_produit(cfg)} AS produit, espece,
               CASE WHEN tag_halal THEN 'halal'
                    WHEN len(list_intersect(labels_tags,
                         {liste_sql(q['labels_kasher'])})) > 0 THEN 'kasher'
                    ELSE 'temoin' END AS bras3,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               CASE WHEN salt_100g BETWEEN 0 AND 100 THEN salt_100g END AS sel,
               CASE WHEN saturated_fat_100g BETWEEN 0 AND 100
                    THEN saturated_fat_100g END AS ags,
               CASE WHEN proteins_100g BETWEEN 0 AND 100
                    THEN proteins_100g END AS proteines,
               nutriscore_score, nutriscore_grade
        FROM '{PERIMETRE}'
        WHERE ({COMPLET})
          -- Un produit a la fois halal et kasher n'appartient a aucun des
          -- deux bras de cette comparaison. Ils sont rares et exclus.
          AND NOT (tag_halal AND len(list_intersect(labels_tags,
                   {liste_sql(q['labels_kasher'])})) > 0)
    """).df()
    d = d[d.produit.isin(analyses)]

    # ---- Effectifs : le lecteur doit voir ce qui est testable avant les ecarts.
    titre("Effectifs par produit et par bras (produits a nutrition complete)")
    eff = (d.groupby(["produit", "bras3"]).size().unstack(fill_value=0)
             .reindex(analyses))
    eff["libelle"] = [libelles[p] for p in eff.index]
    print(eff.to_string())
    eff.to_csv(SORTIES / "p0_effectifs_produits.csv")
    print(f"\n  Regle des 30 : une cellule sous {SEUIL} produits est decrite, "
          f"jamais testee.")
    sous = [(p, b) for p in analyses for b in ("halal", "kasher")
            if eff.loc[p, b] < SEUIL]
    print("  Cellules sous le seuil : "
          + ", ".join(f"{p}/{b} (n={eff.loc[p, b]})" for p, b in sous) + ".")

    # ---- Composition en especes : la cle de lecture de tout ce qui suit.
    titre("De quelle espece est chaque produit, dans chaque bras")
    esp = (d.groupby(["produit", "bras3", "espece"]).size()
             .unstack(fill_value=0))
    print(esp.to_string())
    esp.to_csv(SORTIES / "p1_especes_par_produit.csv")

    garde = {}
    # ---- Lecture 1 : le rayon.
    for var, libelle, sens in VARIABLES:
        titre(f"Lecture RAYON — {libelle} ({sens})")
        print("Especes confondues : ce que le client trouve sous ce nom.\n")
        t = comparer(d, var, rng, ["produit"])
        afficher(t, ["produit"])
        t.to_csv(SORTIES / f"p2_rayon_{var}.csv", index=False)
        garde.setdefault("rayon", {})[var] = t

    # ---- Lecture 2 : a espece egale.
    for var, libelle, sens in VARIABLES:
        titre(f"Lecture A ESPECE EGALE — {libelle} ({sens})")
        print("Meme produit, meme espece. Seules les lignes 'testable = True'")
        print("comparent deux cellules d'au moins 30 produits.\n")
        t = comparer(d, var, rng, ["produit", "espece"])
        t = t[t.n > 0]
        afficher(t[t.get("testable", False) == True], ["produit", "espece"])
        t.to_csv(SORTIES / f"p3_espece_{var}.csv", index=False)
        garde.setdefault("espece", {})[var] = t[t.get("testable", False) == True]

    # ---- Lecture 3 : a marque egale. Le test le plus dur.
    dm = d[d.marque.notna() & (d.marque != "")]
    for var, libelle, sens in VARIABLES:
        titre(f"Lecture A MARQUE ET ESPECE EGALES — {libelle} ({sens})")
        print("halal contre temoin chez le MEME fabricant, sur le meme produit")
        print("et la meme espece.")
        print(f"Seul un ecart avec testable = True compare deux cellules d'au "
              f"moins\n{SEUIL_MARQUE} produits. Les autres lignes sont "
              f"descriptives.\n")
        t = comparer_intra_marque(dm, var, rng)
        if len(t):
            print(t.to_string(index=False, na_rep=""))
        else:
            print("  Aucune marque ne vend les deux versions du meme produit.")
        t.to_csv(SORTIES / f"p4_intra_marque_{var}.csv", index=False)
        garde.setdefault("intra", {})[var] = t

    # ---- Dispersion DANS le bras halal : l'ecart entre fabricants halal.
    titre("Dans le bras halal : l'ecart entre fabricants")
    print("Si l'ecart intra-marque est nul mais l'ecart entre marques halal")
    print("est large, ce que mesure la comparaison n'est pas le label.\n")
    h = d[(d.bras3 == "halal") & d.marque.notna()]
    disp = (h.groupby(["produit", "marque"])
              .agg(n=("nutriscore_score", "size"),
                   nutriscore=("nutriscore_score", "median"),
                   sel=("sel", "median"), proteines=("proteines", "median"))
              .reset_index())
    disp = disp[disp.n >= 10].sort_values(["produit", "nutriscore"])
    # Les flottants de l'export OFF trainent des artefacts de conversion
    # (2.4000000953674). Arrondir a l'affichage, pas dans les calculs.
    for c in ("nutriscore", "sel", "proteines"):
        disp[c] = disp[c].round(2)
    print(disp.to_string(index=False))
    disp.to_csv(SORTIES / "p5_marques_bras_halal.csv", index=False)

    v = "nutriscore_score"
    (SORTIES / "rapport_produits_emblematiques.md").write_text(
        rapport(eff, garde["rayon"][v], garde["espece"][v],
                garde["intra"][v], disp, libelles), encoding="utf-8")

    print("\nEcrit : sorties/rapport_produits_emblematiques.md,")
    print("        sorties/p0_effectifs_produits.csv, "
          "p1_especes_par_produit.csv,\n        p2_rayon_*.csv, p3_espece_*.csv, "
          "p4_intra_marque_*.csv,\n        p5_marques_bras_halal.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
