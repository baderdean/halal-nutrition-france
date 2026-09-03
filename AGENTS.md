# Regles de l'etude — non negociables sans issue dediee

Etude comparant la qualite nutritionnelle des produits carnes industriels
estampilles halal et leurs equivalents non estampilles, en France, sur le dump
Open Food Facts. Destination : article de vulgarisation pour un media en ligne,
avec annexe methodologique. Public : consommateurs musulmans cherchant a
choisir en rayon.

Le traitement est le **label**, pas la halalite religieuse. Tout produit carne
sans estampille relevee est classe temoin, assume et documente.

Contrainte transverse : chaque conclusion doit etre rattachable a une variable
observable sur l'emballage. Les resultats seront lus hors contexte et
potentiellement retournes contre la population concernee. Aucune approximation
silencieuse n'est acceptable.

Etat d'avancement : **couche 1 executee**. Couches 2 a 5 non commencees.

## Definitions verrouillees

- Traitement : presence du tag `en:halal` dans `labels_tags`. Le temoin est
  tout produit carne du perimetre sans ce tag. Ce n'est pas une mesure de la
  halalite reelle.
- Perimetre categories : liste figee dans `config/perimetre.yaml`. Toute
  modification passe par une issue, jamais par un ajustement de requete.
- Regle des 30 : toute strate comptant moins de 30 produits a donnees
  nutritionnelles completes sort de l'analyse principale. Elle peut etre
  decrite, jamais testee.
- Completude nutritionnelle : energie kcal, acides gras satures, sucres, sel
  et proteines tous renseignes pour 100 g. Definie une seule fois, dans
  `src/commun.py` (`COMPLET`).
- Source figee : `config/source.yaml`. Le pipeline verifie taille et sha256 du
  dump et s'arrete si l'un des deux bouge.

## Interdits

- Elargir un filtre, retirer une condition ou supprimer des NULL pour faire
  passer une requete vide ou une erreur. Echouer bruyamment a la place
  (`commun.echec`).
- Substituer une variable proche a une variable absente sans le declarer.
- Ajouter un bras vegetarien ou un substitut vegetal. Hors perimetre, decide.
- Extraire en masse des notes Yuka. Le score est recalcule a partir de la
  methode publiee et d'une grille additifs relevee manuellement et datee.
- Fixer le perimetre sur les graines de recherche. Les graines amorcent la
  decouverte ; la liste figee vient des categories observees.

## Assertions qui font echouer le pipeline

Implementees dans `src/etape1_assertions.py`, executees avant la production du
rapport. Ecart hors tolerance = arret, pas d'avertissement.

- Effectifs par strate conformes a `config/effectifs_attendus.yaml`, tolerance
  declaree par strate.
- Aucune ligne du jeu final sans `code` produit, sans categorie, sans statut.
- Somme des bras (halal + temoin) = total du perimetre, a zero pres.
- Aucun code produit duplique dans le jeu final.
- Aucune valeur nutritionnelle hors bornes physiques (sel, AGS, proteines,
  sucres > 100 g/100 g ; energie > 900 kcal/100 g). Les lignes fautives sont
  comptees et exclues des seules statistiques nutritionnelles, jamais du
  denombrement du perimetre, et le compte figure au rapport.

## Lecture d'image (couche 2)

- La lecture machine d'un emballage n'est PAS une variable d'analyse. Elle le
  devient quand `src/couche2_validation.py` a publie son taux d'erreur contre
  un double codage humain en aveugle d'au moins 200 produits. Au-dela de 10 %
  d'erreur, la variable est declassee en descriptive et le pipeline le dit.
- L'echantillon de lecture est tire PAR MARQUE, pas par produit. Une marque
  partage un design d'emballage : l'erreur de lecture est correlee a la marque,
  et injectee telle quelle dans le modele de la couche 4 elle fabriquerait un
  effet certificateur qui n'est qu'un effet marque mal mesure.
- Le double codage humain est un fichier d'entree du depot
  (`donnees_humaines/double_codage.csv`), jamais une sortie generee.
- Priorite : ce passage sur les images sert d'abord a mesurer le taux de faux
  negatifs du tag halal. Le certificateur est un sous-produit du meme passage.
- Un jeu de lectures ne melange jamais deux fournisseurs. Leurs taux d'erreur
  different ; un taux global n'aurait pas de sens et la qualite varierait
  d'une ligne a l'autre sans que rien ne le signale. `couche2_validation.py`
  s'arrete si le jeu en contient plusieurs, et le taux d'erreur d'un
  fournisseur ne se transporte pas a un autre.
- Aucun lot de lecture ne part sans un preflight reussi. Une passerelle qui
  ignore silencieusement le bloc image repond quand meme, a partir du seul
  texte de la consigne : la sortie serait entierement inventee et rien dans le
  CSV ne le signalerait. Le preflight verifie le compte de tokens d'entree,
  qui est la seule preuve que l'image a bien ete analysee.

## Distinction obligatoire dans toute sortie

Fait mesure / inference / hypothese non testee. Un chiffre sans statut est un
bug. Convention de balisage dans les rapports :

- `[FAIT]`      : lu directement dans le dump, reproductible par requete.
- `[INFERENCE]` : deduit d'un fait par un raisonnement explicite et faillible.
- `[HYPOTHESE]` : non teste par ce depot, a verifier dans une couche ulterieure.

## Ecarts aux specs deja actes

- **Source.** Les specs prevoyaient `food.parquet` sur HuggingFace. L'hote
  `huggingface.co` est refuse par la politique de sortie reseau de
  l'environnement d'execution (403 sur le CONNECT). L'export plat officiel Open
  Food Facts (`openfoodfacts-ds.s3.eu-west-3.amazonaws.com`,
  `en.openfoodfacts.org.products.csv.gz`) est utilise a la place : meme
  organisation, memes licences, meme base. Consequences connues listees dans
  `config/source.yaml`. A rebasculer sur le Parquet des que l'hote est joignable.
- **Version du Nutri-Score.** L'export plat n'expose qu'une colonne
  `nutriscore_grade` sans indication de version d'algorithme. La couche 1 la
  traite comme « la note publiee par OFF a la date du dump » et ne pretend pas
  distinguer 2021 de 2023. Le recalcul FSAm-NPS versionne est un travail de
  couche 3.
