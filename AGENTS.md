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
- Le script n'accepte jamais de lui-meme la licence d'un modele. Certains
  modeles Workers AI l'exigent avant tout usage : c'est un engagement
  juridique du titulaire du compte, pas une formalite technique. L'etape
  existe (`--accepter-licence`) mais ne tourne que sur demande explicite.
- Aucun lot de lecture ne part sans un preflight reussi. Une passerelle qui
  ignore silencieusement le bloc image repond quand meme, a partir du seul
  texte de la consigne : la sortie serait entierement inventee et rien dans le
  CSV ne le signalerait. Le preflight verifie le compte de tokens d'entree,
  qui est la seule preuve que l'image a bien ete analysee.

## Faits etablis par mesure, non renegociables sans nouvelle mesure

- Taux de faux negatifs du tag `en:halal` dans le bras temoin : **0 / 100**,
  IC 95 % de Wilson [0 ; 3,7] %, sur tirage aleatoire recode a la main en
  aveugle (`donnees_humaines/double_codage.csv`, 2026-09-04). La borne basse
  de 4,26 % issue des marques specialisees ne vaut PAS comme plancher global :
  c'etait une extrapolation d'une sous-population choisie pour maximiser le
  phenomene.
- Taux de produits tagues `en:halal` sans estampille reperable : 16 / 100,
  IC 95 % [10,1 ; 24,4] %.
- Un codage humain qui etablit le statut hors de la photo doit porter
  `lisibilite = zone_absente`. La colonne `source_lecture` (image / externe /
  non_code) en decoule et separe ce qui est comparable a une lecture machine
  de ce qui ne l'est pas. Melanger les deux dans un taux d'erreur machine
  reviendrait a reprocher au modele d'ignorer ce qui n'est pas sur l'image.

## Origine : le label visible, pas la metadonnee

La question « les produits halal fabriques en France different-ils des
autres » se traite par le **label de production visible sur l'emballage**
(`en:made-in-france`, `fr:origine-france`, logo Viande de France...), pas par
`origins_tags` ni `emb_codes_tags`. Raison : la contrainte transverse de
l'etude veut que toute conclusion se rattache a une variable qu'un client
peut voir en rayon. L'origine des ingredients et le code d'emballage
sanitaire n'en sont pas.

Les colonnes `origins_tags`, `manufacturing_places_tags` et `emb_codes_tags`
restent extraites, comme variables de CONTROLE, jamais comme la variable
d'interet. Elles ne mesurent pas la meme chose entre elles et ne se fusionnent
pas : ingredients, usine, dernier conditionnement.

Couverture du label visible dans le perimetre : 10,6 % du bras halal,
9,5 % du temoin. `en:made-in-france` couvre 109 produits halal, au-dessus de
la regle des 30. La lecture d'emballage sert precisement a combler ce que le
tag OFF sous-declare.

## Detection des certificateurs : jamais par la chaine 'halal'

Un certificateur se detecte PAR LES DONNEES : label porte par au moins 20
produits du perimetre dont 80 % ou plus sont tagues `en:halal`. Chercher la
chaine `halal` dans le nom du tag rate les organismes nommes par leur mosquee
ou leur association, a commencer par AVS — A Votre Service, le principal
certificateur francais. Cette erreur a fait annoncer 6,9 % de couverture la
ou elle est de 30,5 %, et abandonner a tort la question du certificateur.

La liste figee est dans `config/certificateurs.yaml`.

## Distinction obligatoire dans toute sortie

Fait mesure / inference / hypothese non testee. Un chiffre sans statut est un
bug. Convention de balisage dans les rapports :

- `[FAIT]`      : lu directement dans le dump, reproductible par requete.
- `[INFERENCE]` : deduit d'un fait par un raisonnement explicite et faillible.
- `[HYPOTHESE]` : non teste par ce depot, a verifier dans une couche ulterieure.

## Documentation au fil de l'eau — obligatoire

Un resultat qui n'existe que dans une conversation n'existe pas. Tout resultat
etabli, refute ou declare non testable est documente DANS LE DEPOT, dans le
meme mouvement que le calcul qui le produit, jamais « plus tard ».

Concretement, pour chaque resultat :

1. le calcul vit dans un script de `src/`, pas dans une commande jetable ;
2. ses chiffres sortent dans `sorties/`, en CSV ;
3. il porte un numero d'hypothese et un verdict dans `RESULTATS.md`, via
   `src/rapport_hypotheses.py` ;
4. le message de commit dit ce qui a ete etabli, avec ses chiffres, et ce que
   le resultat aurait ete sans la correction si une correction a eu lieu.

RESULTATS.md est GENERE. Il ne se redige pas a la main : trois corrections de
cette etude ont deja renverse un resultat publie, et un document tape a la
main aurait garde les anciens chiffres. `tests/test_coherence.py` echoue s'il
ne cite plus son generateur.

Une erreur corrigee se documente au meme titre qu'un resultat, dans le tableau
des erreurs de RESULTATS.md, avec l'affirmation fausse qu'elle aurait produite.
Deux des erreurs deja recensees allaient dans le sens du resultat attendu :
c'est la raison pour laquelle la couverture des donnees est mesuree et publiee
AVANT chaque comparaison.

## Ce que l'etude ne peut pas dire : l'intention

Aucune donnee nutritionnelle n'atteint une intention. Une intention est un
etat mental de decideurs ; Open Food Facts contient des etiquettes declarees.

Aucune sortie de ce depot ne doit etre redigee de facon a suggerer un choix
delibere, une volonte, une strategie ou une coordination. Le vocabulaire
autorise decrit des produits et des pratiques de formulation observees :
« ces produits contiennent plus de phosphates », jamais « ce segment a choisi
de degrader ».

La seule chose testable est la TRACE OBSERVABLE d'une prescription commune :
une norme partagee RESSERRE la dispersion. La couche 11 mesure ce
resserrement. Elle ne le trouve pas — le bras halal est plus disperse a tous
les niveaux mesures. Une lecture en terme d'intention coordonnee n'a donc,
dans ces donnees, aucun appui, et l'affirmer serait une faute.

Une explication sans intention est toujours a considerer avant une
explication par l'intention : contrainte technique, taille de marche,
anciennete des recettes. Aucune n'est testee ici, et aucune n'est ecartee.

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
