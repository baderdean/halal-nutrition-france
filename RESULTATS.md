# Qualite nutritionnelle des produits carnes halal en France

## Resultats, hypothese par hypothese

Document **genere** par `src/rapport_hypotheses.py` depuis `sorties/`.
Ne pas l'editer a la main : il serait ecrase, et surtout il se mettrait
a diverger des donnees. Trois corrections de cette etude ont deja
renverse un resultat publie.

### Ce que l'etude mesure, et ce qu'elle ne mesure pas

Le traitement est **le label**, pas la halalite. Tout ce qui suit porte
sur une mention d'etiquetage declaree par le fabricant, telle que la
base Open Food Facts la reporte. Rien ici ne dit quoi que ce soit de la
conformite religieuse, de la validite d'une certification, du respect
d'un cahier des charges ou de la securite sanitaire d'un produit.

L'etude est **observationnelle**. Les produits ne sont pas assignes au
hasard a un label : aucun verdict ci-dessous n'est causal, meme quand
un ecart est etabli avec un intervalle etroit.

Les marques et les organismes de certification nommes le sont toujours
avec leurs effectifs et leurs intervalles.

### Vocabulaire des verdicts

| verdict | sens |
|:--|:--|
| **ETABLI** | IC 95 % excluant zero, cellules au-dessus de 30 |
| **NON ETABLI** | teste, IC contenant zero. Pas une preuve d'absence |
| **NON TESTABLE** | effectifs insuffisants. Decrit, jamais teste |
| **REFUTE** | un controle fait disparaitre ou inverse l'ecart |

### Le jeu de donnees

- Dump Open Food Facts fige du **2026-09-03T11:55:24Z**, sha256 `f72687ee8bc65220…`, epingle par son `versionId` S3.
- Perimetre carne France : **90337 produits**, dont **2382 halal** et **87955 temoin**.
- A nutrition complete : **70288**, dont **1955 halal**.
- Licences ODbL / DbCL, contributeurs Open Food Facts.

---

## 1. Ce que vaut le perimetre

Avant toute hypothese : de quoi les chiffres sont-ils faits.

### Assertions bloquantes

Le pipeline s'arrete si l'une echoue. Elles ne prouvent pas que
l'etude est juste ; elles empechent qu'elle devienne fausse en
silence.

| assertion | ce qu'elle verifie |
|:--|:--|
| A1 | integrite des lignes, code et categorie presents |
| A2 | halal + temoin = total du perimetre |
| A3 | aucun code-barres duplique |
| A4 | chaque sous-categorie declaree est peuplee |
| A5 | valeurs dans les bornes physiques |
| A6 | effectifs conformes a la reference figee |
| A7 | part des produits halal classes porc sous 2 % |

A7 recense **26 produits halal classes porc**. La liste est publiee (`sorties/a7_halal_classes_porc.csv`) : elle melange des erreurs de taxonomie Open Food Facts et de vraies erreurs d'etiquetage.

### Defauts connus, corriges

- **Aides culinaires** (fonds, bouillons) exclues : un fond de veau a
  22 g de sel pour 100 g n'est pas un aliment consomme tel quel.
- **Strate « decoupes » scindee** entre decoupe crue et preparation
  marinee. Le melange differait entre les bras et l'ecart de sel qu'on
  y lisait etait pour l'essentiel un ecart de forme de produit.
- **Bornes de plausibilite** : 481 produits portaient plus de 10 g de
  sel pour 100 g, dont une saucisse a 100 g. Plafond pose a 15 g.

### Defauts connus, NON corriges

- Quatre marques au nom evoquant un produit de la mer figurent au
  classement des marques malgre l'exclusion composee du perimetre.
  Liste dans `sorties/classement_alerte_mer.csv`. **Le haut du
  classement des marques n'est pas publiable avant verification
  produit par produit.**
- Le taux de faux negatifs de l'etiquetage halal n'est mesure que sur
  43 lectures d'image comparables, contre 200 requises.

---

## 2. L'effet du label

### H1 — A produit comparable, le label halal va avec un moins bon Nutri-Score

**Verdict : ETABLI**

*Methode.* Appariement exact grossier sur sous-categorie et espece, agregation ponderee par l'effectif halal de la strate, IC par bootstrap percentile (graine 20260904).

Deux estimands, jamais melanges.

- **E1, effet total** : espece non ajustee. L'exclusion du porc
  est un MEDIATEUR assume du label, pas un biais.
- **E2, effet direct** : a espece et sous-categorie identiques.

| variable | E1 total | IC 95 % | E2 direct | IC 95 % |
|:--|--:|:-:|--:|:-:|
| nutriscore_score | +0.90 | [+0.41 ; +1.80] | +7.24 | [+5.89 ; +7.47] |
| sel | +0.22 | [+0.20 ; +0.30] | +0.48 | [+0.44 ; +0.56] |
| ags | -1.08 | [-1.27 ; -0.87] | +0.39 | [+0.28 ; +0.53] |
| proteines | -2.71 | [-3.00 ; -2.38] | -2.56 | [-2.82 ; -2.15] |

Ponderation ATT : la question posee est « les produits
halal seraient-ils differents s'ils n'etaient pas halal », pas
« le rayon entier serait-il different ».

*Reserves.*
- Observationnel : ni le label ni l'espece ne sont assignes au hasard.
- E1 et E2 ne repondent pas a la meme question et ne se comparent pas terme a terme.
- L'ecart porte sur des MEDIANES de strates, pas sur un produit type.

### H2 — Le label halal va avec plus de sel

**Verdict : ETABLI**

*Methode.* Meme appariement que H1, variable sel pour 100 g.

E2 direct : **+0.49 g/100 g** [+0.44 ; +0.56].

L'ecart survit au controle de l'espece et de la sous-categorie. La
couche 7 en propose un mecanisme, teste plus bas en H14.

*Reserves.*
- Le sel declare n'est pas le sel dose : c'est une valeur d'etiquetage.

### H3 — Le label halal va avec moins de proteines

**Verdict : ETABLI**

*Methode.* Meme appariement, variable proteines pour 100 g.

E1 total : **-2.71 g/100 g** [-3.00 ; -2.38].
E2 direct : **-2.56 g/100 g** [-2.82 ; -2.15].

C'est le seul ecart de meme ampleur dans les deux estimands : il ne
vient donc pas du changement d'espece.

*Reserves.*
- Voir H14 : l'hypothese de l'hydratation en propose la cause proximale.

---

### H4 — L'abattage rituel explique l'ecart : le kasher devrait etre aussi penalise

**Verdict : REFUTE**

*Methode.* Comparaison a trois bras, halal / kasher / ni l'un ni l'autre, sur le perimetre entier puis par sous-categorie.

| bras | n | mediane Nutri-Score | ecart au temoin | IC 95 % |
|:--|--:|--:|--:|:-:|
| temoin | 67753 | +12.0 | — | — |
| halal | 1943 | +13.0 | +1.0 | [+0.00 ; +1.00] |
| kasher | 153 | +4.0 | -8.0 | [-9.00 ; -7.00] |

Le kasher subit une contrainte d'abattage rituel comparable et
s'adresse a une autre population : c'est le contrefactuel le
plus proche disponible.

Le kasher fait **-8.0 points** [-9.0 ; -7.0], soit nettement
MIEUX que le temoin, quand le halal fait +1.0. Si la contrainte
rituelle expliquait l'ecart, les deux bras iraient dans le meme
sens. Ils vont en sens contraire.

*Reserves.*
- Le kasher ne franchit 30 que sur le jambon cuit et les deux plus grosses sous-categories : partout ailleurs il est decrit, jamais teste.
- La composition en gammes des deux bras differe ; l'ecart de -8 n'est pas decomposable a espece egale faute d'effectifs.
- Deux populations de consommateurs differentes, deux marches differents : ce n'est pas une experience.

---

## 3. Marque, certificateur, origine : ce qui separe et ce qui ne separe pas

### H5 — On peut classer les marques les unes contre les autres

**Verdict : NON ETABLI — l'ordre total n'existe pas**

*Methode.* Ecart de chaque produit a la mediane de marche de sa strate (sous-categorie x espece), agrege en mediane par marque, IC bootstrap. Intervalles de rang par disjonction des IC.

Les 398 marques du perimetre sont classees sur leur ecart a la mediane de marche de leur strate.

- Paires effectivement separees : **29.9 %** des 79 003.
- Largeur mediane de l'intervalle de rang : **292 rangs sur 398**.
- **Aucun point de coupure** : les IC forment une chaine continue du rang 1 au dernier.

Le rang ponctuel ne se lit donc pas seul. `rang_min`-`rang_max`
borne ce que les donnees soutiennent.

*Reserves.*
- Le critere de disjonction est conservateur : les intervalles de rang publies sont au pire trop larges, jamais trop etroits.
- Quatre marques de produits de la mer polluent le haut du classement (defaut de perimetre non corrige).

### H6 — Les marques halal sont moins bonnes que les autres

**Verdict : ETABLI pour les specialistes, REFUTE pour les generalistes**

*Methode.* Classement sur le catalogue entier, puis separation par part du catalogue taguee halal.

Le rang median des marques marquees « gamme halal » melange
deux populations que la sortie D4 separe :

| profil de catalogue | marques | rang median | ecart median |
|:--|--:|--:|--:|
| gamme halal marginale (< 5 produits) | 21 | 177 | +0.0 |
| gamme halal minoritaire | 9 | 192 | +0.0 |
| specialiste halal | 13 | 361 | +5.0 |

Une marque generaliste est classee par son catalogue,
majoritairement non halal : son rang ne dit rien de sa gamme
halal. Seule la ligne « specialiste halal » se lit comme un
resultat portant sur le bras halal.

*Reserves.*
- Un classement de marques nomme des entreprises reelles : il n'a de sens qu'avec ses effectifs et ses intervalles.

### H7 — Dans le halal, certaines marques font nettement mieux que d'autres

**Verdict : ETABLI**

*Methode.* Ecart a la mediane de marche de la strate, calcule sur le seul bras halal. Marque halal = au moins 5 produits tagues et au moins 50 % du catalogue carne tague, seuil tombant dans un vide de la distribution.

12 marques halal estimables, classees sur leurs SEULS produits halal :

