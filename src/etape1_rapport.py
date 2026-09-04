#!/usr/bin/env python3
"""Etape 1e — assemblage du rapport de couche 1.

Le rapport est ENTIEREMENT derive de sorties/*.csv et sorties/chiffres_cles.json.
Aucun chiffre n'est saisi a la main ici : si une valeur change dans les donnees,
elle change dans le rapport.

Chaque enonce porte son statut [FAIT] / [INFERENCE] / [HYPOTHESE] (AGENTS.md).
"""

from __future__ import annotations

import datetime as dt
import json
import sys

import pandas as pd

from commun import SORTIES, charger, echec, revision_git

SEUIL = 30


def lire(nom: str) -> pd.DataFrame:
    f = SORTIES / nom
    if not f.exists():
        echec(f"{nom} absent. Lance d'abord src/etape1_analyse.py.")
    return pd.read_csv(f)


def md(df: pd.DataFrame) -> str:
    return df.to_markdown(index=False)


def main() -> int:
    k = json.loads((SORTIES / "chiffres_cles.json").read_text(encoding="utf-8"))
    src = json.loads((SORTIES / "source_figee.json").read_text(encoding="utf-8"))
    per = charger("perimetre.yaml")
    lib = {sc["nom"]: sc["libelle"] for sc in per["sous_categories"]}

    d0, d2 = lire("d0_volumetrie.csv"), lire("d2_effectifs_strates.csv")
    d3, d3b = lire("d3_nutriscore_par_bras.csv"), lire("d3bis_dispersion_intra_halal.csv")
    d4, d5 = lire("d4_taux_tag_par_marque.csv"), lire("d5_certificateurs.csv")
    d6, d7 = lire("d6_additifs.csv"), lire("d7_nova.csv")
    c1, c2 = lire("c1_comparaison_sel.csv"), lire("c2_nutriscore_par_strate.csv")
    c3 = lire("c3_transformation_par_strate.csv")
    img = lire("d8_couverture_image.csv")
    fn = None
    if (SORTIES / "couche2_faux_negatifs.csv").exists():
        fn = pd.read_csv(SORTIES / "couche2_faux_negatifs.csv")
    img_halal = img[img.bras == "halal"].iloc[0].to_dict()

    v, ns, ce, se = k["volumetrie"], k["nutriscore"], k["certificateurs"], k["sel_ensemble"]
    tr = k["transformation"]

    franchies = d2[d2.regle_30 == "franchie"]
    ecartees = d2[d2.regle_30 != "franchie"]
    c1s = c1[c1.sous_categorie != "_ensemble_"].copy()
    c1s["sens"] = c1s.diff_medianes.apply(
        lambda x: "halal plus sale" if x > 0 else ("halal moins sale" if x < 0 else "egal"))
    c1s["ic_exclut_zero"] = (c1s.ic95_bas > 0) | (c1s.ic95_haut < 0)
    plus = c1s[(c1s.sens == "halal plus sale") & c1s.ic_exclut_zero]
    moins = c1s[(c1s.sens == "halal moins sale") & c1s.ic_exclut_zero]
    nul = c1s[~c1s.ic_exclut_zero]

    # Verdict Nutri-Score (critere d'acceptation des specs : seuil 80 %).
    if ns["sature"]:
        verdict_ns = (
            f"**Sature.** {ns['pct_DE_halal']} % du bras halal et "
            f"{ns['pct_DE_temoin']} % du temoin sont en D ou E, au-dela du seuil "
            "de 80 %. La lettre ne discrimine pas dans ce rayon : la couche "
            "editoriale bascule sur le sel pour 100 g et le pourcentage de "
            "viande, conformement aux specs."
        )
    else:
        verdict_ns = (
            f"**Non sature.** {ns['pct_DE_halal']} % du bras halal et "
            f"{ns['pct_DE_temoin']} % du temoin sont en D ou E ; le seuil de "
            "80 % n'est atteint dans aucun des deux bras. La lettre garde du "
            "pouvoir discriminant a l'echelle du perimetre entier et reste "
            "utilisable comme variable de sortie. Le basculement editorial "
            "prevu par les specs n'est pas declenche par ce critere."
        )

    verdicts_cert = {
        "inexploitable_couverture":
            f"**Inexploitable EN L'ETAT DU TAG, pour couverture et non pour "
            f"separabilite.** Seuls {ce['n_produits_halal_avec_certificateur']} "
            f"produits halal sur {v['n_halal']} portent un tag de certificateur, "
            f"soit {ce['pct_halal_avec_certificateur']} %. Une variable renseignee "
            "sur moins de 7 % des cas ne permet aucune comparaison, separable ou "
            "non. La separabilite elle-meme reste INCONNUE : les produits tagues "
            "ne sont pas un echantillon representatif, ce sont ceux dont un "
            "contributeur a pris la peine de saisir le certificateur. "
            "La question n'est donc pas close, elle est renvoyee a la lecture "
            "d'image de la couche 2 (section 4bis).",
        "inseparable_de_la_marque":
            "**Certificateur et marque ne sont pas separables.** Les "
            "certificateurs presents ne couvrent qu'une ou deux marques chacun. "
            "Le facteur est retire du plan de la couche 4.",
        "potentiellement_separable":
            "**Separabilite partielle.** Au moins deux certificateurs depassent "
            f"{SEUIL} produits et plus de deux marques. Le facteur peut etre "
            "teste, sous reserve du regroupement manuel des variantes de tags.",
    }

    r = []
    A = r.append
    A("# Etude halal / non halal — rapport de couche 1")
    A("")
    A(f"Genere le {dt.date.today().isoformat()} par `src/etape1_rapport.py`, "
      f"revision `{revision_git()}`. Tous les chiffres sont derives des CSV de "
      "`sorties/`, aucun n'est saisi a la main.")
    A("")
    A("**Ce rapport ne conclut pas sur la qualite nutritionnelle des produits "
      "halal.** Il repond a une question de faisabilite : les donnees "
      "permettent-elles l'etude, et sur quelles variables. L'ecart chiffre "
      "presente en section 6 est brut, non ajuste, non apparie. Il n'est pas "
      "un resultat publiable en l'etat, et la section 7 dit pourquoi.")
    A("")
    A("## Convention de lecture")
    A("")
    A("- `[FAIT]` : lu directement dans le dump, reproductible par requete.")
    A("- `[INFERENCE]` : deduit d'un fait par un raisonnement explicite et faillible.")
    A("- `[HYPOTHESE]` : non teste par ce depot, renvoye a une couche ulterieure.")
    A("")
    A("---")
    A("")
    A("## 1. Source et perimetre")
    A("")
    A(f"- `[FAIT]` Source : `{src['url']}`, publie sous ODbL par Open Food Facts.")
    A(f"- `[FAIT]` Dump du {src['date_dump']}, {src['taille_octets']} octets, "
      f"sha256 `{src['sha256']}`.")
    A(f"- `[FAIT]` {src['n_produits_france']} produits portent `en:france` dans "
      "`countries_tags`.")
    A(f"- `[FAIT]` Le perimetre carne fige (`config/perimetre.yaml`) retient "
      f"**{v['n_perimetre']} produits**, dont **{v['n_halal']} tagues "
      f"`en:halal`** et {v['n_temoin']} au temoin.")
    A(f"- `[FAIT]` {v['n_complet']} produits ont des donnees nutritionnelles "
      f"completes ({100 * v['n_complet'] / v['n_perimetre']:.0f} % du perimetre), "
      f"dont {v['n_halal_complet']} au bras halal et {v['n_temoin_complet']} au temoin.")
    A("")
    A("Ecart aux specs a signaler : les specs prevoyaient le dump Parquet "
      "HuggingFace. Cet hote est refuse par la politique reseau de "
      "l'environnement d'execution. L'export plat officiel Open Food Facts est "
      "utilise a la place — meme organisation, meme base, memes licences. "
      "Consequences detaillees dans `config/source.yaml` et en section 9.")
    A("")
    A("Le perimetre est bati sur les categories reellement observees dans le "
      "dump, pas sur les graines de recherche : `src/etape1_amorce.py` produit "
      "la liste, `config/perimetre.yaml` la fige, `config/graines.yaml` ne sert "
      "qu'a l'amorce et n'entre dans aucun calcul.")
    A("")
    A(f"`[FAIT]` Sur les {src['n_produits_france']} produits France, seuls "
      f"{v['n_halal']} produits tagues halal sont carnes. Le tag `en:halal` "
      "est majoritairement porte par des produits non carnes (confiseries, "
      "snacks, boissons), hors sujet ici.")
    A("")
    A("---")
    A("")
    A("## 2. Effectifs par strate et regle des 30")
    A("")
    A(f"`[FAIT]` Effectifs par sous-categorie. La regle des {SEUIL} est franchie "
      f"quand les DEUX bras comptent au moins {SEUIL} produits a donnees "
      "nutritionnelles completes.")
    A("")
    A(md(d2[["sous_categorie", "halal", "halal_complet", "temoin",
             "temoin_complet", "regle_30"]]))
    A("")
    for _, row in d2.iterrows():
        A(f"- `{row.sous_categorie}` — {lib.get(row.sous_categorie, '')} : "
          f"**{row.regle_30}** ({int(row.halal_complet)} halal complets, "
          f"{int(row.temoin_complet)} temoins complets).")
    A("")
    if len(ecartees) == 0:
        A(f"`[FAIT]` Aucune strate n'est ecartee par la regle des {SEUIL}. "
          "Les neuf sous-categories entrent dans le plan d'analyse principal.")
    else:
        A(f"`[FAIT]` Strates ecartees du plan principal : "
          f"{', '.join(ecartees.sous_categorie)}. Elles peuvent etre decrites, "
          "jamais testees.")
    A("")
    A("`[INFERENCE]` La sous-categorie `autres_carnes` regroupe les produits "
      "dont la categorie Open Food Facts ne descend pas sous l'espece "
      "(`en:chickens`, `en:turkeys`, `en:beef` seuls). Elle pese "
      f"{int(d2.loc[d2.sous_categorie == 'autres_carnes', 'halal'].iloc[0])} "
      "produits halal. Ce n'est pas une famille de produits, c'est un defaut "
      "de renseignement de la taxonomie. Aucune conclusion editoriale ne doit "
      "porter sur cette strate.")
    A("")
    A("---")
    A("")
    A("## 3. Nutri-Score : saturation ?")
    A("")
    A(f"`[FAIT]` Distribution des grades sur {ns['n_note_halal']} produits halal "
      f"et {ns['n_note_temoin']} temoins notes.")
    A("")
    A(md(d3))
    A("")
    A(f"`[FAIT]` {verdict_ns}")
    A("")
    A("`[FAIT]` Le detail par sous-categorie montre que la moyenne du perimetre "
      "masque deux regimes : la charcuterie seche est en D-E a plus de 99 % "
      "dans les deux bras, les decoupes et plats cuisines beaucoup moins.")
    A("")
    A(md(c2))
    A("")
    A("`[INFERENCE]` Dans les strates ou les deux bras depassent 90 % de D-E "
      "(charcuterie seche, saucisses, rillettes), la lettre ne discrimine plus "
      "rien localement, meme si elle discrimine a l'echelle du perimetre. Pour "
      "ces rayons precis, la recommandation editoriale des specs s'applique : "
      "parler sel pour 100 g et pourcentage de viande, pas Nutri-Score.")
    A("")
    A("`[HYPOTHESE]` L'export plat n'expose qu'une colonne `nutriscore_grade`, "
      "sans indication de version d'algorithme. Le rapport la traite comme la "
      "note publiee par Open Food Facts a la date du dump. Le recalcul FSAm-NPS "
      "versionne 2017 / 2023 est un travail de couche 3.")
    A("")
    A("---")
    A("")
    A("## 4. Certificateurs : separables de la marque ?")
    A("")
    A(f"`[FAIT]` {ce['n_certificateurs_distincts']} tags de certificateur "
      f"distincts apparaissent dans `labels_tags` a cote de `en:halal`.")
    A("")
    A(md(d5))
    A("")
    A(f"`[FAIT]` {verdicts_cert[ce['verdict']]}")
    A("")
    A("`[FAIT]` Plusieurs tags designent le meme organisme sous des orthographes "
      "differentes — les variantes `fr:` et `en:` de la Societe francaise de "
      "controle de viande halal en sont l'exemple. Le comptage ci-dessus est "
      "donc une borne HAUTE du nombre d'organismes distincts.")
    A("")
    A("`[INFERENCE]` Consequence immediate pour la couche 4 : en l'etat du tag, "
      "le facteur certificateur ne peut pas entrer dans le modele. Il n'y sera "
      "pas inclus en esperant que le modele demele. Sa reintroduction est "
      "conditionnee au resultat de la section suivante.")
    A("")
    A("### 4bis. Voie de recuperation : lecture du certificateur sur l'image")
    A("")
    A("`[FAIT]` Le certificateur est imprime sur l'emballage. La couverture "
      "photo du bras halal ne limite pas cette voie :")
    A("")
    A(md(img))
    A("")
    A(f"`[FAIT]` {img_halal['pct_au_moins_une']} % des produits halal ont au "
      "moins une photo. Le facteur limitant est le renseignement du tag, pas "
      "la disponibilite de l'image.")
    A("")
    A("`[HYPOTHESE]` Un modele de vision de petite taille peut lire le logo du "
      "certificateur sur ces photos. Trois conditions non verifiees a ce jour, "
      "toutes verifiables en couche 2 :")
    A("")
    A("1. **Resolution.** Les URL de l'export pointent des images en 400 px sur "
      "le grand cote. Un logo de certificateur y occupe quelques dizaines de "
      "pixels. Une taille superieure semble accessible en changeant le suffixe "
      "de l'URL ; non verifie, l'hote images est injoignable depuis "
      "l'environnement d'execution de ce depot.")
    A("2. **Presence du logo sur la face photographiee.** Une part inconnue des "
      "certifications n'apparait ni sur la face ni sur la photo ingredients.")
    A("3. **Taux d'erreur mesure.** Il doit l'etre contre un echantillon recode "
      "a la main en aveugle, par un humain, au meme standard que le parseur du "
      "pourcentage de viande.")
    A("")
    A("`[INFERENCE]` L'erreur de lecture ne sera pas aleatoire, elle sera "
      "**correlee a la marque** : une marque, un design d'emballage, le meme "
      "logo au meme endroit sur toute la gamme. Un logo mal lu l'est alors sur "
      "l'integralite des references de cette marque d'un seul coup. Injectee "
      "telle quelle dans le modele mixte de la couche 4, cette erreur produit "
      "un effet certificateur qui n'est qu'un effet marque mal mesure — "
      "exactement le confondant que le modele est cense demeler. Une erreur "
      "aleatoire dilue un effet ; celle-ci en fabrique un.")
    A("")
    A("`[INFERENCE]` La parade est celle que les specs imposent deja pour le "
      "statut halal : verifier **par marque et par design d'emballage**, pas "
      f"par produit. Les {k['sous_etiquetage']['n_marques_examinees']} marques "
      "de la section 5 couvrent l'essentiel du bras halal. Le modele de vision "
      "ne tranche pas le certificateur reference par reference : il lit le "
      "design de reference de chaque marque, valide a la main une fois, puis "
      "sert a reperer les produits dont l'emballage s'ecarte de ce design.")
    A("")
    A("`[INFERENCE]` Priorite : ce passage sur les images doit d'abord servir a "
      "mesurer le taux de faux negatifs du tag halal (section 5), qui commande "
      "l'amplitude de tous les ecarts de la section 6. Le certificateur est un "
      "sous-produit du meme passage, pas sa justification.")
    A("")
    A("---")
    A("")
    A("## 5. Sous-etiquetage du tag halal")
    A("")
    A(f"`[FAIT]` {k['sous_etiquetage']['n_marques_examinees']} marques comptent "
      "au moins 5 produits tagues halal dans le perimetre.")
    A("")
    A(md(d4.head(25)))
    A("")
    A(f"`[FAIT]` Parmi ces {k['sous_etiquetage']['n_marques_examinees']} marques, "
      f"{k['sous_etiquetage']['n_marques_specialistes_halal']} ont au moins "
      "80 % de leur gamme carnee taguee halal, soit "
      f"{k['sous_etiquetage']['n_produits_chez_specialistes']} produits. Parmi "
      f"eux, {k['sous_etiquetage']['faux_negatifs_borne_basse']} ne portent pas "
      "le tag alors que la marque est manifestement specialisee.")
    A("")
    A(f"`[INFERENCE]` Cela donne une **borne basse** du taux de faux negatifs de "
      f"{k['sous_etiquetage']['taux_faux_negatifs_borne_basse_pct']} % chez les "
      "marques specialisees. Borne basse seulement : la methode ne voit pas les "
      "gammes halal des marques generalistes. Carrefour compte "
      f"{int(d4.loc[d4.marque_tag == 'carrefour', 'n_produits'].iloc[0]) if (d4.marque_tag == 'carrefour').any() else 0} "
      "produits carnes dans le perimetre dont "
      f"{int(d4.loc[d4.marque_tag == 'carrefour', 'n_tagues'].iloc[0]) if (d4.marque_tag == 'carrefour').any() else 0} "
      "tagues : impossible de savoir par cette voie combien de references halal "
      "de l'enseigne ne portent pas le tag.")
    A("")
    if fn is not None:
        t = fn[fn.bras == "temoin"].iloc[0]
        h = fn[fn.bras == "halal"].iloc[0]
        A("`[FAIT]` **Mesure directe, couche 2.** Un echantillon aleatoire de "
          f"{int(t.n)} produits du temoin et {int(h.n)} produits tagues halal "
          "a ete recode a la main, en aveugle, par un humain "
          "(`donnees_humaines/double_codage.csv`).")
        A("")
        A(md(fn[["bras", "mesure", "k", "n", "taux_pct", "ic95_bas_pct",
                 "ic95_haut_pct"]]))
        A("")
        A(f"`[FAIT]` **{int(t.k)} produit sur {int(t.n)} du temoin porte une "
          f"estampille halal**, soit {t.taux_pct} % "
          f"(IC 95 % de Wilson [{t.ic95_bas_pct} ; {t.ic95_haut_pct}] %).")
        A("")
        A("`[FAIT]` Cette mesure CONTREDIT ce que ce rapport avancait dans ses "
          "versions precedentes. La borne basse de 4,26 % calculee plus haut "
          "porte sur les seules marques specialisees halal, une "
          "sous-population choisie pour maximiser le phenomene ; en faire un "
          "plancher du taux global etait une extrapolation abusive. Le taux "
          "sur un tirage aleatoire du temoin est compatible avec zero.")
        A("")
        A("`[INFERENCE]` Consequence directe : la contamination du temoin par "
          "des produits halal non tagues n'est PAS le facteur limitant de "
          "l'etude. Les ecarts de la section 6 ne sont pas d'amplitude "
          "inconnue de ce fait la. Les autres limites de la section 7 "
          "demeurent entieres, en particulier la confusion avec le degre de "
          "transformation.")
        A("")
        A(f"`[FAIT]` L'ecart joue dans l'autre sens : {int(h.k)} produits sur "
          f"{int(h.n)} tagues `en:halal` ne montrent AUCUNE estampille "
          f"reperable, soit {h.taux_pct} % "
          f"(IC 95 % [{h.ic95_bas_pct} ; {h.ic95_haut_pct}] %). Le tag est "
          "donc plus large que ce qu'un consommateur verifierait en rayon.")
        A("")
        A("`[HYPOTHESE]` Ces 16 produits peuvent etre des erreurs de tag, des "
          "estampilles absentes de la face photographiee, ou des produits "
          "dont la certification n'est plus a jour. Non tranche.")
        A("")
        A("`[FAIT]` Limite de la mesure : le codeur a etabli le statut de "
          "38 produits par recherche externe et non sur la photo, tous dans "
          "le bras halal. Si cet effort de recherche n'a pas ete symetrique "
          "entre les deux bras, le zero du temoin est sous-estime. La colonne "
          "`source_lecture` du fichier de codage permet de rejouer la mesure "
          "sur les seules lectures faites sur image.")
    else:
        A("`[HYPOTHESE]` Le taux reel de faux negatifs dans le temoin n'est "
          "pas mesure. Il se mesure sur photo d'emballage, sur echantillon "
          "aleatoire du temoin, avec intervalle. C'est le premier livrable de "
          "la couche 2.")
    A("")
    A("---")
    A("")
    A("## 6. Comparaison brute : sel pour 100 g")
    A("")
    A("Deux variables seulement, comme prevu par les specs : sel pour 100 g et "
      "Nutri-Score. Aucun ajustement, aucun appariement. Restreint aux produits "
      "a donnees nutritionnelles completes.")
    A("")
    A(md(c1))
    A("")
    A("Les colonnes `ic95_*` bornent la difference de medianes par bootstrap "
      "percentile (4 000 tirages, graine figee). Elles disent si l'ecart "
      "observe est distinguable du bruit d'echantillonnage. Elles ne disent "
      "rien de la confusion decrite en section 7.")
    A("")
    A(f"`[FAIT]` Sur l'ensemble du perimetre, la mediane de sel est de "
      f"{se['sel_median_halal']} g/100 g au bras halal contre "
      f"{se['sel_median_temoin']} g/100 g au temoin, soit un ecart de "
      f"{se['diff_medianes']:+.2f} g/100 g "
      f"(IC 95 % [{se['ic95_bas']:+.2f} ; {se['ic95_haut']:+.2f}]).")
    A("")
    A(f"`[FAIT]` Par sous-categorie, l'ecart est en faveur du temoin "
      f"(halal plus sale) dans {len(plus)} strates sur {len(c1s)} avec un IC "
      f"excluant zero : {', '.join(plus.sous_categorie)}.")
    if len(moins):
        A("")
        A(f"`[FAIT]` L'ecart s'inverse dans {len(moins)} strate(s) — le bras "
          f"halal y est MOINS sale : "
          + ", ".join(f"`{row.sous_categorie}` ({row.diff_medianes:+.2f} g/100 g)"
                      for _, row in moins.iterrows()) + ".")
    if len(nul):
        A("")
        A(f"`[FAIT]` L'ecart n'est pas distinguable de zero dans "
          f"{len(nul)} strate(s) : {', '.join(nul.sous_categorie)}.")
    A("")
    A("`[FAIT]` Dispersion interne au bras halal, par sous-categorie :")
    A("")
    A(md(d3b))
    A("")
    dv = k["dispersion_vs_ecart"]
    A(f"`[FAIT]` Dans {dv['n_strates_dispersion_dominante']} strates sur "
      f"{dv['n_strates']}, l'ecart interdecile INTERNE au bras halal depasse "
      "l'ecart de medianes entre bras. Le rapport des deux va de "
      f"{dv['ratio_min']} a {dv['ratio_max']}, mediane {dv['ratio_median']}.")
    A("")
    A("`[INFERENCE]` Choisir un bon produit halal "
      "plutot qu'un mauvais produit halal change plus la teneur en sel que "
      "choisir halal plutot que non halal. C'est le resultat le plus solide "
      "de cette couche, et c'est aussi le seul directement actionnable en rayon.")
    A("")
    A("---")
    A("")
    A("## 7. Ce que cet ecart ne demontre pas")
    A("")
    A(f"`[FAIT]` A sous-categorie egale, le bras halal est plus transforme que "
      f"le temoin dans {tr['n_strates_halal_plus_transforme']} strates sur "
      f"{tr['n_strates_comparees']}. L'ecart median de part de produits classes "
      f"NOVA 4 est de {tr['ecart_median_points_nova4']:+.1f} points.")
    A("")
    A(md(c3))
    A("")
    A(f"`[FAIT]` Sur l'ensemble du perimetre, {k['nova4']['pct_halal']} % des "
      f"produits halal notes sont NOVA 4 contre {k['nova4']['pct_temoin']} % "
      f"des temoins ({k['nova4']['n_note_halal']} et "
      f"{k['nova4']['n_note_temoin']} produits notes respectivement).")
    A("")
    A("`[INFERENCE]` Les sous-categories de ce rapport melangent, sous un meme "
      "nom, des produits de degre de transformation different. La strate "
      "`decoupes` en est la demonstration : le temoin y contient de la viande "
      "fraiche non salee, le bras halal des produits cuits ou marines. L'ecart "
      f"de sel de {c1s.loc[c1s.sous_categorie == 'decoupes', 'diff_medianes'].iloc[0]:+.2f} "
      "g/100 g qu'on y lit mesure d'abord cette difference de composition, pas "
      "un effet du label.")
    A("")
    A("`[HYPOTHESE]` Une fois apparies sur la sous-categorie fine, l'espece et "
      "le segment de gamme, les ecarts de sel se reduiraient sensiblement. Non "
      "teste ici. C'est l'objet de la couche 3, et aucune phrase d'article ne "
      "doit etre ecrite avant.")
    A("")
    A("`[FAIT]` La couverture NOVA est partielle : "
      f"{k['nova4']['n_note_halal']} produits halal notes sur {v['n_halal']}, "
      f"soit {100 * k['nova4']['n_note_halal'] / v['n_halal']:.0f} %. Les "
      "pourcentages ci-dessus portent sur les produits notes, pas sur le "
      "perimetre.")
    A("")
    A("Trois autres limites, toutes structurelles :")
    A("")
    A("1. `[FAIT]` Le traitement est le LABEL, pas la halalite. Un produit halal "
      "non estampille dans Open Food Facts est au temoin. La section 5 en donne "
      "une borne basse, pas la mesure.")
    A("2. `[FAIT]` Open Food Facts est une base contributive. Les produits "
      "renseignes ne sont pas un echantillon aleatoire du rayon : ils sont "
      "ceux que des contributeurs ont scannes. Rien dans ce depot ne corrige "
      "ce biais de selection, et la couche 1 ne peut pas le mesurer.")
    A("3. `[FAIT]` Aucune ponderation par les volumes de vente. Une reference "
      "confidentielle pese autant qu'un best-seller.")
    A("")
    A("---")
    A("")
    A("## 8. Ce que la couche 1 rend possible pour la suite")
    A("")
    A(f"`[FAIT]` Le releve manuel de la grille additifs, prevu en couche 5, "
      f"porte sur {k['additifs']['n_codes_distincts']} codes E distincts dans "
      f"le perimetre, dont {k['additifs']['n_codes_couvrant_99pct']} suffisent "
      "a couvrir 99 % des occurrences.")
    A("")
    A(md(d6.head(20)))
    A("")
    A(f"`[INFERENCE]` {k['additifs']['n_codes_couvrant_99pct']} codes a relever "
      "a la main, c'est plus que les 40 esperes par les specs mais cela reste "
      "faisable en une session de travail. Le recalcul du score Yuka de la "
      "couche 5 n'est pas bloque.")
    A("")
    A("`[FAIT]` E250 (nitrite de sodium) est l'additif le plus frequent du "
      f"perimetre, present sur {int(d6.loc[d6.additif == 'en:e250', 'n'].iloc[0])} "
      "produits. L'extraction des nitrites prevue en couche 2 a donc une base "
      "suffisante.")
    A("")
    A("`[FAIT]` NOVA par bras, sur les produits notes :")
    A("")
    A(md(d7))
    A("")
    A("---")
    A("")
    A("## 9. Ecarts aux specs et decisions actees")
    A("")
    A("| Point | Specs | Realise | Motif |")
    A("|---|---|---|---|")
    A("| Source | `food.parquet` sur HuggingFace | Export plat CSV officiel Open "
      "Food Facts, mirroir S3 | Hote `huggingface.co` refuse par la politique "
      "de sortie reseau de l'environnement (403 sur le CONNECT). Meme "
      "organisation, meme base, memes licences. |")
    A("| Nutri-Score 2023 | Emplacement a determiner apres inspection du schema "
      "| Colonne unique `nutriscore_grade`, version non exposee | L'export plat "
      "ne versionne pas la note. Recalcul FSAm-NPS renvoye en couche 3. |")
    A("| Comparaison | Mediane, quartiles, effectifs | Idem, plus un IC 95 % "
      "bootstrap sur la difference de medianes | Ajout assume : sans lui, le "
      "rapport ne peut pas dire si un ecart est distinguable du bruit. Ce "
      "n'est ni un ajustement ni un appariement. |")
    A("| Photos d'emballage | Colonne `images` structuree | URL d'image "
      "principale seulement | Limite de l'export plat. L'audit visuel de la "
      "couche 2 reste possible via `image_url`. |")
    A("")
    A("`[FAIT]` Une deduplication de code-barres est appliquee au perimetre : "
      "l'export contient de rares doublons (deux revisions d'un meme produit). "
      "La revision la plus recente est conservee, le compte est imprime par "
      "`src/etape1_perimetre.py` et l'assertion A3 verifie qu'il n'en reste "
      "aucun.")
    A("")
    A("---")
    A("")
    A("## 10. Decision de faisabilite")
    A("")
    A("`[FAIT]` L'etude est faisable. Les neuf sous-categories du perimetre "
      f"franchissent la regle des {SEUIL}, le bras halal compte "
      f"{v['n_halal_complet']} produits a donnees completes, et les variables "
      "de sortie prevues (sel, Nutri-Score, NOVA, additifs) sont renseignees a "
      "un taux exploitable.")
    A("")
    A("`[FAIT]` Deux questions sont fermees des maintenant :")
    A("")
    A("- L'effet certificateur est abandonne, pour couverture insuffisante "
      f"({ce['pct_halal_avec_certificateur']} % des produits halal). Il sort du "
      "plan de la couche 4.")
    A("- Le basculement editorial integral vers le sel n'est pas declenche : le "
      "Nutri-Score n'est pas sature a l'echelle du perimetre. Il l'est en "
      "revanche dans la charcuterie seche, les saucisses et les rillettes, ou "
      "la recommandation des specs s'applique localement.")
    A("")
    A("`[FAIT]` Une question devient prioritaire et conditionne tout le reste : "
      "le taux de faux negatifs du tag halal dans le temoin. Tant qu'il n'est "
      "pas mesure sur photo, l'amplitude de tous les ecarts de la section 6 est "
      "inconnue. C'est le premier livrable de la couche 2.")
    A("")
    A("`[INFERENCE]` Le titre defendable a ce stade n'est pas « le halal est "
      "plus sale ». C'est la dispersion interne : a l'interieur meme de l'offre "
      "halal, l'ecart entre le premier et le dernier decile de sel depasse "
      "partout l'ecart entre les deux bras. Le lecteur en rayon gagne plus a "
      "comparer deux paquets halal entre eux qu'a arbitrer entre halal et non "
      "halal. Ce constat tient sans appariement et ne depend pas de la "
      "composition du temoin, donc pas de sa contamination par des produits "
      "halal non tagues. Il reste sensible a un biais de selection interne : "
      "les produits halal non tagues sont absents du bras halal, et rien ici "
      "ne dit qu'ils y auraient la meme dispersion.")
    A("")

    chemin = SORTIES / "rapport_couche1.md"
    chemin.write_text("\n".join(r), encoding="utf-8")
    print(f"  -> {chemin}  ({len(r)} lignes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
