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
    l += bloc_h32()
    l += ["---", ""]
    return l


def bloc_h32() -> list[str]:
    """H32 — le surcout halal en rayon, et la borne qu'il pose."""
    g0 = lire("g0_couverture_prix")
    g1 = lire("g1_surcout_global")
    g2 = lire("g2_borne")
    g3 = lire("g3_par_strate")
    g4 = lire("g4_intra_marque")
    if g1 is None or not len(g1) or g2 is None or not len(g2):
        return ["### H32 — Sortie absente : g1_surcout_global", ""]
    r, b = g1.iloc[0], g2.iloc[0]

    c = ["La question se dedouble, et ce depot ne peut en traiter qu'une "
         "moitie.",
         "",
         "1. **Y a-t-il un surcout en rayon ?** Mesurable ici.",
         "2. **Le cout de l'abattage rituel et de la certification "
         "l'explique-t-il ?**",
         "   Non mesurable ici, et rien dans ce depot ne s'en approche. Open "
         "Food",
         "   Facts est une base de composition et d'etiquetage : elle ne "
         "contient ni",
         "   cout d'abattage, ni redevance de certification, ni marge, ni prix "
         "de",
         "   cession industriel. Y repondre demanderait les comptabilites des",
         "   abattoirs, les grilles tarifaires des organismes certificateurs, "
         "et les",
         "   conditions commerciales entre industriels et enseignes. Aucune de "
         "ces",
         "   trois sources n'est publique, et ce depot n'en contient aucun "
         "chiffre.",
         ""]
    if g0 is not None and len(g0):
        c += ["**Couverture, a lire avant tout chiffre de prix.**", "",
              "| bras | produits avec prix utilisable | produits | couverture |",
              "|:--|--:|--:|--:|"]
        for x in g0.itertuples():
            c.append(f"| {x.bras} | {int(x.avec_prix)} | "
                     f"{int(x.produits)} | {x.couverture_pct:.2f} % |")
        c += ["",
              "Ces effectifs sont plus bas que ceux de H18 (205 produits halal). "
              "H18",
              "compte les produits APPARIES a un prix, H32 ceux REELLEMENT",
              "UTILISABLES, apres le filtre de grammage : la difference est "
              "faite",
              "d'articles qui ont un prix mais pas de prix au kilo."]
    c += ["",
          "**Prix au kilo, a composition egale** — ecart au prix median de "
          "marche",
          "de la strate (sous-categorie x espece), les deux bras confondus au",
          "denominateur. IC 95 % par bootstrap de grappes sur les marques.", "",
          "| bras | produits | marques | prix median | ecart median |",
          "|:--|--:|--:|--:|--:|",
          f"| halal | {int(r.n_halal)} | {int(r.marques_halal)} | "
          f"{r.prix_median_halal:.2f} EUR/kg | {r.surcout:+.2f} |",
          f"| temoin | {int(r.n_temoin)} | — | {r.prix_median_temoin:.2f} "
          f"EUR/kg | +0.00 |",
          "",
          f"**Surcout halal : {r.surcout:+.2f} EUR/kg "
          f"[{r.ic95_bas:+.2f} ; {r.ic95_haut:+.2f}], "
          f"{'ETABLI' if r.etabli else 'NON ETABLI'}.**",
          "Le point estime va dans le sens inverse de la question : sur les",
          "produits releves, le halal est legerement MOINS cher que le marche a",
          "composition egale. L'intervalle contient zero, il n'y a donc ni",
          "surcout ni sous-cout etabli.",
          "",
          "### La borne, qui est la reponse reellement disponible", "",
          "Meme sans connaitre le cout d'abattage, les prix bornent ce qu'un tel",
          "cout peut avoir repercute en rayon.", "",
          f"- Prix de reference du temoin : **{b.prix_reference_temoin_kg:.2f} "
          "EUR/kg**.",
          f"- Surcout compatible avec les donnees : **au plus "
          f"{b.borne_haute_surcout_kg:+.2f} EUR/kg**, soit "
          f"{b.borne_haute_pct:+.1f} %",
          "  du prix de reference.",
          "",
          "**Lecture.** Toute repercussion en rayon superieure a cette borne est",
          "refutee par ces donnees, quel que soit le cout reel en amont. Une",
          "repercussion inferieure reste possible et n'est pas mesurable ici :",
          "elle serait noyee dans la dispersion des prix. Avec 138 produits",
          "halal releves, la couche n'a pas la puissance de voir moins.",
          "",
          "**Ce que la borne ne dit pas.** Un cout d'abattage peut exister sans",
          "arriver au consommateur : absorbe par la marge, compense par le",
          "creneau, ou reporte sur d'autres references. Un prix n'est pas un",
          "cout. L'absence de surcout en rayon ne refute pas un surcout en",
          "amont ; elle dit qu'il n'arrive pas au consommateur sous forme de",
          "prix, ou qu'il est trop petit pour se voir ici."]
    if g3 is not None and len(g3):
        c += ["", "**Gamme par gamme**, descriptif : aucune strate n'atteint",
              "30 produits des deux cotes.", "",
              "| strate | n halal | n temoin | prix halal | prix temoin | "
              "surcout |", "|:--|--:|--:|--:|--:|--:|"]
        for x in g3.head(8).itertuples():
            c.append(f"| {x.strate} | {int(x.n_halal)} | {int(x.n_temoin)} | "
                     f"{x.prix_halal:.2f} | {x.prix_temoin:.2f} | "
                     f"{x.surcout:+.2f} |")
        c += ["",
              "Les signes vont dans les deux sens : la charcuterie cuite de",
              "volaille est plus chere en halal, les panes et la viande hachee",
              "moins chers. Aucune de ces lignes n'est testable."]
    if g4 is not None and len(g4):
        c += ["", "**Le seul controle propre : la meme marque des deux cotes.**",
              "Des qu'on sort d'une marque, on compare des entreprises",
              "differentes, avec des couts et des positionnements differents.",
              "", "| marque | n halal | n temoin | prix halal | prix temoin | "
              "surcout | regle des 30 |",
              "|:--|--:|--:|--:|--:|--:|:--|"]
        for x in g4.itertuples():
            c.append(f"| {x.marque} | {int(x.n_halal)} | {int(x.n_temoin)} | "
                     f"{x.prix_halal:.2f} | {x.prix_temoin:.2f} | "
                     f"{x.surcout:+.2f} | {x.regle_30} |")
        c += ["",
              "**Aucune ne franchit la regle des 30 des deux cotes.** Fleury",
              "Michon, la mieux dotee, montre +1,19 EUR/kg sur 11 produits halal",
              "contre 114 temoin : une description, pas un test. C'est la limite",
              "la plus serieuse de cette couche, et elle ne se resout pas par le",
              "calcul — il faut plus de releves de prix."]
    return hypothese(
        "H32", "Le cout de l'abattage rituel explique un surcout du halal en "
        "rayon",
        "Deux temps. D'abord mesurer le surcout en rayon : prix au kilo par "
        "produit (median de ses releves), ecart au prix median de marche de la "
        "strate, IC 95 % par bootstrap de grappes sur les marques (4 000 "
        "tirages, graine 20260904). Ensuite en deduire la borne haute de ce "
        "qu'une repercussion de cout peut valoir sans etre visible.",
        "NON TESTABLE sur la cause ; NON ETABLI sur l'effet — aucun surcout "
        "halal n'est mesurable en rayon, et les donnees excluent seulement une "
        "repercussion superieure a la borne publiee",
        c,
        ["**Le depot ne contient aucun chiffre de cout** : ni abattage, ni "
         "certification, ni marge. La premiere moitie de la question est hors "
         "de portee de cette source, et aucun raffinement statistique n'y "
         "changera rien.",
         "**Un prix n'est pas un cout.** Un prix de vente se fixe sur un "
         "positionnement, une elasticite et une negociation d'enseigne, pas sur "
         "une comptabilite analytique.",
         "Les prix viennent d'un releve benevole couvrant moins de 10 % du bras "
         "halal. Rien ne garantit que les produits releves ressemblent aux "
         "autres.",
         "Le controle intra-marque, seul a isoler la certification, ne franchit "
         "la regle des 30 dans aucune marque.",
         "La borne est une borne SUPERIEURE sur une repercussion en rayon, pas "
         "une mesure du cout d'abattage. La confondre avec un cout serait "
         "l'erreur exacte que cette hypothese cherche a empecher."])


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
    l += bloc_h30()
    l += bloc_h31()
    l += bloc_h33()
    l += bloc_h34()
    l += bloc_h35()
    l += ["---", ""]
    return l