| rang | rangs possibles | marque | n | % catalogue | ecart | IC 95 % |
|--:|:-:|:--|--:|--:|--:|:-:|
| 1 | 1-6 | Royal HALAL | 29 | 100 | +0.0 | [-1.00 ; +1.00] |
| 2 | 1-11 | Isla Mondial | 74 | 98 | +2.5 | [+1.00 ; +8.50] |
| 3 | 1-11 | ID-Halal | 35 | 100 | +3.0 | [+0.00 ; +10.00] |
| 4 | 2-11 | Oriental Viandes | 80 | 93 | +4.0 | [+2.00 ; +8.00] |
| 5 | 1-12 | Wassila | 21 | 100 | +4.0 | [+0.00 ; +12.00] |
| 6 | 2-11 | Isla Délice | 181 | 99 | +4.0 | [+2.00 ; +9.00] |
| 7 | 2-11 | Réghalal | 97 | 88 | +6.0 | [+3.00 ; +10.00] |
| 8 | 1-12 | Al Jadid | 19 | 92 | +6.0 | [-3.00 ; +12.00] |
| 9 | 1-11 | Halal | 19 | 96 | +6.0 | [+0.00 ; +10.00] |
| 10 | 2-11 | suntat | 21 | 100 | +6.0 | [+2.00 ; +8.00] |
| 11 | 2-12 | Arabi | 43 | 98 | +11.0 | [+7.88 ; +12.00] |
| 12 | 9-12 | Volibon | 15 | 100 | +15.0 | [+12.00 ; +16.00] |

**Aucune marque halal ne fait mieux que la mediane de marche
de ses strates.** Le meilleur ecart est +0.0.

*Reserves.*
- 13 des 66 paires seulement sont separees : l'ordre ne se lit pas rang par rang.
- Le classement couvre 78 % des produits halal mais 36 % des marques halal : les 21 marques absentes sont petites, pas negligeables.

### H8 — L'ecart vient du LABEL et non du FABRICANT

**Verdict : REFUTE la ou le test est possible**

*Methode.* Comparaison halal / temoin a marque, produit et espece identiques. Seul test qui separe l'effet du label de celui du fabricant.

Jambon cuit de volaille, dans le bras halal :

| marque | n | Nutri-Score | sel | proteines |
|:--|--:|--:|--:|--:|
| fleury-michon | 54 | +2.0 | 1.80 | 21.0 |
| carrefour | 12 | +12.0 | 2.30 | 20.0 |
| isla-mondial | 28 | +13.0 | 2.40 | 18.9 |
| reghalal | 33 | +13.0 | 2.50 | 18.0 |
| arabi | 12 | +14.5 | 2.50 | 11.1 |
| isla-delice | 54 | +18.0 | 3.40 | 15.6 |

**Le meme produit, chez le meme fabricant, a la meme
espece** :

| produit | marque | espece | n halal | n temoin | ecart | IC 95 % |
|:--|:--|:--|--:|--:|--:|:-:|
| jambon_cuit | fleury-michon | poulet | 34 | 164 | +0.00 | [+0.00 ; +0.00] |

L'ecart de 10 a 12 points mesure a espece egale ne survit pas
au controle du fabricant. Il vient de la dispersion DANS le
bras halal : le meme jambon de volaille va de 2.0 a 18.0 selon
le fabricant, le sel de 1.8 a 3.4 g, les proteines de 21.0 a
16.6 g.

*Reserves.*
- **Une seule cellule au monde** permet ce controle dans ces donnees. Carrefour pointe dans l'autre sens mais a n=6 contre 5, donc descriptif.
- Un resultat sur un fabricant n'est pas un resultat sur le marche.

---

### H9 — Le certificateur est un indicateur de qualite nutritionnelle

**Verdict : NON TESTABLE — le certificateur n'est pas separable de la marque**

*Methode.* Ecart a la mediane de marche par organisme certificateur, avec test de sensibilite au retrait de la marque dominante.

Concentration de chaque organisme sur sa premiere marque :

| organisme | produits | marques | 1re marque | part |
|:--|--:|--:|--:|--:|
| Mosquee d'Evry-Courcouronnes | 225 | 29 | 63 | 28.0 % |
| ARGML — Grande Mosquee de Lyon | 165 | 18 | 129 | 78.2 % |
| AVS — A Votre Service | 139 | 15 | 56 | 40.3 % |
| SFCVH — Grande Mosquee de Paris | 92 | 16 | 55 | 59.8 % |
| Halal Food Council of Europe | 22 | 6 | 14 | 63.6 % |
| Achahada | 9 | 3 | 6 | 66.7 % |
| Halal Certification Germany | 6 | 3 | 3 | 50.0 % |
| Muslim Council International | 4 | 1 | 4 | 100.0 % |
| Extra Kalite | 4 | 2 | 2 | 50.0 % |
| Tracabilite 100 % Halal | 3 | 1 | 3 | 100.0 % |
| Centre Islamique de Aachen | 1 | 1 | 1 | 100.0 % |
| ID Halal | 1 | 1 | 1 | 100.0 % |
| World Islamic Foundation | 1 | 1 | 1 | 100.0 % |

Chaque comparaison entre organismes s'effondre au retrait de sa
marque dominante. Le marche halal francais est trop concentre
pour qu'un certificateur soit observe independamment de ses
marques.

*Reserves.*
- Le certificateur n'est lu que sur 31,9 % des produits halal : l'absence de mention n'est pas l'absence de certification.
- Un organisme mal classe le serait sur la formulation de ses clients, pas sur son propre travail. Nommer un organisme sur cette base serait une mise en cause infondee.

### H10 — Les certificateurs francais font mieux que les etrangers

**Verdict : REFUTE**

*Methode.* Comparaison par nationalite de l'organisme, puis retrait de la marque dominante du groupe.

Ecart a la mediane de marche, Nutri-Score continu :

| groupe | n | ecart | IC 95 % |
|:--|--:|--:|:-:|
| certificateur etranger | 39 | +12.0 | [+8.00 ; +13.00] |
| certificateur francais | 631 | +2.0 | [+2.00 ; +4.00] |
| sans certificateur | 1247 | +2.0 | [+2.00 ; +2.00] |

Les autres variables sont dans `sorties/c_nationalite.csv`.

L'ecart apparent tenait a une seule marque, qui pesait 42 % du
groupe etranger et se trouve etre la pire du classement. Retiree,
l'ecart passe sous le seuil.

*Reserves.*
- « Est dit francais un organisme dont le nom designe une institution francaise » : une convention de nommage, pas un fait juridique.

### H11 — Les certificateurs sans electronarcose font mieux

**Verdict : NON TESTABLE**

*Methode.* Regroupement des organismes selon une classification de la pratique d'abattage.

Ecart a la mediane de marche, Nutri-Score continu :

| groupe | n | marques | ecart | IC 95 % |
|:--|--:|--:|--:|:-:|
| avec electronarcose (declare) | 323 | 2 | +2.0 | [+1.00 ; +4.00] |
| sans certificateur | 1247 | 0 | +2.0 | [+2.00 ; +2.00] |
| sans electronarcose (declare) | 307 | 3 | +3.0 | [+1.00 ; +6.00] |

La colonne « marques » compte les marques distinctes du groupe :
deux marques pour le groupe « avec electronarcose », ce qui
suffit a expliquer pourquoi rien n'y est separable.

Meme obstacle qu'en H9 : la comparaison entre groupes
d'organismes est une comparaison entre leurs marques.

*Reserves.*
- **La classification des organismes par pratique d'electronarcose est DECLAREE PAR LE COMMANDITAIRE de l'etude. Elle n'est pas etablie par ce depot.** Toute publication doit citer les cahiers des charges des organismes eux-memes.
- Un organisme dont la pratique n'etait pas connue n'a pas ete devine : classer a tort un organisme sur une pratique d'abattage serait une mise en cause publique infondee.

### H12 — Les produits halal fabriques en France sont meilleurs

**Verdict : NON ETABLI**

*Methode.* Comparaison au sein du bras halal entre produits portant une mention de production francaise VISIBLE et les autres, puis a gamme egale.

| variable | ecart France / sans mention | IC 95 % |
|:--|--:|:-:|
| Nutri-Score | +0.00 | [-1.00 ; +1.00] |
| sel | +0.20 | [-0.05 ; +0.40] |
| AGS | -1.50 | [-1.90 ; -0.60] |
| proteines | -0.30 | [-2.00 ; +2.00] |
| Nutri-Score, charcuterie_cuite | -1.00 | [-2.50 ; +2.00] |

L'ecart sur les AGS est un effet de composition : la mention
France est portee a 37 % par de la charcuterie cuite, pauvre en
AGS, contre 16 % sans mention. A gamme egale, une seule strate
est testable et ne montre rien.

*Reserves.*
- **Absence de mention n'est pas origine etrangere.** La comparaison oppose une revendication a son absence.
- 109 produits sur 1 955 portent la mention, soit 5,6 % du bras.
- Aucun autre pays n'atteint un effectif testable : l'origine par pays reste hors de portee.

### H13 — La qualite nutritionnelle se deduit de l'origine culturelle du produit

**Verdict : REFUTE**

*Methode.* Classement des NOMS de produits par repertoire culinaire (maghrebin, turc, levantin, charcuterie europeenne, industriel anglo-saxon), puis comparaison a gamme egale.

A gamme egale, chaque repertoire contre les produits non classes de la meme gamme :

| gamme | repertoire | n | ecart | IC 95 % | |
|:--|:--|--:|--:|:-:|:--|
| autres_carnes | turc | 34 | -1.5 | [-3.50 ; +1.00] | non etabli |
| autres_carnes | anglo-saxon industriel | 49 | -8.0 | [-10.00 ; -1.00] | etabli |
| charcuterie_cuite | charcuterie europeenne | 79 | +3.0 | [+1.00 ; +3.00] | etabli |
| charcuterie_seche | charcuterie europeenne | 162 | +5.5 | [+0.50 ; +7.00] | etabli |
| panes | anglo-saxon industriel | 200 | -1.5 | [-6.00 ; +5.00] | non etabli |
| saucisses | maghrebin | 32 | +1.0 | [-2.50 ; +4.00] | non etabli |
| viande_hachee | anglo-saxon industriel | 49 | +3.0 | [-3.00 ; +4.00] | non etabli |

Le repertoire est une redite de la gamme : le maghrebin est a
78 % des saucisses, le levantin a 100 % dans une seule gamme.
Une fois la gamme fixee, les repertoires maghrebin et turc ne
montrent plus rien. Ce qui subsiste concerne le vocabulaire
charcutier et le vocabulaire industriel, c'est-a-dire la forme
du produit.

*Reserves.*
- `config/repertoires_culinaires.yaml` classe des RECETTES. Jamais des personnes, jamais des entreprises, jamais un pays de fabrication.
- Publier ce decoupage sans le controle par gamme produirait exactement l'affirmation que cette etude doit rendre impossible.

---

## 4. Par quel mecanisme

### H14 — L'ecart de sel et de proteines vient de l'HYDRATATION, pas de la recette

**Verdict : ETABLI**

