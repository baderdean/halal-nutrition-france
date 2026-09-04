# Etude halal / non halal — rapport de couche 1

Genere le 2026-09-04 par `src/etape1_rapport.py`, revision `6eb9a64`. Tous les chiffres sont derives des CSV de `sorties/`, aucun n'est saisi a la main.

**Ce rapport ne conclut pas sur la qualite nutritionnelle des produits halal.** Il repond a une question de faisabilite : les donnees permettent-elles l'etude, et sur quelles variables. L'ecart chiffre presente en section 6 est brut, non ajuste, non apparie. Il n'est pas un resultat publiable en l'etat, et la section 7 dit pourquoi.

## Convention de lecture

- `[FAIT]` : lu directement dans le dump, reproductible par requete.
- `[INFERENCE]` : deduit d'un fait par un raisonnement explicite et faillible.
- `[HYPOTHESE]` : non teste par ce depot, renvoye a une couche ulterieure.

---

## 1. Source et perimetre

- `[FAIT]` Source : `https://openfoodfacts-ds.s3.eu-west-3.amazonaws.com/en.openfoodfacts.org.products.csv.gz`, publie sous ODbL par Open Food Facts.
- `[FAIT]` Dump du 2026-09-03T11:55:24Z, 1275171186 octets, sha256 `f72687ee8bc6522054fe69dbfda6b91902c16af1ec2e043cde27bc6c29ad8176`.
- `[FAIT]` 1263854 produits portent `en:france` dans `countries_tags`.
- `[FAIT]` Le perimetre carne fige (`config/perimetre.yaml`) retient **90398 produits**, dont **2387 tagues `en:halal`** et 88011 au temoin.
- `[FAIT]` 70344 produits ont des donnees nutritionnelles completes (78 % du perimetre), dont 1960 au bras halal et 68384 au temoin.

Ecart aux specs a signaler : les specs prevoyaient le dump Parquet HuggingFace. Cet hote est refuse par la politique reseau de l'environnement d'execution. L'export plat officiel Open Food Facts est utilise a la place — meme organisation, meme base, memes licences. Consequences detaillees dans `config/source.yaml` et en section 9.

Le perimetre est bati sur les categories reellement observees dans le dump, pas sur les graines de recherche : `src/etape1_amorce.py` produit la liste, `config/perimetre.yaml` la fige, `config/graines.yaml` ne sert qu'a l'amorce et n'entre dans aucun calcul.

`[FAIT]` Sur les 1263854 produits France, seuls 2387 produits tagues halal sont carnes. Le tag `en:halal` est majoritairement porte par des produits non carnes (confiseries, snacks, boissons), hors sujet ici.

---

## 2. Effectifs par strate et regle des 30

`[FAIT]` Effectifs par sous-categorie. La regle des 30 est franchie quand les DEUX bras comptent au moins 30 produits a donnees nutritionnelles completes.

| sous_categorie          |   halal |   halal_complet |   temoin |   temoin_complet | regle_30     |
|:------------------------|--------:|----------------:|---------:|-----------------:|:-------------|
| autres_carnes           |     436 |             358 |    22194 |            15716 | franchie     |
| charcuterie_cuite       |     379 |             343 |    15180 |            13206 | franchie     |
| panes                   |     338 |             290 |     2482 |             2155 | franchie     |
| saucisses               |     259 |             240 |     6950 |             5778 | franchie     |
| charcuterie_seche       |     260 |             235 |     6935 |             6031 | franchie     |
| decoupes                |     391 |             208 |    13885 |             7939 | franchie     |
| plats_cuisines          |     164 |             142 |    12253 |            10770 | franchie     |
| viande_hachee           |     119 |             104 |     1447 |             1118 | franchie     |
| rillettes_pates_mousses |      40 |              39 |     6600 |             5594 | franchie     |
| foie_gras               |       1 |               1 |       85 |               77 | NON franchie |

