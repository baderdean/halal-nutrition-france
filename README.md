# Qualite nutritionnelle des produits carnes halal industriels en France

Etude comparant les produits carnes industriels estampilles halal et leurs
equivalents non estampilles, sur le dump Open Food Facts. Destination : article
de vulgarisation avec annexe methodologique.

**Le traitement est le label, pas la halalite religieuse.** Tout produit carne
sans estampille relevee est classe temoin, assume et documente. Les regles de
l'etude sont dans [`AGENTS.md`](AGENTS.md) et ne se modifient pas par un
ajustement de requete.

Etat : **couche 1 executee**. Voir [`sorties/rapport_couche1.md`](sorties/rapport_couche1.md).

## Rejouer

Machine vierge, Python 3.11+, ~15 Go de disque libre :

```bash
pip install -r requirements.txt
make couche1
```

Le dump (1,2 Go compresse) est telecharge, verifie par taille et sha256, puis
lu une seule fois. Comptez une dizaine de minutes au total. Pour placer les
gros fichiers ailleurs que dans `data/` :

```bash
make couche1 HNF_DATA=/chemin/vers/scratch
```

Le dump Open Food Facts est republie chaque jour. Si sa signature a change, le
pipeline s'arrete : c'est voulu. Pour acter la nouvelle version :

```bash
make figer      # met a jour source.yaml puis effectifs_attendus.yaml
make couche1
```

## Organisation

| Chemin | Role |
|---|---|
| `AGENTS.md` | regles non negociables : definitions, interdits, assertions |
| `config/source.yaml` | dump figé : URL, date, taille, sha256, licences |
| `config/graines.yaml` | graines de recherche. N'entrent dans aucun calcul |
| `config/perimetre.yaml` | perimetre FIGE : racines, exclusions, sous-categories |
| `config/effectifs_attendus.yaml` | effectifs de reference, tolerance declaree |
| `src/etape0_source.py` | telechargement et verification du dump |
| `src/etape0_extraction_france.py` | une passe sur le dump -> `france.parquet` |
| `src/etape1_amorce.py` | decouverte des categories. Hors pipeline principal |
| `src/etape1_perimetre.py` | application du perimetre fige, deduplication |
| `src/etape1_assertions.py` | assertions bloquantes, avant toute sortie |
| `src/etape1_analyse.py` | comptages D0-D7 et comparaisons C1-C4 -> CSV |
| `src/etape1_rapport.py` | assemblage du rapport, aucun chiffre en dur |
| `sorties/` | CSV, `chiffres_cles.json`, rapport. Versionnes |

`make amorce` est la seule etape qui ne fait pas partie du pipeline : elle sert
a construire `config/perimetre.yaml` a la main. La relancer ne change aucun
resultat.

## Ce que la couche 1 conclut

Reponses courtes, chiffres et nuances dans le rapport :

- **L'etude est faisable.** Neuf sous-categories carnees franchissent la regle
  des 30 dans les deux bras.
- **Le Nutri-Score n'est pas sature** a l'echelle du perimetre, mais il l'est
  dans la charcuterie seche, les saucisses et les rillettes.
- **L'effet certificateur est abandonne**, non pour inseparabilite mais pour
  couverture : moins de 7 % des produits halal portent un tag de certificateur.
- **L'ecart brut de sel existe mais est confondu avec la transformation** : a
  sous-categorie egale, le bras halal est plus transforme dans 9 strates sur 9.
- **La dispersion interne au bras halal domine l'ecart entre bras** dans les
  neuf strates. C'est le seul constat de cette couche qui soit a la fois solide
  et actionnable en rayon.

## Licence et attribution des donnees

Donnees Open Food Facts, base sous
[Open Database License (ODbL) v1.0](https://opendatacommons.org/licenses/odbl/1-0/),
contenus sous [Database Contents License (DbCL) v1.0](https://opendatacommons.org/licenses/dbcl/1-0/).
Toute reutilisation des sorties de ce depot doit citer Open Food Facts et ses
contributeurs.
