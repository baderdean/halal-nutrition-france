#!/usr/bin/env python3
"""Couche 10 — l'estampille sanitaire, ou le fabricant enfin observable.

Toute cette etude bute sur le meme obstacle : ce qu'on mesure entre bras est
peut-etre le fabricant et non le label. Le controle du fabricant n'existait
jusqu'ici que dans UNE cellule (Fleury Michon, jambon de poulet).

L'estampille sanitaire ovale imprimee sur l'emballage identifie l'ETABLISSEMENT
agree, pas la marque. Une usine qui fabrique pour dix marques porte le meme
code sur les dix. C'est donc l'identifiant de fabricant que l'etude cherchait,
et il est VISIBLE PAR LE CONSOMMATEUR, ce que la marque de distributeur ne dit
jamais.

DEUX FORMATS, UN SEUL UTILISABLE.

  `fr-56-222-002-ec` et ses variantes etrangeres identifient un
  ETABLISSEMENT. 19 535 produits, 1 803 codes. Utilisable.

  `emb-56222` est l'ancien code d'emballage : il designe une COMMUNE, pas une
  usine. Plusieurs sites d'une meme commune s'y confondent. 6 832 produits,
  ecartes. Les fusionner avec les premiers attribuerait a un site la
  production d'un autre.

Ce que ce script produit nomme des SITES INDUSTRIELS REELS. Un site mal classe
le serait sur les recettes que ses donneurs d'ordre lui commandent, pas sur
son propre travail : un fabricant a facon execute un cahier des charges. Le
classement est donc accompagne, comme celui des certificateurs, d'un test de
retrait de la marque dominante.
"""

from __future__ import annotations

import re
import sys

import numpy as np
import pandas as pd

from commun import (COMPLET, PERIMETRE, SORTIES, borne, connexion, titre)
from etape5_produits_emblematiques import ic_diff

SEUIL = 30
SEUIL_DESC = 10      # publie mais jamais teste
GRAINE = 20260904

# Un identifiant d'ETABLISSEMENT se termine par le suffixe d'agrement et
# porte un numero de site. L'ancien `emb-ddddd` n'en a pas : c'est une commune.
MOTIF_ETABLISSEMENT = re.compile(r"^[a-z]{2}-.+-(ec|ue|ce)$")


def utilisable(code: str) -> bool:
    return bool(MOTIF_ETABLISSEMENT.match(code)) and not code.startswith("emb-")


def normaliser_etablissement(code: str) -> str:
    """Retire le suffixe d'agrement, qui n'identifie pas le site.

    `fr-14-752-020-ec` et `fr-14-752-020-ue` sont le MEME etablissement : EC
    et UE sont deux redactions de la meme mention d'agrement europeen, la
    seconde ayant remplace la premiere. Les garder distincts scinde un site
    en deux et divise ses effectifs.
    """
    return re.sub(r"-(ec|ue|ce)$", "", code)


def icc(df: pd.DataFrame, cle: str, val: str, n_min: int = 5):
    """Part de la variance de `val` qui separe les groupes `cle`.

    Decomposition a un facteur : variance INTER groupes sur variance totale.
    Proche de 1, connaitre le groupe suffit a predire le produit ; proche de
    0, deux produits d'un meme groupe different autant que deux produits pris
    au hasard.

    Le point de la couche : sur le Nutri-Score BRUT elle melange le CRENEAU du
    site (un salaisonnier ne fait pas de la decoupe) et son SAVOIR-FAIRE. Sur
    l'ecart a la mediane de la strate, le creneau est neutralise.
    """
    tailles = df.groupby(cle)[val].size()
    s = df[df[cle].isin(tailles[tailles >= n_min].index)]
    if s[cle].nunique() < 5:
        return None
    moy = s.groupby(cle)[val].mean()
    n = s.groupby(cle)[val].size()
    ddl_b, ddl_w = len(moy) - 1, len(s) - len(moy)
    if ddl_b <= 0 or ddl_w <= 0:
        return None
    msb = float((n * (moy - s[val].mean()) ** 2).sum()) / ddl_b
    msw = float(((s[val] - s[cle].map(moy)) ** 2).sum()) / ddl_w
    n0 = (n.sum() - (n ** 2).sum() / n.sum()) / ddl_b
    var_b = max(0.0, (msb - msw) / n0)
    return {"icc": var_b / (var_b + msw), "groupes": len(moy),
            "n": int(n.sum()), "ecart_type_intra": float(np.sqrt(msw))}