- `autres_carnes` — Autres produits carnes : categorie OFF ne descendant pas sous l'espece : **franchie** (358 halal complets, 15716 temoins complets).
- `charcuterie_cuite` — Charcuterie cuite en tranches (jambons, blancs de volaille cuits) : **franchie** (343 halal complets, 13206 temoins complets).
- `panes` — Produits panes (nuggets, cordons bleus, escalopes panees) : **franchie** (290 halal complets, 2155 temoins complets).
- `saucisses` — Saucisses fraiches et merguez : **franchie** (240 halal complets, 5778 temoins complets).
- `charcuterie_seche` — Charcuterie seche (saucissons, salami, chorizo, viandes sechees) : **franchie** (235 halal complets, 6031 temoins complets).
- `decoupes` — Decoupes et preparations non transformees (blancs, cuisses, steaks) : **franchie** (208 halal complets, 7939 temoins complets).
- `plats_cuisines` — Plats cuisines et sandwichs a base de viande : **franchie** (142 halal complets, 10770 temoins complets).
- `viande_hachee` — Viande hachee et steaks haches : **franchie** (104 halal complets, 1118 temoins complets).
- `rillettes_pates_mousses` — Rillettes, pates, terrines, mousses et tartinables carnes : **franchie** (39 halal complets, 5594 temoins complets).
- `foie_gras` — Foie gras et produits de foie gras (halalite disputee) : **NON franchie** (1 halal complets, 77 temoins complets).

`[FAIT]` Strates ecartees du plan principal : foie_gras. Elles peuvent etre decrites, jamais testees.

`[INFERENCE]` La sous-categorie `autres_carnes` regroupe les produits dont la categorie Open Food Facts ne descend pas sous l'espece (`en:chickens`, `en:turkeys`, `en:beef` seuls). Elle pese 436 produits halal. Ce n'est pas une famille de produits, c'est un defaut de renseignement de la taxonomie. Aucune conclusion editoriale ne doit porter sur cette strate.

---

## 3. Nutri-Score : saturation ?

`[FAIT]` Distribution des grades sur 1956 produits halal et 70341 temoins notes.

| grade   |   halal |   temoin |   pct_halal |   pct_temoin |
|:--------|--------:|---------:|------------:|-------------:|
| A       |     165 |    11149 |         8.4 |         15.8 |
| B       |     160 |     6403 |         8.2 |          9.1 |
| C       |     320 |    12926 |        16.4 |         18.4 |
| D       |     832 |    18349 |        42.5 |         26.1 |
| E       |     479 |    21514 |        24.5 |         30.6 |

`[FAIT]` **Non sature.** 67.0 % du bras halal et 56.7 % du temoin sont en D ou E ; le seuil de 80 % n'est atteint dans aucun des deux bras. La lettre garde du pouvoir discriminant a l'echelle du perimetre entier et reste utilisable comme variable de sortie. Le basculement editorial prevu par les specs n'est pas declenche par ce critere.

`[FAIT]` Le detail par sous-categorie montre que la moyenne du perimetre masque deux regimes : la charcuterie seche est en D-E a plus de 99 % dans les deux bras, les decoupes et plats cuisines beaucoup moins.

| sous_categorie          | bras   |   n_note |   pct_DE |   score_moyen |   score_median |
|:------------------------|:-------|---------:|---------:|--------------:|---------------:|
| autres_carnes           | halal  |      356 |     65.7 |         11.58 |             12 |
| autres_carnes           | temoin |    15961 |     52.5 |         10.35 |             11 |
| charcuterie_cuite       | halal  |      342 |     76.3 |         12.68 |             14 |
| charcuterie_cuite       | temoin |    13694 |     76.8 |         14.98 |             13 |
| charcuterie_seche       | halal  |      235 |     99.1 |         26.76 |             28 |
| charcuterie_seche       | temoin |     6143 |     99.3 |         29.57 |             33 |
| decoupes                | halal  |      204 |     41.7 |          5.84 |              3 |
| decoupes                | temoin |     8317 |      9.3 |         -0.9  |             -2 |
| foie_gras               | halal  |        1 |    100   |         14    |             14 |
| foie_gras               | temoin |       80 |     97.5 |         20.24 |             21 |
| panes                   | halal  |      293 |     46.4 |          7.31 |              6 |
| panes                   | temoin |     2208 |     28.7 |          4.91 |              4 |
| plats_cuisines          | halal  |      142 |     29.6 |          7.32 |              5 |
| plats_cuisines          | temoin |    11075 |     19.3 |          5.46 |              4 |
| rillettes_pates_mousses | halal  |       39 |     89.7 |         16.23 |             18 |
| rillettes_pates_mousses | temoin |     5746 |     92.4 |         17.84 |             19 |
| saucisses               | halal  |      241 |     95.4 |         17.68 |             18 |
| saucisses               | temoin |     5988 |     92.8 |         18.7  |             19 |
| viande_hachee           | halal  |      103 |     52.4 |          9.87 |             11 |
| viande_hachee           | temoin |     1129 |     34.1 |          7.66 |              6 |

