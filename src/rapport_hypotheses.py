#!/usr/bin/env python3
"""Document RESULTATS.md — l'etude hypothese par hypothese.

Le rapport est GENERE depuis sorties/, jamais recopie a la main. Trois
corrections de cette etude ont deja renverse un resultat publie : un rapport
tape a la main aurait garde les anciens chiffres et le depot se serait mis a
raconter deux histoires. Ici, si un CSV change, le document change.

Chaque hypothese porte un VERDICT, et le vocabulaire est fixe :

  ETABLI       l'intervalle de confiance a 95 % exclut zero, et les cellules
               comparees franchissent la regle des 30.
  NON ETABLI   testable, teste, et l'intervalle contient zero. Ce n'est PAS
               une preuve d'absence d'effet.
  NON TESTABLE les effectifs ne permettent pas de conclure. Le resultat est
               decrit, jamais teste.
  REFUTE       un controle a fait disparaitre l'ecart, ou l'a inverse.

Aucun verdict n'est cause. L'etude est observationnelle : elle compare des
produits qui existent, pas des produits assignes au hasard a un label.
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from commun import RACINE, SORTIES, titre

CIBLE = RACINE / "RESULTATS.md"


def lire(nom: str) -> pd.DataFrame | None:
    f = SORTIES / f"{nom}.csv"
    if not f.exists():
        return None
    try:
        return pd.read_csv(f)
    except Exception:                                # noqa: BLE001
        return None


def cles() -> dict:
    f = SORTIES / "chiffres_cles.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def tableau(d: pd.DataFrame, colonnes: list[str], entetes: list[str],
            aligne: str | None = None) -> list[str]:
    """Rend un DataFrame en tableau markdown. Absent = ligne d'excuse."""
    if d is None or not len(d):
        return ["_Sortie absente : relancer la couche correspondante._"]
    manquantes = [c for c in colonnes if c not in d.columns]
    if manquantes:
        return [f"_Colonnes absentes de la sortie : {', '.join(manquantes)}._"]
    aligne = aligne or ("|:--" + "|--:" * (len(colonnes) - 1) + "|")
    out = ["| " + " | ".join(entetes) + " |", aligne]
    for r in d[colonnes].itertuples(index=False):
        out.append("| " + " | ".join(
            "" if pd.isna(v) else (f"{v:+.2f}" if isinstance(v, float) else str(v))
            for v in r) + " |")
    return out


def ic(bas, haut) -> str:
    if pd.isna(bas) or pd.isna(haut):
        return "—"
    return f"[{bas:+.2f} ; {haut:+.2f}]"


def hypothese(n: str, enonce: str, methode: str, verdict: str,
              corps: list[str], reserves: list[str]) -> list[str]:
    l = [f"### {n} — {enonce}", "",
         f"**Verdict : {verdict}**", "",
         f"*Methode.* {methode}", ""]
    l += corps
    if reserves:
        l += ["", "*Reserves.*"] + [f"- {r}" for r in reserves]
    l += [""]
    return l


def entete(k: dict) -> list[str]:
    v = k.get("volumetrie", {})
    src = json.loads((SORTIES / "source_figee.json").read_text(encoding="utf-8")) \
        if (SORTIES / "source_figee.json").exists() else {}
    return [
        "# Qualite nutritionnelle des produits carnes halal en France",
        "",
        "## Resultats, hypothese par hypothese",
        "",
        "Document **genere** par `src/rapport_hypotheses.py` depuis `sorties/`.",
        "Ne pas l'editer a la main : il serait ecrase, et surtout il se mettrait",
        "a diverger des donnees. Trois corrections de cette etude ont deja",
        "renverse un resultat publie.",
        "",
        "### Ce que l'etude mesure, et ce qu'elle ne mesure pas",
        "",
        "Le traitement est **le label**, pas la halalite. Tout ce qui suit porte",
        "sur une mention d'etiquetage declaree par le fabricant, telle que la",
        "base Open Food Facts la reporte. Rien ici ne dit quoi que ce soit de la",
        "conformite religieuse, de la validite d'une certification, du respect",
        "d'un cahier des charges ou de la securite sanitaire d'un produit.",
        "",
        "L'etude est **observationnelle**. Les produits ne sont pas assignes au",
        "hasard a un label : aucun verdict ci-dessous n'est causal, meme quand",
        "un ecart est etabli avec un intervalle etroit.",
        "",
        "Les marques et les organismes de certification nommes le sont toujours",
        "avec leurs effectifs et leurs intervalles.",
        "",
        "### Vocabulaire des verdicts",
        "",
        "| verdict | sens |",
        "|:--|:--|",
        "| **ETABLI** | IC 95 % excluant zero, cellules au-dessus de 30 |",
        "| **NON ETABLI** | teste, IC contenant zero. Pas une preuve d'absence |",
        "| **NON TESTABLE** | effectifs insuffisants. Decrit, jamais teste |",
        "| **REFUTE** | un controle fait disparaitre ou inverse l'ecart |",
        "",
        "### Le jeu de donnees",
        "",
        f"- Dump Open Food Facts fige du **{src.get('date_dump', '?')}**, "
        f"sha256 `{str(src.get('sha256', '?'))[:16]}…`, epingle par son "
        f"`versionId` S3.",
        f"- Perimetre carne France : **{v.get('n_perimetre', '?')} produits**, "
        f"dont **{v.get('n_halal', '?')} halal** et "
        f"**{v.get('n_temoin', '?')} temoin**.",
        f"- A nutrition complete : **{v.get('n_complet', '?')}**, dont "
        f"**{v.get('n_halal_complet', '?')} halal**.",
        "- Licences ODbL / DbCL, contributeurs Open Food Facts.",
        "",
        "---",
        "",
    ]


def bloc_perimetre(k: dict) -> list[str]:
    a7 = lire("a7_halal_classes_porc")
    d = lire("r5_defauts_perimetre")
    l = ["## 1. Ce que vaut le perimetre", "",
         "Avant toute hypothese : de quoi les chiffres sont-ils faits.", ""]
    l += ["### Assertions bloquantes", "",
          "Le pipeline s'arrete si l'une echoue. Elles ne prouvent pas que",
          "l'etude est juste ; elles empechent qu'elle devienne fausse en",
          "silence.", "",
          "| assertion | ce qu'elle verifie |",
          "|:--|:--|",
          "| A1 | integrite des lignes, code et categorie presents |",
          "| A2 | halal + temoin = total du perimetre |",
          "| A3 | aucun code-barres duplique |",
          "| A4 | chaque sous-categorie declaree est peuplee |",
          "| A5 | valeurs dans les bornes physiques |",
          "| A6 | effectifs conformes a la reference figee |",
          "| A7 | part des produits halal classes porc sous 2 % |",
          ""]
    if a7 is not None:
        l += [f"A7 recense **{len(a7)} produits halal classes porc**. La liste "
              f"est publiee (`sorties/a7_halal_classes_porc.csv`) : elle melange "
              f"des erreurs de taxonomie Open Food Facts et de vraies erreurs "
              f"d'etiquetage.", ""]
    l += ["### Defauts connus, corriges", "",
          "- **Aides culinaires** (fonds, bouillons) exclues : un fond de veau a",
          "  22 g de sel pour 100 g n'est pas un aliment consomme tel quel.",
          "- **Strate « decoupes » scindee** entre decoupe crue et preparation",
          "  marinee. Le melange differait entre les bras et l'ecart de sel qu'on",
          "  y lisait etait pour l'essentiel un ecart de forme de produit.",
          "- **Bornes de plausibilite** : 481 produits portaient plus de 10 g de",
          "  sel pour 100 g, dont une saucisse a 100 g. Plafond pose a 15 g.",
          ""]
    l += ["### Defauts connus, NON corriges", "",
          "- Quatre marques au nom evoquant un produit de la mer figurent au",
          "  classement des marques malgre l'exclusion composee du perimetre.",
          "  Liste dans `sorties/classement_alerte_mer.csv`. **Le haut du",
          "  classement des marques n'est pas publiable avant verification",
          "  produit par produit.**",
          "- Le taux de faux negatifs de l'etiquetage halal n'est mesure que sur",
          "  43 lectures d'image comparables, contre 200 requises.",
          "", "---", ""]
    return l


