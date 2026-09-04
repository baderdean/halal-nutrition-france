# Quatre produits que le lecteur reconnait

Jambon cuit, cordon bleu, nuggets, saucisson sec, compares entre halal,
kasher et ni l'un ni l'autre. Le jambon SEC est ajoute parce que son
absence du rayon halal est elle-meme un resultat.

`n` suivi de `*` : moins de 30 produits, ligne decrite et jamais testee.
Un ecart n'est affiche que si les deux cellules comparees franchissent 30.

## Combien de produits, dans chaque bras

| produit | halal | kasher | ni l'un ni l'autre |
|:--|--:|--:|--:|
| Jambon sec et cru (Bayonne, Serrano, Parme, coppa) | 3 | 1 | 2660 |
| Saucisson sec, salami, chorizo | 187 | 13 | 5186 |
| Cordon bleu | 82 | 1 | 534 |
| Nuggets | 85 | 2 | 414 |
| Jambon cuit (blanc, de volaille, a l'os) | 253 | 36 | 7087 |

Le kasher ne franchit 30 que sur le jambon cuit. Partout ailleurs il est
decrit et jamais teste : conclure sur 1 ou 2 produits n'est pas conclure.

## Lecture 1 — le rayon

Especes confondues : ce que le client trouve sous ce nom. Cette lecture
melange le label et le changement d'espece qu'il impose.

| produit | bras | n | mediane | ecart_vs_temoin | ic95_bas | ic95_haut |
|:--|:--|--:|--:|--:|--:|--:|
| cordon_bleu | halal | 82 | 11.0 | +5.00 | +0.00 | +5.50 |
| cordon_bleu | kasher | 1 * | 4.0 |  |  |  |
| cordon_bleu | temoin | 534 | 6.0 |  |  |  |
| jambon_cuit | halal | 251 | 13.0 | +2.00 | +1.00 | +3.00 |
| jambon_cuit | kasher | 36 | 3.0 | -8.00 | -8.50 | -8.00 |
| jambon_cuit | temoin | 7054 | 11.0 |  |  |  |
| jambon_sec | halal | 3 * | 23.0 |  |  |  |
| jambon_sec | kasher | 1 * | 28.0 |  |  |  |
| jambon_sec | temoin | 2650 | 27.0 |  |  |  |
| nugget | halal | 85 | 5.0 | +1.00 | +0.00 | +2.00 |
| nugget | kasher | 2 * | 3.5 |  |  |  |
| nugget | temoin | 413 | 4.0 |  |  |  |
| saucisson_sec | halal | 187 | 30.0 | -4.00 | -5.00 | -3.00 |
| saucisson_sec | kasher | 13 * | 32.0 |  |  |  |
| saucisson_sec | temoin | 5170 | 34.0 |  |  |  |

## Lecture 2 — a espece egale

Jambon de dinde contre jambon de dinde. Seules les cellules testables
figurent ici.

| produit | espece | bras | n | mediane | ecart_vs_temoin | ic95_bas | ic95_haut |
|:--|:--|:--|--:|--:|--:|--:|--:|
| cordon_bleu | dinde | halal | 37 | 11.0 | +0.00 | +0.00 | +5.00 |
| jambon_cuit | dinde | halal | 85 | 14.0 | +12.00 | +11.00 | +13.00 |
| jambon_cuit | poulet | halal | 137 | 12.0 | +10.00 | +9.00 | +10.00 |
| nugget | poulet | halal | 64 | 5.0 | +2.00 | +0.00 | +6.50 |
| saucisson_sec | indetermine | halal | 112 | 30.0 | -4.00 | -6.00 | -2.00 |

## Lecture 3 — a marque et espece egales

Le meme fabricant, le meme produit, la meme espece : ne reste que le
label. Une seule cellule au monde le permet dans ces donnees.

| produit | marque | espece | n halal | n temoin | mediane halal | mediane temoin | ecart | IC 95 % |
|:--|:--|:--|--:|--:|--:|--:|--:|:-:|
| jambon_cuit | fleury-michon | poulet | 32 | 159 | 2.0 | 2.0 | +0.00 | [+0.00 ; +0.00] |

## L'ecart entre fabricants, a l'interieur du bras halal

| produit | marque | n | Nutri-Score | sel | proteines |
|:--|:--|--:|--:|--:|--:|
| jambon_cuit | fleury-michon | 51 | 2.0 | 1.8 | 21.0 |
| jambon_cuit | carrefour | 10 | 12.0 | 2.3 | 20.0 |
| jambon_cuit | isla-mondial | 16 | 12.0 | 2.4 | 19.1 |
| jambon_cuit | reghalal | 27 | 13.0 | 2.4 | 18.0 |
| jambon_cuit | isla-delice | 37 | 18.0 | 3.4 | 16.6 |
| nugget | isla-delice | 10 | 0.0 | 1.25 | 10.8 |
| saucisson_sec | isla-mondial | 13 | 32.0 | 3.6 | 22.1 |
| saucisson_sec | oriental-viandes | 10 | 32.0 | 3.8 | 21.75 |
| saucisson_sec | isla-delice | 18 | 34.5 | 4.4 | 27.7 |

---

Le tag halal et le tag kasher sont des **declarations d'etiquetage**.
Rien ici ne dit quoi que ce soit de la halalite, de la casherout, de la
conformite ni de la qualite sanitaire d'aucun produit.
