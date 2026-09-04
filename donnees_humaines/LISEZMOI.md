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

Gabarit vide genere sans aucun appel API, donc sans rien depenser :

```bash
python3 src/couche2_lecture_image.py --gabarit-seul --max 200 --taille full
```

Il sort dans `sorties/double_codage_a_remplir.csv`, avec les URL en pleine
resolution : le codeur doit voir exactement ce que le modele voit, sinon les
deux ne codent pas la meme chose. Le tirage est a graine figee, donc le
gabarit porte les memes produits que la lecture machine a venir. Minimum 200 produits : en dessous, le
taux d'erreur n'est pas publiable et `src/couche2_validation.py` s'arrete.