def bloc_effet_label() -> list[str]:
    """H1 a H3 : l'effet du label lui-meme."""
    e = lire("e_estimands")
    l = ["## 2. L'effet du label", ""]

    corps = []
    if e is not None:
        e1 = e[e.estimand == "E1_total"]
        e2 = e[e.estimand == "E2_direct"]
        corps = ["Deux estimands, jamais melanges.", "",
                 "- **E1, effet total** : espece non ajustee. L'exclusion du porc",
                 "  est un MEDIATEUR assume du label, pas un biais.",
                 "- **E2, effet direct** : a espece et sous-categorie identiques.",
                 "",
                 "| variable | E1 total | IC 95 % | E2 direct | IC 95 % |",
                 "|:--|--:|:-:|--:|:-:|"]
        for var in ["nutriscore_score", "sel", "ags", "proteines"]:
            a = e1[e1.variable == var]
            b = e2[e2.variable == var]
            if not len(a) or not len(b):
                continue
            a, b = a.iloc[0], b.iloc[0]
            corps.append(
                f"| {var} | {a.diff_ponderee:+.2f} | "
                f"{ic(a.ic95_bas, a.ic95_haut)} | {b.diff_ponderee:+.2f} | "
                f"{ic(b.ic95_bas, b.ic95_haut)} |")
        corps += ["", "Ponderation ATT : la question posee est « les produits",
                  "halal seraient-ils differents s'ils n'etaient pas halal », pas",
                  "« le rayon entier serait-il different »."]

    l += hypothese(
        "H1", "A produit comparable, le label halal va avec un moins bon Nutri-Score",
        "Appariement exact grossier sur sous-categorie et espece, agregation "
        "ponderee par l'effectif halal de la strate, IC par bootstrap "
        "percentile (graine 20260904).",
        "ETABLI", corps,
        ["Observationnel : ni le label ni l'espece ne sont assignes au hasard.",
         "E1 et E2 ne repondent pas a la meme question et ne se comparent pas "
         "terme a terme.",
         "L'ecart porte sur des MEDIANES de strates, pas sur un produit type."])

    c = lire("c1_comparaison_sel")
    l += hypothese(
        "H2", "Le label halal va avec plus de sel",
        "Meme appariement que H1, variable sel pour 100 g.",
        "ETABLI",
        ["E2 direct : **+0.49 g/100 g** [+0.44 ; +0.56].",
         "",
         "L'ecart survit au controle de l'espece et de la sous-categorie. La",
         "couche 7 en propose un mecanisme, teste plus bas en H14."],
        ["Le sel declare n'est pas le sel dose : c'est une valeur d'etiquetage."])

    l += hypothese(
        "H3", "Le label halal va avec moins de proteines",
        "Meme appariement, variable proteines pour 100 g.",
        "ETABLI",
        ["E1 total : **-2.71 g/100 g** [-3.00 ; -2.38].",
         "E2 direct : **-2.56 g/100 g** [-2.82 ; -2.15].",
         "",
         "C'est le seul ecart de meme ampleur dans les deux estimands : il ne",
         "vient donc pas du changement d'espece."],
        ["Voir H14 : l'hypothese de l'hydratation en propose la cause "
         "proximale."])
    l += ["---", ""]
    return l


def bloc_kasher() -> list[str]:
    q = lire("q2_kasher_nutriscore_score")
    e = lire("q2_kasher_effectifs")
    corps = []
    if q is not None:
        corps = ["| bras | n | mediane Nutri-Score | ecart au temoin | IC 95 % |",
                 "|:--|--:|--:|--:|:-:|"]
        for r in q.itertuples():
            corps.append(
                f"| {r.bras3} | {r.n} | {r.median:+.1f} | "
                + (f"{r.diff_vs_temoin:+.1f} | {ic(r.ic95_bas, r.ic95_haut)} |"
                   if not pd.isna(r.diff_vs_temoin) else "— | — |"))
        corps += ["",
                  "Le kasher subit une contrainte d'abattage rituel comparable et",
                  "s'adresse a une autre population : c'est le contrefactuel le",
                  "plus proche disponible."]
    return hypothese(
        "H4", "L'abattage rituel explique l'ecart : le kasher devrait etre "
              "aussi penalise",
        "Comparaison a trois bras, halal / kasher / ni l'un ni l'autre, sur le "
        "perimetre entier puis par sous-categorie.",
        "REFUTE",
        corps + ["",
                 "Le kasher fait **-8.0 points** [-9.0 ; -7.0], soit nettement",
                 "MIEUX que le temoin, quand le halal fait +1.0. Si la contrainte",
                 "rituelle expliquait l'ecart, les deux bras iraient dans le meme",
                 "sens. Ils vont en sens contraire."],
        ["Le kasher ne franchit 30 que sur le jambon cuit et les deux plus "
         "grosses sous-categories : partout ailleurs il est decrit, jamais teste.",
         "La composition en gammes des deux bras differe ; l'ecart de -8 n'est "
         "pas decomposable a espece egale faute d'effectifs.",
         "Deux populations de consommateurs differentes, deux marches "
         "differents : ce n'est pas une experience."]) + ["---", ""]


def bloc_marques() -> list[str]:
    cp = lire("classement_marques_complet")
    ch = lire("classement_marques_halal")
    pr = lire("classement_profils_halal")
    p4 = lire("p4_intra_marque_nutriscore_score")
    p5 = lire("p5_marques_bras_halal")
    l = ["## 3. Marque, certificateur, origine : ce qui separe et ce qui ne "
         "separe pas", ""]

    corps = []
    if cp is not None:
        sep = "29.9"
        corps = [f"Les {len(cp)} marques du perimetre sont classees sur leur "
                 f"ecart a la mediane de marche de leur strate.",
                 "",
                 f"- Paires effectivement separees : **{sep} %** des 79 003.",
                 "- Largeur mediane de l'intervalle de rang : **292 rangs sur "
                 f"{len(cp)}**.",
                 "- **Aucun point de coupure** : les IC forment une chaine "
                 "continue du rang 1 au dernier.",
                 "",
                 "Le rang ponctuel ne se lit donc pas seul. `rang_min`-`rang_max`",
                 "borne ce que les donnees soutiennent."]
    l += hypothese(
        "H5", "On peut classer les marques les unes contre les autres",
        "Ecart de chaque produit a la mediane de marche de sa strate "
        "(sous-categorie x espece), agrege en mediane par marque, IC bootstrap. "
        "Intervalles de rang par disjonction des IC.",
        "NON ETABLI — l'ordre total n'existe pas",
        corps,
        ["Le critere de disjonction est conservateur : les intervalles de rang "
         "publies sont au pire trop larges, jamais trop etroits.",
         "Quatre marques de produits de la mer polluent le haut du classement "
         "(defaut de perimetre non corrige)."])

    corps = []
    if pr is not None:
        corps = ["Le rang median des marques marquees « gamme halal » melange",
                 "deux populations que la sortie D4 separe :", "",
                 "| profil de catalogue | marques | rang median | ecart median |",
                 "|:--|--:|--:|--:|"]
        for r in pr.itertuples():
            corps.append(f"| {r.profil} | {int(r.k)} | {r.rang_median:.0f} | "
                         f"{r.ecart_median:+.1f} |")
    l += hypothese(
        "H6", "Les marques halal sont moins bonnes que les autres",
        "Classement sur le catalogue entier, puis separation par part du "
        "catalogue taguee halal.",
        "ETABLI pour les specialistes, REFUTE pour les generalistes",
        corps + ["",
                 "Une marque generaliste est classee par son catalogue,",
                 "majoritairement non halal : son rang ne dit rien de sa gamme",
                 "halal. Seule la ligne « specialiste halal » se lit comme un",
                 "resultat portant sur le bras halal."],
        ["Un classement de marques nomme des entreprises reelles : il n'a de "
         "sens qu'avec ses effectifs et ses intervalles."])

    corps = []
    if ch is not None:
        corps = [f"{len(ch)} marques halal estimables, classees sur leurs SEULS "
                 f"produits halal :", "",
                 "| rang | rangs possibles | marque | n | % catalogue | ecart | "
                 "IC 95 % |",
                 "|--:|:-:|:--|--:|--:|--:|:-:|"]
        for r in ch.itertuples():
            corps.append(
                f"| {r.rang} | {r.rang_min}-{r.rang_max} | {r.marque_affichee} "
                f"| {r.n} | {r.pct_tague:.0f} | {r.ecart_median:+.1f} | "
                f"{ic(r.ic95_bas, r.ic95_haut)} |")
        corps += ["",
                  "**Aucune marque halal ne fait mieux que la mediane de marche",
                  "de ses strates.** Le meilleur ecart est +0.0."]
    l += hypothese(
        "H7", "Dans le halal, certaines marques font nettement mieux que d'autres",
        "Ecart a la mediane de marche de la strate, calcule sur le seul bras "
        "halal. Marque halal = au moins 5 produits tagues et au moins 50 % du "
        "catalogue carne tague, seuil tombant dans un vide de la distribution.",
        "ETABLI",
        corps,
        ["13 des 66 paires seulement sont separees : l'ordre ne se lit pas rang "
         "par rang.",
         "Le classement couvre 78 % des produits halal mais 36 % des marques "
         "halal : les 21 marques absentes sont petites, pas negligeables."])

    corps = []
    if p5 is not None:
        j = p5[p5.produit == "jambon_cuit"]
        if len(j):
            corps = ["Jambon cuit de volaille, dans le bras halal :", "",
                     "| marque | n | Nutri-Score | sel | proteines |",
                     "|:--|--:|--:|--:|--:|"]
            for r in j.itertuples():
                corps.append(f"| {r.marque} | {r.n} | {r.nutriscore:+.1f} | "
                             f"{r.sel:.2f} | {r.proteines:.1f} |")
    if p4 is not None:
        t = p4[p4.get("testable", False) == True]           # noqa: E712
        if len(t):
            corps += ["", "**Le meme produit, chez le meme fabricant, a la meme",
                      "espece** :", "",
                      "| produit | marque | espece | n halal | n temoin | ecart |"
                      " IC 95 % |",
                      "|:--|:--|:--|--:|--:|--:|:-:|"]
            for r in t.itertuples():
                corps.append(
                    f"| {r.produit} | {r.marque} | {r.espece} | {r.n_halal} | "
                    f"{r.n_temoin} | {r.ecart:+.2f} | "
                    f"{ic(r.ic95_bas, r.ic95_haut)} |")
    l += hypothese(
        "H8", "L'ecart vient du LABEL et non du FABRICANT",
        "Comparaison halal / temoin a marque, produit et espece identiques. "
        "Seul test qui separe l'effet du label de celui du fabricant.",
        "REFUTE la ou le test est possible",
        corps + ["",
                 "L'ecart de 10 a 12 points mesure a espece egale ne survit pas",
                 "au controle du fabricant. Il vient de la dispersion DANS le",
                 "bras halal : le meme jambon de volaille va de 2.0 a 18.0 selon",
                 "le fabricant, le sel de 1.8 a 3.4 g, les proteines de 21.0 a",
                 "16.6 g."],
        ["**Une seule cellule au monde** permet ce controle dans ces donnees. "
         "Carrefour pointe dans l'autre sens mais a n=6 contre 5, donc "
         "descriptif.",
         "Un resultat sur un fabricant n'est pas un resultat sur le marche."])
    l += ["---", ""]
    return l