def _icc_de_stats(n, som, somcar):
    """ICC calculee depuis les statistiques par groupe, sans reconstruire les
    donnees. Indispensable pour le bootstrap : rebatir un DataFrame a chaque
    tirage coutait des minutes par variable."""
    k = len(n)
    ntot = n.sum()
    if k < 2 or ntot <= k:
        return None
    moy = som / n
    grand = som.sum() / ntot
    msb = float((n * (moy - grand) ** 2).sum()) / (k - 1)
    ssw = float((somcar - som ** 2 / n).sum())
    msw = ssw / (ntot - k)
    if msw <= 0:
        return None
    n0 = (ntot - (n ** 2).sum() / ntot) / (k - 1)
    var_b = max(0.0, (msb - msw) / n0)
    return var_b / (var_b + msw)


def icc_boot(df, cle, val, rng, n_boot: int = 400, n_min: int = 5):
    """IC de l'ICC par bootstrap DE GRAPPES.

    On retire des GROUPES entiers, pas des produits : l'incertitude porte sur
    l'echantillon d'usines observees, pas sur celui de leurs references. Un
    bootstrap ordinaire, en retirant des produits, ferait croire a une
    precision que 23 etablissements ne donnent pas.
    """
    base = icc(df, cle, val, n_min)
    if base is None:
        return None
    g = df.dropna(subset=[val]).groupby(cle)[val]
    st = pd.DataFrame({"n": g.size(), "som": g.sum(),
                       "somcar": g.apply(lambda x: float((x ** 2).sum()))})
    st = st[st.n >= n_min]
    n = st.n.to_numpy(float)
    som = st.som.to_numpy(float)
    somcar = st.somcar.to_numpy(float)
    k = len(n)
    vals = []
    for _ in range(n_boot):
        i = rng.integers(0, k, k)
        r = _icc_de_stats(n[i], som[i], somcar[i])
        if r is not None:
            vals.append(r)
    if len(vals) >= 50:
        base["ic95_bas"] = float(np.percentile(vals, 2.5))
        base["ic95_haut"] = float(np.percentile(vals, 97.5))
    return base


