#!/usr/bin/env python3
"""Couche 15 — MDD, industriel generaliste, specialiste du halal.

QUESTION. Dans le halal, une marque de distributeur fait-elle mieux ou moins
bien qu'un industriel generaliste, et l'un des deux fait-il mieux ou moins
bien qu'un specialiste du halal ? La comparaison porte sur les SEULS produits
halal des trois familles : comparer le halal d'un specialiste au catalogue
entier de Fleury Michon ne repondrait a rien.

TROIS FAMILLES, dont deux se deduisent des donnees et une seule est declaree.
Le detail de la regle et les preuves sont dans config/familles_marques.yaml.

  mdd                 marque appartenant a une enseigne. NON OBSERVABLE dans
                      une table de composition : liste declaree, chaque entree
                      portant sa preuve.
  specialiste_halal   au moins 50 % du catalogue carne tague halal.
  industriel          moins de 50 %, et pas une marque de distributeur.

CE QUE CETTE COUCHE NE PEUT PAS FAIRE, ET NE FAIT PAS.

  1. Attribuer un ecart a la famille elle-meme. La famille mdd repose sur
     TROIS marques et Carrefour en fournit la majorite : « les MDD » et
     « Carrefour » sont ici la meme mesure faite deux fois. Le script publie
     donc systematiquement le resultat sans Carrefour a cote.

  2. Se fier a un intervalle etroit. Deux produits d'une meme marque ne sont
     pas deux observations independantes : la couche 10 a mesure un ICC de
     0,304 a strate fixee. Tous les IC de ce fichier sont donc calcules par
     BOOTSTRAP DE GRAPPES sur les marques, jamais sur les produits. Avec 3 et
     6 marques, deux des trois familles donnent des IC tres larges. C'est la
     precision reelle de la comparaison, pas un defaut de la methode.

  3. Dire pourquoi. Une difference entre familles peut venir du creneau, du
     site, du prix ou de la recette. Les couches 8, 10 et 13 ont mesure ces
     trois-la separement.

Les ecarts sont calcules a composition egale : ecart a la mediane de MARCHE
de la strate (sous-categorie x espece), les deux bras confondus au
denominateur. Sans cela, on comparerait des merguez a du jambon.

Le tag halal est une DECLARATION d'etiquetage. Ce fichier nomme des
entreprises reelles et ne dit rien de la halalite, de la conformite ni de la
qualite sanitaire d'aucun produit.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, charger, connexion, \
    echec, titre

GRAINE = 20260904
TIRAGES = 4000
SEUIL_GAMME = 5       # produits tagues halal : une gamme, pas une reference
SEUIL_PART = 50.0     # % du catalogue carne tague halal (tombe dans un vide)
SEUIL = 30            # regle des 30 : sous ce seuil on decrit, on ne teste pas

FAMILLES = ["mdd", "industriel", "specialiste_halal"]
LIBELLE = {"mdd": "MDD (marque de distributeur)",
           "industriel": "industriel generaliste",
           "specialiste_halal": "specialiste du halal"}


def familles() -> tuple[dict, set]:
    cfg = charger("familles_marques.yaml")
    mdd = {e["marque"]: e for e in cfg["mdd"]}
    return mdd, set(cfg.get("exclusions", []))


def controle_du_vide(t: pd.DataFrame) -> tuple[float, float, float]:
    """Le seuil de 50 % doit tomber dans le plus grand vide de la distribution.

    Si un futur dump comble ce vide, le seuil redevient un choix arbitraire et
    la frontiere entre industriel et specialiste devient une decision de
    l'analyste. L'assertion le fait savoir plutot que de le masquer.
    """
    v = sorted(t.part.dropna(), reverse=True)
    sauts = [(v[i] - v[i + 1], v[i + 1], v[i]) for i in range(len(v) - 1)]
    saut, bas, haut = max(sauts)
    if not bas < SEUIL_PART < haut:
        echec(f"Le seuil de {SEUIL_PART} % ne tombe plus dans le plus grand "
              f"vide de la distribution ([{bas} ; {haut}]). La frontiere entre "
              "industriel et specialiste doit etre rediscutee avant de "
              "publier cette comparaison.")
    return saut, bas, haut


def grappes(d: pd.DataFrame, col: str) -> dict:
    """Tableau par marque : (somme des valeurs triees) pour un bootstrap rapide."""
    return {m: g[col].to_numpy(float) for m, g in d.groupby("marque")}


def boot_mediane(paquets: dict, rng) -> np.ndarray:
    """Mediane d'une famille, marques retirees et remises.

    On tire des MARQUES, pas des produits. Tirer des produits supposerait que
    deux merguez de la meme marque sont deux observations independantes.
    """
    cles = list(paquets)
    out = np.empty(TIRAGES)
    for i in range(TIRAGES):
        k = rng.integers(0, len(cles), len(cles))
        out[i] = np.median(np.concatenate([paquets[cles[j]] for j in k]))
    return out


def ic(v: np.ndarray) -> tuple[float, float]:
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def comparer(d: pd.DataFrame, col: str, etiquette: str) -> pd.DataFrame:
    """Mediane par famille, puis differences deux a deux, IC de grappes.

    Les lignes sans valeur sur la mesure sont retirees ICI et leur nombre est
    publie : 436 produits du perimetre ont une nutrition complete sans
    Nutri-Score calcule, et 271 un sel hors bornes de plausibilite. Les
    garder ferait une mediane NaN ; les retirer en silence ferait un effectif
    faux.
    """
    manquants = int(d[col].isna().sum())
    if manquants:
        print(f"  ({manquants} produits sans valeur sur « {etiquette} » "
              "retires du calcul)")
    d = d[d[col].notna()]
    rng = np.random.default_rng(GRAINE)
    tirs, lignes = {}, []
    for f in FAMILLES:
        g = d[d.famille == f]
        if not len(g):
            continue
        p = grappes(g, col)
        tirs[f] = boot_mediane(p, rng)
        b, h = ic(tirs[f])
        lignes.append({"mesure": etiquette, "famille": f,
                       "marques": g.marque.nunique(), "n": len(g),
                       "mediane": round(float(g[col].median()), 2),
                       "ic95_bas": round(b, 2), "ic95_haut": round(h, 2),
                       "regle_30": "franchie" if len(g) >= SEUIL else "sous 30"})
    t = pd.DataFrame(lignes)
    diffs = []
    for i, a in enumerate(FAMILLES):
        for b in FAMILLES[i + 1:]:
            if a not in tirs or b not in tirs:
                continue
            v = tirs[a] - tirs[b]
            lo, hi = ic(v)
            point = (float(d[d.famille == a][col].median())
                     - float(d[d.famille == b][col].median()))
            diffs.append({"mesure": etiquette, "famille_a": a, "famille_b": b,
                          "difference": round(point, 2),
                          "ic95_bas": round(lo, 2), "ic95_haut": round(hi, 2),
                          "etabli": bool(lo > 0 or hi < 0)})
    return t, pd.DataFrame(diffs)


def dire(t: pd.DataFrame, dif: pd.DataFrame, unite: str) -> None:
    print(t.to_string(index=False))
    print()
    for r in dif.itertuples():
        verdict = "ETABLI" if r.etabli else "non etabli"
        print(f"  {LIBELLE[r.famille_a]:30s} - {LIBELLE[r.famille_b]:30s} "
              f"{r.difference:+6.2f} [{r.ic95_bas:+.2f} ; {r.ic95_haut:+.2f}] "
              f"{unite}  {verdict}")


def main() -> int:
    mdd, exclus = familles()
    con = connexion()

    d = con.execute(f"""
        SELECT code, product_name,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               sous_categorie, espece, tag_halal,
               nutriscore_score AS ns, {borne('salt_100g', 'sel')},
               {borne('proteins_100g', 'prot')}
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    d["marque"] = [str(x) if x is not None and x == x else None for x in d.marque]

    # Catalogue et part halal mesures sur le PERIMETRE ENTIER, pas sur les
    # seuls produits a nutrition complete : la part halal d'une marque est une
    # propriete de son catalogue, pas de la qualite de saisie de sa nutrition.
    cat = con.execute(f"""
        SELECT regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               count(*) AS n_catalogue,
               count(*) FILTER (WHERE tag_halal) AS n_halal
        FROM '{PERIMETRE}' WHERE brands_tags IS NOT NULL GROUP BY 1 ORDER BY 1
    """).df()
    cat["marque"] = [str(x) if x is not None and x == x else None
                     for x in cat.marque]
    cat = cat[cat.marque.notna() & ~cat.marque.isin(exclus)]
    cat = cat[cat.n_halal >= SEUIL_GAMME].copy()
    cat["part"] = (100.0 * cat.n_halal / cat.n_catalogue).round(1)

    titre("Trois familles, et comment chaque marque y arrive")
    saut, bas, haut = controle_du_vide(cat)
    print(f"Controle du seuil : le plus grand vide de la distribution des parts")
    print(f"halal va de {bas:.1f} % a {haut:.1f} % (saut de {saut:.1f} points). "
          f"Le seuil de\n{SEUIL_PART:.0f} % tombe dedans : le deplacer dans ce "
          "vide ne changerait l'appartenance\nd'aucune marque.\n")
    cat["famille"] = ["mdd" if m in mdd
                      else ("specialiste_halal" if p >= SEUIL_PART
                            else "industriel")
                      for m, p in zip(cat.marque, cat.part)]
    cat["preuve_mdd"] = [mdd[m]["preuve"] if m in mdd else "" for m in cat.marque]
    cat["enseigne"] = [mdd[m]["enseigne"] if m in mdd else "" for m in cat.marque]

    for f in FAMILLES:
        # Tri secondaire par nom : sans lui, deux marques a egalite sortent
        # dans un ordre qui change d'une execution a l'autre, et un fichier
        # versionne se met a bouger sans qu'aucune donnee n'ait change.
        g = cat[cat.famille == f].sort_values(["n_halal", "marque"],
                                              ascending=[False, True])
        print(f"  {LIBELLE[f]} — {len(g)} marques, "
              f"{int(g.n_halal.sum())} produits halal au catalogue")
        for r in g.itertuples():
            note = (f"  [{r.preuve_mdd}, {r.enseigne}]" if r.preuve_mdd else "")
            print(f"      {r.marque:22s} {int(r.n_halal):4d} halal sur "
                  f"{int(r.n_catalogue):5d} ({r.part:5.1f} %){note}")
        print()
    cat.to_csv(SORTIES / "f1_familles_marques.csv", index=False)

    # --- Ecart a composition egale, calcule sur le MARCHE entier.
    d["strate"] = d.sous_categorie + " / " + d.espece
    n = d.groupby("strate").size()
    d = d[d.strate.isin(n[n >= SEUIL].index)].copy()
    d["ecart"] = d.ns - d.groupby("strate").ns.transform("median")
    d["ecart_sel"] = d.sel - d.groupby("strate").sel.transform("median")

    tous_halal = d[d.tag_halal]
    h = tous_halal.merge(cat[["marque", "famille", "part"]], on="marque")
    hors = len(tous_halal) - len(h)
    sans_marque = int(tous_halal.marque.isna().sum())

    # La moitie du bras halal n'a pas de marque a gamme. Si cette moitie se
    # comportait autrement, la comparaison des familles decrirait un
    # sous-ensemble choisi. Mesure avant de comparer, comme pour les additifs.
    titre("Couverture : quelle part du bras halal ces trois familles couvrent")
    dedans = set(cat.marque)
    reste = d[d.tag_halal & ~d.marque.isin(dedans) & d.ecart.notna()]
    dans = d[d.tag_halal & d.marque.isin(dedans) & d.ecart.notna()]
    print(f"  Dans les familles : {len(dans)} produits, ecart median "
          f"{dans.ecart.median():+.1f}, sel {dans.sel.median():.2f}")
    print(f"  Hors familles     : {len(reste)} produits, ecart median "
          f"{reste.ecart.median():+.1f}, sel {reste.sel.median():.2f}")
    print("\n  Si ces deux lignes divergent, la comparaison des familles ne")
    print("  decrit pas le rayon halal mais sa moitie identifiable.")
    pd.DataFrame([
        {"groupe": "dans_familles", "n": len(dans),
         "ecart_median": round(float(dans.ecart.median()), 1),
         "sel_median": round(float(dans.sel.median()), 2)},
        {"groupe": "hors_familles", "n": len(reste),
         "ecart_median": round(float(reste.ecart.median()), 1),
         "sel_median": round(float(reste.sel.median()), 2)},
    ]).to_csv(SORTIES / "f0_couverture.csv", index=False)

    titre("Les trois familles comparees sur leurs SEULS produits halal")
    print(f"{len(h)} produits halal classes. {hors} restent hors familles, dont")
    print(f"{sans_marque} sans marque saisie et le reste appartenant a des "
          "marques de moins de\n5 produits halal : sans gamme, il n'y a pas de "
          "politique de marque a lire.\n")
    print("Ecart a la mediane de marche de la strate (sous-categorie x espece),")
    print("les deux bras confondus au denominateur. Negatif = mieux que le")
    print("marche sur le meme type de produit. IC 95 % par bootstrap de")
    print(f"grappes sur les MARQUES, {TIRAGES} tirages, graine {GRAINE}.\n")
    t_ns, d_ns = comparer(h, "ecart", "nutriscore")
    dire(t_ns, d_ns, "pts")
    print()
    t_sel, d_sel = comparer(h, "ecart_sel", "sel")
    dire(t_sel, d_sel, "g/100g")

    titre("La meme comparaison, une voix par marque")
    print("Les medianes ci-dessus sont ponderees par le PRODUIT : Isla Delice,")
    print("avec 182 references, y pese quarante fois une marque de cinq. C'est")
    print("la bonne lecture pour « ce que le client trouve en rayon », et la")
    print("mauvaise pour « comment se comportent les entreprises ». Ici chaque")
    print("marque compte pour une, quelle que soit sa taille.\n")
    par_marque = (h[h.ecart.notna()].groupby(["famille", "marque"])
                    .agg(n=("ecart", "size"), ecart=("ecart", "median"),
                         sel=("ecart_sel", "median")).reset_index())
    vm = []
    for f_ in FAMILLES:
        g = par_marque[par_marque.famille == f_]
        if not len(g):
            continue
        vm.append({"famille": f_, "marques": len(g),
                   "mediane_des_medianes": round(float(g.ecart.median()), 2),
                   "q1": round(float(g.ecart.quantile(0.25)), 2),
                   "q3": round(float(g.ecart.quantile(0.75)), 2),
                   "sel_mediane_des_medianes": round(float(g.sel.median()), 2)})
    tvm = pd.DataFrame(vm)
    print(tvm.to_string(index=False))
    print("\n  Pas d'IC ici : une mediane de 3 valeurs n'en supporte pas.")
    print("  Les quartiles disent l'etendue reelle a l'interieur de chaque")
    print("  famille, qui est le point important.")
    tvm.to_csv(SORTIES / "f2c_une_voix_par_marque.csv", index=False)
    par_marque.round(2).to_csv(SORTIES / "f2d_par_marque.csv", index=False)
    pd.concat([t_ns, t_sel]).to_csv(SORTIES / "f2_familles_halal.csv",
                                    index=False)
    pd.concat([d_ns, d_sel]).to_csv(SORTIES / "f2b_differences.csv", index=False)

    # --- La famille mdd tient-elle sans Carrefour ?
    titre("Sans Carrefour : la famille MDD est-elle autre chose que Carrefour ?")
    print("La famille mdd repose sur 3 marques. Si son resultat s'effondre")
    print("quand on retire la plus grosse, il decrivait une entreprise et non")
    print("une position de marche.\n")
    sc = h[h.marque != "carrefour"]
    t2, d2 = comparer(sc, "ecart", "nutriscore_sans_carrefour")
    dire(t2, d2, "pts")
    t2.to_csv(SORTIES / "f3_sans_carrefour.csv", index=False)
    d2.to_csv(SORTIES / "f3b_sans_carrefour_differences.csv", index=False)

    # --- Par strate : la comparaison tient-elle gamme par gamme ?
    titre("Gamme par gamme")
    print("Une difference globale peut n'etre qu'une difference de melange de")
    print("gammes. Seules les strates ou DEUX familles atteignent 30 produits")
    print("sont testables ; les autres sont decrites.\n")
    lignes = []
    for s, g in h.groupby("strate"):
        eff = g.groupby("famille").size()
        if len(eff) < 2:
            continue
        lig = {"strate": s, "n": len(g)}
        for f in FAMILLES:
            gf = g[g.famille == f]
            lig[f"n_{f}"] = len(gf)
            lig[f"ecart_{f}"] = (round(float(gf.ecart.median()), 1)
                                 if len(gf) else None)
        lig["testable"] = bool((eff >= SEUIL).sum() >= 2)
        lignes.append(lig)
    st = pd.DataFrame(lignes).sort_values(["n", "strate"],
                                          ascending=[False, True])
    print(st.to_string(index=False))
    st.to_csv(SORTIES / "f4_par_strate.csv", index=False)
    print(f"\n  {int(st.testable.sum())} strates sur {len(st)} ont deux "
          "familles au-dessus de 30 produits.")

    # --- Le controle interne : mdd et industriel ont un temoin, pas le
    # specialiste. C'est la seule lecture qui echappe au confondant de creneau.
    titre("Chaque famille comparee a SON PROPRE temoin")
    print("Un specialiste du halal n'a pas de version non halal : la ligne")
    print("n'existe pas pour lui, et son absence n'est pas un resultat manquant")
    print("mais une propriete de son catalogue. Pour les deux autres familles,")
    print("l'ecart entre leur halal et leur non-halal est la seule lecture qui")
    print("ne compare pas des entreprises differentes.\n")
    lignes = []
    for f in ["mdd", "industriel"]:
        marques = set(cat[cat.famille == f].marque)
        g = d[d.marque.isin(marques)]
        g = g[g.ecart.notna()]
        ha, te = g[g.tag_halal], g[~g.tag_halal]
        if len(ha) < SEUIL or len(te) < SEUIL:
            continue
        rng = np.random.default_rng(GRAINE)
        va = boot_mediane(grappes(ha, "ecart"), rng)
        vb = boot_mediane(grappes(te, "ecart"), rng)
        lo, hi = ic(va - vb)
        lignes.append({"famille": f, "marques": len(marques),
                       "n_halal": len(ha), "n_temoin": len(te),
                       "ecart_halal": round(float(ha.ecart.median()), 1),
                       "ecart_temoin": round(float(te.ecart.median()), 1),
                       "difference": round(float(ha.ecart.median())
                                           - float(te.ecart.median()), 1),
                       "ic95_bas": round(lo, 2), "ic95_haut": round(hi, 2),
                       "etabli": bool(lo > 0 or hi < 0)})
    ti = pd.DataFrame(lignes)
    if len(ti):
        print(ti.to_string(index=False))
        ti.to_csv(SORTIES / "f5_temoin_interne.csv", index=False)

    print("\n  Marque par marque — descriptif, pas un test. Une cellule sous")
    print("  30 produits est decrite avec son effectif, jamais testee.\n")
    det = []
    for f_ in ["mdd", "industriel"]:
        for m in sorted(cat[cat.famille == f_].marque):
            g = d[(d.marque == m) & d.ecart.notna()]
            ha, te = g[g.tag_halal], g[~g.tag_halal]
            if not len(ha) or not len(te):
                continue
            det.append({"famille": f_, "marque": m, "n_halal": len(ha),
                        "n_temoin": len(te),
                        "ecart_halal": round(float(ha.ecart.median()), 1),
                        "ecart_temoin": round(float(te.ecart.median()), 1),
                        "difference": round(float(ha.ecart.median())
                                            - float(te.ecart.median()), 1),
                        "regle_30": "franchie" if min(len(ha), len(te)) >= SEUIL
                                    else "sous 30"})
    dt = pd.DataFrame(det).sort_values(["difference", "marque"])
    print(dt.to_string(index=False))
    dt.to_csv(SORTIES / "f5b_temoin_par_marque.csv", index=False)

    print("\nEcrit : sorties/f0_couverture.csv, f1_familles_marques.csv,")
    print("        f2_familles_halal.csv,")
    print("        f2b_differences.csv, f3_sans_carrefour.csv,")
    print("        f3b_sans_carrefour_differences.csv,")
    print("        f2c_une_voix_par_marque.csv, f2d_par_marque.csv,")
    print("        f4_par_strate.csv, f5_temoin_interne.csv,")
    print("        f5b_temoin_par_marque.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