`[INFERENCE]` Dans les strates ou les deux bras depassent 90 % de D-E (charcuterie seche, saucisses, rillettes), la lettre ne discrimine plus rien localement, meme si elle discrimine a l'echelle du perimetre. Pour ces rayons precis, la recommandation editoriale des specs s'applique : parler sel pour 100 g et pourcentage de viande, pas Nutri-Score.

`[HYPOTHESE]` L'export plat n'expose qu'une colonne `nutriscore_grade`, sans indication de version d'algorithme. Le rapport la traite comme la note publiee par Open Food Facts a la date du dump. Le recalcul FSAm-NPS versionne 2017 / 2023 est un travail de couche 3.

---

## 4. Certificateurs : separables de la marque ?

`[FAIT]` 16 tags de certificateur distincts apparaissent dans `labels_tags` a cote de `en:halal`.

| certificateur                                                            |   n_produits |   n_marques |
|:-------------------------------------------------------------------------|-------------:|------------:|
| fr:societe-francaise-de-controle-de-viande-halal                         |          116 |          19 |
| en:societe-francaise-de-controle-de-viande-halal-grande-mosquee-de-paris |           44 |           7 |
| en:halal-food-council-of-europe                                          |           28 |           8 |
| fr:societe-francaise-de-controle-de-viande-halal-grande-mosquee-de-paris |            6 |           2 |
| fr:halal-certification-germany                                           |            3 |           3 |
| fr:tracabilite-100-halal                                                 |            3 |           1 |
| en:societe-francaise-de-controle-de-viande-halal                         |            2 |           2 |
| fr:organisme-de-controle-independant-avs-halal                           |            1 |           1 |
| fr:halal-food-concil-of-europe                                           |            1 |           1 |
| en:label-certification-halal                                             |            1 |           1 |
| fr:controle-certification-avs-halal                                      |            1 |           1 |
| fr:id-halal                                                              |            1 |           1 |
| en:tracabilite100halal                                                   |            1 |           1 |
| fr:controle-grande-mosquee-de-lyon-halal                                 |            1 |           1 |
| fr:controle-mosquee-de-paris-halal                                       |            1 |           1 |
| fr:halal-mosquee-courcouronnes                                           |            1 |           1 |

`[FAIT]` **Inexploitable EN L'ETAT DU TAG, pour couverture et non pour separabilite.** Seuls 165 produits halal sur 2387 portent un tag de certificateur, soit 6.9 %. Une variable renseignee sur moins de 7 % des cas ne permet aucune comparaison, separable ou non. La separabilite elle-meme reste INCONNUE : les produits tagues ne sont pas un echantillon representatif, ce sont ceux dont un contributeur a pris la peine de saisir le certificateur. La question n'est donc pas close, elle est renvoyee a la lecture d'image de la couche 2 (section 4bis).

`[FAIT]` Plusieurs tags designent le meme organisme sous des orthographes differentes — les variantes `fr:` et `en:` de la Societe francaise de controle de viande halal en sont l'exemple. Le comptage ci-dessus est donc une borne HAUTE du nombre d'organismes distincts.

`[INFERENCE]` Consequence immediate pour la couche 4 : en l'etat du tag, le facteur certificateur ne peut pas entrer dans le modele. Il n'y sera pas inclus en esperant que le modele demele. Sa reintroduction est conditionnee au resultat de la section suivante.

### 4bis. Voie de recuperation : lecture du certificateur sur l'image

`[FAIT]` Le certificateur est imprime sur l'emballage. La couverture photo du bras halal ne limite pas cette voie :

| bras   |     n |   pct_photo_face |   pct_photo_ingredients |   pct_au_moins_une |
|:-------|------:|-----------------:|------------------------:|-------------------:|
| halal  |  2387 |             98.3 |                    56.9 |               99.7 |
| temoin | 88011 |             94.2 |                    56.7 |               96.3 |