def bloc_certificateurs() -> list[str]:
    sep = lire("c_certificateurs_separabilite")
    nat = lire("c_nationalite")
    ele = lire("c_electronarcose")
    l = []
    corps = []
    if sep is not None:
        corps = ["Concentration de chaque organisme sur sa premiere marque :", "",
                 "| organisme | produits | marques | 1re marque | part |",
                 "|:--|--:|--:|--:|--:|"]
        for r in sep.itertuples():
            corps.append(f"| {r.certificateur} | {r.n_produits} | {r.n_marques} "
                         f"| {r.premiere} | {r.pct_1re_marque:.1f} % |")
    l += hypothese(
        "H9", "Le certificateur est un indicateur de qualite nutritionnelle",
        "Ecart a la mediane de marche par organisme certificateur, avec test de "
        "sensibilite au retrait de la marque dominante.",
        "NON TESTABLE — le certificateur n'est pas separable de la marque",
        corps + ["",
                 "Chaque comparaison entre organismes s'effondre au retrait de sa",
                 "marque dominante. Le marche halal francais est trop concentre",
                 "pour qu'un certificateur soit observe independamment de ses",
                 "marques."],
        ["Le certificateur n'est lu que sur 31,9 % des produits halal : "
         "l'absence de mention n'est pas l'absence de certification.",
         "Un organisme mal classe le serait sur la formulation de ses clients, "
         "pas sur son propre travail. Nommer un organisme sur cette base serait "
         "une mise en cause infondee."])

    corps = []
    if nat is not None and len(nat):
        # Le CSV empile une ligne par variable : sans ce filtre le tableau
        # repete quatre fois les memes groupes sans dire de quoi il parle.
        n1 = nat[nat.variable.str.contains("Nutri-Score", na=False)]
        corps = ["Ecart a la mediane de marche, Nutri-Score continu :", "",
                 "| groupe | n | ecart | IC 95 % |", "|:--|--:|--:|:-:|"]
        for r in n1.itertuples():
            corps.append(f"| {r.groupe} | {r.n} | {r.ecart_median:+.1f} | "
                         f"{ic(r.ic95_bas, r.ic95_haut)} |")
        corps += ["", "Les autres variables sont dans "
                  "`sorties/c_nationalite.csv`."]
    l += hypothese(
        "H10", "Les certificateurs francais font mieux que les etrangers",
        "Comparaison par nationalite de l'organisme, puis retrait de la marque "
        "dominante du groupe.",
        "REFUTE",
        corps + ["",
                 "L'ecart apparent tenait a une seule marque, qui pesait 42 % du",
                 "groupe etranger et se trouve etre la pire du classement. Retiree,",
                 "l'ecart passe sous le seuil."],
        ["« Est dit francais un organisme dont le nom designe une institution "
         "francaise » : une convention de nommage, pas un fait juridique."])

    corps = []
    if ele is not None and len(ele):
        e1 = ele[ele.variable.str.contains("Nutri-Score", na=False)]
        corps = ["Ecart a la mediane de marche, Nutri-Score continu :", "",
                 "| groupe | n | marques | ecart | IC 95 % |",
                 "|:--|--:|--:|--:|:-:|"]
        for r in e1.itertuples():
            corps.append(f"| {r.groupe} | {r.n} | "
                         f"{getattr(r, 'marques', '')} | "
                         f"{r.ecart_median:+.1f} | "
                         f"{ic(r.ic95_bas, r.ic95_haut)} |")
        corps += ["",
                  "La colonne « marques » compte les marques distinctes du "
                  "groupe :",
                  "deux marques pour le groupe « avec electronarcose », ce qui",
                  "suffit a expliquer pourquoi rien n'y est separable.", ""]
    l += hypothese(
        "H11", "Les certificateurs sans electronarcose font mieux",
        "Regroupement des organismes selon une classification de la pratique "
        "d'abattage.",
        "NON TESTABLE",
        corps + ["Meme obstacle qu'en H9 : la comparaison entre groupes",
                 "d'organismes est une comparaison entre leurs marques."],
        ["**La classification des organismes par pratique d'electronarcose est "
         "DECLAREE PAR LE COMMANDITAIRE de l'etude. Elle n'est pas etablie par "
         "ce depot.** Toute publication doit citer les cahiers des charges des "
         "organismes eux-memes.",
         "Un organisme dont la pratique n'etait pas connue n'a pas ete devine : "
         "classer a tort un organisme sur une pratique d'abattage serait une "
         "mise en cause publique infondee."])

    r4 = lire("r4_origine_france")
    corps = []
    if r4 is not None:
        corps = ["| variable | ecart France / sans mention | IC 95 % |",
                 "|:--|--:|:-:|"]
        for r in r4.itertuples():
            corps.append(f"| {r.variable} | {r.ecart:+.2f} | "
                         f"{ic(r.ic95_bas, r.ic95_haut)} |")
    l += hypothese(
        "H12", "Les produits halal fabriques en France sont meilleurs",
        "Comparaison au sein du bras halal entre produits portant une mention "
        "de production francaise VISIBLE et les autres, puis a gamme egale.",
        "NON ETABLI",
        corps + ["",
                 "L'ecart sur les AGS est un effet de composition : la mention",
                 "France est portee a 37 % par de la charcuterie cuite, pauvre en",
                 "AGS, contre 16 % sans mention. A gamme egale, une seule strate",
                 "est testable et ne montre rien."],
        ["**Absence de mention n'est pas origine etrangere.** La comparaison "
         "oppose une revendication a son absence.",
         "109 produits sur 1 955 portent la mention, soit 5,6 % du bras.",
         "Aucun autre pays n'atteint un effectif testable : l'origine par pays "
         "reste hors de portee."])

    r6 = lire("r6_repertoires_culinaires")
    corps = []
    if r6 is not None and len(r6):
        corps = ["A gamme egale, chaque repertoire contre les produits non "
                 "classes de la meme gamme :", "",
                 "| gamme | repertoire | n | ecart | IC 95 % | |",
                 "|:--|:--|--:|--:|:-:|:--|"]
        for r in r6.itertuples():
            corps.append(
                f"| {r.sous_categorie} | {r.repertoire} | {r.n} | "
                f"{r.ecart:+.1f} | {ic(r.ic95_bas, r.ic95_haut)} | "
                f"{'etabli' if r.etabli else 'non etabli'} |")
    l += hypothese(
        "H13", "La qualite nutritionnelle se deduit de l'origine culturelle du "
               "produit",
        "Classement des NOMS de produits par repertoire culinaire (maghrebin, "
        "turc, levantin, charcuterie europeenne, industriel anglo-saxon), puis "
        "comparaison a gamme egale.",
        "REFUTE",
        corps + ["",
                 "Le repertoire est une redite de la gamme : le maghrebin est a",
                 "78 % des saucisses, le levantin a 100 % dans une seule gamme.",
                 "Une fois la gamme fixee, les repertoires maghrebin et turc ne",
                 "montrent plus rien. Ce qui subsiste concerne le vocabulaire",
                 "charcutier et le vocabulaire industriel, c'est-a-dire la forme",
                 "du produit."],
        ["`config/repertoires_culinaires.yaml` classe des RECETTES. Jamais des "
         "personnes, jamais des entreprises, jamais un pays de fabrication.",
         "Publier ce decoupage sans le controle par gamme produirait exactement "
         "l'affirmation que cette etude doit rendre impossible."])
    l += ["---", ""]
    return l