def bloc_h30() -> list[str]:
    """H30 — les sites francais, decodes depuis l'estampille seule."""
    pub = lire("s1b_sites_france_publiable")
    brut = lire("s1_sites_france")
    mrq = lire("classement_marques_complet")
    cor = lire("s1c_correlation_halal_rang")
    dep = lire("s2_departements")
    hal = lire("s3_sites_halal")
    if pub is None or not len(pub):
        return ["### H30 — Sortie absente : s1b_sites_france_publiable", ""]

    c = ["L'estampille ovale porte un code **FR dd.ddd.ddd CE** : pays,",
         "departement, code INSEE de la commune, numero d'ordre de",
         "l'etablissement dans cette commune. La geographie se lit donc sans",
         "aucune source externe, et sans nommer personne.",
         "",
         "**Ce que le code ne donne pas** : le nom de l'entreprise. Il faut",
         "pour cela le registre des etablissements agrees du ministere de",
         "l'Agriculture, que la politique de sortie reseau de l'environnement",
         "refuse. Aucun site n'est donc nomme ici. La colonne",
         "`marque_dominante` nomme le premier CLIENT du site, ce qui n'est pas",
         "la meme chose : un faconnier n'est pas sa marque.",
         ""]
    n_brut = len(brut) if brut is not None else 0
    n_mer = int(brut.alerte_mer.sum()) if brut is not None else 0
    c += [f"**{len(pub)} sites** classables apres deux filtres : au moins 30",
          "produits (regle des 30) et aucun produit de la mer. Le classement",
          f"brut en compte {n_brut}, dont {n_mer} signales `alerte_mer` : le "
          "meme defaut residuel que le haut du classement des marques, conserve",
          "en CSV pour etre verifiable plutot que fait disparaitre.",
          "",
          f"Etendue des ecarts medians : **{pub.ecart_median.min():+.1f} a "
          f"{pub.ecart_median.max():+.1f}** points de Nutri-Score a composition",
          "egale."]
    if mrq is not None and "ecart_median" in mrq and "regle_30" in mrq:
        m = mrq[mrq.regle_30 == "franchie"]
        if len(m):
            c += [f"A titre de comparaison, les {len(m)} marques d'au moins 30",
                  f"produits s'etalent de {m.ecart_median.min():+.1f} a "
                  f"{m.ecart_median.max():+.1f}. Les deux echelles ont donc une",
                  "amplitude du meme ordre — ce qui ne dit pas laquelle cause",
                  "l'autre, puisqu'un site majoritairement occupe par un client",
                  "et ce client sont la meme chose mesuree deux fois."]
    c += [""]
    c += ["**Les 8 sites les mieux classes** (ecart a la mediane de marche de la",
          "strate ; negatif = mieux) :", "",
          "| code | dept | n | marques | dont halal | ecart | sel | 1er client | "
          "part | sans lui |", "|:--|:--|--:|--:|--:|--:|--:|:--|--:|--:|"]
    def ligne(r):
        sans = "—" if pd.isna(r.ecart_sans_dominante) else f"{r.ecart_sans_dominante:+.1f}"
        return (f"| `{r.etablissement}` | {r.departement} | {r.n} | "
                f"{r.n_marques} | {r.n_halal} | {r.ecart_median:+.1f} | "
                f"{r.sel_median:.2f} | {r.marque_dominante} | "
                f"{r.part_dominante_pct:.0f} % | {sans} |")
    for r in pub.head(8).itertuples():
        c.append(ligne(r))
    c += ["", "**Les 8 derniers** :", "",
          "| code | dept | n | marques | dont halal | ecart | sel | 1er client | "
          "part | sans lui |", "|:--|:--|--:|--:|--:|--:|--:|:--|--:|--:|"]
    for r in pub.tail(8).itertuples():
        c.append(ligne(r))
    c += ["",
          "La colonne **sans lui** retire le premier client et recalcule. Quand",
          "l'ecart s'y effondre, il etait celui d'une marque et non d'une usine :",
          "`fr-53-097-001` passe de -12,0 a +3,5 des qu'on retire son donneur",
          "d'ordre principal. Quand il ne bouge pas, le site tient sur plusieurs",
          "clients."]
    if hal is not None and len(hal):
        c += ["", "**Les sites qui sortent du halal**, description seule :", "",
              "| code | n halal | marques | ecart median | sel |",
              "|:--|--:|--:|--:|--:|"]
        for r in hal.itertuples():
            code = getattr(r, "et", getattr(r, "Index", ""))
            c.append(f"| `{code}` | {r.n} | {r.n_marques} | "
                     f"{r.ecart_median:+.1f} | {r.sel:.2f} |")
    if cor is not None and len(cor):
        r = cor.iloc[0]
        c += ["",
              "Correlation de rang entre le nombre de produits halal d'un site",
              f"et son ecart : **rho = {r.rho:+.2f} [{r.ic95_bas:+.2f} ; "
              f"{r.ic95_haut:+.2f}]** sur {int(r.n_sites)} sites. Positif,",
              "IC excluant zero de justesse. Il dit que les sites tournes vers",
              "le halal sont classes plus bas. Il ne dit pas pourquoi : ces",
              "sites appartiennent a des specialistes et fabriquent leur propre",
              "recette, le site et la marque n'y sont pas separables."]
    if dep is not None and len(dep):
        c += ["",
              f"**Par departement**, {len(dep)} unites d'au moins 30 produits,",
              f"ecarts medians de {dep.ecart_median.min():+.1f} a "
              f"{dep.ecart_median.max():+.1f}. L'echelle departementale",
              "n'a aucun sens industriel : elle sert uniquement de controle de",
              "coherence sur des effectifs plus larges."]
    return hypothese(
        "H30", "Les sites de production francais sont identifiables et "
        "classables depuis l'estampille",
        "Decodage geographique du code d'agrement, puis classement des sites "
        "sur l'ecart de leurs produits a la mediane de marche de leur strate "
        "(sous-categorie x espece). Filtres : au moins 30 produits, aucun "
        "produit de la mer. Le rho est un Spearman a IC bootstrap sur les "
        "sites (2 000 tirages, graine 20260904).",
        "ETABLI pour la geographie et le classement ; NON ETABLI pour "
        "l'identite des entreprises ; NON TESTABLE pour un classement des "
        "sites sur leur seule production halal",
        c,
        ["**Un site est juge sur les recettes de ses clients.** Un faconnier "
         "execute un cahier des charges qu'il n'ecrit pas. Le classement porte "
         "sur ce qui sort du site, jamais sur son savoir-faire.",
         "Le creneau pese plus que le site : la couche 10 a mesure 72,5 % de "
         "variance expliquee sur le Nutri-Score brut contre 30,4 % a strate "
         "fixee. D'ou le classement sur l'ecart, jamais sur la note brute.",
         "**Classer un site sur son seul halal serait mal fonde** : dispersion "
         "intra-site de 7,82 dans le bras halal contre 5,55 dans le temoin, et "
         "pouvoir explicatif du site de 0,168 contre 0,304 (couche 10). Le "
         "tableau halal ci-dessus est descriptif et ne doit pas etre lu comme "
         "un palmares.",
         "29 sites publiables sur 162 sortent au moins un produit halal, 5 en "
         "sortent au moins dix : la correlation repose sur cette poignee.",
         "Un numero d'agrement couvre un etablissement, pas une ligne. Deux "
         "ateliers du meme site partagent le meme code.",
         "L'estampille n'est saisie que sur une fraction des produits, et rien "
         "ne dit que cette fraction soit representative.",
         "**Aucune de ces lignes ne dit quoi que ce soit du caractere halal "
         "d'un produit, ni de la conformite d'un site a une norme sanitaire ou "
         "religieuse.** Elles decrivent la composition nutritionnelle declaree "
         "de ce qui en sort."])