`[FAIT]` 99.7 % des produits halal ont au moins une photo. Le facteur limitant est le renseignement du tag, pas la disponibilite de l'image.

`[HYPOTHESE]` Un modele de vision de petite taille peut lire le logo du certificateur sur ces photos. Trois conditions non verifiees a ce jour, toutes verifiables en couche 2 :

1. **Resolution.** Les URL de l'export pointent des images en 400 px sur le grand cote. Un logo de certificateur y occupe quelques dizaines de pixels. Une taille superieure semble accessible en changeant le suffixe de l'URL ; non verifie, l'hote images est injoignable depuis l'environnement d'execution de ce depot.
2. **Presence du logo sur la face photographiee.** Une part inconnue des certifications n'apparait ni sur la face ni sur la photo ingredients.
3. **Taux d'erreur mesure.** Il doit l'etre contre un echantillon recode a la main en aveugle, par un humain, au meme standard que le parseur du pourcentage de viande.

`[INFERENCE]` L'erreur de lecture ne sera pas aleatoire, elle sera **correlee a la marque** : une marque, un design d'emballage, le meme logo au meme endroit sur toute la gamme. Un logo mal lu l'est alors sur l'integralite des references de cette marque d'un seul coup. Injectee telle quelle dans le modele mixte de la couche 4, cette erreur produit un effet certificateur qui n'est qu'un effet marque mal mesure — exactement le confondant que le modele est cense demeler. Une erreur aleatoire dilue un effet ; celle-ci en fabrique un.

`[INFERENCE]` La parade est celle que les specs imposent deja pour le statut halal : verifier **par marque et par design d'emballage**, pas par produit. Les 42 marques de la section 5 couvrent l'essentiel du bras halal. Le modele de vision ne tranche pas le certificateur reference par reference : il lit le design de reference de chaque marque, valide a la main une fois, puis sert a reperer les produits dont l'emballage s'ecarte de ce design.

`[INFERENCE]` Priorite : ce passage sur les images doit d'abord servir a mesurer le taux de faux negatifs du tag halal (section 5), qui commande l'amplitude de tous les ecarts de la section 6. Le certificateur est un sous-produit du meme passage, pas sa justification.

---

## 5. Sous-etiquetage du tag halal

`[FAIT]` 42 marques comptent au moins 5 produits tagues halal dans le perimetre.

| marque_tag       | marque_affichee      |   n_produits |   n_tagues |   pct_tague |
|:-----------------|:---------------------|-------------:|-----------:|------------:|
| carrefour        | carrefour            |         2868 |         61 |         2.1 |
| fleury-michon    | Fleury Michon        |         1084 |         75 |         6.9 |
| lidl             | Lidl                 |          443 |          8 |         1.8 |
| socopa           | Socopa               |          265 |          7 |         2.6 |
| isla-delice      | Isla Délice          |          192 |        190 |        99   |
| sans-marque      | Sans marque, St Géry |          188 |          9 |         4.8 |
| reghalal         | Reghalal             |          147 |        129 |        87.8 |
| aia              | Aia, Montorsi        |           93 |         21 |        22.6 |
| oriental-viandes | Oriental viandes     |           91 |         85 |        93.4 |
| isla-mondial     | Isla Mondial         |           80 |         78 |        97.5 |
| arabi            | arabi                |           49 |         48 |        98   |
| jack-link-s      | Jack Link's          |           42 |          6 |        14.3 |
| duc              | DUC                  |           41 |          5 |        12.2 |
| id-halal         | Id Halal             |           38 |         38 |       100   |
| royal-halal      | Royal Halal          |           30 |         30 |       100   |
| suntat           | suntat               |           25 |         25 |       100   |
| al-jadid         | Al Jadid             |           24 |         22 |        91.7 |
| halal            | halal                |           24 |         23 |        95.8 |
| wassila          | Wassila              |           22 |         22 |       100   |
| doux             | Doux, Père Dodu      |           19 |          5 |        26.3 |
| hunkar           | Hunkar               |           17 |         14 |        82.4 |
| medina-halal     | MEDINA HALAL         |           15 |         15 |       100   |
| volibon          | Volibon              |           15 |         15 |       100   |
| dounia-halal     | Dounia Halal         |           14 |         14 |       100   |
| kenza-halal      | Kenza halal          |           14 |         14 |       100   |