*Methode.* Prevalence des phosphates (retenteurs d'eau) a gamme egale ; puis effet des phosphates sur les proteines a gamme egale ; puis ecart halal / temoin sur les proteines EN TENANT LES PHOSPHATES FIXES.

Ecart de prevalence halal - temoin, a gamme egale, methode de Newcombe :

| gamme | halal | temoin | ecart (points) | IC 95 % |
|:--|--:|--:|--:|:-:|
| charcuterie_cuite | 58.1 % | 9.0 % | +49.1 | [+42.80 ; +55.10] |
| saucisses | 69.6 % | 22.5 % | +47.1 | [+38.70 ; +54.30] |
| autres_carnes | 49.6 % | 7.3 % | +42.3 | [+33.30 ; +51.30] |
| charcuterie_seche | 50.0 % | 9.4 % | +40.6 | [+32.30 ; +49.00] |
| preparations_marinees | 40.5 % | 10.5 % | +30.0 | [+15.60 ; +46.10] |
| panes | 53.9 % | 30.4 % | +23.5 | [+14.00 ; +32.80] |
| decoupes | 17.1 % | 3.1 % | +14.0 | [+4.90 ; +29.60] |
| plats_cuisines | 22.9 % | 14.9 % | +8.0 | [+0.20 ; +18.10] |

**Les phosphates predisent moins de proteines** a gamme egale :
-9.4 g sur la charcuterie seche, -4.0 sur la cuite, -3.0 sur
les panes.

**Et l'ecart halal - temoin sur les proteines s'efface une fois
les phosphates tenus fixes** :

| gamme | sans phosphates | avec phosphates |
|:--|--:|--:|
| charcuterie seche | -5.18 [-7.85 ; -2.35] | -1.30 [-5.00 ; +0.65] |
| panes | -2.45 [-3.20 ; -0.30] | +0.00 [-1.00 ; +1.00] |
| autres carnes | -1.00 [-3.00 ; +0.00] | +0.80 [-1.70 ; +1.80] |

La phrase juste n'est donc pas « la charcuterie halal est plus
salee » mais **« elle est plus hydratee »**. Ce n'est pas la
meme affirmation : l'une vise la sante publique, l'autre le
rapport qualite-prix.

*Reserves.*
- Un additif declare n'est pas un additif dose.
- La liste d'ingredients est mieux saisie cote halal (50,7 % contre 44,0 %). Toutes les prevalences excluent les produits dont la liste n'a pas ete lue ; sans cette precaution le biais irait dans le sens du resultat.
- Un mediateur identifie sur donnees observationnelles reste une hypothese de mecanisme, pas une chaine causale demontree.

### H15 — La charcuterie halal utilise plus de nitrites

**Verdict : ETABLI sur cinq gammes, NON ETABLI sur la charcuterie cuite**

*Methode.* Prevalence des nitrites et nitrates (E249 a E252) a gamme egale, methode de Newcombe, sur les seuls produits dont la liste d'ingredients a ete lue.

| gamme | halal | temoin | ecart (points) | IC 95 % | |
|:--|--:|--:|--:|:-:|:--|
| saucisses | 68.1 % | 47.1 % | +21.0 | [+12.60 ; +28.50] | etabli |
| autres_carnes | 45.2 % | 31.2 % | +14.1 | [+5.20 ; +23.20] | etabli |
| panes | 29.6 % | 15.6 % | +14.0 | [+6.10 ; +23.10] | etabli |
| charcuterie_seche | 91.2 % | 81.8 % | +9.4 | [+3.20 ; +13.40] | etabli |
| charcuterie_cuite | 73.8 % | 68.5 % | +5.3 | [-0.70 ; +10.50] | non etabli |
| decoupes | 5.7 % | 1.9 % | +3.8 | [-0.40 ; +16.70] | non etabli |
| preparations_marinees | 10.8 % | 8.7 % | +2.1 | [-4.80 ; +16.10] | non etabli |
| plats_cuisines | 15.7 % | 16.8 % | -1.1 | [-7.40 ; +8.30] | non etabli |
| viande_hachee | 0.0 % | 1.7 % | -1.7 | [-3.00 ; +4.10] | non etabli |

L'ecart n'est PAS etabli sur la charcuterie cuite, qui est
pourtant le principal usage des nitrites.

*Reserves.*
- **Aucune trajectoire n'est mesurable.** Le dump est une photo, sans historique de reformulation : la question « la charcuterie halal a-t-elle suivi la baisse post-2023 » reste sans reponse ici.
- Prevalence, pas dose. Un produit peut porter E250 a 50 mg/kg comme a 150.

### H16 — Les produits halal sont plus ultra-transformes

**Verdict : ETABLI sur six gammes sur neuf**

*Methode.* Part de NOVA 4 a gamme egale, sur les produits ou le classement NOVA est renseigne.

Part de NOVA 4 (ultra-transforme), ecart halal - temoin :

| gamme | halal | temoin | ecart (points) | IC 95 % | |
|:--|--:|--:|--:|:-:|:--|
| autres_carnes | 87.4 % | 64.4 % | +23.0 | [+15.50 ; +28.10] | etabli |
| charcuterie_cuite | 98.8 % | 76.5 % | +22.3 | [+19.70 ; +23.60] | etabli |
| preparations_marinees | 88.9 % | 76.3 % | +12.6 | [-1.90 ; +20.10] | non etabli |
| plats_cuisines | 90.1 % | 80.2 % | +9.9 | [+1.40 ; +14.80] | etabli |
| viande_hachee | 47.3 % | 37.4 % | +9.9 | [-3.30 ; +23.40] | non etabli |
| panes | 97.3 % | 88.3 % | +9.0 | [+3.80 ; +11.80] | etabli |
| saucisses | 100.0 % | 92.6 % | +7.4 | [+4.50 ; +8.60] | etabli |
| charcuterie_seche | 98.5 % | 91.7 % | +6.8 | [+2.80 ; +8.30] | etabli |
| decoupes | 43.3 % | 37.7 % | +5.6 | [-10.60 ; +23.20] | non etabli |

*Reserves.*
- NOVA n'est renseigne que sur 48,8 % du bras halal et 42,0 % du temoin.
- NOVA est un classement derive de la liste d'ingredients : il herite de ses erreurs de saisie.

### H17 — Les produits halal comptent plus d'additifs

**Verdict : ETABLI a gamme egale, REFUTE a fabricant egal**

*Methode.* Mediane du nombre d'additifs a gamme egale, puis a marque, gamme et espece egales. Un decompte ne depend pas du Nutri-Score.

| gamme | ecart du nombre d'additifs | IC 95 % |
|:--|--:|:-:|
| autres_carnes | +3.00 | [+2.00 ; +4.00] |
| charcuterie_cuite | +3.00 | [+2.00 ; +3.00] |
| charcuterie_seche | +2.00 | [+1.00 ; +2.00] |
| decoupes | +0.00 | [+0.00 ; +1.00] |
| panes | +1.00 | [+0.00 ; +2.00] |
| plats_cuisines | +1.00 | [+0.00 ; +2.00] |
| preparations_marinees | +1.00 | [+0.00 ; +2.00] |
| saucisses | +2.00 | [+1.50 ; +2.50] |
| viande_hachee | +0.00 | [+0.00 ; +0.00] |

A marque, gamme et espece egales :

| cellule | n halal | n temoin | ecart | IC 95 % |
|:--|--:|--:|--:|:-:|
| fleury-michon / charcuterie_cuite / poulet | 23 | 112 | +0.00 | [+0.00 ; +0.00] |

A fabricant egal, l'ecart est **nul et l'intervalle est un
point**. Comme partout ailleurs dans cette etude, ce que la
comparaison mesure est le fabricant.

*Reserves.*
- Une seule cellule permet le controle du fabricant.

---

## 5. Le prix

Le prix vient d'Open Prices, projet de releves benevoles d'Open Food
Facts, collecte par un runner GitHub — l'environnement de
developpement ne joint pas ce service. **L'unite d'analyse est le
PRODUIT**, prix median de ses releves : un produit peut porter 68
releves, qui sont 68 passages en magasin et non 68 produits.

| bras | produits avec prix | produits | couverture |
|:--|--:|--:|--:|
| halal | 205 | 1955 | 10.49 % |
| temoin | 3715 | 68333 | 5.44 % |

### H18 — Le halal est un segment bon marche

**Verdict : NON ETABLI**

*Methode.* Prix median au kilo par produit, a gamme egale, IC bootstrap. Releves en promotion ecartes : une remise ne dit rien du positionnement d'une gamme.

| gamme | halal | temoin | ecart | IC 95 % | |
|:--|--:|--:|--:|:-:|:--|
| charcuterie_cuite | 16.58 | 17.30 | -0.72 | [-1.74 ; +0.98] | non etabli |

Une seule gamme franchit 30 produits halal, la charcuterie
cuite, et l'ecart y est non etabli.

*Reserves.*
- Open Prices est un releve BENEVOLE : la couverture n'est ni large ni aleatoire. Quelqu'un photographie ce qu'il achete, la ou il fait ses courses.
- Un prix releve vaut pour un magasin et un jour, pas pour un marche.

### H19 — Dans le halal, le moins cher est le moins bon

**Verdict : NON ETABLI dans le halal**

*Methode.* Correlation de rang de Spearman entre prix au kilo et Nutri-Score continu, a gamme egale, IC par bootstrap.

Correlation de rang prix / Nutri-Score. **Positif = plus cher va avec MOINS bon.**

| gamme | bras | n | rho | IC 95 % | |
|:--|:--|--:|--:|:-:|:--|
| autres_carnes | temoin | 339 | +0.320 | [+0.21 ; +0.42] | etabli |
| charcuterie_cuite | halal | 65 | -0.115 | [-0.35 ; +0.13] | non etabli |
| charcuterie_cuite | temoin | 651 | +0.133 | [+0.05 ; +0.21] | etabli |
| charcuterie_seche | temoin | 375 | +0.005 | [-0.11 ; +0.12] | non etabli |
| decoupes | temoin | 45 | +0.088 | [-0.18 ; +0.35] | non etabli |
| panes | temoin | 188 | -0.158 | [-0.30 ; -0.01] | etabli |
| plats_cuisines | temoin | 1074 | +0.116 | [+0.06 ; +0.18] | etabli |
| preparations_marinees | temoin | 61 | -0.204 | [-0.47 ; +0.08] | non etabli |
| rillettes_pates_mousses | temoin | 240 | -0.227 | [-0.35 ; -0.09] | etabli |
| saucisses | temoin | 213 | +0.307 | [+0.17 ; +0.43] | etabli |
| viande_hachee | temoin | 134 | -0.585 | [-0.69 ; -0.46] | etabli |

Terciles de prix dans le bras halal, charcuterie cuite :

| tercile | n | EUR/kg | Nutri-Score | sel | proteines |
|:--|--:|--:|--:|--:|--:|
| bas | 22 | 12.18 | +15.5 | 2.58 | 14.0 |
| moyen | 21 | 16.58 | +15.0 | 2.70 | 16.8 |
| haut | 22 | 19.85 | +14.0 | 2.65 | 19.0 |

Du simple au double de prix, le Nutri-Score ne bouge pas et le
sel non plus. **Payer plus cher du halal n'achete pas une
meilleure note.** Les proteines, elles, montent de 14.0 a 19.0 :
le prix achete de la matiere seche, ce qui rejoint H14.

Dans le temoin la relation existe et change de sens selon la
gamme, ce qui interdit de la resumer par un chiffre unique.

*Reserves.*
- Une seule gamme halal atteint 30 produits avec un prix.

### H20 — La moindre qualite nutritionnelle est un corollaire d'un prix moindre

**Verdict : REFUTE la ou le test est possible**

*Methode.* Terciles de prix calcules sur la gamme entiere, les deux bras confondus, puis comparaison halal / temoin DANS chaque bande.

| gamme | bande | n halal | n temoin | prix halal | prix temoin | ecart Nutri-Score | IC 95 % | ecart sel |
|:--|:--|--:|--:|--:|--:|--:|:-:|--:|
| charcuterie_cuite | bas | 17 | 222 | — | — | sous le seuil de 30 | — | — |
| charcuterie_cuite | moyen | 40 | 198 | 17.19 | 16.82 | +4.0 | [+3.00 ; +8.00] | +0.86 |
| charcuterie_cuite | haut | 8 | 231 | — | — | sous le seuil de 30 | — | — |

Dans la seule cellule testable — charcuterie cuite, bande de
prix moyenne — 40 produits halal a 17,19 EUR/kg contre 198
temoin a 16,82, donc **a prix quasi identique**, l'ecart
subsiste et il est plus net que l'ecart moyen de la gamme.

**L'ecart nutritionnel n'est pas un corollaire du prix.**

*Reserves.*
- Une seule gamme, une seule bande de prix. Ce resultat ne se generalise pas au rayon.
- Il suffit en revanche a ecarter l'explication par le prix la ou elle etait la plus plausible, et cette gamme est celle ou l'ecart nutritionnel est le mieux documente.

### H32 — Le cout de l'abattage rituel explique un surcout du halal en rayon

**Verdict : NON TESTABLE sur la cause ; NON ETABLI sur l'effet — aucun surcout halal n'est mesurable en rayon, et les donnees excluent seulement une repercussion superieure a la borne publiee**

*Methode.* Deux temps. D'abord mesurer le surcout en rayon : prix au kilo par produit (median de ses releves), ecart au prix median de marche de la strate, IC 95 % par bootstrap de grappes sur les marques (4 000 tirages, graine 20260904). Ensuite en deduire la borne haute de ce qu'une repercussion de cout peut valoir sans etre visible.

La question se dedouble, et ce depot ne peut en traiter qu'une moitie.

1. **Y a-t-il un surcout en rayon ?** Mesurable ici.
2. **Le cout de l'abattage rituel et de la certification l'explique-t-il ?**
   Non mesurable ici, et rien dans ce depot ne s'en approche. Open Food
   Facts est une base de composition et d'etiquetage : elle ne contient ni
   cout d'abattage, ni redevance de certification, ni marge, ni prix de
   cession industriel. Y repondre demanderait les comptabilites des
   abattoirs, les grilles tarifaires des organismes certificateurs, et les
   conditions commerciales entre industriels et enseignes. Aucune de ces
   trois sources n'est publique, et ce depot n'en contient aucun chiffre.

**Couverture, a lire avant tout chiffre de prix.**

| bras | produits avec prix utilisable | produits | couverture |
|:--|--:|--:|--:|
| temoin | 3333 | 68333 | 4.88 % |
| halal | 187 | 1955 | 9.57 % |

Ces effectifs sont plus bas que ceux de H18 (205 produits halal). H18
compte les produits APPARIES a un prix, H32 ceux REELLEMENT
UTILISABLES, apres le filtre de grammage : la difference est faite
d'articles qui ont un prix mais pas de prix au kilo.

**Prix au kilo, a composition egale** — ecart au prix median de marche
de la strate (sous-categorie x espece), les deux bras confondus au
denominateur. IC 95 % par bootstrap de grappes sur les marques.

| bras | produits | marques | prix median | ecart median |
|:--|--:|--:|--:|--:|
| halal | 138 | 23 | 14.14 EUR/kg | -0.38 |
| temoin | 3100 | — | 13.34 EUR/kg | +0.00 |

**Surcout halal : -0.38 EUR/kg [-2.04 ; +1.39], NON ETABLI.**
Le point estime va dans le sens inverse de la question : sur les
produits releves, le halal est legerement MOINS cher que le marche a
composition egale. L'intervalle contient zero, il n'y a donc ni
surcout ni sous-cout etabli.

### La borne, qui est la reponse reellement disponible

Meme sans connaitre le cout d'abattage, les prix bornent ce qu'un tel
cout peut avoir repercute en rayon.

- Prix de reference du temoin : **13.34 EUR/kg**.
- Surcout compatible avec les donnees : **au plus +1.39 EUR/kg**, soit +10.4 %
  du prix de reference.

**Lecture.** Toute repercussion en rayon superieure a cette borne est
refutee par ces donnees, quel que soit le cout reel en amont. Une
repercussion inferieure reste possible et n'est pas mesurable ici :
elle serait noyee dans la dispersion des prix. Avec 138 produits
halal releves, la couche n'a pas la puissance de voir moins.

**Ce que la borne ne dit pas.** Un cout d'abattage peut exister sans
arriver au consommateur : absorbe par la marge, compense par le
creneau, ou reporte sur d'autres references. Un prix n'est pas un
cout. L'absence de surcout en rayon ne refute pas un surcout en
amont ; elle dit qu'il n'arrive pas au consommateur sous forme de
prix, ou qu'il est trop petit pour se voir ici.

**Gamme par gamme**, descriptif : aucune strate n'atteint
30 produits des deux cotes.

| strate | n halal | n temoin | prix halal | prix temoin | surcout |
|:--|--:|--:|--:|--:|--:|
| charcuterie_cuite / poulet | 28 | 56 | 17.57 | 16.02 | +1.55 |
| charcuterie_cuite / dinde | 20 | 14 | 15.62 | 14.31 | +1.31 |
| panes / dinde | 17 | 25 | 10.20 | 12.72 | -2.53 |
| charcuterie_seche / indetermine | 10 | 243 | 16.19 | 20.76 | -4.58 |
| preparations_marinees / poulet | 9 | 45 | 14.72 | 12.36 | +2.36 |
| viande_hachee / boeuf | 8 | 122 | 13.96 | 17.48 | -3.52 |
| charcuterie_cuite / indetermine | 7 | 306 | 7.50 | 20.71 | -13.21 |
| charcuterie_seche / porc | 6 | 113 | 23.03 | 21.44 | +1.59 |

Les signes vont dans les deux sens : la charcuterie cuite de
volaille est plus chere en halal, les panes et la viande hachee
moins chers. Aucune de ces lignes n'est testable.

**Le seul controle propre : la meme marque des deux cotes.**
Des qu'on sort d'une marque, on compare des entreprises
differentes, avec des couts et des positionnements differents.

| marque | n halal | n temoin | prix halal | prix temoin | surcout | regle des 30 |
|:--|--:|--:|--:|--:|--:|:--|
| fleury-michon | 11 | 114 | 18.55 | 17.36 | +1.19 | sous 30 |
| isla-mondial | 9 | 1 | 18.14 | 17.69 | +0.45 | sous 30 |
| carrefour | 1 | 274 | 18.37 | 12.99 | +5.38 | sous 30 |
| herta | 1 | 79 | 18.88 | 14.50 | +4.38 | sous 30 |
| lidl | 1 | 6 | 3.38 | 8.96 | -5.58 | sous 30 |
| marque-repere | 1 | 321 | 14.72 | 10.44 | +4.28 | sous 30 |

**Aucune ne franchit la regle des 30 des deux cotes.** Fleury
Michon, la mieux dotee, montre +1,19 EUR/kg sur 11 produits halal
contre 114 temoin : une description, pas un test. C'est la limite
la plus serieuse de cette couche, et elle ne se resout pas par le
calcul — il faut plus de releves de prix.

*Reserves.*
- **Le depot ne contient aucun chiffre de cout** : ni abattage, ni certification, ni marge. La premiere moitie de la question est hors de portee de cette source, et aucun raffinement statistique n'y changera rien.
- **Un prix n'est pas un cout.** Un prix de vente se fixe sur un positionnement, une elasticite et une negociation d'enseigne, pas sur une comptabilite analytique.
- Les prix viennent d'un releve benevole couvrant moins de 10 % du bras halal. Rien ne garantit que les produits releves ressemblent aux autres.
- Le controle intra-marque, seul a isoler la certification, ne franchit la regle des 30 dans aucune marque.
- La borne est une borne SUPERIEURE sur une repercussion en rayon, pas une mesure du cout d'abattage. La confondre avec un cout serait l'erreur exacte que cette hypothese cherche a empecher.

---

## 6. Produit par produit

### H21 — L'ecart se retrouve sur les produits que le consommateur reconnait

**Verdict : ETABLI, mais le sens change selon le produit**

*Methode.* Dix produits definis dans `config/produits_emblematiques.yaml`, affectation ordonnee premier match gagnant, comparaison halal / temoin au niveau du rayon puis a espece egale.

| produit | n halal | halal | temoin | ecart | IC 95 % |
|:--|--:|--:|--:|--:|:-:|
| Mortadelle | 33 | +18.0 | +22.0 | -4.0 | [-6.00 ; -3.00] |
| Saucisson sec, salami, chorizo | 187 | +30.0 | +34.0 | -4.0 | [-5.00 ; -3.00] |
| Merguez | 31 | +18.0 | +21.0 | -3.0 | [-6.00 ; +1.00] |
| Jambon cuit (blanc, de volaille, a l'os) | 324 | +14.0 | +13.0 | +1.0 | [+0.00 ; +2.00] |
| Nuggets | 85 | +5.0 | +4.0 | +1.0 | [+0.00 ; +2.00] |
| Blanc de poulet en decoupe (non pane, non cuit en tranches) | 59 | -2.0 | -6.0 | +4.0 | [+0.00 ; +6.00] |
| Saucisses de volaille (hors merguez) | 129 | +17.0 | +13.0 | +4.0 | [+3.00 ; +6.00] |
| Escalopes et blancs panes (hors nuggets et cordons bleus) | 96 | +4.0 | -1.0 | +5.0 | [+4.00 ; +5.00] |
| Cordon bleu | 82 | +11.0 | +6.0 | +5.0 | [+0.00 ; +5.00] |
| Steak hache et viande hachee | 114 | +11.0 | +6.0 | +5.0 | [+2.00 ; +5.00] |
| Jambon sec et cru (Bayonne, Serrano, Parme, coppa) | 3 | +23.0 | +27.0 | non testable | — |

Le halal fait **mieux** la ou il remplace le porc (mortadelle,
saucisson sec, merguez), **moins bien** partout ailleurs.

Le jambon SEC est le cas limite : 3 produits halal contre
2 660 temoin. Le consommateur halal n'a pas un moins bon jambon
sec, **il n'en a pas** — le jambon sec est du porc par
definition. C'est un resultat, pas une donnee manquante.

*Reserves.*
- « Les plus references » n'est pas « les plus vendus » : Open Food Facts ne contient aucune donnee de vente.
- Le kasher ne franchit 30 que sur le jambon cuit.

### H22 — Les substituts halal de produits traditionnellement au porc sont moins bons

**Verdict : REFUTE contre le substitut, ETABLI contre l'original**

*Methode.* Pour les produits dont la version traditionnelle est au porc, comparaison du substitut halal au substitut NON halal de meme espece, puis a l'original au porc.

| produit | comparaison | variable | n | ecart | IC 95 % |
|:--|:--|:--|:--|--:|:-:|
| saucisson_sec | substitut halal - substitut non halal | Nutri-Score en score continu | 58/65 | +0.00 | [-3.00 ; +2.00] |
| saucisson_sec | substitut halal - substitut non halal | sel g/100 g | 58/65 | -0.38 | [-0.70 ; +0.00] |
| saucisson_sec | substitut halal - substitut non halal | AGS g/100 g | 58/65 | -0.20 | [-1.30 ; +2.75] |
| saucisson_sec | substitut halal - substitut non halal | proteines g/100 g | 58/65 | -6.00 | [-8.00 ; -2.10] |
| saucisson_sec | substitut halal - original au porc | Nutri-Score en score continu | 58/906 | -4.00 | [-5.50 ; -3.00] |
| saucisson_sec | substitut halal - original au porc | sel g/100 g | 58/906 | -0.68 | [-0.80 ; -0.30] |
| saucisson_sec | substitut halal - original au porc | AGS g/100 g | 58/906 | -3.00 | [-4.15 ; -0.30] |
| saucisson_sec | substitut halal - original au porc | proteines g/100 g | 58/906 | -7.00 | [-8.00 ; -4.65] |

Le substitut halal et le substitut non halal de meme espece
sont **indiscernables** sur le Nutri-Score. Contre l'original
au porc, le halal fait mieux. Le gain vient du changement
d'espece, pas du label.

**Reserve qui annule l'essentiel du benefice : 99 a 100 % de
D/E dans tous les groupes.** On compare deux mauvais produits.
Et le substitut perd 6 a 7 g de proteines pour 100 g, ce qui
rejoint H14.

*Reserves.*
- La mortadelle n'est pas testable : l'espece n'est pas derivable pour 249 produits sur 297.

---

## 7. Ce que le rayon halal contient, et qui le fabrique

### H23 — Le rayon halal couvre la cuisine maghrebine

**Verdict : REFUTE**

*Methode.* Taux d'estampille halal par repertoire culinaire, sur le perimetre entier et non sur le seul bras halal.

Part des produits d'un repertoire portant une estampille halal, sur le perimetre entier :

| repertoire | produits | dont halal | taux |
|:--|--:|--:|--:|
| turc | 172 | 93 | 54.1 % |
| anglo-saxon industriel | 1717 | 329 | 19.2 % |
| levantin | 69 | 6 | 8.7 % |
| maghrebin | 848 | 41 | 4.8 % |
| non classe | 48613 | 1195 | 2.5 % |
| charcuterie europeenne | 18869 | 291 | 1.5 % |

Le repertoire maghrebin du bras halal est a 78 % des
saucisses. Ce n'est pas que la cuisine maghrebine s'y
reduise : le couscous et le tajine sont bien dans le
perimetre et bien ranges en plats cuisines. **Sur 135
couscous, UN SEUL porte une estampille halal ; sur 131
tajines, deux.**

Le contraste avec le repertoire turc, estampille a 54 %, est
le resultat : deux cuisines, deux pratiques d'etiquetage.

*Reserves.*
- Ce taux mesure l'ETIQUETAGE, pas la halalite : un couscous sans mention peut etre halal sans le dire.
- Aucune cause n'est etablie. Le fabricant peut ne pas certifier, ou certifier sans l'afficher.

### H24 — Chez un meme fabricant, la version halal differe de la version non halal

**Verdict : REFUTE dans la majorite des cas**

*Methode.* Paires appariees sur marque, nom normalise, gamme et espece. Deux filtres de plausibilite declares en config ecartent les erreurs de saisie et les produits dont la forme contredit leur categorie.

29 paires comparables : **15 identiques**, 9 defavorables au halal, 5 favorables.

| marque | produit | EAN halal | EAN non halal | ecart |
|:--|:--|:--|:--|--:|
| carrefour | blanc dinde fum | `3560070503735` | `3560071013837` | +10.0 |
| carrefour | merguez volaille | `3560070569212` | `3560070756568` | +7.0 |
| carrefour | blanc poulet | `3560071488086` | `3560071449605` | +3.0 |
| carrefour | saucisses volaille | `3560070569182` | `3560070756629` | +3.0 |
| duc | aiguillettes poulet | `225019031955` | `3531940163007` | +2.0 |
| isla-mondial | blanc poulet | `15825889` | `3459860005750` | +1.0 |
| fleury-michon | blanc poulet | `3095759626011` | `6636074` | +1.0 |
| leader-price | nuggets poulet | `3255790616581` | `3263859581916` | +1.0 |
| jack-link-s | beef jerky sweet hot | `4251097403106` | `4251097402918` | +0.5 |
| carrefour | saucisson sec | `3700141402790` | `3560071014681` | -2.0 |
| carrefour | filets poulet | `3560070486892` | `3270190209614` | -4.0 |
| herta | lardons fum s | `3512690003379` | `7613036113281` | -4.0 |
| fleury-michon | fleury michon | `3095752586015` | `3095757119010` | -5.0 |
| fleury-michon | blanc poulet fum | `3095759627018` | `3095759625014` | -8.5 |

Detail complet, avec les codes-barres et les trois niveaux de
solidite : `sorties/rapport_produits_nommes.md`.

Le motif le plus net est Carrefour, defavorable sur quatre
produits transformes et neutre ou favorable sur la decoupe
crue — le meme motif que les couches 3 et 7.

*Reserves.*
- **Une paire n'est pas un test** : la plupart reposent sur une reference de chaque cote. C'est une observation, pas une mesure avec un intervalle.
- Le palmares contre le marche n'est PAS publiable : trois tentatives ont chacune produit une comparaison truquee au detriment du produit halal, faute d'un comparateur fiable dans les categories.

### H25 — L'estampille sanitaire permet d'observer le fabricant

**Verdict : ETABLI comme methode, NON TESTABLE faute d'effectifs**

*Methode.* L'estampille ovale identifie l'ETABLISSEMENT agree, pas la marque : une usine qui fabrique pour dix marques porte le meme code sur les dix. Comparaison halal / temoin au sein d'un meme etablissement, a gamme egale.

| bras | produits | avec estampille |
|:--|--:|--:|
| halal | 1955 | 31.2 % |
| temoin | 68333 | 33.6 % |

427 etablissements a 10 produits ou plus. **3 seulement en fabriquent des deux bras.**

Les gros faconniers multi-marques du rayon carne — jusqu'a
45 marques sur un site — ne produisent presque pas de halal.

| etablissement | gamme | n halal | n temoin | ecart | IC 95 % |
|:--|:--|--:|--:|--:|:-:|
| `fr-85-051-003` | charcuterie_cuite | 24 | 70 | +0.0 | [+0.00 ; +1.00] |

La methode fonctionne et l'identifiant est **visible par le
consommateur**, ce que la marque de distributeur ne dit
jamais. Mais le rayon halal et l'industrie du faconnage
multi-marques ne se recouvrent presque pas dans ces donnees.

La seule cellule disponible va dans le meme sens que celle de
H8 : **+0.0 de Nutri-Score et +0.00 g de sel**, halal contre
temoin, dans le meme etablissement. Deux observations
independantes, meme resultat.

*Reserves.*
- L'estampille est un fait d'emballage, mais sa saisie dans Open Food Facts est facultative : 31 % du bras halal, 34 % du temoin.
- 24 produits halal : sous le seuil de 30, donc decrit et jamais teste.
- `emb-ddddd`, l'ancien code, designe une COMMUNE et non une usine : 6 832 produits ecartes plutot que fusionnes a tort.
- Un site mal classe le serait sur les recettes que ses donneurs d'ordre lui commandent : un fabricant a facon execute un cahier des charges. D'ou le retrait de la marque dominante dans le classement.

### H26 — L'usine explique la qualite nutritionnelle

**Verdict : ETABLI dans le temoin, NON ETABLI dans le halal**

*Methode.* Decomposition de la variance a un facteur. Sur le Nutri-Score BRUT l'ICC melange le CRENEAU du site et son SAVOIR-FAIRE ; sur l'ecart a la mediane de la strate, le creneau est neutralise. IC par bootstrap de grappes.

Part de la variance du Nutri-Score qui separe les groupes (ICC), avec IC par bootstrap de grappes — on retire des usines entieres, pas des produits :

| bras | groupe | variable | ICC | IC 95 % | groupes | n | sigma intra |
|:--|:--|:--|--:|:-:|--:|--:|--:|
| temoin | etablissement | brut | 0.725 | [0.68 ; 0.76] | 683 | 18647 | 5.61 |
| temoin | etablissement | ecart | 0.304 | [0.26 ; 0.35] | 683 | 18647 | 5.55 |
| temoin | marque | brut | 0.463 | [0.36 ; 0.56] | 445 | 14897 | 7.91 |
| temoin | marque | ecart | 0.153 | [0.11 ; 0.20] | 445 | 14897 | 6.16 |
| halal | etablissement | brut | 0.511 | [0.32 ; 0.67] | 23 | 362 | 5.99 |
| halal | etablissement | ecart | 0.168 | [0.06 ; 0.27] | 23 | 362 | 7.82 |
| halal | marque | brut | 0.173 | [0.04 ; 0.31] | 17 | 341 | 6.98 |
| halal | marque | ecart | 0.100 | [0.01 ; 0.22] | 17 | 341 | 7.85 |

**Le creneau pese plus que le savoir-faire.** Dans le temoin,
l'etablissement explique 72,5 % de la variance brute mais
30,4 % une fois la strate fixee : 42 points sur 72 tenaient a
ce que le site fabrique, pas a comment il le fabrique.

**L'usine explique deux fois plus que la marque** : 0,304
contre 0,153 a composition egale, intervalles disjoints. Qui
fabrique compte davantage que le nom sur l'emballage.

**Mais pas dans le halal.** L'ICC y tombe a 0,168
[0,06 ; 0,27] et l'ecart-type INTRA site monte a 7,82 contre
5,55 au temoin : dans un meme site, les produits halal varient
PLUS que les non halal. Designer un site comme bon ou mauvais
eleve sur sa production halal serait donc mal fonde.

*Reserves.*
- 23 etablissements et 362 produits cote halal : les intervalles y sont larges et se recouvrent avec ceux du temoin. La comparaison des deux ICC est indicative, pas etablie.
- L'ICC depend du decoupage en strates : un decoupage plus fin absorberait davantage de creneau et abaisserait encore l'ICC sur l'ecart.
- Une variance intra plus grande peut venir d'un assortiment halal plus heterogene au sein du site, pas d'une conduite de fabrication moins reguliere. Les donnees ne separent pas les deux.

### H27 — Un cahier des charges commun impose la sous-qualite au halal

**Verdict : REFUTE — la trace observable d'une prescription est absente**

*Methode.* Une prescription partagee RESSERRE la dispersion : les produits qui s'y conforment se ressemblent. On mesure donc le rapport de dispersion halal / temoin sur l'ecart a la mediane de la strate, avec trois mesures — ecart-type, ecart interquartile, ecart absolu median — et un IC bootstrap.

Rapport de dispersion halal / temoin sur l'ecart a la mediane de la strate. **Sous 1, le halal serait plus homogene**, ce que produirait une prescription commune :

| mesure | halal | temoin | rapport | IC 95 % |
|:--|--:|--:|--:|:-:|
| ecart_type | 8.42 | 6.98 | **1.21** | [1.16 ; 1.25] |
| iqr | 11.00 | 6.00 | **1.83** | [1.83 ; 1.83] |
| mad | 5.00 | 3.00 | **1.67** | [1.67 ; 2.00] |

A strate fixee : 4 strates plus dispersees, 2 plus homogenes, 13 non etablies. Une part du rapport global vient donc de l'assortiment et non des recettes.

Dispersion A L'INTERIEUR d'une meme marque, ecart-type median :

- halal : 21 marques, ecart-type intra median a lire dans le CSV
- temoin : 544 marques, ecart-type intra median a lire dans le CSV

Le bras halal est **plus disperse**, pas moins : de 1,2 a 1,8
fois selon la mesure, les trois intervalles au-dessus de 1.
Meme constat a l'interieur d'une marque et, en H26, a
l'interieur d'un etablissement, ou l'ecart-type intra halal
atteint 7,82 contre 5,55 au temoin.

C'est la signature de choix de formulation **independants**,
pas d'une norme partagee.

Combine a H8, H17 et H25 — a fabricant fixe, aucun ecart — le
faisceau dit : le label n'impose rien, et ce sont certains
fabricants qui formulent ainsi, chacun de son cote.

*Reserves.*
- **AUCUNE DONNEE NUTRITIONNELLE NE PEUT ATTEINDRE UNE INTENTION.** Une intention est un etat mental de decideurs ; cette base contient des etiquettes. Ce test porte sur une trace observable, jamais sur une volonte.
- Ce resultat ne prouve pas qu'aucun cahier des charges n'existe, et il ne dit rien de leur contenu : ceux des organismes certificateurs portent sur l'abattage et la tracabilite, et il faudrait les lire.
- A strate fixee le tableau est partage : le rapport global tient en partie a l'assortiment. Cela nuance le resultat sans l'inverser — nulle part on n'observe le resserrement qu'une norme produirait.
- Des explications sans intention restent ouvertes et non testees ici : contrainte technique de la substitution d'espece, marche plus etroit, recettes anciennes non reformulees quand le marche general reduisait le sel.

### H28 — Sur une gamme halal, la dimension nutritionnelle pese moins dans le cahier des charges de la MARQUE

**Verdict : ETABLI sur le perimetre, appuye par une marque sur trois**

*Methode.* L'effort nutritionnel d'un industriel laisse une trace volontaire sur le paquet : Nutri-Score affiche, sel reduit, sans additif. Une famille TEMOIN de revendications non nutritionnelles — sans gluten, sans huile de palme, sans OGM — sert de falsification : si le halal revendiquait moins de TOUT, on mesurerait un emballage moins documente et non une posture. Newcombe, puis bootstrap sur la difference des deux ecarts.

Prevalence des allegations d'emballage, ecart halal - temoin en points :

| famille | halal | temoin | ecart | IC 95 % |
|:--|--:|--:|--:|:-:|
| effort_nutritionnel | 9.97 % | 22.28 % | **-12.30** | [-13.59 ; -10.86] |
| autres_revendications | 13.04 % | 15.64 % | **-2.60** | [-4.05 ; -1.01] |
| **difference des deux** | | | **-9.70** | [-11.63 ; -7.89] |

**Le test decisif : dans une meme marque.**

| marque | famille | n halal | n temoin | halal | temoin | ecart | IC 95 % | |
|:--|:--|--:|--:|--:|--:|--:|:-:|:--|
| aia | effort_nutritionnel | 20 | 68 | 0.0 % | 2.9 % | -2.9 | [-10.1 ; +13.3] | non etabli |
| carrefour | effort_nutritionnel | 39 | 1332 | 53.9 % | 38.6 % | +15.3 | [-0.2 ; +30.1] | non etabli |
| fleury-michon | effort_nutritionnel | 71 | 960 | 50.7 % | 63.9 % | -13.2 | [-24.9 ; -1.4] | etabli |
| aia | autres_revendications | 20 | 68 | 25.0 % | 60.3 % | -35.3 | [-52.8 ; -10.4] | etabli |
| carrefour | autres_revendications | 39 | 1332 | 28.2 % | 30.1 % | -1.9 | [-13.8 ; +13.8] | non etabli |
| fleury-michon | autres_revendications | 71 | 960 | 42.2 % | 38.1 % | +4.1 | [-7.1 ; +16.1] | non etabli |

**Le recul nutritionnel excede le recul general de 9,7
points** [-11,6 ; -7,9]. Ces gammes revendiquent, mais moins
la nutrition.

A gamme egale, le recul de l'effort nutritionnel est etabli
dans 8 gammes sur 10, celui de la famille temoin dans 4. Sur
les plats cuisines et les preparations marinees, la gamme
halal revendique DAVANTAGE sur la famille temoin et MOINS sur
la nutrition : c'est le motif le plus net.

Fleury Michon est le cas d'ecole : **-13,1 points**
[-24,9 ; -1,4] d'effort nutritionnel sur sa gamme halal,
quand la famille temoin y est a +4,1, non etabli. C'est la
marque dont H8 montre que le produit halal est nutritionnellement
IDENTIQUE au non halal : meme recette, moins de
communication nutritionnelle.

Cette hypothese ne contredit pas H27, elle s'y accorde : une
contrainte nutritionnelle plus lache produit PLUS de
dispersion, ce que H27 observe.

*Reserves.*
- **Trois marques seulement** atteignent 20 produits des deux cotes, et elles divergent : Fleury Michon appuie l'hypothese, Carrefour va en sens inverse (+15,3, non etabli), Aia n'informe pas. Le test le plus propre est aussi le moins fourni.
- Une mention absente n'est pas une nutrition negligee : elle peut signifier un produit non reformule, ou un produit reformule dont on n'a pas juge utile de le dire.
- Les labels d'Open Food Facts sont saisis par des contributeurs. La famille temoin controle cette saisie, elle ne l'annule pas.
- **Ce test mesure ce qui est imprime, pas ce qui est decide.** Aucun cahier des charges n'a ete lu. Parler de posture reste une interpretation, et l'ecrire comme une intention prouvee serait une faute.

### H29 — L'ecart tient au changement de SITE de fabrication

**Verdict : ETABLI sur le sel, NON ETABLI sur le Nutri-Score, et le motif ne tient pas dans toutes les marques**

*Methode.* Pour chaque produit halal, on regarde si son etablissement sert aussi a la production non halal de la MEME marque. Comparaison a composition egale, ecart a la mediane de marche de la strate.

Produits halal, selon que leur etablissement sert AUSSI a la production non halal de la meme marque :

| variable | n site partage | n site halal seul | ecart | IC 95 % | |
|:--|--:|--:|--:|:-:|:--|
| ecart Nutri-Score | 98 | 391 | -4.00 | [-6.00 ; -0.50] | etabli |
| sel g/100 g | 98 | 391 | -0.30 | [-0.50 ; -0.20] | etabli |

**A l'interieur d'une marque** — seule lecture qui echappe au confondant :

| marque | n partage | n halal seul | difference |
|:--|--:|--:|--:|
| carrefour | 8 | 31 | -8.5 |
| reghalal | 25 | 18 | +9.0 |
| sans-marque | 1 | 5 | +4.8 |

Sur un site partage, le halal est a **1,8 g de sel** et un
ecart de **+1,0** ; sur un site qui ne sert qu'au halal, 2,0 g
et **+5,0**.

**Carrefour est l'illustration nette** : sa gamme halal sort
majoritairement de sites qu'il n'emploie pas pour le reste, et
c'est la que l'ecart se creuse (+9,0 sur 31 produits). Sur les
sites qu'il partage, l'ecart s'efface presque (+0,5 sur 8).
Cela reinterprete son mauvais classement de H24 : moins une
recette revue a la baisse qu'un approvisionnement ailleurs.

**Reghalal montre l'inverse** : +10,0 sur site partage contre
+1,0 sur site halal seul. Le motif n'est donc pas general.

*Reserves.*
- **Confondant assume et non resolu** : les sites partages appartiennent surtout aux generalistes, qui font mieux par ailleurs. Comparer les deux groupes revient en partie a comparer des generalistes a des specialistes. Le detail par marque est publie pour cette raison.
- Seules 3 marques ont assez de produits des deux cotes, et elles ne disent pas la meme chose.
- L'estampille n'est saisie que sur 31 % du bras halal : ce test porte sur une fraction, et rien ne dit qu'elle soit representative.
- Un site partage n'est pas une ligne de production partagee : un meme agrement peut couvrir des ateliers distincts.

### H30 — Les sites de production francais sont identifiables et classables depuis l'estampille

**Verdict : ETABLI pour la geographie et le classement ; NON ETABLI pour l'identite des entreprises ; NON TESTABLE pour un classement des sites sur leur seule production halal**

*Methode.* Decodage geographique du code d'agrement, puis classement des sites sur l'ecart de leurs produits a la mediane de marche de leur strate (sous-categorie x espece). Filtres : au moins 30 produits, aucun produit de la mer. Le rho est un Spearman a IC bootstrap sur les sites (2 000 tirages, graine 20260904).

L'estampille ovale porte un code **FR dd.ddd.ddd CE** : pays,
departement, code INSEE de la commune, numero d'ordre de
l'etablissement dans cette commune. La geographie se lit donc sans
aucune source externe, et sans nommer personne.

**Ce que le code ne donne pas** : le nom de l'entreprise. Il faut
pour cela le registre des etablissements agrees du ministere de
l'Agriculture, que la politique de sortie reseau de l'environnement
refuse. Aucun site n'est donc nomme ici. La colonne
`marque_dominante` nomme le premier CLIENT du site, ce qui n'est pas
la meme chose : un faconnier n'est pas sa marque.

**162 sites** classables apres deux filtres : au moins 30
produits (regle des 30) et aucun produit de la mer. Le classement
brut en compte 370, dont 20 signales `alerte_mer` : le meme defaut residuel que le haut du classement des marques, conserve
en CSV pour etre verifiable plutot que fait disparaitre.

Etendue des ecarts medians : **-12.0 a +15.0** points de Nutri-Score a composition
egale.
A titre de comparaison, les 230 marques d'au moins 30
produits s'etalent de -15.0 a +14.0. Les deux echelles ont donc une
amplitude du meme ordre — ce qui ne dit pas laquelle cause
l'autre, puisqu'un site majoritairement occupe par un client
et ce client sont la meme chose mesuree deux fois.

**Les 8 sites les mieux classes** (ecart a la mediane de marche de la
strate ; negatif = mieux) :

| code | dept | n | marques | dont halal | ecart | sel | 1er client | part | sans lui |
|:--|:--|--:|--:|--:|--:|--:|:--|--:|--:|
| `fr-53-097-001` | 53 | 42 | 4 | 0 | -12.0 | 0.15 | l-etal-du-boucher | 67 % | +3.5 |
| `fr-43-211-010` | 43 | 36 | 12 | 0 | -7.0 | 4.60 | saint-agaune | 42 % | -7.0 |
| `fr-59-597-001` | 59 | 50 | 5 | 0 | -7.0 | 1.40 | fleury-michon | 84 % | — |
| `fr-80-799-001` | 80 | 53 | 8 | 0 | -6.0 | 1.50 | inconnue | 77 % | -4.5 |
| `fr-19-031-008` | 19 | 45 | 8 | 0 | -6.0 | 1.80 | carrefour | 64 % | -13.0 |
| `fr-85-182-003` | 85 | 255 | 5 | 0 | -5.0 | 1.80 | fleury-michon | 98 % | — |
| `fr-35-238-019` | 35 | 58 | 3 | 0 | -5.0 | 1.47 | maitre-jacques | 60 % | -13.0 |
| `fr-67-218-001` | 67 | 101 | 2 | 0 | -4.0 | 1.80 | herta | 78 % | -7.0 |

**Les 8 derniers** :

| code | dept | n | marques | dont halal | ecart | sel | 1er client | part | sans lui |
|:--|:--|--:|--:|--:|--:|--:|:--|--:|--:|
| `fr-85-006-001` | 85 | 71 | 16 | 0 | +8.0 | 3.30 | petitgas | 41 % | +10.0 |
| `fr-56-222-002` | 56 | 85 | 17 | 71 | +8.0 | 2.40 | reghalal | 32 % | +6.0 |
| `fr-56-166-001` | 56 | 39 | 4 | 38 | +9.0 | 2.30 | isla-mondial | 92 % | — |
| `fr-42-156-006` | 42 | 53 | 5 | 52 | +12.0 | 3.40 | isla-delice | 92 % | — |
| `fr-11-262-047` | 11 | 97 | 29 | 0 | +13.0 | 4.70 | montagne-noire | 20 % | +12.5 |
| `fr-40-261-001` | 40 | 34 | 9 | 0 | +13.0 | 2.70 | labeyrie | 35 % | +13.0 |
| `fr-65-100-003` | 65 | 58 | 23 | 0 | +15.0 | 5.00 | carrefour | 38 % | +14.5 |
| `fr-64-010-003` | 64 | 31 | 15 | 0 | +15.0 | 4.90 | carrefour | 19 % | +15.0 |

La colonne **sans lui** retire le premier client et recalcule. Quand
l'ecart s'y effondre, il etait celui d'une marque et non d'une usine :
`fr-53-097-001` passe de -12,0 a +3,5 des qu'on retire son donneur
d'ordre principal. Quand il ne bouge pas, le site tient sur plusieurs
clients.

**Les sites qui sortent du halal**, description seule :

| code | n halal | marques | ecart median | sel |
|:--|--:|--:|--:|--:|
| `fr-85-051-003` | 32 | 2 | +0.0 | 1.80 |
| `fr-88-218-001` | 12 | 4 | +0.0 | 1.84 |
| `fr-69-135-001` | 21 | 8 | +2.0 | 3.00 |
| `fr-61-096-018` | 13 | 3 | +3.0 | 1.20 |
| `fr-22-277-004` | 12 | 3 | +7.0 | 1.45 |
| `fr-41-053-002` | 10 | 5 | +8.0 | 2.28 |
| `fr-56-222-002` | 71 | 11 | +9.0 | 2.40 |
| `fr-56-166-001` | 38 | 3 | +9.0 | 2.33 |
| `fr-89-013-001` | 20 | 2 | +11.5 | 2.48 |
| `fr-42-156-006` | 52 | 4 | +12.5 | 3.40 |

Correlation de rang entre le nombre de produits halal d'un site
et son ecart : **rho = +0.17 [+0.02 ; +0.32]** sur 162 sites. Positif,
IC excluant zero de justesse. Il dit que les sites tournes vers
le halal sont classes plus bas. Il ne dit pas pourquoi : ces
sites appartiennent a des specialistes et fabriquent leur propre
recette, le site et la marque n'y sont pas separables.

**Par departement**, 75 unites d'au moins 30 produits,
ecarts medians de -4.0 a +5.0. L'echelle departementale
n'a aucun sens industriel : elle sert uniquement de controle de
coherence sur des effectifs plus larges.

*Reserves.*
- **Un site est juge sur les recettes de ses clients.** Un faconnier execute un cahier des charges qu'il n'ecrit pas. Le classement porte sur ce qui sort du site, jamais sur son savoir-faire.
- Le creneau pese plus que le site : la couche 10 a mesure 72,5 % de variance expliquee sur le Nutri-Score brut contre 30,4 % a strate fixee. D'ou le classement sur l'ecart, jamais sur la note brute.
- **Classer un site sur son seul halal serait mal fonde** : dispersion intra-site de 7,82 dans le bras halal contre 5,55 dans le temoin, et pouvoir explicatif du site de 0,168 contre 0,304 (couche 10). Le tableau halal ci-dessus est descriptif et ne doit pas etre lu comme un palmares.
- 29 sites publiables sur 162 sortent au moins un produit halal, 5 en sortent au moins dix : la correlation repose sur cette poignee.
- Un numero d'agrement couvre un etablissement, pas une ligne. Deux ateliers du meme site partagent le meme code.
- L'estampille n'est saisie que sur une fraction des produits, et rien ne dit que cette fraction soit representative.
- **Aucune de ces lignes ne dit quoi que ce soit du caractere halal d'un produit, ni de la conformite d'un site a une norme sanitaire ou religieuse.** Elles decrivent la composition nutritionnelle declaree de ce qui en sort.

### H31 — Dans le halal, MDD, industriels et specialistes ne font pas la meme qualite

**Verdict : NON ETABLI — l'ordre est constant (specialistes derriere, industriels devant) mais aucune difference ne survit au bootstrap de grappes**

*Methode.* Comparaison des trois familles sur leurs SEULS produits halal, a l'ecart de la mediane de marche de la strate (sous-categorie x espece). IC 95 % par bootstrap de grappes sur les marques (4 000 tirages, graine 20260904). Une marque doit avoir au moins 5 produits halal pour entrer : sans gamme, il n'y a pas de politique de marque a lire.

Trois familles, dont **deux se deduisent des donnees** et une seule
est declaree. Une marque appartenant a une enseigne ne se lit pas
dans une table de composition : la liste des MDD est donc declaree
dans `config/familles_marques.yaml`, chaque entree portant sa preuve
(le nom de l'enseigne, ou le champ `brand_owner` du dump — c'est ce
dernier qui rattache Wassila a Casino). Les deux autres familles se
separent sur la part halal du catalogue, au seuil de 50 % qui tombe
dans le plus grand vide de la distribution (26,3 % puis 57,1 %).

| famille | marques | produits halal au catalogue | exemples |
|:--|--:|--:|:--|
| MDD | 3 | 91 | carrefour, wassila, lidl |
| industriel generaliste | 6 | 119 | fleury-michon, aia, socopa, jack-link-s |
| specialiste du halal | 32 | 886 | isla-delice, reghalal, oriental-viandes, isla-mondial |

**Couverture mesuree avant de comparer.** Les trois familles
couvrent 951 produits halal ; 967 restent dehors,
sans marque saisie ou appartenant a une marque de moins de cinq
references halal. Les deux moities ont le **meme ecart median**
(+2.0 contre +2.0) et un sel
proche (2.00 contre 1.70 g). La
moitie identifiable n'est donc pas un sous-ensemble choisi.

**Ecart a la mediane de marche de la strate**, sur les seuls
produits halal de chaque famille. Negatif = mieux que le marche sur
le meme type de produit.

| famille | marques | produits | ecart median | IC 95 % | sel | IC 95 % |
|:--|--:|--:|--:|:--:|--:|:--:|
| MDD | 3 | 67 | +1.0 | [-2.0 ; +4.0] | +0.22 | [-0.08 ; +0.49] |
| industriel generaliste | 6 | 108 | +0.0 | [+0.0 ; +5.0] | +0.00 | [-0.09 ; +0.42] |
| specialiste du halal | 32 | 776 | +4.0 | [+2.0 ; +6.0] | +0.41 | [+0.27 ; +0.58] |

Les IC sont calcules par **bootstrap de grappes sur les marques**,
jamais sur les produits : deux references d'une meme marque ne sont
pas deux observations independantes (ICC de 0,304 a strate fixee,
couche 10). Avec 3 marques pour les MDD et 6 pour les industriels,
ces intervalles sont larges. C'est la precision reelle de la
comparaison.

**Aucune des six differences n'est etablie :**

| mesure | comparaison | difference | IC 95 % | verdict |
|:--|:--|--:|:--:|:--|
| nutriscore | MDD − industriel generaliste | +1.00 pts | [-4.00 ; +3.50] | non etabli |
| nutriscore | MDD − specialiste du halal | -3.00 pts | [-6.00 ; +0.00] | non etabli |
| nutriscore | industriel generaliste − specialiste du halal | -4.00 pts | [-6.00 ; +2.00] | non etabli |
| sel | MDD − industriel generaliste | +0.22 g | [-0.22 ; +0.49] | non etabli |
| sel | MDD − specialiste du halal | -0.19 g | [-0.48 ; +0.09] | non etabli |
| sel | industriel generaliste − specialiste du halal | -0.41 g | [-0.58 ; +0.07] | non etabli |

Le point le plus proche du seuil est MDD − specialiste sur le
Nutri-Score : **−3,00 [−6,00 ; +0,00]**. La borne haute touche zero
exactement. Compter cette ligne comme etablie serait lire un
intervalle comme un point, l'erreur n° 10 de la section 8.

**Une voix par marque**, pour ne pas laisser Isla Delice et ses
182 references parler pour trente-deux marques :

| famille | marques | mediane des medianes | Q1 | Q3 | sel |
|:--|--:|--:|--:|--:|--:|
| MDD | 3 | +1.0 | -0.50 | +2.50 | +0.20 |
| industriel generaliste | 6 | +0.5 | -1.88 | +3.62 | -0.01 |
| specialiste du halal | 32 | +3.5 | +1.00 | +6.50 | +0.37 |

L'ordre des trois familles ne change pas, et l'ecart
interquartile de chaque famille recouvre celui des deux autres.
Le desaccord entre marques d'une meme famille est plus grand que
l'ecart entre familles.

**Sans Carrefour**, la famille MDD tombe a 2 marques et 28 produits, sous la
regle des 30, avec une mediane de +1.25. La
ligne « MDD » de cette etude est donc pour l'essentiel une
ligne « Carrefour », et doit se lire ainsi.

**Chaque marque comparee a son propre temoin** — la seule
lecture qui ne compare pas des entreprises differentes. Un
specialiste du halal n'a pas de version non halal : la ligne
n'existe pas pour lui, et Wassila non plus, dont le catalogue
est halal a 100 % bien qu'elle appartienne a une enseigne.

| famille | marque | n halal | n temoin | halal | temoin | difference | regle des 30 |
|:--|:--|--:|--:|--:|--:|--:|:--|
| industriel generaliste | doux | 4 | 13 | -2.5 | +1.0 | -3.5 | sous 30 |
| MDD | lidl | 7 | 414 | -2.0 | +0.0 | -2.0 | sous 30 |
| industriel generaliste | jack-link-s | 6 | 33 | +4.5 | +6.0 | -1.5 | sous 30 |
| industriel generaliste | duc | 3 | 24 | -4.0 | -4.0 | +0.0 | sous 30 |
| MDD | carrefour | 39 | 1313 | +1.0 | +0.0 | +1.0 | franchie |
| industriel generaliste | socopa | 5 | 219 | +1.0 | +0.0 | +1.0 | sous 30 |
| industriel generaliste | fleury-michon | 70 | 946 | +0.0 | -2.0 | +2.0 | franchie |
| industriel generaliste | aia | 20 | 68 | +5.0 | +0.0 | +5.0 | sous 30 |

Deux cellules seulement franchissent la regle des 30 des
deux cotes : carrefour +1.0, fleury-michon +2.0. Les autres sont decrites avec leur
effectif et ne doivent pas etre lues comme un classement.

*Reserves.*
- **La famille MDD est Carrefour.** Trois marques, dont une, Wassila, sans temoin non halal. Retirer Carrefour fait passer la famille sous la regle des 30.
- **La famille industriel n'est pas homogene.** Fleury Michon (71 produits halal, ecart 0,0) et Jack Link's (6 produits, ecart +4,5 sur un creneau de viande sechee) y sont ranges ensemble parce que le halal est minoritaire chez les deux. C'est ce que mesure l'ecart interquartile publie.
- **Specialiste du halal n'est pas une categorie commerciale unique.** Suntat, Baktat, Hunkar et Yayla sont des marques d'epicerie turque dont le catalogue est majoritairement tague halal : la regle des 50 % les range avec Isla Delice. Un decoupage par repertoire culinaire donnerait une autre partition.
- La moitie du bras halal reste hors familles, faute de marque saisie ou de gamme. Sa composition est semblable (verifiee ci-dessus), ce qui autorise la comparaison sans la rendre exhaustive.
- Une seule strate sur 28 compte deux familles au-dessus de 30 produits : la comparaison gamme par gamme n'est presque jamais testable, et le tableau f4 est descriptif.
- Ces familles decrivent une POSITION SUR LE MARCHE, lisible en rayon. Elles ne disent rien de la halalite d'un produit, de la conformite d'une entreprise, ni de qui la dirige.

---

## 8. Erreurs commises et corrigees en cours d'etude

Elles sont listees parce qu'un lecteur doit pouvoir juger de la
fiabilite du reste, et parce que chacune a failli produire une
affirmation publique fausse.

| # | erreur | consequence si non corrigee | correction |
|--:|:--|:--|:--|
| 1 | Detection du certificateur par la chaine « halal » | Couverture annoncee a 6,9 % au lieu de 31,9 % ; AVS et les mosquees invisibles | Registre par organisme, `config/certificateurs.yaml` |
| 2 | Especes derivees de FORMES de produit | 203 produits halal classes porc ; salami de dinde compte comme du porc | Motifs restreints a l'espece, assertion A7 |
| 3 | Exclusion des produits de la mer trop large | 3 785 exclusions au lieu de 924 ; « Grillons de canard » pris pour des insectes | Exclusion composee, deux motifs |
| 4 | Strate « decoupes » melangeant cru et marine | Ecart de sel de 1,30 contre 0,25 g attribue au label | Strate scindee |
| 5 | Aides culinaires dans un perimetre carne | Fonds de veau a 22 g de sel comptes comme des aliments | Exclusion par categorie |
| 6 | `additives_tags` vide pris pour « sans additif » | Prevalence halal gonflee, biais dans le sens du resultat | Restriction aux produits dont la liste est lue |
| 7 | Repertoire culinaire rattache par position | Appariement arbitraire entre nom et produit ; le maghrebin passait de 54 a 78 % de saucisses | Nom lu dans la meme requete |
| 8 | Collecte de prix plafonnee a 16 % de la base | « Open Food Facts ne couvre pas le rayon halal », faux | Pagination revue |
| 9 | Prix compares au RELEVE et non au PRODUIT | 3 des 4 ecarts « etablis » disparaissent ; le signe s'inverse sur la charcuterie cuite | Agregation par produit |
| 10 | Verdict prix lu sur le point et non l'intervalle | Un ecart de +0.0 range du cote « meilleur » | Verdict fonde sur les IC |
| 11 | Dump fige declare irrecuperable | Etude declaree non rejouable | `versionId` S3 ajoute a `config/source.yaml` |
| 12 | Sortie A7 sans `ORDER BY` | Fichier versionne changeant d'ordre a chaque execution | Tri explicite |

Deux d'entre elles, la 6 et la 9, allaient dans le sens du resultat
attendu. C'est la raison pour laquelle la couverture des donnees est
desormais mesuree et publiee AVANT chaque comparaison.

---

## 9. Ce qui reste ouvert

| sujet | etat | ce qu'il faudrait |
|:--|:--|:--|
| Faux negatifs d'etiquetage | 0 sur 43 lectures d'image, IC 95 % [0 ; 8,2 %] | 200 codages humains sur image, contre 43 |
| Haut du classement des marques | Non publiable | Verifier produit par produit les 4 marques de produits de la mer |
| Origine par pays | Hors de portee | Aucun pays hors France n'atteint un effectif testable |
| Nitrites, trajectoire | Impossible ici | Une serie temporelle, pas une photo |
| Prix | Une seule gamme testable | Un relevé de prix systematique, pas benevole |
| Controle du fabricant | Une seule cellule | Des marques vendant les deux versions du meme produit |
| Electronarcose | Classification non etablie ici | Les cahiers des charges des organismes eux-memes |
| Faconnage multi-marques | 3 etablissements mixtes seulement | Une meilleure saisie des estampilles, ou le registre public des agrements |
| Nom des sites de production | 1 683 codes francais decodes en departement et commune, aucune entreprise nommee | Le registre des etablissements agrees du ministere de l'Agriculture, refuse par la politique de sortie reseau ; a rapatrier par un runner GitHub comme les prix |
| Cout de l'abattage et de la certification | Hors de portee de cette source, definitivement | Les comptabilites d'abattoirs et les grilles tarifaires des certificateurs. Aucune n'est publique |
| Surcout halal en rayon | Non etabli, borne haute a +1,39 EUR/kg | Un releve de prix systematique : 138 produits halal ne permettent pas de voir moins |
| MDD contre specialistes | Ordre constant, aucune difference etablie | Plus de MDD avec une gamme halal : 3 marques ne portent pas une famille |
| « Specialiste du halal » comme categorie | Melange epicerie turque et marques maghrebines | Un decoupage par repertoire culinaire, teste contre celui par part de catalogue |
| Classement des sites sur leur seul halal | Non fonde | Une dispersion intra-site qui ne depasse plus celle du temoin, ou beaucoup plus de produits par site |
| Couscous et tajine halal | 1 sur 135, 2 sur 131 | Comprendre pourquoi : absence de certification, ou d'affichage |

---

## Reproduire

```sh
make install
make couche1     # source, perimetre, assertions, analyse, rapport
make couche3     # appariement, les deux estimands
make couche4     # marques, certificateurs, classements
make couche5     # produits emblematiques
make couche6     # reperes consommateur
make couche7     # additifs et transformation
make couche8     # prix (collecte via l'Action couche8-prix)
make couche9     # podiums et paires appariees
make couche10    # etablissements, variance intra-site
make couche11    # homogeneite des deux bras
make couche12    # allegations d'emballage
make couche13    # site partage ou site halal seul
make couche14    # sites francais decodes depuis l'estampille
make couche15    # MDD, industriels, specialistes du halal
make couche16    # surcout halal en rayon, et la borne
python3 src/rapport_hypotheses.py   # regenere ce document
```

Le dump est epingle par son `versionId` S3 : `make couche1` rejoue la
meme base, pas celle du jour.