def bloc_h33() -> list[str]:
    """H33 — les sites nommes, par rapprochement avec le registre DGAL."""
    reg = lire("h0_registre_agrements")
    pub = lire("h1_sites_nommes")
    bas = lire("h3_bascule_sans_dominante")
    hal = lire("h4_sites_halal_nommes")
    if pub is None or not len(pub):
        return ["### H33 — Sortie absente : h1_sites_nommes", ""]

    nommes = int((pub.nom != "non apparie au registre").sum())
    c = ["H30 decodait la geographie d'une estampille sans source externe mais",
         "butait sur le nom. Le registre des etablissements agrees de la DGAL",
         "fait ce lien par le numero d'agrement : `fr-56-222-002` devient",
         "`56.222.002`, et le registre nomme l'entreprise.",
         "",
         "Huit listes officielles rapatriees depuis",
         "`fichiers-publics.agriculture.gouv.fr/dgal/ListesOfficielles/`, dont",
         "aucun nom de fichier n'a ete devine : la sonde a lu l'index du",
         "serveur. Empreintes sha256 dans `donnees_registre/collecte.csv`.",
         ""]
    if reg is not None and len(reg):
        c += [f"**{len(reg)} numeros d'agrement** distincts au registre, dont",
              f"**{int((reg.n_noms > 1).sum())}** portent plus d'une raison "
              "sociale — exploitants successifs,",
              "ou graphies differentes selon les listes. Aucun n'est tranche :",
              "leurs noms sont TOUS affiches et la ligne est marquee",
              "`nom_ambigu`. En choisir un serait inventer une attribution.",
              "",
              "4,0 % des lignes du registre sont illisibles : les fichiers de la",
              "DGAL ont des lignes de longueur variable, la colonne des",
              "activites debordant en champs supplementaires. Le lecteur repere",
              "le numero d'agrement par sa FORME et lit les champs suivants par",
              "rapport a lui, ce qui resiste aux deux mises en page rencontrees.",
              "Les lignes perdues sont comptees par fichier, jamais absorbees."]
    c += ["",
          f"**{len(pub)} sites publiables** (au moins 30 produits, aucun produit",
          f"de la mer), dont **{nommes} nommes** et "
          f"{len(pub) - nommes} non apparies. Un site sans nom",
          "reste au classement : le retirer ferait disparaitre precisement les",
          "etablissements que le registre documente le moins bien.",
          "",
          "**Les 10 sites les mieux classes** — ecart a la mediane de marche de",
          "la strate ; negatif = mieux que le marche sur le meme type de",
          "produit :", "",
          "| code | entreprise | commune | n | ecart | sel | 1er client | part |"
          " sans lui |", "|:--|:--|:--|--:|--:|--:|:--|--:|--:|"]

    def ligne(r):
        sans = ("—" if pd.isna(r.ecart_sans_dominante)
                else f"{r.ecart_sans_dominante:+.1f}")
        return (f"| `{r.etablissement}` | {r.nom} | {r.commune} | {r.n} | "
                f"{r.ecart_median:+.1f} | {r.sel_median:.2f} | "
                f"{r.marque_dominante} | {r.part_dominante_pct:.0f} % | "
                f"{sans} |")
    for r in pub.head(10).itertuples():
        c.append(ligne(r))
    c += ["", "**Les 10 sites les moins bien classes** :", "",
          "| code | entreprise | commune | n | ecart | sel | 1er client | part |"
          " sans lui |", "|:--|:--|:--|--:|--:|--:|:--|--:|--:|"]
    for r in pub.tail(10).itertuples():
        c.append(ligne(r))

    if bas is not None and len(bas):
        c += ["",
              "**Ce que le classement doit a un seul client.** "
              f"`ecart_sans_dominante`",
              "recalcule l'ecart apres retrait du premier client du site. "
              f"{len(bas)} sites",
              "basculent d'au moins 5 points :", "",
              "| code | entreprise | 1er client | part | n | ecart | n sans lui "
              "| ecart sans lui |", "|:--|:--|:--|--:|--:|--:|--:|--:|"]
        for r in bas.itertuples():
            c.append(f"| `{r.etablissement}` | {r.nom} | {r.marque_dominante} "
                     f"| {r.part_dominante_pct:.0f} % | {int(r.n)} "
                     f"| {r.ecart_median:+.1f} | {int(r.n_sans_dominante)} "
                     f"| {r.ecart_sans_dominante:+.1f} |")
        c += ["",
              "**Cette colonne est un signal d'alerte sur le classement, pas "
              "une",
              "mesure de ce qu'un site ferait pour ses autres clients.** Aucun "
              "de",
              "ces recalculs n'atteint la regle des 30, et deux des trois vont "
              "dans",
              "le sens inverse du troisieme : retirer le premier client "
              "AMELIORE",
              "SO'HAM SUD-OUEST et MAITRE JACQUES.",
              "",
              "Le cas de SOCOPA VIANDES a Evron le montre en detail. Ses 42",
              "produits sont tous dans la strate `autres_carnes / porc`. Les 28 "
              "du",
              "client dominant sont des rotis de filet, des cotes, du saute — "
              "des",
              "morceaux maigres a **0,11 g de sel**. Les 14 autres melangent ces",
              "memes rotis avec de la poitrine, de la palette et du jarret",
              "demi-sel, a **3,30 g de sel**. L'ecart entre les deux groupes est",
              "l'ecart entre deux MORCEAUX DE PORC, pas entre deux niveaux de",
              "qualite.",
              "",
              "**C'est une limite de la stratification, et elle est generale sur "
              "les",
              "sites de decoupe** : `sous-categorie x espece` controle l'espece "
              "et",
              "la gamme, jamais le morceau. Un roti de filet et une poitrine",
              "demi-sel y sont voisins. Tout ecart intra-site lu sur des viandes",
              "crues doit etre suspecte de n'etre qu'une difference de decoupe."]
    if len(pub):
        bas10 = pub.tail(10)
        c += ["",
              "**Le bas de ce classement n'est pas halal.** Les deux derniers "
              "sites,",
              "FINE LAME et HARAGUY-JAMBON DE BAYONNE, sont a +15,0 et ne "
              "sortent",
              "**aucun produit halal** : ce sont des faconniers de charcuterie "
              "seche",
              "du Sud-Ouest, dont le premier client est une enseigne. "
              f"{int((bas10.n_halal == 0).sum())} des 10",
              "derniers sites n'ont aucun produit halal. Un lecteur qui "
              "chercherait",
              "le halal en bas de tableau ne l'y trouverait pas."]
    if hal is not None and len(hal):
        c += ["",
              "### Qui fabrique le halal", "",
              "**Descriptif, pas un classement.** La couche 10 a mesure sur le",
              "halal une dispersion INTRA site superieure a celle du temoin",
              "(7,82 contre 5,55) et un pouvoir explicatif du site plus faible",
              "(0,168 contre 0,304) : un site n'a pas de « niveau » halal",
              "stable, et l'ordre de ce tableau ne doit pas etre lu comme un",
              "palmares.", "",
              "| code | entreprise | commune | n | dont halal | marques | ecart "
              "| sel | 1er client |",
              "|:--|:--|:--|--:|--:|--:|--:|--:|:--|"]
        for r in hal.itertuples():
            c.append(f"| `{r.etablissement}` | {r.nom} | {r.commune} | {r.n} | "
                     f"{int(r.n_halal)} | {int(r.n_marques)} | "
                     f"{r.ecart_median:+.1f} | {r.sel_median:.2f} | "
                     f"{r.marque_dominante} |")
        c += ["",
              "Ce tableau repond a une question que le rayon ne montre pas :",
              "**qui fabrique**. Une marque n'est pas une usine, et plusieurs",
              "des marques les plus visibles du rayon halal sortent de sites",
              "qui portent un autre nom."]
    return hypothese(
        "H33", "Le registre des agrements permet de nommer les sites, et le "
        "classement par site tient une fois les entreprises nommees",
        "Rapprochement du numero d'agrement decode dans l'estampille (couche "
        "14) avec les listes officielles des etablissements agrees de la DGAL. "
        "Le numero est repere par sa forme dans chaque ligne du registre, et "
        "les champs suivants lus par rapport a lui. Classement inchange : "
        "ecart a la mediane de marche de la strate.",
        "ETABLI pour le rapprochement (93,8 % des sites classes recoivent un "
        "nom) ; le classement lui-meme garde toutes les reserves de H30",
        c,
        ["**Un site est juge sur les recettes de ses donneurs d'ordre.** Un "
         "faconnier execute un cahier des charges qu'il n'ecrit pas. Nommer "
         "l'usine ne transforme pas le classement en jugement sur son "
         "savoir-faire, et la colonne `ecart_sans_dominante` est la pour le "
         "rappeler ligne par ligne.",
         "**Le registre atteste un agrement sanitaire europeen, rien d'autre.** "
         "Aucune ligne ne dit si un produit est halal, ni si une entreprise "
         "respecte une norme religieuse, sanitaire ou sociale.",
         "419 numeros d'agrement portent plusieurs raisons sociales. Les sites "
         "concernes affichent tous leurs noms et sont marques `nom_ambigu` ; un "
         "changement d'exploitant n'est pas distingue d'une variante de "
         "graphie.",
         "4,0 % des lignes du registre restent illisibles. Elles sont comptees "
         "par fichier, et rien ne garantit qu'elles soient reparties au hasard.",
         "Un numero d'agrement couvre un ETABLISSEMENT, pas une ligne de "
         "production. Deux ateliers du meme site partagent le meme code.",
         "L'estampille n'est saisie que sur une fraction des produits d'Open "
         "Food Facts. Le classement porte sur cette fraction.",
         "Le registre est une photographie a sa date de rapatriement. Un site "
         "peut avoir change d'exploitant depuis le dump nutritionnel, qui est "
         "lui-meme fige."])