`[FAIT]` Parmi ces 42 marques, 29 ont au moins 80 % de leur gamme carnee taguee halal, soit 916 produits. Parmi eux, 39 ne portent pas le tag alors que la marque est manifestement specialisee.

`[INFERENCE]` Cela donne une **borne basse** du taux de faux negatifs de 4.26 % chez les marques specialisees. Borne basse seulement : la methode ne voit pas les gammes halal des marques generalistes. Carrefour compte 2868 produits carnes dans le perimetre dont 61 tagues : impossible de savoir par cette voie combien de references halal de l'enseigne ne portent pas le tag.

`[FAIT]` **Mesure directe, couche 2.** Un echantillon aleatoire de 96 produits du temoin et 100 produits tagues halal a ete recode a la main, en aveugle, par un humain (`donnees_humaines/double_codage.csv`).

| bras   | mesure                                 |   k |   n |   taux_pct |   ic95_bas_pct |   ic95_haut_pct |
|:-------|:---------------------------------------|----:|----:|-----------:|---------------:|----------------:|
| temoin | faux negatifs (temoin avec estampille) |   0 |  96 |          0 |            0   |             3.8 |
| halal  | tagues halal SANS estampille trouvee   |  16 | 100 |         16 |           10.1 |            24.4 |

`[FAIT]` **0 produit sur 96 du temoin porte une estampille halal**, soit 0.0 % (IC 95 % de Wilson [0.0 ; 3.8] %).

`[FAIT]` Cette mesure CONTREDIT ce que ce rapport avancait dans ses versions precedentes. La borne basse de 4,26 % calculee plus haut porte sur les seules marques specialisees halal, une sous-population choisie pour maximiser le phenomene ; en faire un plancher du taux global etait une extrapolation abusive. Le taux sur un tirage aleatoire du temoin est compatible avec zero.

`[INFERENCE]` Consequence directe : la contamination du temoin par des produits halal non tagues n'est PAS le facteur limitant de l'etude. Les ecarts de la section 6 ne sont pas d'amplitude inconnue de ce fait la. Les autres limites de la section 7 demeurent entieres, en particulier la confusion avec le degre de transformation.

`[FAIT]` L'ecart joue dans l'autre sens : 16 produits sur 100 tagues `en:halal` ne montrent AUCUNE estampille reperable, soit 16.0 % (IC 95 % [10.1 ; 24.4] %). Le tag est donc plus large que ce qu'un consommateur verifierait en rayon.

`[HYPOTHESE]` Ces 16 produits peuvent etre des erreurs de tag, des estampilles absentes de la face photographiee, ou des produits dont la certification n'est plus a jour. Non tranche.

`[FAIT]` Limite de la mesure : le codeur a etabli le statut de 38 produits par recherche externe et non sur la photo, tous dans le bras halal. Si cet effort de recherche n'a pas ete symetrique entre les deux bras, le zero du temoin est sous-estime. La colonne `source_lecture` du fichier de codage permet de rejouer la mesure sur les seules lectures faites sur image.

---

## 6. Comparaison brute : sel pour 100 g

Deux variables seulement, comme prevu par les specs : sel pour 100 g et Nutri-Score. Aucun ajustement, aucun appariement. Restreint aux produits a donnees nutritionnelles completes.

