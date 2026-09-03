# Étude halal / non halal — specs de développement

Découpage en pelure d'oignon. La couche 1 couvre l'intégralité du périmètre
fonctionnel en faible profondeur et produit déjà une conclusion publiable.
Chaque couche suivante approfondit sur l'ensemble du périmètre. Chaque couche
est arrêtable : si ses résultats disent que le sujet n'existe pas, on
s'arrête là et on l'écrit.

---

## Contexte à donner à l'agent en préambule

> Étude comparant la qualité nutritionnelle des produits carnés industriels
> estampillés halal et leurs équivalents non estampillés, en France, sur le
> dump Open Food Facts. Destination : article de vulgarisation pour un média
> en ligne, avec annexe méthodologique. Public : consommateurs musulmans
> cherchant à choisir en rayon.
>
> Le traitement est le **label**, pas la halalité religieuse. Tout produit
> carné sans estampille relevée est classé témoin, assumé et documenté.
>
> Contrainte transverse : chaque conclusion doit être rattachable à une
> variable observable sur l'emballage. Les résultats seront lus hors contexte
> et potentiellement retournés contre la population concernée. Aucune
> approximation silencieuse n'est acceptable.

---

## AGENTS.md — à créer en couche 1, à enrichir à chaque couche

Contenu minimal, à figer et à faire respecter par le pipeline :

```markdown
# Règles de l'étude — non négociables sans issue dédiée

## Définitions verrouillées
- Traitement : présence du tag `en:halal` dans `labels_tags`. Le témoin est
  tout produit carné du périmètre sans ce tag. Ce n'est pas une mesure de la
  halalité réelle.
- Périmètre catégories : liste figée dans `config/perimetre.yaml`. Toute
  modification passe par une issue, jamais par un ajustement de requête.
- Règle des 30 : toute strate comptant moins de 30 produits à données
  nutritionnelles complètes sort de l'analyse principale. Elle peut être
  décrite, jamais testée.

## Interdits
- Élargir un filtre, retirer une condition ou supprimer des NULL pour faire
  passer une requête vide ou une erreur. Échouer bruyamment à la place.
- Substituer une variable proche à une variable absente sans le déclarer.
- Ajouter un bras végétarien ou un substitut végétal. Hors périmètre, décidé.
- Extraire en masse des notes Yuka. Le score est recalculé à partir de la
  méthode publiée et d'une grille additifs relevée manuellement et datée.

## Assertions à faire échouer le pipeline
- Effectifs par strate conformes à `config/effectifs_attendus.yaml`, tolérance
  déclarée. Écart hors tolérance = arrêt, pas d'avertissement.
- Aucune ligne du jeu final sans `code` produit, sans catégorie, sans statut.
- Somme des trois bras = total du périmètre, à zéro près.

## Distinction obligatoire dans toute sortie
Fait mesuré / inférence / hypothèse non testée. Un chiffre sans statut est
un bug.
```

---

## Couche 1 — Chaîne complète, faible profondeur

**Valeur livrée seule.** On sait si les données permettent l'étude, et on a
un premier écart chiffré sur les deux variables les plus vérifiables en rayon.

**Périmètre.**
- Récupération du dump Parquet Open Food Facts via DuckDB + httpfs.
  Source : `openfoodfacts/product-database`, fichier `food.parquet`,
  Open Database License. Inspection du schéma d'abord, adaptation ensuite :
  la structure de `nutriments` et l'emplacement du Nutri-Score 2023 varient
  entre versions.
- Extraction du périmètre France × carné vers un Parquet local.
- Comptages de faisabilité : effectifs par catégorie × statut × complétude ;
  distribution Nutri-Score par statut ; taux de tag halal par marque ;
  effectifs et nombre de marques distinctes par certificateur ; additifs les
  plus fréquents ; NOVA par statut.
- Comparaison brute halal / témoin sur deux variables seulement :
  **sel pour 100 g** et **Nutri-Score en grade**. Médiane, quartiles,
  effectifs. Aucun ajustement, aucun appariement.
- Sortie : un rapport Markdown et un CSV, versionnés.
- Création d'`AGENTS.md` et de `config/perimetre.yaml` à partir des
  catégories réellement observées, pas des graines de recherche.

**Hors périmètre.** Parseur pourcentage de viande. Appariement. Ciqual.
Modèles. Recalcul Yuka.

**Critères d'acceptation.**
- Le rapport indique, pour chaque catégorie, si la règle des 30 est franchie.
- Le rapport conclut explicitement sur la saturation du Nutri-Score : si plus
  de 80 % des deux groupes sont en D ou E, il le dit et recommande le
  basculement éditorial sur sel et pourcentage de viande.
- Le rapport conclut explicitement sur la séparabilité certificateur / marque.
- Rejouable de bout en bout par une commande, sur une machine vierge.

---

## Couche 2 — Profondeur sur la mesure

**Valeur livrée seule.** Les variables deviennent fiables et leur taux
d'erreur est chiffré. Sans cette couche, tous les écarts de la couche 1 sont
d'amplitude inconnue.

**Périmètre.**
- Table marque → statut halal, construite à la main, une vérification par
  marque et non par produit, pour les marques dont toute la gamme carnée est
  estampillée. Cette table devient la source du statut, le tag produit
  devient un secours.