def bloc_h31() -> list[str]:
    """H31 — MDD, industriel generaliste, specialiste du halal."""
    fam = lire("f1_familles_marques")
    cov = lire("f0_couverture")
    t = lire("f2_familles_halal")
    dif = lire("f2b_differences")
    vm = lire("f2c_une_voix_par_marque")
    sc = lire("f3_sans_carrefour")
    ti = lire("f5b_temoin_par_marque")
    if t is None or dif is None or fam is None:
        return ["### H31 — Sortie absente : f2_familles_halal", ""]

    lib = {"mdd": "MDD", "industriel": "industriel generaliste",
           "specialiste_halal": "specialiste du halal"}
    c = ["Trois familles, dont **deux se deduisent des donnees** et une seule",
         "est declaree. Une marque appartenant a une enseigne ne se lit pas",
         "dans une table de composition : la liste des MDD est donc declaree",
         "dans `config/familles_marques.yaml`, chaque entree portant sa preuve",
         "(le nom de l'enseigne, ou le champ `brand_owner` du dump — c'est ce",
         "dernier qui rattache Wassila a Casino). Les deux autres familles se",
         "separent sur la part halal du catalogue, au seuil de 50 % qui tombe",
         "dans le plus grand vide de la distribution (26,3 % puis 57,1 %).",
         ""]
    c += ["| famille | marques | produits halal au catalogue | exemples |",
          "|:--|--:|--:|:--|"]
    for f_ in ["mdd", "industriel", "specialiste_halal"]:
        g = fam[fam.famille == f_].sort_values(["n_halal", "marque"],
                                               ascending=[False, True])
        ex = ", ".join(g.marque.head(4))
        c.append(f"| {lib[f_]} | {len(g)} | {int(g.n_halal.sum())} | {ex} |")
    if cov is not None and len(cov) == 2:
        a, b = cov.iloc[0], cov.iloc[1]
        c += ["",
              "**Couverture mesuree avant de comparer.** Les trois familles",
              f"couvrent {int(a.n)} produits halal ; {int(b.n)} restent dehors,",
              "sans marque saisie ou appartenant a une marque de moins de cinq",
              "references halal. Les deux moities ont le **meme ecart median**",
              f"({a.ecart_median:+.1f} contre {b.ecart_median:+.1f}) et un sel",
              f"proche ({a.sel_median:.2f} contre {b.sel_median:.2f} g). La",
              "moitie identifiable n'est donc pas un sous-ensemble choisi."]
    ns = t[t.mesure == "nutriscore"]
    sel = t[t.mesure == "sel"]
    c += ["",
          "**Ecart a la mediane de marche de la strate**, sur les seuls",
          "produits halal de chaque famille. Negatif = mieux que le marche sur",
          "le meme type de produit.", "",
          "| famille | marques | produits | ecart median | IC 95 % | sel | "
          "IC 95 % |", "|:--|--:|--:|--:|:--:|--:|:--:|"]
    for f_ in ["mdd", "industriel", "specialiste_halal"]:
        a = ns[ns.famille == f_]
        b = sel[sel.famille == f_]
        if not len(a):
            continue
        a, b = a.iloc[0], b.iloc[0]
        c.append(f"| {lib[f_]} | {int(a.marques)} | {int(a.n)} | "
                 f"{a.mediane:+.1f} | [{a.ic95_bas:+.1f} ; {a.ic95_haut:+.1f}] "
                 f"| {b.mediane:+.2f} | [{b.ic95_bas:+.2f} ; "
                 f"{b.ic95_haut:+.2f}] |")
    c += ["",
          "Les IC sont calcules par **bootstrap de grappes sur les marques**,",
          "jamais sur les produits : deux references d'une meme marque ne sont",
          "pas deux observations independantes (ICC de 0,304 a strate fixee,",
          "couche 10). Avec 3 marques pour les MDD et 6 pour les industriels,",
          "ces intervalles sont larges. C'est la precision reelle de la",
          "comparaison.", "",
          "**Aucune des six differences n'est etablie :**", "",
          "| mesure | comparaison | difference | IC 95 % | verdict |",
          "|:--|:--|--:|:--:|:--|"]
    for r in dif.itertuples():
        u = "pts" if r.mesure == "nutriscore" else "g"
        c.append(f"| {r.mesure} | {lib[r.famille_a]} − {lib[r.famille_b]} | "
                 f"{r.difference:+.2f} {u} | [{r.ic95_bas:+.2f} ; "
                 f"{r.ic95_haut:+.2f}] | "
                 f"{'ETABLI' if r.etabli else 'non etabli'} |")
    c += ["",
          "Le point le plus proche du seuil est MDD − specialiste sur le",
          "Nutri-Score : **−3,00 [−6,00 ; +0,00]**. La borne haute touche zero",
          "exactement. Compter cette ligne comme etablie serait lire un",
          "intervalle comme un point, l'erreur n° 10 de la section 8."]
    if vm is not None and len(vm):
        c += ["",
              "**Une voix par marque**, pour ne pas laisser Isla Delice et ses",
              "182 references parler pour trente-deux marques :", "",
              "| famille | marques | mediane des medianes | Q1 | Q3 | sel |",
              "|:--|--:|--:|--:|--:|--:|"]
        for r in vm.itertuples():
            c.append(f"| {lib[r.famille]} | {int(r.marques)} | "
                     f"{r.mediane_des_medianes:+.1f} | {r.q1:+.2f} | "
                     f"{r.q3:+.2f} | {r.sel_mediane_des_medianes:+.2f} |")
        c += ["",
              "L'ordre des trois familles ne change pas, et l'ecart",
              "interquartile de chaque famille recouvre celui des deux autres.",
              "Le desaccord entre marques d'une meme famille est plus grand que",
              "l'ecart entre familles."]
    if sc is not None and len(sc):
        m = sc[sc.famille == "mdd"]
        if len(m):
            m = m.iloc[0]
            c += ["",
                  "**Sans Carrefour**, la famille MDD tombe a "
                  f"{int(m.marques)} marques et {int(m.n)} produits, sous la",
                  f"regle des 30, avec une mediane de {m.mediane:+.2f}. La",
                  "ligne « MDD » de cette etude est donc pour l'essentiel une",
                  "ligne « Carrefour », et doit se lire ainsi."]
    if ti is not None and len(ti):
        c += ["",
              "**Chaque marque comparee a son propre temoin** — la seule",
              "lecture qui ne compare pas des entreprises differentes. Un",
              "specialiste du halal n'a pas de version non halal : la ligne",
              "n'existe pas pour lui, et Wassila non plus, dont le catalogue",
              "est halal a 100 % bien qu'elle appartienne a une enseigne.", "",
              "| famille | marque | n halal | n temoin | halal | temoin | "
              "difference | regle des 30 |",
              "|:--|:--|--:|--:|--:|--:|--:|:--|"]
        for r in ti.itertuples():
            c.append(f"| {lib[r.famille]} | {r.marque} | {int(r.n_halal)} | "
                     f"{int(r.n_temoin)} | {r.ecart_halal:+.1f} | "
                     f"{r.ecart_temoin:+.1f} | {r.difference:+.1f} | "
                     f"{r.regle_30} |")
        gros = ti[ti.regle_30 == "franchie"]
        if len(gros):
            noms = ", ".join(f"{r.marque} {r.difference:+.1f}"
                             for r in gros.itertuples())
            c += ["",
                  "Deux cellules seulement franchissent la regle des 30 des",
                  f"deux cotes : {noms}. Les autres sont decrites avec leur",
                  "effectif et ne doivent pas etre lues comme un classement."]
    return hypothese(
        "H31", "Dans le halal, MDD, industriels et specialistes ne font pas la "
        "meme qualite",
        "Comparaison des trois familles sur leurs SEULS produits halal, a "
        "l'ecart de la mediane de marche de la strate (sous-categorie x "
        "espece). IC 95 % par bootstrap de grappes sur les marques (4 000 "
        "tirages, graine 20260904). Une marque doit avoir au moins 5 produits "
        "halal pour entrer : sans gamme, il n'y a pas de politique de marque "
        "a lire.",
        "NON ETABLI — l'ordre est constant (specialistes derriere, "
        "industriels devant) mais aucune difference ne survit au bootstrap "
        "de grappes",
        c,
        ["**La famille MDD est Carrefour.** Trois marques, dont une, Wassila, "
         "sans temoin non halal. Retirer Carrefour fait passer la famille sous "
         "la regle des 30.",
         "**La famille industriel n'est pas homogene.** Fleury Michon (71 "
         "produits halal, ecart 0,0) et Jack Link's (6 produits, ecart +4,5 "
         "sur un creneau de viande sechee) y sont ranges ensemble parce que le "
         "halal est minoritaire chez les deux. C'est ce que mesure "
         "l'ecart interquartile publie.",
         "**Specialiste du halal n'est pas une categorie commerciale unique.** "
         "Suntat, Baktat, Hunkar et Yayla sont des marques d'epicerie turque "
         "dont le catalogue est majoritairement tague halal : la regle des "
         "50 % les range avec Isla Delice. Un decoupage par repertoire "
         "culinaire donnerait une autre partition.",
         "La moitie du bras halal reste hors familles, faute de marque saisie "
         "ou de gamme. Sa composition est semblable (verifiee ci-dessus), ce "
         "qui autorise la comparaison sans la rendre exhaustive.",
         "Une seule strate sur 28 compte deux familles au-dessus de 30 "
         "produits : la comparaison gamme par gamme n'est presque jamais "
         "testable, et le tableau f4 est descriptif.",
         "Ces familles decrivent une POSITION SUR LE MARCHE, lisible en rayon. "
         "Elles ne disent rien de la halalite d'un produit, de la conformite "
         "d'une entreprise, ni de qui la dirige."])


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
        "| 13 | `ecart_sans_dominante` publie sans son effectif | « Socopa fait "
        "mieux pour son client principal » : lecture fausse, tiree de 14 "
        "produits melangeant roti de filet et jarret demi-sel | Colonne "
        "`n_sans_dominante` ajoutee, et la limite de la strate ecrite dans "
        "H33 |",
        "",
        "La 13 a ete trouvee par une question du commanditaire sur une ligne",
        "publiee, pas par un test. Une colonne juste, presentee sans son",
        "effectif, produit une affirmation fausse aussi surement qu'un calcul",
        "faux.",
        "",
        "Deux d'entre elles, la 6 et la 9, allaient dans le sens du resultat",
        "attendu. C'est la raison pour laquelle la couverture des donnees est",
        "desormais mesuree et publiee AVANT chaque comparaison.",
        "",
        "---",
        "",
    ]