| sous_categorie          |   n_halal |   n_temoin |   sel_median_halal |   sel_q1_halal |   sel_q3_halal |   sel_median_temoin |   sel_q1_temoin |   sel_q3_temoin |   diff_medianes |   ic95_bas |   ic95_haut | testable_regle_30   |
|:------------------------|----------:|-----------:|-------------------:|---------------:|---------------:|--------------------:|----------------:|----------------:|----------------:|-----------:|------------:|:--------------------|
| autres_carnes           |       358 |      15716 |               1.8  |           1.21 |           2.52 |                1.3  |            0.4  |            1.9  |            0.5  |      0.4   |        0.7  | True                |
| charcuterie_cuite       |       343 |      13206 |               2.4  |           1.9  |           3    |                1.9  |            1.7  |            2.5  |            0.5  |      0.5   |        0.6  | True                |
| panes                   |       290 |       2154 |               1.27 |           1    |           1.5  |                1.1  |            0.8  |            1.3  |            0.17 |      0.14  |        0.2  | True                |
| saucisses               |       240 |       5778 |               2.2  |           1.83 |           2.57 |                1.9  |            1.7  |            2.2  |            0.3  |      0.165 |        0.3  | True                |
| charcuterie_seche       |       235 |       6031 |               3.6  |           2.6  |           4.4  |                4.3  |            3.4  |            4.8  |           -0.7  |     -0.8   |       -0.5  | True                |
| decoupes                |       208 |       7939 |               1.3  |           0.56 |           1.8  |                0.25 |            0.13 |            1.21 |            1.05 |      0.94  |        1.25 | True                |
| plats_cuisines          |       142 |      10770 |               1.15 |           0.9  |           1.5  |                0.87 |            0.7  |            1.1  |            0.28 |      0.13  |        0.4  | True                |
| viande_hachee           |       104 |       1118 |               0.2  |           0.17 |           0.81 |                0.22 |            0.17 |            0.84 |           -0.02 |     -0.02  |        0    | True                |
| rillettes_pates_mousses |        39 |       5594 |               1.5  |           1.4  |           1.9  |                1.5  |            1.2  |            1.7  |            0    |      0     |        0.3  | True                |
| foie_gras               |         1 |         77 |               2.88 |           2.88 |           2.88 |                1.2  |            1.1  |            1.4  |          nan    |    nan     |      nan    | False               |
| _ensemble_              |      1960 |      68383 |               1.8  |           1.2  |           2.6  |                1.5  |            0.85 |            2    |            0.3  |      0.3   |        0.4  | True                |

Les colonnes `ic95_*` bornent la difference de medianes par bootstrap percentile (4 000 tirages, graine figee). Elles disent si l'ecart observe est distinguable du bruit d'echantillonnage. Elles ne disent rien de la confusion decrite en section 7.

`[FAIT]` Sur l'ensemble du perimetre, la mediane de sel est de 1.8 g/100 g au bras halal contre 1.5 g/100 g au temoin, soit un ecart de +0.30 g/100 g (IC 95 % [+0.30 ; +0.40]).

`[FAIT]` Par sous-categorie, l'ecart est en faveur du temoin (halal plus sale) dans 6 strates sur 10 avec un IC excluant zero : autres_carnes, charcuterie_cuite, panes, saucisses, decoupes, plats_cuisines.

`[FAIT]` L'ecart s'inverse dans 1 strate(s) — le bras halal y est MOINS sale : `charcuterie_seche` (-0.70 g/100 g).

`[FAIT]` L'ecart n'est pas distinguable de zero dans 3 strate(s) : viande_hachee, rillettes_pates_mousses, foie_gras.

`[FAIT]` Dispersion interne au bras halal, par sous-categorie :

| sous_categorie          |   n |   sel_median |   sel_p10 |   sel_p90 |   ecart_interdecile |   ags_median |
|:------------------------|----:|-------------:|----------:|----------:|--------------------:|-------------:|
| autres_carnes           | 363 |         1.8  |      0.53 |      3.49 |                2.96 |         2.3  |
| charcuterie_cuite       | 345 |         2.4  |      1.8  |      3.45 |                1.65 |         0.9  |
| panes                   | 292 |         1.27 |      0.86 |      1.87 |                1.01 |         2.5  |
| saucisses               | 241 |         2.2  |      1.7  |      3    |                1.3  |         5.4  |
| charcuterie_seche       | 239 |         3.6  |      2.2  |      5.1  |                2.9  |         9.35 |
| decoupes                | 222 |         1.27 |      0.11 |      2.3  |                2.19 |         2    |
| plats_cuisines          | 144 |         1.15 |      0.61 |      2.23 |                1.62 |         1.8  |
| viande_hachee           | 105 |         0.2  |      0.14 |      1.2  |                1.06 |         8    |
| rillettes_pates_mousses |  39 |         1.5  |      1.21 |      2.32 |                1.11 |         6.8  |

`[FAIT]` Dans 9 strates sur 9, l'ecart interdecile INTERNE au bras halal depasse l'ecart de medianes entre bras. Le rapport des deux va de 2.1 a inf, mediane 5.8.