def main() -> int:
    con = connexion()
    rng = np.random.default_rng(GRAINE)
    d = con.execute(f"""
        SELECT code, emb_codes_tags, sous_categorie, espece,
               CASE WHEN tag_halal THEN 'halal' ELSE 'temoin' END AS bras,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               nutriscore_score AS ns,
               {borne('salt_100g', 'sel')},
               {borne('proteins_100g', 'proteines')}
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()

    # ---- 0. Couverture, avant tout resultat.
    titre("0. COUVERTURE DE L'ESTAMPILLE — a lire avant le reste")
    d["a_code"] = d.emb_codes_tags.apply(
        lambda x: bool(x is not None and len(x)))
    cov = d.groupby("bras").agg(n=("ns", "size"), avec=("a_code", "mean"))
    cov["avec"] = (100 * cov.avec).round(1)
    print(cov.to_string())
    print("\n  L'estampille est un fait d'emballage, mais sa SAISIE dans Open")
    print("  Food Facts est facultative. Un produit sans code n'est pas un")
    print("  produit sans usine : c'est un produit dont personne n'a saisi le")
    print("  code. Tout ce qui suit porte sur la fraction saisie.")
    cov.to_csv(SORTIES / "w0_couverture_estampille.csv")

    e = (d.explode("emb_codes_tags")
           .rename(columns={"emb_codes_tags": "etablissement"}))
    e = e[e.etablissement.notna()]
    # Un produit sans marque saisie n'a PAS de marque. Le nommer « inconnue »
    # en fabriquerait une, qui compterait pour une marque de plus dans w1 et
    # formerait une grappe geante dans l'ICC de w4 : le pouvoir explicatif de
    # la marque tombait de 0,463 a 0,391 par ce seul artefact. Ces lignes sont
    # donc laissees vides et exclues des statistiques PAR MARQUE, jamais des
    # statistiques par etablissement.
    e["marque"] = [str(x) if x is not None and x == x and str(x) != ""
                   else None for x in e.marque]
    avant = e.etablissement.nunique()
    e = e[e.etablissement.apply(utilisable)]
    e["etablissement"] = e.etablissement.apply(normaliser_etablissement)
    print(f"\n  Codes distincts : {avant}, dont {e.etablissement.nunique()} "
          f"identifient un etablissement.")
    print(f"  Produits rattaches a un etablissement : {e.code.nunique()}.")

    # ---- 1. Les usines qui fabriquent pour plusieurs marques.
    titre("1. LES USINES MULTI-MARQUES")
    print("Un etablissement qui porte plusieurs marques fabrique a facon. La")
    print("marque affichee en rayon ne dit alors pas qui produit.\n")
    u = (e.groupby("etablissement")
          .agg(n_produits=("code", "nunique"),
               n_marques=("marque", "nunique"),
               n_halal=("bras", lambda x: int((x == "halal").sum())),
               n_temoin=("bras", lambda x: int((x == "temoin").sum())))
          .reset_index())
    u = u[u.n_produits >= SEUIL_DESC].sort_values("n_marques", ascending=False)
    print(u.head(20).to_string(index=False))
    u.to_csv(SORTIES / "w1_usines_multimarques.csv", index=False)
    mixtes = u[(u.n_halal >= SEUIL_DESC) & (u.n_temoin >= SEUIL_DESC)]
    print(f"\n  {len(u)} etablissements a {SEUIL_DESC} produits ou plus.")
    print(f"  {len(mixtes)} en fabriquent des deux bras, halal et temoin.")

    # ---- 2. Le controle du fabricant, a l'echelle.
    titre("2. HALAL CONTRE TEMOIN, DANS UN MEME ETABLISSEMENT")
    print("C'est le controle que l'etude cherchait : meme site, meme outil,")
    print("souvent le meme cahier des charges. Compare a gamme egale, faute de")
    print("quoi l'ecart mesurerait l'assortiment du site.\n")
    lignes = []
    for (et, sc), g in e.groupby(["etablissement", "sous_categorie"]):
        a, b = g[g.bras == "halal"], g[g.bras == "temoin"]
        if len(a) < SEUIL_DESC or len(b) < SEUIL_DESC:
            continue
        r = ic_diff(a.ns.to_numpy(float), b.ns.to_numpy(float), rng)
        if not r:
            continue
        testable = len(a) >= SEUIL and len(b) >= SEUIL
        etabli = ("etabli" if testable and (r[1] > 0 or r[2] < 0)
                  else "non etabli" if testable else "sous 30, decrit")
        rs = ic_diff(a.sel.to_numpy(float), b.sel.to_numpy(float), rng)
        print(f"  {et:20s} {sc:22s} n={len(a):3d}/{len(b):3d}  "
              f"Nutri-Score {r[0]:+5.1f} [{r[1]:+.1f} ; {r[2]:+.1f}]  {etabli}"
              + (f"   sel {rs[0]:+.2f}" if rs else ""))
        lignes.append({"etablissement": et, "sous_categorie": sc,
                       "n_halal": len(a), "n_temoin": len(b),
                       "ecart_nutriscore": round(r[0], 1),
                       "ic95_bas": round(r[1], 1), "ic95_haut": round(r[2], 1),
                       "ecart_sel": round(rs[0], 2) if rs else None,
                       "testable": testable, "etabli": etabli == "etabli"})
    if not lignes:
        print("  Aucune cellule n'atteint le seuil des deux cotes.")
    pd.DataFrame(lignes).to_csv(SORTIES / "w2_intra_etablissement.csv",
                                index=False)

    # ---- 3. Bons et mauvais eleves, a composition egale.
    titre("3. LES ETABLISSEMENTS, A COMPOSITION EGALE")
    print("Ecart de chaque produit a la mediane de marche de sa strate")
    print("(sous-categorie x espece), agrege en mediane par etablissement. Un")
    print("classement brut opposerait un site de charcuterie seche a un")
    print("atelier de decoupe, ce qui ne dit rien de leur travail.\n")
    e["strate"] = e.sous_categorie + " / " + e.espece
    tailles = e.groupby("strate").size()
    ev = e[e.strate.isin(tailles[tailles >= SEUIL].index)].copy()
    ev["ecart"] = ev.ns - ev.groupby("strate").ns.transform("median")
    lignes3 = []
    for et, g in ev.groupby("etablissement"):
        if len(g) < SEUIL_DESC:
            continue
        med = float(g.ecart.median())
        if np.isnan(med):
            continue
        # Tri secondaire par nom : sans lui, deux marques a egalite sortent
        # dans un ordre qui change d'une execution a l'autre.
        dom = (g.marque.value_counts()
                .rename_axis("m").reset_index(name="k")
                .sort_values(["k", "m"], ascending=[False, True]))
        part = 100.0 * dom.k.iloc[0] / len(g) if len(dom) else 100.0
        # Retrait de la marque dominante : un site dont 80 % de la production
        # est une seule marque est juge sur cette marque.
        premiere = dom.m.iloc[0] if len(dom) else None
        sans = g[g.marque != premiere] if len(dom) > 1 else g.iloc[0:0]
        lignes3.append({
            "etablissement": et, "n": len(g),
            "n_marques": int(g.marque.nunique()),
            "n_halal": int((g.bras == "halal").sum()),
            "ecart_median": round(med, 1),
            "marque_dominante": premiere,
            "part_dominante_pct": round(part, 1),
            "ecart_sans_dominante": (round(float(sans.ecart.median()), 1)
                                     if len(sans) >= SEUIL_DESC else None),
            "n_sans_dominante": len(sans),
            "regle_30": "franchie" if len(g) >= SEUIL else "sous 30",
        })
    t3 = pd.DataFrame(lignes3).sort_values("ecart_median")
    print("  --- Les 12 meilleurs eleves")
    print(t3.head(12).to_string(index=False))
    print("\n  --- Les 12 mauvais eleves")
    print(t3.tail(12).to_string(index=False))
    t3.to_csv(SORTIES / "w3_classement_etablissements.csv", index=False)
    print(f"\n  {len(t3)} etablissements classes, dont "
          f"{int((t3.regle_30 == 'franchie').sum())} au-dessus de 30 produits.")
    print("  La colonne `ecart_sans_dominante` est le garde-fou : un site dont")
    print("  la production est concentree sur une marque est juge sur cette")
    print("  marque, pas sur son savoir-faire.")

    # ---- 4. L'usine explique-t-elle quelque chose ?
    titre("4. L'USINE EXPLIQUE-T-ELLE LA QUALITE ?")
    print("Un faconnier ne se contente pas d'executer : il se positionne sur")
    print("un creneau. La question est donc double. Le site explique-t-il la")
    print("qualite, et cette explication est-elle son CRENEAU ou son")
    print("SAVOIR-FAIRE ?")
    print()
    print("  ICC sur le Nutri-Score BRUT  = creneau + savoir-faire")
    print("  ICC sur l'ECART a la strate  = savoir-faire seul")
    print()
    print("Et si la dispersion INTRA site est aussi grande en halal qu'en")
    print("temoin, parler d'un effet site sur le halal n'a pas de sens.")
    print()
    lignes4 = []
    entete4 = ("  {:8s} {:14s} {:7s} {:>6s} {:>15s} {:>8s} {:>6s} {:>12s}"
               .format("bras", "groupe", "variable", "ICC", "IC 95 %",
                       "groupes", "n", "sigma intra"))
    print(entete4)
    for bras in ("temoin", "halal"):
        sous = ev[ev.bras == bras]
        for cle, lib in (("etablissement", "etablissement"),
                         ("marque", "marque")):
            for val, lv in (("ns", "brut"), ("ecart", "ecart")):
                r = icc_boot(sous, cle, val, rng)
                if not r:
                    print("  {:8s} {:14s} {:7s} {:>6s}  effectifs insuffisants"
                          .format(bras, lib, lv, "-"))
                    continue
                ici = ("[{:.2f} ; {:.2f}]".format(r["ic95_bas"], r["ic95_haut"])
                       if "ic95_bas" in r else "-")
                print("  {:8s} {:14s} {:7s} {:6.3f} {:>15s} {:8d} {:6d} {:12.2f}"
                      .format(bras, lib, lv, r["icc"], ici, r["groupes"],
                              r["n"], r["ecart_type_intra"]))
                lignes4.append({"bras": bras, "groupe": lib, "variable": lv,
                                "icc": round(r["icc"], 3),
                                "ic95_bas": round(r.get("ic95_bas", float("nan")), 3),
                                "ic95_haut": round(r.get("ic95_haut", float("nan")), 3),
                                "groupes": r["groupes"], "n": r["n"],
                                "ecart_type_intra": round(r["ecart_type_intra"], 2)})
    pd.DataFrame(lignes4).to_csv(SORTIES / "w4_variance_etablissement.csv",
                                 index=False)

    print("\nEcrit : sorties/w0_couverture_estampille.csv, "
          "w1_usines_multimarques.csv,\n        w2_intra_etablissement.csv, "
          "w3_classement_etablissements.csv,\n        w4_variance_etablissement.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