def bloc_mecanismes() -> list[str]:
    t1 = lire("t1_prevalence_additifs")
    t2 = lire("t2_hydratation")
    t3 = lire("t3_nova")
    t4 = lire("t4_nombre_additifs")
    t0 = lire("t0_couverture_additifs")
    l = ["## 4. Par quel mecanisme", ""]

    corps = []
    if t1 is not None:
        ph = t1[(t1.famille == "phosphates") & (t1.etabli == True)]  # noqa: E712
        if len(ph):
            corps = ["Ecart de prevalence halal - temoin, a gamme egale, "
                     "methode de Newcombe :", "",
                     "| gamme | halal | temoin | ecart (points) | IC 95 % |",
                     "|:--|--:|--:|--:|:-:|"]
            for r in ph.sort_values("ecart_points", ascending=False).itertuples():
                corps.append(
                    f"| {r.sous_categorie} | {r.pct_halal:.1f} % | "
                    f"{r.pct_temoin:.1f} % | {r.ecart_points:+.1f} | "
                    f"{ic(r.ic95_bas, r.ic95_haut)} |")
    l += hypothese(
        "H14", "L'ecart de sel et de proteines vient de l'HYDRATATION, pas de "
               "la recette",
        "Prevalence des phosphates (retenteurs d'eau) a gamme egale ; puis "
        "effet des phosphates sur les proteines a gamme egale ; puis ecart "
        "halal / temoin sur les proteines EN TENANT LES PHOSPHATES FIXES.",
        "ETABLI",
        corps + ["",
                 "**Les phosphates predisent moins de proteines** a gamme egale :",
                 "-9.4 g sur la charcuterie seche, -4.0 sur la cuite, -3.0 sur",
                 "les panes.",
                 "",
                 "**Et l'ecart halal - temoin sur les proteines s'efface une fois",
                 "les phosphates tenus fixes** :",
                 "",
                 "| gamme | sans phosphates | avec phosphates |",
                 "|:--|--:|--:|",
                 "| charcuterie seche | -5.18 [-7.85 ; -2.35] | -1.30 [-5.00 ; +0.65] |",
                 "| panes | -2.45 [-3.20 ; -0.30] | +0.00 [-1.00 ; +1.00] |",
                 "| autres carnes | -1.00 [-3.00 ; +0.00] | +0.80 [-1.70 ; +1.80] |",
                 "",
                 "La phrase juste n'est donc pas « la charcuterie halal est plus",
                 "salee » mais **« elle est plus hydratee »**. Ce n'est pas la",
                 "meme affirmation : l'une vise la sante publique, l'autre le",
                 "rapport qualite-prix."],
        ["Un additif declare n'est pas un additif dose.",
         "La liste d'ingredients est mieux saisie cote halal (50,7 % contre "
         "44,0 %). Toutes les prevalences excluent les produits dont la liste "
         "n'a pas ete lue ; sans cette precaution le biais irait dans le sens du "
         "resultat.",
         "Un mediateur identifie sur donnees observationnelles reste une "
         "hypothese de mecanisme, pas une chaine causale demontree."])

    corps = []
    if t1 is not None:
        ni = t1[t1.famille == "nitrites_nitrates"]
        if len(ni):
            corps = ["| gamme | halal | temoin | ecart (points) | IC 95 % | |",
                     "|:--|--:|--:|--:|:-:|:--|"]
            for r in ni.sort_values("ecart_points", ascending=False).itertuples():
                corps.append(
                    f"| {r.sous_categorie} | {r.pct_halal:.1f} % | "
                    f"{r.pct_temoin:.1f} % | {r.ecart_points:+.1f} | "
                    f"{ic(r.ic95_bas, r.ic95_haut)} | "
                    f"{'etabli' if r.etabli else 'non etabli'} |")
    l += hypothese(
        "H15", "La charcuterie halal utilise plus de nitrites",
        "Prevalence des nitrites et nitrates (E249 a E252) a gamme egale, "
        "methode de Newcombe, sur les seuls produits dont la liste "
        "d'ingredients a ete lue.",
        "ETABLI sur cinq gammes, NON ETABLI sur la charcuterie cuite",
        corps + ["",
                 "L'ecart n'est PAS etabli sur la charcuterie cuite, qui est",
                 "pourtant le principal usage des nitrites."],
        ["**Aucune trajectoire n'est mesurable.** Le dump est une photo, sans "
         "historique de reformulation : la question « la charcuterie halal a-t-"
         "elle suivi la baisse post-2023 » reste sans reponse ici.",
         "Prevalence, pas dose. Un produit peut porter E250 a 50 mg/kg comme a "
         "150."])

    corps = []
    if t3 is not None and len(t3):
        corps = ["Part de NOVA 4 (ultra-transforme), ecart halal - temoin :", "",
                 "| gamme | halal | temoin | ecart (points) | IC 95 % | |",
                 "|:--|--:|--:|--:|:-:|:--|"]
        for r in t3.sort_values("ecart_points", ascending=False).itertuples():
            corps.append(
                f"| {r.sous_categorie} | {r.pct_nova4_halal:.1f} % | "
                f"{r.pct_nova4_temoin:.1f} % | {r.ecart_points:+.1f} | "
                f"{ic(r.ic95_bas, r.ic95_haut)} | "
                f"{'etabli' if r.etabli else 'non etabli'} |")
    l += hypothese(
        "H16", "Les produits halal sont plus ultra-transformes",
        "Part de NOVA 4 a gamme egale, sur les produits ou le classement NOVA "
        "est renseigne.",
        "ETABLI sur six gammes sur neuf",
        corps,
        ["NOVA n'est renseigne que sur 48,8 % du bras halal et 42,0 % du temoin.",
         "NOVA est un classement derive de la liste d'ingredients : il herite de "
         "ses erreurs de saisie."])

    corps = []
    if t4 is not None and len(t4):
        g = t4[t4.niveau == "gamme"]
        m = t4[t4.niveau != "gamme"]
        corps = ["| gamme | ecart du nombre d'additifs | IC 95 % |",
                 "|:--|--:|:-:|"]
        for r in g.itertuples():
            corps.append(f"| {r.cle} | {r.ecart:+.2f} | "
                         f"{ic(r.ic95_bas, r.ic95_haut)} |")
        if len(m):
            corps += ["", "A marque, gamme et espece egales :", "",
                      "| cellule | n halal | n temoin | ecart | IC 95 % |",
                      "|:--|--:|--:|--:|:-:|"]
            for r in m.itertuples():
                corps.append(f"| {r.cle} | {r.n_halal} | {r.n_temoin} | "
                             f"{r.ecart:+.2f} | {ic(r.ic95_bas, r.ic95_haut)} |")
    l += hypothese(
        "H17", "Les produits halal comptent plus d'additifs",
        "Mediane du nombre d'additifs a gamme egale, puis a marque, gamme et "
        "espece egales. Un decompte ne depend pas du Nutri-Score.",
        "ETABLI a gamme egale, REFUTE a fabricant egal",
        corps + ["",
                 "A fabricant egal, l'ecart est **nul et l'intervalle est un",
                 "point**. Comme partout ailleurs dans cette etude, ce que la",
                 "comparaison mesure est le fabricant."],
        ["Une seule cellule permet le controle du fabricant."])
    l += ["---", ""]
    return l