`[INFERENCE]` Choisir un bon produit halal plutot qu'un mauvais produit halal change plus la teneur en sel que choisir halal plutot que non halal. C'est le resultat le plus solide de cette couche, et c'est aussi le seul directement actionnable en rayon.

---

## 7. Ce que cet ecart ne demontre pas

`[FAIT]` A sous-categorie egale, le bras halal est plus transforme que le temoin dans 9 strates sur 10. L'ecart median de part de produits classes NOVA 4 est de +11.5 points.

| sous_categorie          | bras   |   n_nova |   pct_nova4 |
|:------------------------|:-------|---------:|------------:|
| autres_carnes           | halal  |      120 |        86.7 |
| autres_carnes           | temoin |     6396 |        59   |
| charcuterie_cuite       | halal  |      247 |        98.8 |
| charcuterie_cuite       | temoin |     6472 |        76.7 |
| charcuterie_seche       | halal  |      142 |        98.6 |
| charcuterie_seche       | temoin |     2892 |        91.9 |
| decoupes                | halal  |       74 |        64.9 |
| decoupes                | temoin |     2409 |        49.3 |
| foie_gras               | halal  |        1 |         0   |
| foie_gras               | temoin |       82 |        13.4 |
| panes                   | halal  |      119 |        96.6 |
| panes                   | temoin |     1104 |        88   |
| plats_cuisines          | halal  |       88 |        90.9 |
| plats_cuisines          | temoin |     7090 |        80.3 |
| rillettes_pates_mousses | halal  |       18 |        88.9 |
| rillettes_pates_mousses | temoin |     2267 |        49.6 |
| saucisses               | halal  |      142 |       100   |
| saucisses               | temoin |     2388 |        92.6 |
| viande_hachee           | halal  |       59 |        49.2 |
| viande_hachee           | temoin |      628 |        36.9 |

`[FAIT]` Sur l'ensemble du perimetre, 90.9 % des produits halal notes sont NOVA 4 contre 71.9 % des temoins (1010 et 31728 produits notes respectivement).

`[INFERENCE]` Les sous-categories de ce rapport melangent, sous un meme nom, des produits de degre de transformation different. La strate `decoupes` en est la demonstration : le temoin y contient de la viande fraiche non salee, le bras halal des produits cuits ou marines. L'ecart de sel de +1.05 g/100 g qu'on y lit mesure d'abord cette difference de composition, pas un effet du label.

`[HYPOTHESE]` Une fois apparies sur la sous-categorie fine, l'espece et le segment de gamme, les ecarts de sel se reduiraient sensiblement. Non teste ici. C'est l'objet de la couche 3, et aucune phrase d'article ne doit etre ecrite avant.

`[FAIT]` La couverture NOVA est partielle : 1010 produits halal notes sur 2387, soit 42 %. Les pourcentages ci-dessus portent sur les produits notes, pas sur le perimetre.

Trois autres limites, toutes structurelles :

1. `[FAIT]` Le traitement est le LABEL, pas la halalite. Un produit halal non estampille dans Open Food Facts est au temoin. La section 5 en donne une borne basse, pas la mesure.
2. `[FAIT]` Open Food Facts est une base contributive. Les produits renseignes ne sont pas un echantillon aleatoire du rayon : ils sont ceux que des contributeurs ont scannes. Rien dans ce depot ne corrige ce biais de selection, et la couche 1 ne peut pas le mesurer.
3. `[FAIT]` Aucune ponderation par les volumes de vente. Une reference confidentielle pese autant qu'un best-seller.

---

## 8. Ce que la couche 1 rend possible pour la suite

`[FAIT]` Le releve manuel de la grille additifs, prevu en couche 5, porte sur 282 codes E distincts dans le perimetre, dont 112 suffisent a couvrir 99 % des occurrences.

| additif   |     n |   dont_halal |
|:----------|------:|-------------:|
| en:e250   | 11321 |          519 |
| en:e301   |  6399 |          325 |
| en:e316   |  3867 |          217 |
| en:e14xx  |  3416 |          110 |
| en:e252   |  3236 |           75 |
| en:e300   |  2735 |          150 |
| en:e262   |  2702 |          252 |
| en:e451   |  2542 |          348 |
| en:e450   |  2436 |          388 |
| en:e330   |  2302 |           96 |
| en:e407   |  2077 |          170 |
| en:e326   |  1934 |           94 |
| en:e415   |  1736 |           29 |
| en:e331   |  1695 |          172 |
| en:e150a  |  1217 |           93 |
| en:e120   |  1134 |           26 |
| en:e428   |  1130 |            4 |
| en:e412   |  1034 |           31 |
| en:e621   |  1029 |          188 |
| en:e452   |   999 |          115 |

