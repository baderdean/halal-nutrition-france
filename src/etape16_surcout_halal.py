#!/usr/bin/env python3
"""Couche 16 — y a-t-il un surcout halal en rayon, et jusqu'ou peut-il aller ?

QUESTION POSEE. Le cout de l'abattage rituel et de la certification
expliquerait-il un surcout du produit halal pour le consommateur ?

CETTE QUESTION SE DECOMPOSE EN DEUX, ET LE DEPOT NE PEUT EN TRAITER QU'UNE.

  1. Y A-T-IL UN SURCOUT EN RAYON ? Mesurable ici, et c'est ce que fait ce
     script. Prix au kilo, a composition egale, ecart a la mediane de marche
     de la strate.

  2. LE COUT DE L'ABATTAGE ET DE LA CERTIFICATION EXPLIQUE-T-IL CE SURCOUT ?
     NON MESURABLE ICI, et rien dans ce depot ne s'en approche. Open Food
     Facts est une base de composition et d'etiquetage. Elle ne contient ni
     cout d'abattage, ni redevance de certification, ni marge, ni prix de
     cession industriel. Repondre a cette question demanderait les
     comptabilites des abattoirs, les grilles tarifaires des organismes
     certificateurs et les conditions commerciales entre industriels et
     enseignes. Aucune de ces trois sources n'est publique.

CE QUE LE SCRIPT PUBLIE A LA PLACE : UNE BORNE. Meme sans connaitre le cout
d'abattage, les donnees de prix bornent ce qu'un tel cout peut avoir
repercute en rayon. Si l'intervalle de confiance du surcout observe exclut
toute valeur au-dessus de X euros par kilo, alors une repercussion
superieure a X est refutee par les donnees, quel que soit le cout reel en
amont. C'est une reponse partielle, et c'est la seule que ces donnees
autorisent.

TROIS LIMITES A LIRE AVANT LES CHIFFRES.

  1. Les prix viennent d'Open Prices, un releve BENEVOLE. 10,5 % du bras
     halal et 5,4 % du temoin portent un prix. Rien ne garantit que les
     produits releves soient representatifs des autres.

  2. Le prix d'un produit n'est pas son cout. Un prix de vente se fixe sur un
     positionnement, une elasticite et une negociation d'enseigne. Une
     absence de surcout en rayon ne prouve pas une absence de surcout en
     amont : elle prouve qu'il n'arrive pas au consommateur sous forme de
     prix, ou qu'il est absorbe ailleurs.

  3. La comparaison porte sur des ENTREPRISES DIFFERENTES des qu'on sort
     d'une marque. Le seul controle propre est intra-marque, et une seule
     marque a des prix des deux cotes en nombre suffisant pour etre decrite.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from commun import COMPLET, PERIMETRE, RACINE, SORTIES, borne, connexion, \
    titre

PRIX = RACINE / "donnees_prix" / "prix_open_prices.csv"
GRAINE = 20260904
TIRAGES = 4000
SEUIL = 30            # regle des 30
SEUIL_DESC = 5        # au-dessous, on ne decrit meme pas une ligne par strate
PRIX_MIN, PRIX_MAX = 0.5, 200.0   # bornes de plausibilite, euros par kilo
# Prefixe des sorties : « g ». « p » etait deja pris par la couche 2, et
# p4_intra_marque.csv y existe deja : un fichier de cette couche l'aurait
# ecrase en silence.


def grappes(d: pd.DataFrame, col: str) -> list:
    """Un paquet par marque ; un produit sans marque saisie fait son paquet.

    Deux references d'une meme marque ne sont pas deux observations
    independantes. Un produit sans marque, lui, n'a pas de raison d'etre
    rattache a un autre : le grouper avec ses semblables inventerait une
    entreprise, le laisser seul est le choix neutre.
    """
    paquets = []
    for m, g in d[d.marque.notna()].groupby("marque"):
        paquets.append(g[col].to_numpy(float))
    for v in d[d.marque.isna()][col].to_numpy(float):
        paquets.append(np.array([v]))
    return paquets


def boot_diff(a: pd.DataFrame, b: pd.DataFrame, col: str) -> tuple:
    """Difference de medianes, IC 95 % par bootstrap de grappes."""
    rng = np.random.default_rng(GRAINE)
    pa, pb = grappes(a, col), grappes(b, col)
    out = np.empty(TIRAGES)
    for i in range(TIRAGES):
        ia = rng.integers(0, len(pa), len(pa))
        ib = rng.integers(0, len(pb), len(pb))
        out[i] = (np.median(np.concatenate([pa[j] for j in ia]))
                  - np.median(np.concatenate([pb[j] for j in ib])))
    point = float(a[col].median()) - float(b[col].median())
    return point, float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def charger_prix() -> pd.DataFrame:
    p = pd.read_csv(PRIX, dtype={"product_code": str})
    avant = len(p)
    if "price_is_discounted" in p:
        p = p[p.price_is_discounted != True]          # noqa: E712
    p = p[p.currency == "EUR"] if "currency" in p else p
    print(f"  {avant} releves, {len(p)} retenus apres retrait des promotions")
    print("  et des devises autres que l'euro. Une promotion est un prix, mais")
    print("  pas le prix du produit : la garder ferait dependre la comparaison")
    print("  du calendrier commercial de chaque enseigne.")
    return p


def main() -> int:
    titre("Prix : ce qui est retenu")
    p = charger_prix()

    con = connexion()
    d = con.execute(f"""
        SELECT code, product_name, sous_categorie, espece, tag_halal,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               CASE WHEN product_quantity BETWEEN 10 AND 5000
                    THEN product_quantity END AS format_g,
               nutriscore_score AS ns, {borne('salt_100g', 'sel')}
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    d["marque"] = [str(x) if x is not None and x == x else None for x in d.marque]

    j = d.merge(p, left_on="code", right_on="product_code", how="inner")
    j = j[j.format_g.notna() & j.price.notna()].copy()
    # Le grammage vient du perimetre fige, jamais du service de prix : une
    # seule source versionnee pour la variable qui sert de denominateur.
    j["prix_kg"] = j.price / (j.format_g / 1000.0)
    j = j[(j.prix_kg > PRIX_MIN) & (j.prix_kg < PRIX_MAX)]

    # L'UNITE EST LE PRODUIT, PAS LE RELEVE. Un produit peut porter des
    # dizaines de passages en magasin ; les compter separement donnerait le
    # poids d'une gamme aux articles les plus photographies. La couche 8 a
    # commis cette erreur et trois de ses quatre ecarts « etablis » n'y ont
    # pas survecu.
    j = (j.groupby(["code", "product_name", "sous_categorie", "espece",
                    "tag_halal", "marque", "ns", "sel"], dropna=False)
           .prix_kg.median().reset_index())

    titre("Couverture — a lire avant tout chiffre de prix")
    cov = (j.groupby("tag_halal").code.nunique().to_frame("avec_prix")
             .join(d.groupby("tag_halal").code.nunique().to_frame("produits")))
    cov["couverture_pct"] = (100 * cov.avec_prix / cov.produits).round(2)
    cov.index = ["temoin", "halal"]
    cov.index.name = "bras"
    print(cov.to_string())
    print("\n  Ces chiffres different de ceux de la couche 8 (205 produits "
          "halal,\n  10,49 %). La couche 8 compte les produits APPARIES a un "
          "prix ; celle-ci\n  compte ceux REELLEMENT UTILISABLES, apres le "
          "filtre de grammage et les\n  bornes de plausibilite. La difference "
          "est faite d'articles sans grammage\n  exploitable : ils ont un "
          "prix, mais pas de prix au kilo.")
    print("\n  Open Prices est un releve benevole. Un produit sans prix n'est")
    print("  pas un produit sans prix en magasin : c'est un produit que")
    print("  personne n'a photographie. Tout ce qui suit porte sur cette")
    print("  fraction, et rien ne garantit qu'elle soit representative.")
    cov.to_csv(SORTIES / "g0_couverture_prix.csv")

    # --- Prix a composition egale.
    j["strate"] = j.sous_categorie + " / " + j.espece
    n = j.groupby("strate").size()
    gardees = n[n >= SEUIL].index
    perdus = int((~j.strate.isin(gardees)).sum())
    j = j[j.strate.isin(gardees)].copy()
    j["ecart_prix"] = j.prix_kg - j.groupby("strate").prix_kg.transform("median")

    titre("Y a-t-il un surcout halal en rayon ?")
    print("Ecart au prix median de MARCHE de la strate (sous-categorie x")
    print("espece), les deux bras confondus au denominateur. Positif = plus")
    print("cher que le marche sur le meme type de produit. Comparer sans cela")
    print("opposerait des merguez a du jambon de porc.\n")
    print(f"  {perdus} produits ecartes : leur strate compte moins de {SEUIL}")
    print("  produits avec prix, sa mediane ne tiendrait pas.\n")
    h, t = j[j.tag_halal], j[~j.tag_halal]
    point, bas, haut = boot_diff(h, t, "ecart_prix")
    etabli = bas > 0 or haut < 0
    print(f"  halal   {len(h):5d} produits, {h.marque.nunique():3d} marques, "
          f"ecart median {h.ecart_prix.median():+6.2f} EUR/kg "
          f"(prix median {h.prix_kg.median():.2f})")
    print(f"  temoin  {len(t):5d} produits, {t.marque.nunique():3d} marques, "
          f"ecart median {t.ecart_prix.median():+6.2f} EUR/kg "
          f"(prix median {t.prix_kg.median():.2f})")
    print(f"\n  SURCOUT HALAL : {point:+.2f} EUR/kg "
          f"[{bas:+.2f} ; {haut:+.2f}]  "
          f"{'ETABLI' if etabli else 'NON ETABLI'}")
    print("\n  IC 95 % par bootstrap de grappes sur les marques, "
          f"{TIRAGES} tirages,\n  graine {GRAINE}.")
    pd.DataFrame([{"mesure": "ecart_prix_kg", "n_halal": len(h),
                   "n_temoin": len(t),
                   "marques_halal": int(h.marque.nunique()),
                   "prix_median_halal": round(float(h.prix_kg.median()), 2),
                   "prix_median_temoin": round(float(t.prix_kg.median()), 2),
                   "surcout": round(point, 2), "ic95_bas": round(bas, 2),
                   "ic95_haut": round(haut, 2), "etabli": bool(etabli)}]
                 ).to_csv(SORTIES / "g1_surcout_global.csv", index=False)

    # --- La borne : ce que les donnees excluent.
    titre("La borne : quelle repercussion les donnees excluent-elles ?")
    print("Le cout de l'abattage rituel et de la certification n'est nulle part")
    print("dans ce depot, et ne peut pas y etre : Open Food Facts est une base")
    print("de composition. Mais les prix bornent ce qu'un tel cout peut avoir")
    print("repercute en rayon.\n")
    ref = float(t.prix_kg.median())
    print(f"  Prix median du temoin, toutes strates : {ref:.2f} EUR/kg.")
    print(f"  Surcout halal compatible avec les donnees : au plus "
          f"{haut:+.2f} EUR/kg,")
    print(f"  soit {100 * haut / ref:+.1f} % du prix de reference.")
    print("\n  LECTURE. Toute repercussion en rayon superieure a cette borne")
    print("  est refutee par ces donnees, quel que soit le cout reel en amont.")
    print("  Une repercussion inferieure reste possible et n'est pas mesurable")
    print("  ici : elle serait noyee dans la dispersion des prix.")
    print("\n  CE QUE CELA NE DIT PAS. Un cout d'abattage peut exister sans")
    print("  arriver au consommateur : absorbe par la marge, compense par le")
    print("  creneau, ou reporte sur d'autres references. Un prix n'est pas un")
    print("  cout, et l'absence de surcout en rayon ne refute pas un surcout")
    print("  en amont.")
    pd.DataFrame([{"prix_reference_temoin_kg": round(ref, 2),
                   "borne_haute_surcout_kg": round(haut, 2),
                   "borne_haute_pct": round(100 * haut / ref, 1),
                   "borne_basse_surcout_kg": round(bas, 2)}]
                 ).to_csv(SORTIES / "g2_borne.csv", index=False)

    # --- Gamme par gamme.
    titre("Gamme par gamme")
    lignes = []
    for s, g in j.groupby("strate"):
        a, b = g[g.tag_halal], g[~g.tag_halal]
        if len(a) < SEUIL_DESC:
            continue
        lignes.append({"strate": s, "n_halal": len(a), "n_temoin": len(b),
                       "prix_halal": round(float(a.prix_kg.median()), 2),
                       "prix_temoin": round(float(b.prix_kg.median()), 2),
                       "surcout": round(float(a.prix_kg.median())
                                        - float(b.prix_kg.median()), 2),
                       "testable": bool(min(len(a), len(b)) >= SEUIL)})
    st = pd.DataFrame(lignes).sort_values(["n_halal", "strate"],
                                          ascending=[False, True])
    print(st.to_string(index=False))
    st.to_csv(SORTIES / "g3_par_strate.csv", index=False)
    print(f"\n  {int(st.testable.sum())} strates sur {len(st)} atteignent 30 "
          "produits des deux cotes.")

    # --- Le seul controle propre : la meme marque des deux cotes.
    titre("Le seul controle propre : la meme marque des deux cotes")
    print("Des qu'on sort d'une marque, on compare des entreprises")
    print("differentes, avec des couts, des reseaux et des positionnements")
    print("differents. A l'interieur d'une marque, la certification est ce qui")
    print("change.\n")
    lignes = []
    for m, g in j[j.marque.notna()].groupby("marque"):
        a, b = g[g.tag_halal], g[~g.tag_halal]
        if not len(a) or not len(b):
            continue
        lignes.append({"marque": m, "n_halal": len(a), "n_temoin": len(b),
                       "prix_halal": round(float(a.prix_kg.median()), 2),
                       "prix_temoin": round(float(b.prix_kg.median()), 2),
                       "surcout": round(float(a.prix_kg.median())
                                        - float(b.prix_kg.median()), 2),
                       "regle_30": "franchie" if min(len(a), len(b)) >= SEUIL
                                   else "sous 30"})
    im = pd.DataFrame(lignes).sort_values(["n_halal", "marque"],
                                          ascending=[False, True])
    if len(im):
        print(im.to_string(index=False))
        im.to_csv(SORTIES / "g4_intra_marque.csv", index=False)
        print("\n  Aucune de ces lignes ne franchit la regle des 30 des deux")
        print("  cotes : elles sont DECRITES, jamais testees. C'est la limite")
        print("  la plus serieuse de cette couche, et elle ne se resout pas")
        print("  par le calcul : il faut plus de releves de prix.")

    print("\nEcrit : sorties/g0_couverture_prix.csv, g1_surcout_global.csv,")
    print("        g2_borne.csv, g3_par_strate.csv, g4_intra_marque.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