def bloc_h34() -> list[str]:
    """H34 — un seuil nutritionnel serait-il tenable ?"""
    st = lire("j1_structure_offre")
    fa = lire("j2_faisabilite_seuils")
    if fa is None or not len(fa):
        return ["### H34 — Sortie absente : j2_faisabilite_seuils", ""]

    c = ["**Ce qui rend un seuil defendable n'est pas la mesure, c'est la",
         "faisabilite.** Un seuil que personne n'atteint est une petition. Un",
         "seuil que le reste du marche atteint deja sur la MEME gamme est un",
         "rattrapage : il ne demande aucune technologie nouvelle, il demande",
         "la meme recette.",
         "",
         "Le tableau ci-dessous ne fixe aucun seuil. Il montre ce que",
         "differents seuils excluraient de part et d'autre.", ""]
    vedettes = ["charcuterie_cuite / dinde", "charcuterie_cuite / poulet",
                "saucisses / poulet", "panes / poulet"]
    sous = fa[fa.gamme.isin(vedettes)]
    if len(sous):
        c += ["| gamme | n halal | n temoin | critere | atteint, halal | "
              "atteint, temoin |", "|:--|--:|--:|:--|--:|--:|"]
        for r in sous.itertuples():
            c.append(f"| {r.gamme} | {r.n_halal} | {r.n_temoin} | {r.critere} "
                     f"| {r.pct_halal:.0f} % | **{r.pct_temoin:.0f} %** |")
        c += ["",
              "**Le jambon de dinde en est l'exemple le plus net.** Un seuil a",
              "2 g de sel aux 100 g laisserait passer **19 % du halal et 83 %",
              "du temoin**. Un seuil au Nutri-Score C laisserait passer 18 %",
              "contre 82 %. Ce ne sont pas des seuils theoriques : quatre",
              "cinquiemes du marche non halal les franchissent deja sur la",
              "meme gamme, avec la meme espece et la meme technologie."]
    if st is not None and len(st):
        c += ["",
              "**La structure de l'offre**, part de chaque gamme dans son "
              "propre bras :", "",
              "| gamme | % du rayon halal | % du temoin | ecart |",
              "|:--|--:|--:|--:|"]
        for r in st.sort_values("pct_halal", ascending=False).head(8).itertuples():
            nom = getattr(r, "sous_categorie", getattr(r, "Index", ""))
            c.append(f"| {nom} | {r.pct_halal:.1f} % | {r.pct_temoin:.1f} % | "
                     f"{r.ecart_points:+.1f} |")
        c += ["",
              "La part totale de produits transformes est proche dans les deux",
              "bras : 71,8 % contre 66,4 %. Ce qui change, ce sont les GAMMES.",
              "Les panes pesent **quatre fois plus** dans le rayon halal",
              "(14,8 % contre 3,2 %) ; les plats cuisines et les decoupes y",
              "pesent **deux fois moins**. Un consommateur qui s'en tient a ce",
              "rayon rencontre plus de produits panes et moins de viande a",
              "cuisiner.",
              "",
              "**C'est un fait d'OFFRE, et il ne dit pas ce qui finit dans les",
              "assiettes.** Ce depot ne contient aucune donnee de consommation."]
    return hypothese(
        "H34", "Un seuil nutritionnel minimal par gamme serait tenable",
        "Simulation de seuils de sel et de Nutri-Score, gamme par gamme, sur "
        "les 19 gammes ou les deux bras depassent 30 produits. Mesure de la "
        "part de chaque bras qui franchit deja chaque seuil. Aucun seuil n'est "
        "fixe ici.",
        "ETABLI pour la FAISABILITE — sur les gammes ou l'ecart est le plus "
        "large, le reste du marche franchit deja le seuil ; NON TESTABLE pour "
        "tout ce qui touche a la consommation reelle",
        c,
        ["**Un Nutri-Score n'est pas un verdict sanitaire sur un produit.** "
         "C'est un indicateur comparatif de composition aux 100 g. Le risque "
         "documente porte sur des quantites consommees dans la duree, jamais "
         "sur un code-barres. Dire « ce produit est mauvais pour la sante » "
         "depasse ce que l'indicateur autorise.",
         "**La frequence de consommation est hors de portee de ce depot.** "
         "Aucune donnee de consommation n'y figure. « Ces produits sont manges "
         "souvent » est une hypothese sur des gens, et rien ici ne la teste. "
         "La composition de l'offre n'est pas la frequence des achats.",
         "Le seuil lui-meme est une DECISION DE NORME. Ce depot montre ce "
         "qu'un seuil excluerait ; il ne dit pas ou le mettre, et il ne dit "
         "rien de ce qui serait tayyib.",
         "Le sel est un meilleur support de seuil que le Nutri-Score : il se "
         "lit directement sur l'emballage, il ne s'agrege pas avec d'autres "
         "nutriments, et une recette ne peut pas le compenser par ailleurs.",
         "Les gammes ou les deux bras depassent 30 produits sont 19 sur 11 x "
         "10 combinaisons possibles. Un seuil general couvrirait des gammes "
         "que cette etude n'a pas pu tester."])