`[INFERENCE]` 112 codes a relever a la main, c'est plus que les 40 esperes par les specs mais cela reste faisable en une session de travail. Le recalcul du score Yuka de la couche 5 n'est pas bloque.

`[FAIT]` E250 (nitrite de sodium) est l'additif le plus frequent du perimetre, present sur 11321 produits. L'extraction des nitrites prevue en couche 2 a donc une base suffisante.

`[FAIT]` NOVA par bras, sur les produits notes :

|   nova |   halal |   temoin |   pct_halal |   pct_temoin |
|-------:|--------:|---------:|------------:|-------------:|
|      1 |      71 |     3193 |         7   |         10.1 |
|      2 |       1 |       10 |         0.1 |          0   |
|      3 |      20 |     5701 |         2   |         18   |
|      4 |     918 |    22824 |        90.9 |         71.9 |

---

## 9. Ecarts aux specs et decisions actees

| Point | Specs | Realise | Motif |
|---|---|---|---|
| Source | `food.parquet` sur HuggingFace | Export plat CSV officiel Open Food Facts, mirroir S3 | Hote `huggingface.co` refuse par la politique de sortie reseau de l'environnement (403 sur le CONNECT). Meme organisation, meme base, memes licences. |
| Nutri-Score 2023 | Emplacement a determiner apres inspection du schema | Colonne unique `nutriscore_grade`, version non exposee | L'export plat ne versionne pas la note. Recalcul FSAm-NPS renvoye en couche 3. |
| Comparaison | Mediane, quartiles, effectifs | Idem, plus un IC 95 % bootstrap sur la difference de medianes | Ajout assume : sans lui, le rapport ne peut pas dire si un ecart est distinguable du bruit. Ce n'est ni un ajustement ni un appariement. |
| Photos d'emballage | Colonne `images` structuree | URL d'image principale seulement | Limite de l'export plat. L'audit visuel de la couche 2 reste possible via `image_url`. |

`[FAIT]` Une deduplication de code-barres est appliquee au perimetre : l'export contient de rares doublons (deux revisions d'un meme produit). La revision la plus recente est conservee, le compte est imprime par `src/etape1_perimetre.py` et l'assertion A3 verifie qu'il n'en reste aucun.

---

## 10. Decision de faisabilite

`[FAIT]` L'etude est faisable. Les neuf sous-categories du perimetre franchissent la regle des 30, le bras halal compte 1960 produits a donnees completes, et les variables de sortie prevues (sel, Nutri-Score, NOVA, additifs) sont renseignees a un taux exploitable.

`[FAIT]` Deux questions sont fermees des maintenant :

- L'effet certificateur est abandonne, pour couverture insuffisante (6.9 % des produits halal). Il sort du plan de la couche 4.
- Le basculement editorial integral vers le sel n'est pas declenche : le Nutri-Score n'est pas sature a l'echelle du perimetre. Il l'est en revanche dans la charcuterie seche, les saucisses et les rillettes, ou la recommandation des specs s'applique localement.

`[FAIT]` Une question devient prioritaire et conditionne tout le reste : le taux de faux negatifs du tag halal dans le temoin. Tant qu'il n'est pas mesure sur photo, l'amplitude de tous les ecarts de la section 6 est inconnue. C'est le premier livrable de la couche 2.

`[INFERENCE]` Le titre defendable a ce stade n'est pas « le halal est plus sale ». C'est la dispersion interne : a l'interieur meme de l'offre halal, l'ecart entre le premier et le dernier decile de sel depasse partout l'ecart entre les deux bras. Le lecteur en rayon gagne plus a comparer deux paquets halal entre eux qu'a arbitrer entre halal et non halal. Ce constat tient sans appariement et ne depend pas de la composition du temoin, donc pas de sa contamination par des produits halal non tagues. Il reste sensible a un biais de selection interne : les produits halal non tagues sont absents du bras halal, et rien ici ne dit qu'ils y auraient la meme dispersion.