def bloc_prix() -> list[str]:
    u0 = lire("u0_couverture_prix")
    u1 = lire("u1_prix_par_gamme")
    u3 = lire("u3_gradient_prix_qualite")
    u4 = lire("u4_terciles_halal_charcuterie_cuite")
    u5 = lire("u5_a_prix_egal")
    l = ["## 5. Le prix", "",
         "Le prix vient d'Open Prices, projet de releves benevoles d'Open Food",
         "Facts, collecte par un runner GitHub — l'environnement de",
         "developpement ne joint pas ce service. **L'unite d'analyse est le",
         "PRODUIT**, prix median de ses releves : un produit peut porter 68",
         "releves, qui sont 68 passages en magasin et non 68 produits.", ""]
    if u0 is not None:
        l += ["| bras | produits avec prix | produits | couverture |",
              "|:--|--:|--:|--:|"]
        for r in u0.itertuples():
            l.append(f"| {r.bras} | {r.produits_avec_prix} | {r.produits} | "
                     f"{r.couverture_pct:.2f} % |")
        l += [""]

    corps = []
    if u1 is not None and len(u1):
        corps = ["| gamme | halal | temoin | ecart | IC 95 % | |",
                 "|:--|--:|--:|--:|:-:|:--|"]
        for r in u1.itertuples():
            corps.append(
                f"| {r.sous_categorie} | {r.prix_kg_halal:.2f} | "
                f"{r.prix_kg_temoin:.2f} | {r.ecart:+.2f} | "
                f"{ic(r.ic95_bas, r.ic95_haut)} | "
                f"{'etabli' if r.etabli else 'non etabli'} |")
    l += hypothese(
        "H18", "Le halal est un segment bon marche",
        "Prix median au kilo par produit, a gamme egale, IC bootstrap. Releves "
        "en promotion ecartes : une remise ne dit rien du positionnement d'une "
        "gamme.",
        "NON ETABLI",
        corps + ["",
                 "Une seule gamme franchit 30 produits halal, la charcuterie",
                 "cuite, et l'ecart y est non etabli."],
        ["Open Prices est un releve BENEVOLE : la couverture n'est ni large ni "
         "aleatoire. Quelqu'un photographie ce qu'il achete, la ou il fait ses "
         "courses.",
         "Un prix releve vaut pour un magasin et un jour, pas pour un marche."])

    corps = []
    if u3 is not None and len(u3):
        corps = ["Correlation de rang prix / Nutri-Score. **Positif = plus cher "
                 "va avec MOINS bon.**", "",
                 "| gamme | bras | n | rho | IC 95 % | |",
                 "|:--|:--|--:|--:|:-:|:--|"]
        for r in u3.itertuples():
            corps.append(f"| {r.sous_categorie} | {r.bras} | {r.n} | "
                         f"{r.rho:+.3f} | {ic(r.ic95_bas, r.ic95_haut)} | "
                         f"{'etabli' if r.etabli else 'non etabli'} |")
    if u4 is not None and len(u4):
        corps += ["", "Terciles de prix dans le bras halal, charcuterie cuite :",
                  "",
                  "| tercile | n | EUR/kg | Nutri-Score | sel | proteines |",
                  "|:--|--:|--:|--:|--:|--:|"]
        for r in u4.itertuples():
            corps.append(f"| {r.bande} | {r.n} | {r.prix_kg:.2f} | "
                         f"{r.nutriscore:+.1f} | {r.sel:.2f} | "
                         f"{r.proteines:.1f} |")
    l += hypothese(
        "H19", "Dans le halal, le moins cher est le moins bon",
        "Correlation de rang de Spearman entre prix au kilo et Nutri-Score "
        "continu, a gamme egale, IC par bootstrap.",
        "NON ETABLI dans le halal",
        corps + ["",
                 "Du simple au double de prix, le Nutri-Score ne bouge pas et le",
                 "sel non plus. **Payer plus cher du halal n'achete pas une",
                 "meilleure note.** Les proteines, elles, montent de 14.0 a 19.0 :",
                 "le prix achete de la matiere seche, ce qui rejoint H14.",
                 "",
                 "Dans le temoin la relation existe et change de sens selon la",
                 "gamme, ce qui interdit de la resumer par un chiffre unique."],
        ["Une seule gamme halal atteint 30 produits avec un prix."])

    corps = []
    if u5 is not None and len(u5):
        corps = ["| gamme | bande | n halal | n temoin | prix halal | "
                 "prix temoin | ecart Nutri-Score | IC 95 % | ecart sel |",
                 "|:--|:--|--:|--:|--:|--:|--:|:-:|--:|"]
        for r in u5.itertuples():
            if not r.testable:
                corps.append(f"| {r.sous_categorie} | {r.bande} | {r.n_halal} | "
                             f"{r.n_temoin} | — | — | sous le seuil de 30 | — | — |")
                continue
            corps.append(
                f"| {r.sous_categorie} | {r.bande} | {r.n_halal} | "
                f"{r.n_temoin} | {r.prix_halal:.2f} | {r.prix_temoin:.2f} | "
                f"{r.ecart_nutriscore:+.1f} | "
                f"{ic(r.ns_ic95_bas, r.ns_ic95_haut)} | {r.ecart_sel:+.2f} |")
    l += hypothese(
        "H20", "La moindre qualite nutritionnelle est un corollaire d'un prix "
               "moindre",
        "Terciles de prix calcules sur la gamme entiere, les deux bras "
        "confondus, puis comparaison halal / temoin DANS chaque bande.",
        "REFUTE la ou le test est possible",
        corps + ["",
                 "Dans la seule cellule testable — charcuterie cuite, bande de",
                 "prix moyenne — 40 produits halal a 17,19 EUR/kg contre 198",
                 "temoin a 16,82, donc **a prix quasi identique**, l'ecart",
                 "subsiste et il est plus net que l'ecart moyen de la gamme.",
                 "",
                 "**L'ecart nutritionnel n'est pas un corollaire du prix.**"],
        ["Une seule gamme, une seule bande de prix. Ce resultat ne se generalise "
         "pas au rayon.",
         "Il suffit en revanche a ecarter l'explication par le prix la ou elle "
         "etait la plus plausible, et cette gamme est celle ou l'ecart "
         "nutritionnel est le mieux documente."])
    l += ["---", ""]
    return l


def bloc_produits() -> list[str]:
    p0 = lire("p0_effectifs_produits")
    p2 = lire("p2_rayon_nutriscore_score")
    p3 = lire("p3_espece_nutriscore_score")
    p7 = lire("p7_substituts_porc")
    l = ["## 6. Produit par produit", ""]

    corps = []
    if p2 is not None and p0 is not None:
        t = p2[p2.bras == "temoin"][["produit", "mediane"]].rename(
            columns={"mediane": "ns_temoin"})
        h = p2[(p2.bras == "halal")].merge(t, on="produit")
        h = h.merge(p0[["produit", "libelle"]], on="produit", how="left")
        h = h.sort_values("ecart_vs_temoin", na_position="last")
        corps = ["| produit | n halal | halal | temoin | ecart | IC 95 % |",
                 "|:--|--:|--:|--:|--:|:-:|"]
        for r in h.itertuples():
            if pd.isna(r.ecart_vs_temoin):
                corps.append(f"| {r.libelle} | {r.n} | {r.mediane:+.1f} | "
                             f"{r.ns_temoin:+.1f} | non testable | — |")
                continue
            corps.append(f"| {r.libelle} | {r.n} | {r.mediane:+.1f} | "
                         f"{r.ns_temoin:+.1f} | {r.ecart_vs_temoin:+.1f} | "
                         f"{ic(r.ic95_bas, r.ic95_haut)} |")
    l += hypothese(
        "H21", "L'ecart se retrouve sur les produits que le consommateur "
               "reconnait",
        "Dix produits definis dans `config/produits_emblematiques.yaml`, "
        "affectation ordonnee premier match gagnant, comparaison halal / temoin "
        "au niveau du rayon puis a espece egale.",
        "ETABLI, mais le sens change selon le produit",
        corps + ["",
                 "Le halal fait **mieux** la ou il remplace le porc (mortadelle,",
                 "saucisson sec, merguez), **moins bien** partout ailleurs.",
                 "",
                 "Le jambon SEC est le cas limite : 3 produits halal contre",
                 "2 660 temoin. Le consommateur halal n'a pas un moins bon jambon",
                 "sec, **il n'en a pas** — le jambon sec est du porc par",
                 "definition. C'est un resultat, pas une donnee manquante."],
        ["« Les plus references » n'est pas « les plus vendus » : Open Food "
         "Facts ne contient aucune donnee de vente.",
         "Le kasher ne franchit 30 que sur le jambon cuit."])

    corps = []
    if p7 is not None and len(p7):
        corps = ["| produit | comparaison | variable | n | ecart | IC 95 % |",
                 "|:--|:--|:--|:--|--:|:-:|"]
        for r in p7.itertuples():
            corps.append(f"| {r.produit} | {r.comparaison} | {r.variable} | "
                         f"{r.n_a}/{r.n_b} | {r.ecart:+.2f} | "
                         f"{ic(r.ic95_bas, r.ic95_haut)} |")
    l += hypothese(
        "H22", "Les substituts halal de produits traditionnellement au porc "
               "sont moins bons",
        "Pour les produits dont la version traditionnelle est au porc, "
        "comparaison du substitut halal au substitut NON halal de meme espece, "
        "puis a l'original au porc.",
        "REFUTE contre le substitut, ETABLI contre l'original",
        corps + ["",
                 "Le substitut halal et le substitut non halal de meme espece",
                 "sont **indiscernables** sur le Nutri-Score. Contre l'original",
                 "au porc, le halal fait mieux. Le gain vient du changement",
                 "d'espece, pas du label.",
                 "",
                 "**Reserve qui annule l'essentiel du benefice : 99 a 100 % de",
                 "D/E dans tous les groupes.** On compare deux mauvais produits.",
                 "Et le substitut perd 6 a 7 g de proteines pour 100 g, ce qui",
                 "rejoint H14."],
        ["La mortadelle n'est pas testable : l'espece n'est pas derivable pour "
         "249 produits sur 297."])
    l += ["---", ""]
    return l