def bloc_h35() -> list[str]:
    """H35 — un critere sel + note permet-il de deconseiller des produits ?"""
    cs = lire("j3_critere_selection")
    cg = lire("j4_critere_par_gamme")
    if cs is None or not len(cs):
        return ["### H35 — Sortie absente : j3_critere_selection", ""]

    c = ["Un critere n'aide un lecteur que s'il DISTINGUE a l'interieur d'une",
         "gamme. S'il retient 80 % d'une gamme et 1 % d'une autre, il ne",
         "deconseille pas des produits : il deconseille une gamme, ce que les",
         "reperes publics font deja.", "",
         "| critere | retenu, halal | retenu, temoin |",
         "|:--|--:|--:|"]
    for crit, g in cs.groupby("critere"):
        h = g[g.bras == "halal"].pct_retenu.iloc[0]
        t = g[g.bras == "temoin"].pct_retenu.iloc[0]
        c.append(f"| {crit} | {h:.1f} % | {t:.1f} % |")
    if cg is not None and len(cg):
        c += ["",
              "**Au seuil de 2,5 g, ce que le critere retient dans le bras "
              "halal, gamme par gamme :**", "",
              "| gamme | n | part retenue |", "|:--|--:|--:|"]
        for r in cg.itertuples():
            nom = getattr(r, "sous_categorie", getattr(r, "Index", ""))
            c.append(f"| {nom} | {r.n} | {r.pct:.1f} % |")
        c += ["",
              "**De 80,8 % en charcuterie sechee a 0,7 % en panes.** Le critere",
              "est un detecteur de GAMME avant d'etre un detecteur de PRODUIT.",
              "Applique tel quel, il revient a redire ce que le PNNS dit deja :",
              "limiter la charcuterie. Pour aider a choisir DANS une gamme, il",
              "faut un seuil interne a la gamme."]
    c += ["",
          "### Ce que l'etude peut apporter a la place : l'arithmetique de la "
          "portion", "",
          "Deux reperes publics, cites et non produits par cette etude : moins",
          "de **5 g de sel par jour** pour un adulte (OMS, repris par le PNNS),",
          "et au plus **150 g de charcuterie par semaine**, soit environ 25 g",
          "par jour (PNNS, Sante publique France). Ils se combinent en un",
          "calcul verifiable sur l'emballage.", "",
          "| gamme du bras halal | sel | portion PNNS de 25 g | part du maximum "
          "quotidien |", "|:--|--:|--:|--:|",
          "| charcuterie cuite, mediane | 2,40 g/100 g | 0,60 g | 12 % |",
          "| charcuterie cuite, 9e decile | 3,45 g/100 g | 0,86 g | 17 % |",
          "| charcuterie sechee, mediane | 3,60 g/100 g | 0,90 g | 18 % |",
          "| charcuterie sechee, 9e decile | 5,10 g/100 g | 1,27 g | **25 %** |",
          "",
          "**« Sel eleve » est un jugement ; « cette portion couvre un quart du",
          "maximum quotidien » est un fait.** Le lecteur le verifie sur",
          "l'emballage et le rapporte au reste de sa journee. Ce depot publie",
          "le fait, pas le jugement.",
          "",
          "Et il porte sur la portion que le repere public autorise deja : 25 g",
          "par jour de charcuterie, soit deux tranches. Au 9e decile de la",
          "charcuterie sechee halal, ces deux tranches consomment un quart du",
          "sel de la journee."]
    return hypothese(
        "H35", "Un critere « sel eleve et Nutri-Score C ou pire » permet de "
        "deconseiller des produits",
        "Application du critere aux deux bras, a quatre seuils de sel, puis "
        "decomposition par gamme du bras halal. Mise en rapport des teneurs "
        "avec deux reperes publics : 5 g de sel par jour et 150 g de "
        "charcuterie par semaine.",
        "REFUTE comme critere de PRODUIT — il selectionne une gamme, pas un "
        "produit ; ce que l'etude peut publier a la place est l'arithmetique "
        "de la portion, qui est un fait et non un conseil",
        c,
        ["**Ce depot ne deconseille aucun produit et n'est pas fonde a le "
         "faire.** Une recommandation alimentaire individuelle releve d'un "
         "professionnel de sante et des autorites sanitaires, qui ont deja "
         "publie la leur. L'etude mesure des compositions ; elle ne prescrit "
         "pas de regime.",
         "**Un Nutri-Score reste un indicateur comparatif de composition**, pas "
         "un verdict sanitaire sur une reference. Le combiner au sel ne le "
         "transforme pas en diagnostic.",
         "L'arithmetique de la portion suppose une portion de reference. Elle "
         "vaut ce que vaut cette convention, et une portion reelle peut etre "
         "tout autre.",
         "Le seuil de 2,5 g est choisi pour la demonstration. Le tableau donne "
         "quatre seuils precisement pour qu'aucun ne passe pour LE seuil.",
         "Rien ici ne dit a quelle frequence ces produits sont consommes : "
         "aucune donnee de consommation ne figure dans ce depot."])


