# Donnees saisies a la main

Ce repertoire contient des fichiers d'ENTREE, jamais des sorties generees.
Rien ici ne doit etre produit par un script ou par un agent.

## double_codage.csv

Relecture humaine d'un echantillon d'emballages, en aveugle : le codeur ne
consulte pas `sorties/couche2_lecture_image.csv` avant d'avoir fini.

Colonnes attendues :

| Colonne | Valeurs |
|---|---|
| `code` | code-barres du produit |
| `h_estampille_halal` | `oui` / `non` / `illisible` |
| `h_certificateur` | nom lu sur l'emballage, vide si aucun |
| `h_lisibilite` | `nette` / `floue` / `trop_petite` / `zone_absente` |
| `h_commentaire` | libre |

Gabarit vide genere par `src/couche2_lecture_image.py` dans
`sorties/double_codage_a_remplir.csv`. Minimum 200 produits : en dessous, le
taux d'erreur n'est pas publiable et `src/couche2_validation.py` s'arrete.