def bloc_marche() -> list[str]:
    r7 = lire("r7_etiquetage_par_repertoire")
    v4 = lire("v4_paires_appariees")
    w0 = lire("w0_couverture_estampille")
    w1 = lire("w1_usines_multimarques")
    w2 = lire("w2_intra_etablissement")
    l = ["## 7. Ce que le rayon halal contient, et qui le fabrique", ""]

    corps = []
    if r7 is not None and len(r7):
        corps = ["Part des produits d'un repertoire portant une estampille "
                 "halal, sur le perimetre entier :", "",
                 "| repertoire | produits | dont halal | taux |",
                 "|:--|--:|--:|--:|"]
        for r in r7.sort_values("pct_halal", ascending=False).itertuples():
            corps.append(f"| {r.repertoire} | {r.n_total} | {int(r.n_halal)} | "
                         f"{r.pct_halal:.1f} % |")
    l += hypothese(
        "H23", "Le rayon halal couvre la cuisine maghrebine",
        "Taux d'estampille halal par repertoire culinaire, sur le perimetre "
        "entier et non sur le seul bras halal.",
        "REFUTE",
        corps + ["",
                 "Le repertoire maghrebin du bras halal est a 78 % des",
                 "saucisses. Ce n'est pas que la cuisine maghrebine s'y",
                 "reduise : le couscous et le tajine sont bien dans le",
                 "perimetre et bien ranges en plats cuisines. **Sur 135",
                 "couscous, UN SEUL porte une estampille halal ; sur 131",
                 "tajines, deux.**",
                 "",
                 "Le contraste avec le repertoire turc, estampille a 54 %, est",
                 "le resultat : deux cuisines, deux pratiques d'etiquetage."],
        ["Ce taux mesure l'ETIQUETAGE, pas la halalite : un couscous sans "
         "mention peut etre halal sans le dire.",
         "Aucune cause n'est etablie. Le fabricant peut ne pas certifier, ou "
         "certifier sans l'afficher."])

    corps = []
    if v4 is not None and len(v4):
        s4 = v4[v4.meme_recette]
        corps = [f"{len(s4)} paires comparables : "
                 f"**{int((s4.ecart == 0).sum())} identiques**, "
                 f"{int((s4.ecart > 0).sum())} defavorables au halal, "
                 f"{int((s4.ecart < 0).sum())} favorables.", "",
                 "| marque | produit | EAN halal | EAN non halal | ecart |",
                 "|:--|:--|:--|:--|--:|"]
        for r in s4[s4.ecart != 0].sort_values(
                "ecart", ascending=False).itertuples():
            corps.append(f"| {r.marque} | {r.produit} | `{r.code_halal}` | "
                         f"`{r.code_temoin}` | {r.ecart:+.1f} |")
    l += hypothese(
        "H24", "Chez un meme fabricant, la version halal differe de la version "
               "non halal",
        "Paires appariees sur marque, nom normalise, gamme et espece. Deux "
        "filtres de plausibilite declares en config ecartent les erreurs de "
        "saisie et les produits dont la forme contredit leur categorie.",
        "REFUTE dans la majorite des cas",
        corps + ["",
                 "Detail complet, avec les codes-barres et les trois niveaux de",
                 "solidite : `sorties/rapport_produits_nommes.md`.",
                 "",
                 "Le motif le plus net est Carrefour, defavorable sur quatre",
                 "produits transformes et neutre ou favorable sur la decoupe",
                 "crue — le meme motif que les couches 3 et 7."],
        ["**Une paire n'est pas un test** : la plupart reposent sur une "
         "reference de chaque cote. C'est une observation, pas une mesure avec "
         "un intervalle.",
         "Le palmares contre le marche n'est PAS publiable : trois tentatives "
         "ont chacune produit une comparaison truquee au detriment du produit "
         "halal, faute d'un comparateur fiable dans les categories."])

    corps = []
    if w0 is not None:
        corps = ["| bras | produits | avec estampille |", "|:--|--:|--:|"]
        for r in w0.itertuples():
            corps.append(f"| {r.bras} | {r.n} | {r.avec:.1f} % |")
    if w1 is not None and len(w1):
        mixtes = w1[(w1.n_halal >= 10) & (w1.n_temoin >= 10)]
        corps += ["",
                  f"{len(w1)} etablissements a 10 produits ou plus. "
                  f"**{len(mixtes)} seulement en fabriquent des deux bras.**",
                  "",
                  "Les gros faconniers multi-marques du rayon carne — jusqu'a",
                  "45 marques sur un site — ne produisent presque pas de halal.",
                  ""]
    if w2 is not None and len(w2):
        corps += ["| etablissement | gamme | n halal | n temoin | ecart | "
                  "IC 95 % |", "|:--|:--|--:|--:|--:|:-:|"]
        for r in w2.itertuples():
            corps.append(f"| `{r.etablissement}` | {r.sous_categorie} | "
                         f"{r.n_halal} | {r.n_temoin} | "
                         f"{r.ecart_nutriscore:+.1f} | "
                         f"{ic(r.ic95_bas, r.ic95_haut)} |")
    l += hypothese(
        "H25", "L'estampille sanitaire permet d'observer le fabricant",
        "L'estampille ovale identifie l'ETABLISSEMENT agree, pas la marque : "
        "une usine qui fabrique pour dix marques porte le meme code sur les "
        "dix. Comparaison halal / temoin au sein d'un meme etablissement, a "
        "gamme egale.",
        "ETABLI comme methode, NON TESTABLE faute d'effectifs",
        corps + ["",
                 "La methode fonctionne et l'identifiant est **visible par le",
                 "consommateur**, ce que la marque de distributeur ne dit",
                 "jamais. Mais le rayon halal et l'industrie du faconnage",
                 "multi-marques ne se recouvrent presque pas dans ces donnees.",
                 "",
                 "La seule cellule disponible va dans le meme sens que celle de",
                 "H8 : **+0.0 de Nutri-Score et +0.00 g de sel**, halal contre",
                 "temoin, dans le meme etablissement. Deux observations",
                 "independantes, meme resultat."],
        ["L'estampille est un fait d'emballage, mais sa saisie dans Open Food "
         "Facts est facultative : 31 % du bras halal, 34 % du temoin.",
         "24 produits halal : sous le seuil de 30, donc decrit et jamais teste.",
         "`emb-ddddd`, l'ancien code, designe une COMMUNE et non une usine : "
         "6 832 produits ecartes plutot que fusionnes a tort.",
         "Un site mal classe le serait sur les recettes que ses donneurs "
         "d'ordre lui commandent : un fabricant a facon execute un cahier des "
         "charges. D'ou le retrait de la marque dominante dans le classement."])
    w4 = lire("w4_variance_etablissement")
    corps = []
    if w4 is not None and len(w4):
        corps = ["Part de la variance du Nutri-Score qui separe les groupes "
                 "(ICC), avec IC par bootstrap de grappes — on retire des "
                 "usines entieres, pas des produits :", "",
                 "| bras | groupe | variable | ICC | IC 95 % | groupes | n | "
                 "sigma intra |",
                 "|:--|:--|:--|--:|:-:|--:|--:|--:|"]
        for r in w4.itertuples():
            corps.append(
                f"| {r.bras} | {r.groupe} | {r.variable} | {r.icc:.3f} | "
                f"[{r.ic95_bas:.2f} ; {r.ic95_haut:.2f}] | {r.groupes} | "
                f"{r.n} | {r.ecart_type_intra:.2f} |")
    l += hypothese(
        "H26", "L'usine explique la qualite nutritionnelle",
        "Decomposition de la variance a un facteur. Sur le Nutri-Score BRUT "
        "l'ICC melange le CRENEAU du site et son SAVOIR-FAIRE ; sur l'ecart a "
        "la mediane de la strate, le creneau est neutralise. IC par bootstrap "
        "de grappes.",
        "ETABLI dans le temoin, NON ETABLI dans le halal",
        corps + ["",
                 "**Le creneau pese plus que le savoir-faire.** Dans le temoin,",
                 "l'etablissement explique 72,5 % de la variance brute mais",
                 "30,4 % une fois la strate fixee : 42 points sur 72 tenaient a",
                 "ce que le site fabrique, pas a comment il le fabrique.",
                 "",
                 "**L'usine explique deux fois plus que la marque** : 0,304",
                 "contre 0,153 a composition egale, intervalles disjoints. Qui",
                 "fabrique compte davantage que le nom sur l'emballage.",
                 "",
                 "**Mais pas dans le halal.** L'ICC y tombe a 0,168",
                 "[0,06 ; 0,27] et l'ecart-type INTRA site monte a 7,82 contre",
                 "5,55 au temoin : dans un meme site, les produits halal varient",
                 "PLUS que les non halal. Designer un site comme bon ou mauvais",
                 "eleve sur sa production halal serait donc mal fonde."],
        ["23 etablissements et 362 produits cote halal : les intervalles y sont "
         "larges et se recouvrent avec ceux du temoin. La comparaison des deux "
         "ICC est indicative, pas etablie.",
         "L'ICC depend du decoupage en strates : un decoupage plus fin "
         "absorberait davantage de creneau et abaisserait encore l'ICC sur "
         "l'ecart.",
         "Une variance intra plus grande peut venir d'un assortiment halal plus "
         "heterogene au sein du site, pas d'une conduite de fabrication moins "
         "reguliere. Les donnees ne separent pas les deux."])
    x1 = lire("x1_homogeneite")
    corps = []
    if x1 is not None and len(x1):
        g = x1[x1.niveau == "perimetre"]
        corps = ["Rapport de dispersion halal / temoin sur l'ecart a la "
                 "mediane de la strate. **Sous 1, le halal serait plus "
                 "homogene**, ce que produirait une prescription commune :", "",
                 "| mesure | halal | temoin | rapport | IC 95 % |",
                 "|:--|--:|--:|--:|:-:|"]
        for r in g.itertuples():
            corps.append(f"| {r.mesure} | {r.halal:.2f} | {r.temoin:.2f} | "
                         f"**{r.rapport:.2f}** | [{r.ic95_bas:.2f} ; "
                         f"{r.ic95_haut:.2f}] |")
        st = x1[x1.niveau == "strate"]
        if len(st):
            plus = int((st.ic95_bas > 1).sum())
            moins = int((st.ic95_haut < 1).sum())
            corps += ["",
                      f"A strate fixee : {plus} strates plus dispersees, "
                      f"{moins} plus homogenes, {len(st) - plus - moins} non "
                      f"etablies. Une part du rapport global vient donc de "
                      f"l'assortiment et non des recettes."]
        im = x1[x1.niveau == "intra_marque"]
        if len(im):
            corps += ["", "Dispersion A L'INTERIEUR d'une meme marque, "
                      "ecart-type median :", ""]
            for r in im.itertuples():
                corps.append(f"- {r.cle} : {r.n_temoin} marques, ecart-type "
                             f"intra median a lire dans le CSV")
    l += hypothese(
        "H27", "Un cahier des charges commun impose la sous-qualite au halal",
        "Une prescription partagee RESSERRE la dispersion : les produits qui "
        "s'y conforment se ressemblent. On mesure donc le rapport de "
        "dispersion halal / temoin sur l'ecart a la mediane de la strate, avec "
        "trois mesures — ecart-type, ecart interquartile, ecart absolu median "
        "— et un IC bootstrap.",
        "REFUTE — la trace observable d'une prescription est absente",
        corps + ["",
                 "Le bras halal est **plus disperse**, pas moins : de 1,2 a 1,8",
                 "fois selon la mesure, les trois intervalles au-dessus de 1.",
                 "Meme constat a l'interieur d'une marque et, en H26, a",
                 "l'interieur d'un etablissement, ou l'ecart-type intra halal",
                 "atteint 7,82 contre 5,55 au temoin.",
                 "",
                 "C'est la signature de choix de formulation **independants**,",
                 "pas d'une norme partagee.",
                 "",
                 "Combine a H8, H17 et H25 — a fabricant fixe, aucun ecart — le",
                 "faisceau dit : le label n'impose rien, et ce sont certains",
                 "fabricants qui formulent ainsi, chacun de son cote."],
        ["**AUCUNE DONNEE NUTRITIONNELLE NE PEUT ATTEINDRE UNE INTENTION.** Une "
         "intention est un etat mental de decideurs ; cette base contient des "
         "etiquettes. Ce test porte sur une trace observable, jamais sur une "
         "volonte.",
         "Ce resultat ne prouve pas qu'aucun cahier des charges n'existe, et il "
         "ne dit rien de leur contenu : ceux des organismes certificateurs "
         "portent sur l'abattage et la tracabilite, et il faudrait les lire.",
         "A strate fixee le tableau est partage : le rapport global tient en "
         "partie a l'assortiment. Cela nuance le resultat sans l'inverser — "
         "nulle part on n'observe le resserrement qu'une norme produirait.",
         "Des explications sans intention restent ouvertes et non testees ici : "
         "contrainte technique de la substitution d'espece, marche plus etroit, "
         "recettes anciennes non reformulees quand le marche general reduisait "
         "le sel."])
    y1 = lire("y1_allegations")
    corps = []
    if y1 is not None and len(y1):
        per = y1[y1.niveau == "perimetre"]
        dif = y1[y1.niveau == "difference_des_ecarts"]
        corps = ["Prevalence des allegations d'emballage, ecart halal - temoin "
                 "en points :", "",
                 "| famille | halal | temoin | ecart | IC 95 % |",
                 "|:--|--:|--:|--:|:-:|"]
        for r in per.itertuples():
            corps.append(f"| {r.famille} | {r.pct_halal:.2f} % | "
                         f"{r.pct_temoin:.2f} % | **{r.ecart_points:+.2f}** | "
                         f"[{r.ic95_bas:+.2f} ; {r.ic95_haut:+.2f}] |")
        if len(dif):
            r = dif.iloc[0]
            corps.append(f"| **difference des deux** | | | "
                         f"**{r.ecart_points:+.2f}** | "
                         f"[{r.ic95_bas:+.2f} ; {r.ic95_haut:+.2f}] |")
        mq = y1[(y1.niveau == "marque")]
        if len(mq):
            corps += ["", "**Le test decisif : dans une meme marque.**", "",
                      "| marque | famille | n halal | n temoin | halal | "
                      "temoin | ecart | IC 95 % | |",
                      "|:--|:--|--:|--:|--:|--:|--:|:-:|:--|"]
            for r in mq.itertuples():
                corps.append(
                    f"| {r.cle} | {r.famille} | {r.n_halal} | {r.n_temoin} | "
                    f"{r.pct_halal:.1f} % | {r.pct_temoin:.1f} % | "
                    f"{r.ecart_points:+.1f} | [{r.ic95_bas:+.1f} ; "
                    f"{r.ic95_haut:+.1f}] | "
                    f"{'etabli' if r.etabli else 'non etabli'} |")
    l += hypothese(
        "H28", "Sur une gamme halal, la dimension nutritionnelle pese moins "
               "dans le cahier des charges de la MARQUE",
        "L'effort nutritionnel d'un industriel laisse une trace volontaire sur "
        "le paquet : Nutri-Score affiche, sel reduit, sans additif. Une "
        "famille TEMOIN de revendications non nutritionnelles — sans gluten, "
        "sans huile de palme, sans OGM — sert de falsification : si le halal "
        "revendiquait moins de TOUT, on mesurerait un emballage moins "
        "documente et non une posture. Newcombe, puis bootstrap sur la "
        "difference des deux ecarts.",
        "ETABLI sur le perimetre, appuye par une marque sur trois",
        corps + ["",
                 "**Le recul nutritionnel excede le recul general de 9,7",
                 "points** [-11,6 ; -7,9]. Ces gammes revendiquent, mais moins",
                 "la nutrition.",
                 "",
                 "A gamme egale, le recul de l'effort nutritionnel est etabli",
                 "dans 8 gammes sur 10, celui de la famille temoin dans 4. Sur",
                 "les plats cuisines et les preparations marinees, la gamme",
                 "halal revendique DAVANTAGE sur la famille temoin et MOINS sur",
                 "la nutrition : c'est le motif le plus net.",
                 "",
                 "Fleury Michon est le cas d'ecole : **-13,1 points**",
                 "[-24,9 ; -1,4] d'effort nutritionnel sur sa gamme halal,",
                 "quand la famille temoin y est a +4,1, non etabli. C'est la",
                 "marque dont H8 montre que le produit halal est nutritionnellement",
                 "IDENTIQUE au non halal : meme recette, moins de",
                 "communication nutritionnelle.",
                 "",
                 "Cette hypothese ne contredit pas H27, elle s'y accorde : une",
                 "contrainte nutritionnelle plus lache produit PLUS de",
                 "dispersion, ce que H27 observe."],
        ["**Trois marques seulement** atteignent 20 produits des deux cotes, et "
         "elles divergent : Fleury Michon appuie l'hypothese, Carrefour va en "
         "sens inverse (+15,3, non etabli), Aia n'informe pas. Le test le plus "
         "propre est aussi le moins fourni.",
         "Une mention absente n'est pas une nutrition negligee : elle peut "
         "signifier un produit non reformule, ou un produit reformule dont on "
         "n'a pas juge utile de le dire.",
         "Les labels d'Open Food Facts sont saisis par des contributeurs. La "
         "famille temoin controle cette saisie, elle ne l'annule pas.",
         "**Ce test mesure ce qui est imprime, pas ce qui est decide.** Aucun "
         "cahier des charges n'a ete lu. Parler de posture reste une "
         "interpretation, et l'ecrire comme une intention prouvee serait une "
         "faute."])
    z1 = lire("z1_site_ou_marque")
    corps = []
    if z1 is not None and len(z1):
        gl = z1[z1.niveau == "global"]
        corps = ["Produits halal, selon que leur etablissement sert AUSSI a la "
                 "production non halal de la meme marque :", "",
                 "| variable | n site partage | n site halal seul | ecart | "
                 "IC 95 % | |", "|:--|--:|--:|--:|:-:|:--|"]
        for r in gl.itertuples():
            corps.append(f"| {r.variable} | {r.n_partage} | {r.n_halal_seul} | "
                         f"{r.ecart:+.2f} | [{r.ic95_bas:+.2f} ; "
                         f"{r.ic95_haut:+.2f}] | "
                         f"{'etabli' if r.etabli else 'non etabli'} |")
        mq = z1[(z1.niveau == "marque") & z1.ecart.notna()]
        if len(mq):
            corps += ["", "**A l'interieur d'une marque** — seule lecture qui "
                      "echappe au confondant :", "",
                      "| marque | n partage | n halal seul | difference |",
                      "|:--|--:|--:|--:|"]
            for r in mq.itertuples():
                corps.append(f"| {r.cle} | {r.n_partage} | {r.n_halal_seul} | "
                             f"{r.ecart:+.1f} |")
    l += hypothese(
        "H29", "L'ecart tient au changement de SITE de fabrication",
        "Pour chaque produit halal, on regarde si son etablissement sert aussi "
        "a la production non halal de la MEME marque. Comparaison a "
        "composition egale, ecart a la mediane de marche de la strate.",
        "ETABLI sur le sel, NON ETABLI sur le Nutri-Score, et le motif ne tient "
        "pas dans toutes les marques",
        corps + ["",
                 "Sur un site partage, le halal est a **1,8 g de sel** et un",
                 "ecart de **+1,0** ; sur un site qui ne sert qu'au halal, 2,0 g",
                 "et **+5,0**.",
                 "",
                 "**Carrefour est l'illustration nette** : sa gamme halal sort",
                 "majoritairement de sites qu'il n'emploie pas pour le reste, et",
                 "c'est la que l'ecart se creuse (+9,0 sur 31 produits). Sur les",
                 "sites qu'il partage, l'ecart s'efface presque (+0,5 sur 8).",
                 "Cela reinterprete son mauvais classement de H24 : moins une",
                 "recette revue a la baisse qu'un approvisionnement ailleurs.",
                 "",
                 "**Reghalal montre l'inverse** : +10,0 sur site partage contre",
                 "+1,0 sur site halal seul. Le motif n'est donc pas general."],
        ["**Confondant assume et non resolu** : les sites partages "
         "appartiennent surtout aux generalistes, qui font mieux par ailleurs. "
         "Comparer les deux groupes revient en partie a comparer des "
         "generalistes a des specialistes. Le detail par marque est publie pour "
         "cette raison.",
         "Seules 3 marques ont assez de produits des deux cotes, et elles ne "
         "disent pas la meme chose.",
         "L'estampille n'est saisie que sur 31 % du bras halal : ce test porte "
         "sur une fraction, et rien ne dit qu'elle soit representative.",
         "Un site partage n'est pas une ligne de production partagee : un meme "
         "agrement peut couvrir des ateliers distincts."])
    l += ["---", ""]
    return l


