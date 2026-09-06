#!/usr/bin/env python3
"""Couche 18 — les podiums destines a la publication.

POURQUOI CETTE COUCHE EXISTE. Une etude qui ne nomme personne ne change rien.
Nommer les trois meilleurs et les trois moins bons, a chaque niveau ou la
mesure le permet, donne a une entreprise une raison de bouger : un rang est
verifiable, et il se reprend.

TROIS NIVEAUX, TROIS SOLIDITES DIFFERENTES. Elles ne se lisent pas de la meme
facon et le script refuse de les presenter pareil.

  PRODUITS (EAN)      une observation. Aucun intervalle de confiance n'est
                      possible : un produit n'est pas un echantillon. La ligne
                      est un FAIT D'ETIQUETAGE verifiable en rayon, publie
                      avec la mediane de sa strate pour que la comparaison
                      soit explicite, et avec toutes ses valeurs pour qu'un
                      lecteur puisse la contredire.
  MARQUES             un echantillon de produits. Intervalle de confiance
                      publie, et seules les marques au-dessus du seuil
                      d'estimation entrent au podium.
  CERTIFICATEURS      quatre organismes identifies seulement. Un podium de
                      trois sur quatre serait une mise en scene : le
                      classement COMPLET est publie, sans podium.

CE QU'AUCUNE DE CES LIGNES NE DIT.

  - Rien sur la halalite d'un produit, ni sur la conformite d'un organisme a
    une norme religieuse. Le tag halal est une declaration d'etiquetage, et
    le classement des certificateurs porte sur la composition des produits
    qui portent leur nom, jamais sur leur travail de certification.
  - Rien sur une intention. Un ecart de composition n'est pas un choix.
  - Rien sur la securite sanitaire. Un mauvais rang nutritionnel n'est pas un
    defaut de securite, et le Nutri-Score n'est pas un verdict de sante.

GARDE-FOUS DE COMPARAISON, tires des echecs de la couche 9. Le premier
podium tente comparait des tranches fumees a un filet cru et du cachir cuit a
du saucisson sec. Ici :

  - l'ecart est calcule DANS la strate (sous-categorie x espece), et la
    strate est nommee sur chaque ligne ;
  - les produits de la mer sont exclus par leur categorie saisie ;
  - le sel est affiche partout. Sur les viandes crues, la strate ne controle
    pas le morceau : un ecart accompagne d'un sel eleve signale une piece
    saumuree comparee a une piece maigre, et non deux niveaux de qualite.
"""

from __future__ import annotations

import sys

import pandas as pd

from commun import COMPLET, PERIMETRE, SORTIES, borne, connexion, titre

# Gammes ou le produit a forcement ete sale et cuit ou seche. Une valeur
# nulle de sel ou d'acides gras satures y est une case vide, pas une recette.
TRANSFORMEES = {"charcuterie_cuite", "charcuterie_seche", "saucisses",
                "panes", "plats_cuisines", "rillettes_pates_mousses",
                "foie_gras", "preparations_marinees"}
SEUIL = 30            # regle des 30, pour les strates
SEUIL_GAMME = 30      # produits halal dans une gamme, pour la podiumiser
SEUIL_ESTIME = 15     # produits halal a nutrition complete, pour une marque
PODIUM = 3
MIN_CERTIF = 6        # en dessous, on publie le classement entier, pas un podium


def bloc(t: pd.DataFrame, cols: list[str], titre_bloc: str) -> None:
    print(f"\n  {titre_bloc}")
    print(t[cols].to_string(index=False))