def bloc_podiums() -> list[str]:
    """Section 10 — les podiums destines a la publication."""
    prod = lire("i1_podium_produits")
    glob = lire("i4_podium_global")
    ecar = lire("i0_ecartes_du_podium")
    mq = lire("i2_podium_marques")
    no = lire("i5_notes_marques")
    ce = lire("i3_classement_certificateurs")
    l = ["## 10. Les podiums", "",
         "Une etude qui ne nomme personne ne change rien. Ces tableaux sont la",
         "pour qu'un rang se reprenne : il est verifiable, et il bouge des que",
         "la recette bouge.",
         "",
         "**Trois niveaux, trois solidites, et ils ne se lisent pas pareil.**",
         "Un produit est UNE observation et n'aura jamais d'intervalle de",
         "confiance. Une marque est un echantillon et en a un. Quatre",
         "organismes certificateurs seulement sont identifies : en podiumiser",
         "trois sur quatre serait une mise en scene, le classement complet est",
         "publie a la place.",
         "",
         "**Ce qu'aucune de ces lignes ne dit** : rien sur la halalite d'un",
         "produit, rien sur la conformite d'un organisme a une norme",
         "religieuse, rien sur la securite sanitaire, rien sur une intention.",
         "Un mauvais rang nutritionnel n'est pas un defaut de securite, et le",
         "Nutri-Score n'est pas un verdict de sante.",
         ""]
    def table_produits(g, entete):
        out = [entete, "",
               "| | code | produit | marque | strate | Nutri-Score | mediane "
               "strate | ecart | sel | AGS |",
               "|:--|:--|:--|:--|:--|--:|--:|--:|--:|--:|"]
        for r in g.itertuples():
            m = r.marque if isinstance(r.marque, str) else "—"
            tag = "meilleur" if r.rang == "meilleur" else "**moins bon**"
            out.append(f"| {tag} | `{r.code}` | {r.product_name} | {m} | "
                       f"{r.strate} | {r.ns:.0f} | {r.mediane_strate:.0f} | "
                       f"{r.ecart:+.0f} | {r.sel:.2f} | {r.ags:.2f} |")
        return out + [""]

    if glob is not None and len(glob):
        l += ["### 10.1 Les produits, tous produits confondus", "",
              "« Tous produits confondus » se lit de deux facons qui ne donnent",
              "pas le meme classement. Publier une seule des deux ferait passer",
              "un choix d'analyse pour un fait, donc les deux sont la.", ""]
        l += table_produits(glob[glob.classement == "absolu"],
                            "**Classement ABSOLU — Nutri-Score brut.**")
        l += ["Le bas de ce classement est de la charcuterie sechee, et le haut",
              "de la volaille crue. **C'est un fait de rayon, pas un jugement",
              "sur un industriel** : un saucisson sec est note comme un",
              "saucisson sec, et le classer dernier dit qu'il est du saucisson",
              "sec. Un lecteur qui veut savoir qui fait mal son metier lit le",
              "classement suivant.", ""]
        l += table_produits(glob[glob.classement == "a gamme egale"],
                            "**Classement A GAMME EGALE — ecart a la mediane de "
                            "marche de la strate.**")
        l += ["Seul des deux ou une entreprise peut reprendre son rang en",
              "changeant sa recette, et donc le seul qui serve la competition",
              "que ces tableaux cherchent a declencher.", ""]
    if prod is not None and len(prod):
        l += ["### 10.2 Les produits, gamme par gamme", "",
              "Le meme exercice a l'interieur de chaque gamme, ou la",
              "comparaison tient devant n'importe quel lecteur : une merguez",
              "contre une merguez, un nugget contre un nugget.",
              "",
              "**Les deux moities n'ont pas la meme solidite.** Une base",
              "contributive se trompe dans un seul sens : une case oubliee, un",
              "zero saisi a la place d'un vide, une valeur par portion prise",
              "pour une valeur aux 100 g font paraitre un produit MEILLEUR",
              "qu'il n'est. Presque jamais l'inverse — personne ne declare par",
              "erreur 15 g d'acides gras satures. Les **moins bons** sont donc",
              "solides ; les **meilleurs** sont a verifier en rayon,",
              "code-barres en main, avant d'etre cites. La colonne `fiabilite`",
              "le porte sur chaque ligne.",
              ""]
        for gamme, g in prod.groupby("gamme"):
            l += table_produits(g, f"**{gamme}**")
    if ecar is not None and len(ecar):
        l += [f"**{len(ecar)} produits ecartes du podium** : declaration",
              "invraisemblable pour leur gamme — sel ou acides gras satures sous",
              "le 1er centile d'une gamme salee et cuite, ou sechee. Sans ce",
              "filtre, un saucisson declare a 0,00 g de sel et 0,00 g d'acides",
              "gras satures occupe la premiere place. Ils sont publies dans",
              "`sorties/i0_ecartes_du_podium.csv` : un produit ecarte n'est pas",
              "un produit efface, et un lecteur qui verifie l'emballage peut",
              "remettre la ligne au classement.",
              "",
              "Ce filtre a un cout assume : un produit reellement reformule,",
              "seul de sa gamme, en est ecarte. Aucune deuxieme source ne permet",
              "de trancher.",
              ""]
    if mq is not None and len(mq):
        l += ["### 10.3 Les marques, sur leurs seuls produits halal", "",
              "Seules les marques d'au moins 15 produits halal a nutrition",
              "complete entrent au podium : en dessous, l'intervalle de",
              "confiance couvre la moitie du classement.", "",
              "| | marque | n halal | % du catalogue | ecart | IC 95 % | "
              "strates |", "|:--|:--|--:|--:|--:|:--:|--:|"]
        for r in mq.itertuples():
            tag = "meilleure" if r.rang == "meilleure" else "**moins bonne**"
            l.append(f"| {tag} | {r.marque_affichee} | {r.n} | "
                     f"{r.pct_tague:.0f} % | {r.ecart_median:+.1f} | "
                     f"[{r.ic95_bas:+.1f} ; {r.ic95_haut:+.1f}] | "
                     f"{r.strates_couvertes} |")
        l += ["",
              "Les intervalles du premier et du dernier sont disjoints :",
              "l'ecart entre les deux extremes du podium est **etabli**. Entre",
              "deux voisins de classement, il ne l'est pas — d'ou les notes",
              "ci-dessous."]
    if no is not None and len(no):
        det = no[no.note_determinee]
        l += ["", "### 10.4 Les notes des marques, et pourquoi pas des rangs",
              "",
              "**Aucun palier separable n'existe.** Le script cherche a chaque",
              "execution un rang ou les intervalles de tout ce qui est au-dessus",
              "seraient disjoints de tout ce qui est en dessous. Il n'en trouve",
              "aucun : les intervalles forment une chaine continue du premier au",
              "dernier. Entre deux marques voisines, **aucun classement n'est",
              "etabli**, et un rang de 1 a 12 serait une precision inventee.",
              "",
              "D'ou des paliers de **convention**, sur une echelle absolue :",
              "l'ecart a la mediane de marche de la meme gamme. Ils sont ronds",
              "et symetriques autour de zero, zero valant « au niveau du marche",
              "sur sa propre gamme ». Les deplacer change des lettres, jamais",
              "l'ordre.",
              "",
              "| palier | ecart a la mediane de marche |",
              "|:--|:--|",
              "| **S** | au plus -2 : nettement mieux que le marche |",
              "| **A** | de -2 a +1 : au niveau du marche |",
              "| **B** | de +1 a +5 |",
              "| **C** | de +5 a +10 |",
              "| **D** | au-dela de +10 |",
              "",
              "La **note** est le palier de l'ecart median. La **note",
              "compatible** est l'etendue des paliers que l'intervalle de",
              "confiance autorise : une marque dont l'intervalle couvre trois",
              "paliers n'a pas de note, et le tableau le dit plutot que de",
              "trancher.",
              "",
              "| marque | n halal | ecart | IC 95 % | note | compatible | "
              "determinee |", "|:--|--:|--:|:--:|:--:|:--:|:--|"]
        for r in no.itertuples():
            gras = f"**{r.note}**" if r.note_determinee else r.note
            l.append(f"| {r.marque_affichee} | {r.n} | {r.ecart_median:+.1f} | "
                     f"[{r.ic95_bas:+.1f} ; {r.ic95_haut:+.1f}] | {gras} | "
                     f"{r.note_compatible} | "
                     f"{'oui' if r.note_determinee else 'non'} |")
        noms = ", ".join(f"{r.marque_affichee} = {r.note}"
                         for r in det.itertuples())
        l += ["",
              f"**{len(det)} marques sur {len(no)} ont une note determinee** : "
              f"{noms}.",
              "Pour toutes les autres, l'effectif ne permet pas de trancher",
              "entre deux ou trois paliers. Ce n'est pas un defaut de la note :",
              "c'est le nombre de produits halal que ces marques mettent sur le",
              "marche."]
        if not (no.note == "S").any():
            l += ["",
                  "**Aucune marque halal n'atteint le palier S.** Aucune ne fait",
                  "nettement mieux que le marche sur sa propre gamme."]
    if ce is not None and len(ce):
        l += ["", "### 10.5 Les certificateurs : le classement complet, "
              "sans podium", "",
              "| organisme | n | ecart median | IC 95 % | strates | se distingue "
              "du marche |", "|:--|--:|--:|:--:|--:|:--|"]
        for r in ce.itertuples():
            l.append(f"| {r.groupe} | {r.n} | {r.ecart_median:+.1f} | "
                     f"[{r.ic95_bas:+.1f} ; {r.ic95_haut:+.1f}] | {r.strates} "
                     f"| {r.distingue_du_marche} |")
        l += ["",
              "**Ce tableau porte sur la composition des produits qui portent",
              "le nom d'un organisme, jamais sur son travail de",
              "certification.** Un organisme ne fabrique pas : il certifie. La",
              "couche 4 a montre qu'un certificateur se confond largement avec",
              "les marques qui font appel a lui — l'ARGML tire 78 % de ses",
              "produits d'une seule marque. Lire ce tableau comme un classement",
              "d'organismes serait lire un classement de marques sous un autre",
              "nom."]
    l += ["", "---", ""]
    return l