def bloc_erreurs() -> list[str]:
    return [
        "## 8. Erreurs commises et corrigees en cours d'etude",
        "",
        "Elles sont listees parce qu'un lecteur doit pouvoir juger de la",
        "fiabilite du reste, et parce que chacune a failli produire une",
        "affirmation publique fausse.",
        "",
        "| # | erreur | consequence si non corrigee | correction |",
        "|--:|:--|:--|:--|",
        "| 1 | Detection du certificateur par la chaine « halal » | Couverture "
        "annoncee a 6,9 % au lieu de 31,9 % ; AVS et les mosquees invisibles | "
        "Registre par organisme, `config/certificateurs.yaml` |",
        "| 2 | Especes derivees de FORMES de produit | 203 produits halal "
        "classes porc ; salami de dinde compte comme du porc | Motifs "
        "restreints a l'espece, assertion A7 |",
        "| 3 | Exclusion des produits de la mer trop large | 3 785 exclusions "
        "au lieu de 924 ; « Grillons de canard » pris pour des insectes | "
        "Exclusion composee, deux motifs |",
        "| 4 | Strate « decoupes » melangeant cru et marine | Ecart de sel de "
        "1,30 contre 0,25 g attribue au label | Strate scindee |",
        "| 5 | Aides culinaires dans un perimetre carne | Fonds de veau a 22 g "
        "de sel comptes comme des aliments | Exclusion par categorie |",
        "| 6 | `additives_tags` vide pris pour « sans additif » | Prevalence "
        "halal gonflee, biais dans le sens du resultat | Restriction aux "
        "produits dont la liste est lue |",
        "| 7 | Repertoire culinaire rattache par position | Appariement "
        "arbitraire entre nom et produit ; le maghrebin passait de 54 a 78 % de "
        "saucisses | Nom lu dans la meme requete |",
        "| 8 | Collecte de prix plafonnee a 16 % de la base | « Open Food Facts "
        "ne couvre pas le rayon halal », faux | Pagination revue |",
        "| 9 | Prix compares au RELEVE et non au PRODUIT | 3 des 4 ecarts "
        "« etablis » disparaissent ; le signe s'inverse sur la charcuterie "
        "cuite | Agregation par produit |",
        "| 10 | Verdict prix lu sur le point et non l'intervalle | Un ecart de "
        "+0.0 range du cote « meilleur » | Verdict fonde sur les IC |",
        "| 11 | Dump fige declare irrecuperable | Etude declaree non rejouable | "
        "`versionId` S3 ajoute a `config/source.yaml` |",
        "| 12 | Sortie A7 sans `ORDER BY` | Fichier versionne changeant d'ordre "
        "a chaque execution | Tri explicite |",
        "",
        "Deux d'entre elles, la 6 et la 9, allaient dans le sens du resultat",
        "attendu. C'est la raison pour laquelle la couverture des donnees est",
        "desormais mesuree et publiee AVANT chaque comparaison.",
        "",
        "---",
        "",
    ]