- Audit du sous-étiquetage : échantillon aléatoire du témoin, examen des
  photos d'emballage OFF, estimation du taux de faux négatifs avec intervalle.
  Ce taux est publié, pas corrigé silencieusement.
- Parseur du pourcentage de viande depuis `ingredients_text`. Suite de tests
  sur cas réels. Taux d'erreur mesuré contre un échantillon d'au moins
  200 produits recodés à la main en aveugle, par un humain, pas par l'agent.
- Extraction de la présence de nitrites (E249 à E252) et du compte
  d'additifs.
- Toutes les sorties de la couche 1 sont recalculées avec les variables
  fiabilisées, et l'écart avec la couche 1 est affiché.
- `AGENTS.md` : ajout de la règle de priorité marque > tag produit, et du
  taux de faux négatifs constaté.

**Critères d'acceptation.**
- Le taux d'erreur du parseur viande figure dans le rapport. S'il dépasse
  10 %, la variable est déclassée en descriptive et l'agent le signale au
  lieu de continuer.
- Le double codage humain est un fichier d'entrée du dépôt, pas une sortie
  générée.

---

## Couche 3 — Profondeur sur la comparaison

**Valeur livrée seule.** L'écart mesuré devient interprétable causalement,
et le troisième bras rend lisible un écart nul.

**Périmètre.**
- Appariement halal / témoin : même sous-catégorie, même espèce, même segment
  de gamme. Procédure documentée, reproductible, avec un second codeur sur un
  échantillon et un kappa reporté.
- Troisième bras non transformé, à partir de Ciqual (ANSES). Colonne séparée,
  jamais fondue dans le calcul statistique avec les produits OFF : ce sont des
  compositions moyennes de référence, pas des relevés d'étiquette. Version
  Ciqual citée et figée.
- Deux estimands calculés séparément et rapportés séparément :
  - effet total du label, espèce non ajustée, l'exclusion du porc étant un
    médiateur assumé ;
  - effet direct à espèce et sous-catégorie identiques, restreint aux strates
    où le témoin existe hors porc.
- Sortie principale : FSAm-NPS 2023 en score continu. Version 2017 en
  sensibilité. Sel, AGS, protéines, pourcentage de viande, NOVA, nitrites en
  secondaire.
- Analyse de dispersion intra-halal par sous-catégorie, sans témoin :
  étendue, écart interdécile, identification des extrêmes par marque.
- `AGENTS.md` : ajout du statut des données Ciqual et de l'interdiction de
  les mélanger au calcul.

**Critères d'acceptation.**
- Les deux estimands sont dans deux tableaux distincts, avec une phrase
  chacun expliquant ce qu'ils mesurent.
- La dispersion intra-halal est comparée à l'écart inter-groupes, et le
  rapport dit lequel domine.

---

## Couche 4 — Profondeur sur l'attribution

**Valeur livrée seule.** Réponse à « quel facteur discrimine le plus ».

**Périmètre.**
- Modèle mixte à effets aléatoires croisés : sous-catégorie, espèce,
  fabricant, marque, certificateur niché dans marque. Rapport de la part de
  variance par niveau. C'est la seule formulation qui donne un sens à
  « facteur le plus discriminant ».
- Vérification par modèle d'ensemble, importance par permutation groupée,
  validation croisée **par marque** pour éviter la fuite entre produits d'une
  même gamme.
- Si la couche 1 a conclu que certificateur et marque sont inséparables, ce
  facteur est retiré du modèle et l'annexe l'explique. Ne pas l'inclure en
  espérant que le modèle démêle.
- Plan de multiplicité : un critère principal préspécifié, méthode de
  correction annoncée avant exécution, tout le reste étiqueté exploratoire.
- `AGENTS.md` : ajout du critère principal et de la méthode de correction,
  figés.

**Critères d'acceptation.**
- Aucune comparaison de valeurs p entre facteurs pour établir une hiérarchie.
- Chaque effet rapporté porte son statut : mesuré, inféré, ou hypothèse.

---

## Couche 5 — Profondeur sur la publication

**Valeur livrée seule.** L'article et l'annexe sont défendables.

**Périmètre.**
- Recalcul de la note Yuka selon la méthode publiée par l'éditeur, avec la
  grille de risque des additifs relevée manuellement sur le périmètre borné
  identifié en couche 1, datée, captures à l'appui, publiée en annexe.
  Aucune extraction de masse.
- Décomposition systématique Nutri-Score / bloc additifs, présentée comme
  outil de diagnostic. Interdiction de présenter Nutri-Score et Yuka comme
  deux résultats concordants : le premier est contenu dans le second.
- Tableaux éditoriaux triés par marque, avec sel pour 100 g et pourcentage de
  viande en colonnes principales, et le prix au kilo issu du relevé terrain.
- Gel du jeu de données à une date, export public, code publié, hash du dump
  source.
- Préenregistrement rédigé et déposé **avant** consultation des résultats des
  couches 3 à 5.
- `AGENTS.md` : ajout de la date de gel et du hash du dump.

**Critères d'acceptation.**
- Un tiers peut rejouer l'intégralité à partir du dépôt et du dump figé.
- L'annexe déclare la source de chaque donnée, le taux de faux négatifs, les
  strates écartées par la règle des 30, et les questions abandonnées.