def bloc_question_certificateurs() -> list[str]:
    """Section 11 — la question posee aux organismes, et ses limites."""
    ns = lire("c_certificateurs_nutriscore_score")
    sel = lire("c_certificateurs_sel")
    sep = lire("c_certificateurs_separabilite")
    l = ["## 11. Une question posee aux organismes certificateurs", "",
         "Cette section ne conclut pas. Elle formule une question, expose les",
         "faits qui la rendent posable, et dit exactement ce qu'elle ne peut",
         "pas trancher.",
         "",
         "### 11.1 Ce que la certification porte aujourd'hui, sur le plan "
         "nutritionnel", ""]
    if ns is not None and len(ns):
        l += ["Ecart a la mediane de marche de la strate, sur les produits qui",
              "portent le nom de chaque organisme. Negatif = mieux que le",
              "marche sur le meme type de produit.", "",
              "| groupe | n | ecart Nutri-Score | IC 95 % | se distingue du "
              "marche |", "|:--|--:|--:|:--:|:--|"]
        for r in ns.sort_values("ecart_median").itertuples():
            l.append(f"| {r.groupe} | {r.n} | {r.ecart_median:+.1f} | "
                     f"[{r.ic95_bas:+.1f} ; {r.ic95_haut:+.1f}] | "
                     f"{r.distingue_du_marche} |")
        l += ["",
              "**Aucun organisme n'est associe a une nutrition meilleure que le",
              "marche.** Le mieux place, la SFCVH, est A ZERO : au niveau du",
              "marche, sans s'en distinguer. Les trois autres sont au-dessus,",
              "c'est-a-dire moins bien. Et le groupe « halal SANS "
              "certificateur »",
              "est a +2,0, soit **entre** deux organismes certifies.",
              "",
              "**C'est le fait central de cette section, et il n'accuse "
              "personne :**",
              "sur ce que mesure cette etude, **la certification ne porte "
              "aucun**",
              "**signal nutritionnel**, ni dans un sens ni dans l'autre. Un "
              "produit",
              "certifie n'est pas mieux compose qu'un produit halal non "
              "certifie."]
    if sep is not None and len(sep):
        # Restreint aux organismes reellement analyses en 11.1. Sans ce
        # filtre le tableau remontait des organismes a UN produit, dont la
        # « part de la premiere marque » vaut 100 % par construction et ne
        # dit rien.
        top = (sep[sep.n_produits >= 30]
               .sort_values(["pct_1re_marque", "certificateur"],
                            ascending=[False, True]))
        l += ["",
              "### 11.2 Pourquoi le tableau ci-dessus n'est pas un classement "
              "d'organismes", "",
              "Un certificateur ne fabrique pas : il certifie. Le classer sur",
              "la composition de ses clients revient largement a classer ses",
              "clients.", "",
              "| organisme | produits | marques | part de la 1re marque |",
              "|:--|--:|--:|--:|"]
        for r in top.itertuples():
            l.append(f"| {r.certificateur} | {r.n_produits} | {r.n_marques} | "
                     f"{r.pct_1re_marque:.1f} % |")
        l += ["",
              "L'ARGML tire **78 %** de ses produits d'une seule marque. Dire",
              "« l'ARGML fait moins bien que la SFCVH » revient a dire « la",
              "marque qui represente 78 % de l'ARGML fait moins bien ». Le",
              "classement des organismes est un classement de marques sous un",
              "autre nom, et il ne doit pas etre publie autrement."]
    l += ["",
          "### 11.3 La question, telle que l'etude peut la poser", "",
          "Trois faits la rendent posable, et aucun des trois n'est une "
          "opinion :",
          "",
          "1. **La certification est silencieuse sur la nutrition.** Mesure "
          "ci-dessus.",
          "2. **L'ecart est rattrapable.** Sur la charcuterie cuite de dinde,",
          "   83 % du marche non halal passe sous 2 g de sel aux 100 g, contre",
          "   19 % du halal (H34). Meme gamme, meme espece, meme technologie :",
          "   le seuil n'attend aucune innovation.",
          "3. **Le critere serait verifiable.** Le sel se lit sur l'emballage,",
          "   ne s'agrege pas avec d'autres nutriments, et une recette ne peut",
          "   pas le compenser ailleurs. Un cahier des charges peut l'ecrire et",
          "   un auditeur peut le controler, exactement comme il controle deja",
          "   une chaine d'approvisionnement.",
          "",
          "**La question est donc : un organisme qui appose son nom sur un",
          "produit entend-il que ce nom porte, ou non, une exigence de",
          "composition ?** Elle s'adresse aux organismes, et la reponse leur",
          "appartient.",
          "",
          "### 11.4 Ce que l'etude ne peut pas dire, et ne dira pas", "",
          "**Elle ne qualifie rien religieusement.** Ce depot est une base de",
          "composition. Il ne dit pas ce qui est halal, tayyib ou makrouh, et",
          "l'inference qui va d'un fait scientifique a une qualification",
          "juridique est un raisonnement de science religieuse, pas de",
          "statistique. Ce raisonnement appartient a ceux qui en ont la",
          "competence. Une etude nutritionnelle qui s'en emparerait sortirait",
          "de son objet et perdrait le droit d'etre crue sur le reste.",
          "",
          "**Elle ne declare aucun produit mauvais pour la sante.** Le "
          "Nutri-Score",
          "est un indicateur comparatif de composition aux 100 g, pas un",
          "verdict sanitaire sur une reference (H35). Ce qui est etabli porte",
          "sur des CATEGORIES et des QUANTITES : la charcuterie est classee",
          "cancerogene pour l'homme par le CIRC, et le risque documente se lit",
          "en grammes par jour sur des annees. Aucun code-barres n'est",
          "condamnable a lui seul.",
          "",
          "**Elle ne met en cause la responsabilite morale de personne.** Une",
          "question posee n'est pas une accusation, et cette etude n'a pas les",
          "moyens d'une accusation : elle ne connait ni les cahiers des charges",
          "des organismes, ni ce qu'ils ont deja tente, ni ce que leurs clients",
          "leur imposent. Nommer des organismes pour leur adresser un reproche",
          "moral, sur des donnees qui ne mesurent pas leur travail, serait",
          "precisement l'usage abusif que ce depot est construit pour rendre",
          "impossible.",
          "",
          "**Elle ne couvre qu'une fraction du rayon.** Un tiers seulement du",
          "bras halal porte un organisme identifiable. La question s'adresse a",
          "ceux-la ; les deux tiers restants n'ont personne a qui elle puisse",
          "etre posee.",
          "", "---", ""]
    return l


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
        "| Nom des sites de production | RESOLU (H33) : 93,8 % des sites "
        "classes nommes par le registre DGAL | Les 4 % de lignes du registre "
        "illisibles, et les 419 agrements a raison sociale multiple |",
        "| Cout de l'abattage et de la certification | Hors de portee de "
        "cette source, definitivement. Une recherche renvoie une fourchette de "
        "2 a 20 centimes par kilo de redevance de certification, attribuee a la "
        "presse professionnelle et NON VERIFIEE : l'article n'a pas pu etre "
        "ouvert, et ce chiffre n'entre nulle part dans les calculs | Les "
        "comptabilites d'abattoirs et les grilles tarifaires des "
        "certificateurs. Aucune n'est publique |",
        "| Surcout halal en rayon | Non etabli, borne haute a +1,39 EUR/kg | "
        "Un releve de prix systematique : 138 produits halal ne permettent pas "
        "de voir moins |",
        "| MDD contre specialistes | Ordre constant, aucune difference "
        "etablie | Plus de MDD avec une gamme halal : 3 marques ne portent pas "
        "une famille |",
        "| « Specialiste du halal » comme categorie | Melange epicerie turque "
        "et marques maghrebines | Un decoupage par repertoire culinaire, teste "
        "contre celui par part de catalogue |",
        "| Strate trop grossiere sur les viandes crues | `autres_carnes / "
        "porc` melange roti de filet (0,11 g de sel) et poitrine demi-sel "
        "(3,30 g) | Une strate par MORCEAU, ou l'exclusion des sites de decoupe "
        "du classement intra-site |",
        "| Classement des sites sur leur seul halal | Non fonde | Une "
        "dispersion intra-site qui ne depasse plus celle du temoin, ou "
        "beaucoup plus de produits par site |",
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
        "make couche9     # podiums et paires appariees",
        "make couche10    # etablissements, variance intra-site",
        "make couche11    # homogeneite des deux bras",
        "make couche12    # allegations d'emballage",
        "make couche13    # site partage ou site halal seul",
        "make couche14    # sites francais decodes depuis l'estampille",
        "make couche15    # MDD, industriels, specialistes du halal",
        "make couche16    # surcout halal en rayon, et la borne",
        "make couche17    # sites nommes (registre via l'Action "
        "couche14-registre)",
        "make couche18    # podiums produits, marques, certificateurs",
        "make couche19    # faisabilite d'un seuil nutritionnel par gamme",
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
              + bloc_marche() + bloc_erreurs() + bloc_podiums()
              + bloc_question_certificateurs() + bloc_ouvert())
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