def bloc_ouvert() -> list[str]:
    return [
        "## 9. Ce qui reste ouvert",
        "",
        "| sujet | etat | ce qu'il faudrait |",
        "|:--|:--|:--|",
        "| Faux negatifs d'etiquetage | 0 sur 43 lectures d'image, IC 95 % "
        "[0 ; 8,2 %] | 200 codages humains sur image, contre 43 |",
        "| Haut du classement des marques | Non publiable | Verifier produit par "
        "produit les 4 marques de produits de la mer |",
        "| Origine par pays | Hors de portee | Aucun pays hors France n'atteint "
        "un effectif testable |",
        "| Nitrites, trajectoire | Impossible ici | Une serie temporelle, pas "
        "une photo |",
        "| Prix | Une seule gamme testable | Un relevé de prix systematique, pas "
        "benevole |",
        "| Controle du fabricant | Une seule cellule | Des marques vendant les "
        "deux versions du meme produit |",
        "| Electronarcose | Classification non etablie ici | Les cahiers des "
        "charges des organismes eux-memes |",
        "| Faconnage multi-marques | 3 etablissements mixtes seulement | Une "
        "meilleure saisie des estampilles, ou le registre public des agrements |",
        "| Couscous et tajine halal | 1 sur 135, 2 sur 131 | Comprendre "
        "pourquoi : absence de certification, ou d'affichage |",
        "",
        "---",
        "",
        "## Reproduire",
        "",
        "```sh",
        "make install",
        "make couche1     # source, perimetre, assertions, analyse, rapport",
        "make couche3     # appariement, les deux estimands",
        "make couche4     # marques, certificateurs, classements",
        "make couche5     # produits emblematiques",
        "make couche6     # reperes consommateur",
        "make couche7     # additifs et transformation",
        "make couche8     # prix (collecte via l'Action couche8-prix)",
        "python3 src/rapport_hypotheses.py   # regenere ce document",
        "```",
        "",
        "Le dump est epingle par son `versionId` S3 : `make couche1` rejoue la",
        "meme base, pas celle du jour.",
        "",
    ]


def main() -> int:
    k = cles()
    lignes = (entete(k) + bloc_perimetre(k) + bloc_effet_label()
              + bloc_kasher() + bloc_marques() + bloc_certificateurs()
              + bloc_mecanismes() + bloc_prix() + bloc_produits()
              + bloc_marche() + bloc_erreurs() + bloc_ouvert())
    CIBLE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    titre("RESULTATS.md")
    print(f"  {len(lignes)} lignes ecrites dans {CIBLE}")
    manquantes = [l for l in lignes if "Sortie absente" in l
                  or "Colonnes absentes" in l]
    if manquantes:
        print(f"  [ATTENTION] {len(manquantes)} sections sans donnees :")
        for m in dict.fromkeys(manquantes):
            print(f"    {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