def main() -> int:
    con = connexion()
    d = con.execute(f"""
        SELECT code, product_name,
               regexp_replace(brands_tags[1], '^[a-z]{{2}}:', '') AS marque,
               sous_categorie, espece, tag_halal,
               nutriscore_grade, nutriscore_score AS ns,
               {borne('salt_100g', 'sel')},
               {borne('saturated_fat_100g', 'ags')},
               {borne('proteins_100g', 'prot')},
               (list_contains(categories_tags, 'en:seafood')
                OR list_contains(categories_tags, 'en:fishes')
                OR list_contains(categories_tags, 'en:canned-fishes')
                OR list_contains(categories_tags, 'en:fish-fillets')) AS mer
        FROM '{PERIMETRE}' WHERE ({COMPLET})
    """).df()
    d = d[d.ns.notna() & ~d.mer].copy()
    d["strate"] = d.sous_categorie + " / " + d.espece
    n = d.groupby("strate").size()
    d = d[d.strate.isin(n[n >= SEUIL].index)].copy()
    d["mediane_strate"] = d.groupby("strate").ns.transform("median")
    d["ecart"] = d.ns - d.mediane_strate

    # DECLARATIONS IMPOSSIBLES. Le premier jet de ce podium sortait en tete
    # « Saucisson a cuire » et « Veritable rosette a l'ancienne », tous deux a
    # 0,00 g de sel ET 0,00 g d'acides gras satures. Ce ne sont pas des
    # produits remarquables : ce sont des cases vides enregistrees comme des
    # zeros. Open Food Facts est une base contributive, et l'extreme d'un
    # classement par produit y capte d'abord le bruit de saisie.
    #
    # Regle : dans une gamme TRANSFORMEE — salee et cuite, ou sechee — une
    # valeur de sel ou d'acides gras satures sous le 1er centile de la gamme
    # est plus probablement une case vide qu'une recette. Une mortadelle a
    # 0,22 g d'acides gras satures n'est pas une mortadelle allegee : c'est
    # une declaration incomplete, ou un produit mal range. Sur une viande
    # CRUE, une valeur basse est normale et la regle ne s'applique pas.
    #
    # Ce filtre a un cout assume : un produit reellement reformule, seul de sa
    # gamme, en est ecarte. Aucune deuxieme source ne permet de trancher, et
    # publier un podium fonde sur une declaration unique invraisemblable
    # couterait plus cher que d'en manquer un.
    for col in ("sel", "ags"):
        d[f"{col}_p01"] = d.groupby("sous_categorie")[col].transform(
            lambda x: x.quantile(0.01))
    d["declaration_douteuse"] = (
        d.sous_categorie.isin(TRANSFORMEES)
        & ((d.sel.fillna(0) <= d.sel_p01) | (d.ags.fillna(0) <= d.ags_p01)))

    titre("Podium 1 — les produits, au sens d'un code-barres")
    h = d[d.tag_halal & d.product_name.notna()
          & (d.product_name.str.strip() != "")].copy()
    print(f"{len(h)} produits halal comparables : Nutri-Score calcule, strate")
    print(f"d'au moins {SEUIL} produits, aucun produit de la mer.")
    print("\nUn produit est UNE observation. Il n'a pas d'intervalle de")
    print("confiance et n'en aura jamais : la ligne est un fait d'etiquetage,")
    print("verifiable en rayon avec le code. La mediane de la strate est")
    print("publiee a cote pour que la comparaison soit explicite.")
    cols = ["code", "product_name", "marque", "strate", "nutriscore_grade",
            "ns", "mediane_strate", "ecart", "sel", "ags", "prot"]
    ecartes = h[h.declaration_douteuse]
    h = h[~h.declaration_douteuse].sort_values(["ecart", "code"])
    print(f"\n{len(ecartes)} produits ecartes : declaration invraisemblable "
          "pour leur gamme —\nsel ou acides gras satures sous le 1er centile "
          "d'une gamme salee et cuite\nou sechee. Sans ce filtre, un "
          "saucisson declare a 0,00 g de sel et 0,00 g\nd'acides gras satures "
          "occupe la premiere place.")
    if len(ecartes):
        print(ecartes.sort_values(["ecart", "code"]).head(8)[
            ["code", "product_name", "strate", "ns", "mediane_strate",
             "ecart", "sel", "ags"]].to_string(index=False))
        ecartes[cols].to_csv(SORTIES / "i0_ecartes_du_podium.csv", index=False)
    print("\n  Ils sont publies dans i0 : un produit ecarte n'est pas un")
    print("  produit efface. Un lecteur qui verifie l'emballage et trouve la")
    print("  declaration correcte peut remettre la ligne au classement.")

    # PODIUM GLOBAL, TOUS PRODUITS CONFONDUS.
    #
    # « Tous produits confondus » se lit de deux facons qui ne donnent pas le
    # meme classement, et publier une seule des deux ferait passer un choix
    # d'analyse pour un fait. Les deux sont donc publiees cote a cote.
    #
    #   ABSOLU        le Nutri-Score brut. Repond a « quel est le produit le
    #                 plus / le moins bien note du rayon halal ». Un rayon
    #                 est fait de gammes inegales : le bas de ce classement
    #                 sera de la charcuterie sechee quoi que fasse son
    #                 fabricant, et le haut de la volaille crue. C'est un fait
    #                 de rayon, pas un jugement sur un industriel.
    #
    #   A GAMME EGALE l'ecart a la mediane de marche de la strate. Repond a
    #                 « qui fait le moins bien de ce qu'il fait ». C'est le
    #                 seul des deux ou une entreprise peut reprendre son rang
    #                 en changeant sa recette, et donc le seul qui serve la
    #                 competition que ce classement cherche a declencher.
    titre("Podium global — tous produits confondus")
    print("Deux lectures, deux classements. Publier une seule des deux ferait")
    print("passer un choix d'analyse pour un fait.\n")
    glob = []
    for cle, lib, expl in (
            ("ns", "absolu",
             "Nutri-Score brut. Le bas est de la charcuterie sechee quoi que "
             "fasse\n  son fabricant, le haut de la volaille crue : c'est un "
             "fait de rayon,\n  pas un jugement sur un industriel."),
            ("ecart", "a gamme egale",
             "Ecart a la mediane de marche de la strate. Seul des deux ou une\n"
             "  entreprise peut reprendre son rang en changeant sa recette.")):
        g = h.sort_values([cle, "code"])
        print(f"\n  === Classement {lib.upper()}")
        print(f"  {expl}")
        bloc(g.head(PODIUM), cols, f"--- Les {PODIUM} meilleurs")
        bloc(g.tail(PODIUM).iloc[::-1], cols, f"--- Les {PODIUM} moins bons")
        glob.append(g.head(PODIUM).assign(classement=lib, rang="meilleur",
                                          fiabilite="a verifier en rayon"))
        glob.append(g.tail(PODIUM).assign(classement=lib, rang="moins bon",
                                          fiabilite="solide"))
    pd.concat(glob)[cols + ["classement", "rang", "fiabilite"]].to_csv(
        SORTIES / "i4_podium_global.csv", index=False)

    print("\n  CE QUE LE PODIUM ABSOLU NE DIT PAS. Un saucisson sec est note")
    print("  comme un saucisson sec. Le classer dernier ne dit rien de son")
    print("  fabricant : cela dit qu'il est du saucisson sec. Un lecteur qui")
    print("  veut savoir qui fait mal son metier lit le classement A GAMME")
    print("  EGALE, ou le second podium, gamme par gamme.")

    print("\n  ET LE PODIUM PAR GAMME, ou la comparaison tient devant "
          "n'importe\n  quel lecteur :")

    lignes = []
    for gamme, g in h.groupby("sous_categorie"):
        if len(g) < SEUIL_GAMME:
            continue
        g = g.sort_values(["ecart", "code"])
        print(f"\n  === {gamme} — {len(g)} produits halal")
        bloc(g.head(PODIUM), cols, f"--- Les {PODIUM} meilleurs")
        bloc(g.tail(PODIUM).iloc[::-1], cols, f"--- Les {PODIUM} moins bons")
        lignes.append(g.head(PODIUM).assign(rang="meilleur", gamme=gamme,
                                            fiabilite="a verifier en rayon"))
        lignes.append(g.tail(PODIUM).assign(rang="moins bon", gamme=gamme,
                                            fiabilite="solide"))
    cols = cols + ["fiabilite"]
    if lignes:
        pd.concat(lignes)[cols + ["gamme", "rang"]].to_csv(
            SORTIES / "i1_podium_produits.csv", index=False)
        print(f"\n  {len(lignes) // 2} gammes podiumisees, celles qui "
              f"comptent au moins\n  {SEUIL_GAMME} produits halal. Les autres "
              "sont decrites ailleurs, jamais classees.")
    print("\n  LES DEUX MOITIES DE CE PODIUM N'ONT PAS LA MEME SOLIDITE.")
    print("  Une base contributive se trompe dans un seul sens : une case "
          "oubliee,")
    print("  un zero saisi a la place d'un vide, une valeur pour 100 g "
          "confondue")
    print("  avec une valeur par portion produisent un produit qui parait "
          "MEILLEUR")
    print("  qu'il n'est. Presque jamais l'inverse : personne ne declare par")
    print("  erreur 15 g d'acides gras satures.")
    print("\n  Les MOINS BONS sont donc solides : leurs valeurs sont "
          "coherentes avec")
    print("  leur gamme et rien ne les y aurait pousses par accident. Les")
    print("  MEILLEURS sont a verifier en rayon, code-barres en main, avant "
          "d'etre")
    print("  cites : la colonne `fiabilite` le porte sur chaque ligne. Le "
          "filtre")
    print("  ci-dessus retire les declarations impossibles, il ne rattrape "
          "pas les")
    print("  declarations seulement optimistes.")
    print("\n  Le sel est affiche a dessein. Sur les viandes crues, la strate")
    print("  ne controle pas le MORCEAU : un ecart accompagne d'un sel eleve")
    print("  signale une piece saumuree comparee a une piece maigre, et non")
    print("  deux niveaux de qualite. Un lecteur peut ecarter la ligne.")

    titre("Podium 2 — les marques, sur leurs seuls produits halal")
    m = pd.read_csv(SORTIES / "classement_marques_halal.csv")
    est = m[m.n >= SEUIL_ESTIME].sort_values(["ecart_median", "marque"])
    print(f"{len(m)} marques a gamme halal reelle, dont {len(est)} au-dessus "
          f"de {SEUIL_ESTIME}\nproduits halal a nutrition complete. Seules "
          "celles-la entrent au podium :\nen dessous, l'intervalle de "
          "confiance couvre la moitie du classement.\n")
    cm = ["marque_affichee", "type", "n", "pct_tague", "ecart_median",
          "ic95_bas", "ic95_haut", "strates_couvertes"]
    bloc(est.head(PODIUM), cm, f"--- Les {PODIUM} meilleures")
    bloc(est.tail(PODIUM).iloc[::-1], cm, f"--- Les {PODIUM} moins bonnes")
    pd.concat([est.head(PODIUM).assign(rang="meilleure"),
               est.tail(PODIUM).assign(rang="moins bonne")])[cm + ["rang"]] \
        .to_csv(SORTIES / "i2_podium_marques.csv", index=False)
    a, b = est.iloc[0], est.iloc[-1]
    chevauche = a.ic95_haut >= b.ic95_bas
    print(f"\n  Les intervalles du premier et du dernier "
          f"{'SE CHEVAUCHENT' if chevauche else 'sont disjoints'} : "
          f"[{a.ic95_bas:+.1f} ; {a.ic95_haut:+.1f}] contre "
          f"[{b.ic95_bas:+.1f} ; {b.ic95_haut:+.1f}].")
    if chevauche:
        print("  L'ordre du podium n'est donc pas etabli. Il se lit comme une")
        print("  indication, pas comme un verdict.")
    else:
        print("  L'ecart entre les deux extremes du podium est etabli.")

    titre("Podium 3 — les certificateurs : pas de podium")
    c = pd.read_csv(SORTIES / "c_certificateurs_nutriscore_score.csv")
    c = c[~c.groupe.str.contains("SANS certificateur", case=False, na=False)]
    c = c.sort_values(["ecart_median", "groupe"])
    print(f"{len(c)} organismes identifies. En publier trois sur "
          f"{len(c)} serait une mise\nen scene : le classement COMPLET est "
          "publie, sans podium.\n")
    cc = ["groupe", "n", "ecart_median", "ic95_bas", "ic95_haut", "strates",
          "distingue_du_marche"]
    print(c[cc].to_string(index=False))
    c.to_csv(SORTIES / "i3_classement_certificateurs.csv", index=False)
    if len(c) >= MIN_CERTIF:
        print("\n  [ATTENTION] Le nombre d'organismes a franchi le seuil de "
              f"{MIN_CERTIF} :\n  un podium redevient possible et ce bloc doit "
              "etre rediscute.")
    print("\n  CE QUE CE TABLEAU NE DIT PAS. Il porte sur la composition des")
    print("  produits qui portent le nom d'un organisme, jamais sur son")
    print("  travail de certification. Un organisme ne fabrique pas : il")
    print("  certifie. Le rapprochement entre les deux n'est pas etabli ici,")
    print("  et la couche 4 a montre qu'un certificateur se confond largement")
    print("  avec les marques qui font appel a lui.")

    print("\nEcrit : sorties/i1_podium_produits.csv, i2_podium_marques.csv,")
    print("        i3_classement_certificateurs.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
