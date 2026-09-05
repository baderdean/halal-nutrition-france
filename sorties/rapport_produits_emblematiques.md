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
| Mortadelle | 33 | 1 | 263 |
| Saucisson sec, salami, chorizo | 187 | 13 | 5181 |
| Merguez | 31 | 1 | 444 |
| Saucisses de volaille (hors merguez) | 129 | 11 | 484 |
| Cordon bleu | 82 | 1 | 534 |
| Nuggets | 85 | 2 | 414 |
| Escalopes et blancs panes (hors nuggets et cordons bleus) | 96 | 7 | 787 |
| Steak hache et viande hachee | 116 | 10 | 1268 |
| Jambon cuit (blanc, de volaille, a l'os) | 327 | 38 | 11092 |
| Blanc de poulet en decoupe (non pane, non cuit en tranches) | 60 | 8 | 4737 |

Le kasher ne franchit 30 que sur le jambon cuit. Partout ailleurs il est
decrit et jamais teste : conclure sur 1 ou 2 produits n'est pas conclure.

## Lecture 1 — le rayon

Especes confondues : ce que le client trouve sous ce nom. Cette lecture
melange le label et le changement d'espece qu'il impose.

| produit | bras | n | mediane | ecart_vs_temoin | ic95_bas | ic95_haut |
|:--|:--|--:|--:|--:|--:|--:|
| blanc_de_poulet | halal | 59 | -2.0 | +4.00 | +0.00 | +6.00 |
| blanc_de_poulet | kasher | 8 * | 3.5 |  |  |  |
| blanc_de_poulet | temoin | 4722 | -6.0 |  |  |  |
| cordon_bleu | halal | 82 | 11.0 | +5.00 | +0.00 | +5.00 |
| cordon_bleu | kasher | 1 * | 4.0 |  |  |  |
| cordon_bleu | temoin | 534 | 6.0 |  |  |  |
| escalope_panee | halal | 96 | 4.0 | +5.00 | +4.00 | +5.00 |
| escalope_panee | kasher | 7 * | 5.0 |  |  |  |
| escalope_panee | temoin | 786 | -1.0 |  |  |  |
| jambon_cuit | halal | 324 | 14.0 | +1.00 | +0.00 | +2.00 |
| jambon_cuit | kasher | 38 | 3.0 | -10.00 | -10.00 | -9.00 |
| jambon_cuit | temoin | 11052 | 13.0 |  |  |  |
| jambon_sec | halal | 3 * | 23.0 |  |  |  |
| jambon_sec | kasher | 1 * | 28.0 |  |  |  |
| jambon_sec | temoin | 2650 | 27.0 |  |  |  |
| merguez | halal | 31 | 18.0 | -3.00 | -6.00 | +1.00 |
| merguez | kasher | 1 * | 12.0 |  |  |  |
| merguez | temoin | 443 | 21.0 |  |  |  |
| mortadelle | halal | 33 | 18.0 | -4.00 | -6.00 | -3.00 |
| mortadelle | kasher | 1 * | 15.0 |  |  |  |
| mortadelle | temoin | 261 | 22.0 |  |  |  |
| nugget | halal | 85 | 5.0 | +1.00 | +0.00 | +2.00 |
| nugget | kasher | 2 * | 3.5 |  |  |  |
| nugget | temoin | 413 | 4.0 |  |  |  |
| saucisse_volaille | halal | 129 | 17.0 | +4.00 | +3.00 | +6.00 |
| saucisse_volaille | kasher | 11 * | 15.0 |  |  |  |
| saucisse_volaille | temoin | 480 | 13.0 |  |  |  |
| saucisson_sec | halal | 187 | 30.0 | -4.00 | -5.00 | -3.00 |
| saucisson_sec | kasher | 13 * | 32.0 |  |  |  |
| saucisson_sec | temoin | 5165 | 34.0 |  |  |  |
| steak_hache | halal | 114 | 11.0 | +5.00 | +2.00 | +5.00 |
| steak_hache | kasher | 10 * | 9.5 |  |  |  |
| steak_hache | temoin | 1231 | 6.0 |  |  |  |

## Lecture 2 — a espece egale

Jambon de dinde contre jambon de dinde. Seules les cellules testables
figurent ici.

| produit | espece | bras | n | mediane | ecart_vs_temoin | ic95_bas | ic95_haut |
|:--|:--|:--|--:|--:|--:|--:|--:|
| blanc_de_poulet | poulet | halal | 53 | -5.0 | +1.00 | +0.00 | +6.00 |
| cordon_bleu | dinde | halal | 37 | 11.0 | +0.00 | +0.00 | +5.00 |
| escalope_panee | poulet | halal | 84 | 4.0 | +1.00 | +0.00 | +2.00 |
| jambon_cuit | dinde | halal | 99 | 14.0 | +12.00 | +11.00 | +13.00 |
| jambon_cuit | indetermine | halal | 33 | 17.0 | +5.00 | +2.00 | +6.00 |
| jambon_cuit | poulet | halal | 150 | 12.0 | +10.00 | +10.00 | +11.00 |
| jambon_cuit | volaille_autre | halal | 39 | 17.0 | +0.00 | -2.00 | +1.00 |
| nugget | poulet | halal | 64 | 5.0 | +2.00 | +0.00 | +7.00 |
| saucisse_volaille | poulet | halal | 49 | 18.0 | +4.00 | +2.00 | +6.00 |
| saucisse_volaille | volaille_autre | halal | 71 | 16.0 | +5.00 | +4.00 | +13.00 |
| saucisson_sec | indetermine | halal | 112 | 30.0 | -4.00 | -6.00 | -2.00 |
| steak_hache | boeuf | halal | 109 | 11.0 | +5.00 | +2.00 | +5.00 |

## Lecture 3 — a marque et espece egales

Le meme fabricant, le meme produit, la meme espece : ne reste que le
label. Une seule cellule au monde le permet dans ces donnees.

| produit | marque | espece | n halal | n temoin | mediane halal | mediane temoin | ecart | IC 95 % |
|:--|:--|:--|--:|--:|--:|--:|--:|:-:|
| jambon_cuit | fleury-michon | poulet | 34 | 164 | 2.0 | 2.0 | +0.00 | [+0.00 ; +0.00] |

## L'ecart entre fabricants, a l'interieur du bras halal

| produit | marque | n | Nutri-Score | sel | proteines |
|:--|:--|--:|--:|--:|--:|
| jambon_cuit | fleury-michon | 54 | 2.0 | 1.8 | 21.0 |
| jambon_cuit | carrefour | 12 | 12.0 | 2.3 | 20.0 |
| jambon_cuit | isla-mondial | 28 | 13.0 | 2.4 | 18.9 |
| jambon_cuit | reghalal | 33 | 13.0 | 2.5 | 18.0 |
| jambon_cuit | arabi | 12 | 14.5 | 2.5 | 11.1 |
| jambon_cuit | isla-delice | 54 | 18.0 | 3.4 | 15.55 |
| nugget | isla-delice | 10 | 0.0 | 1.25 | 10.8 |
| saucisse_volaille | royal-halal | 13 | 13.0 | 1.7 | 17.0 |
| saucisson_sec | isla-mondial | 13 | 32.0 | 3.6 | 22.1 |
| saucisson_sec | oriental-viandes | 10 | 32.0 | 3.8 | 21.75 |
| saucisson_sec | isla-delice | 18 | 34.5 | 4.4 | 27.7 |
| steak_hache | isla-delice | 13 | 11.0 | 0.4 | 16.8 |

---

Le tag halal et le tag kasher sont des **declarations d'etiquetage**.
Rien ici ne dit quoi que ce soit de la halalite, de la casherout, de la
conformite ni de la qualite sanitaire d'aucun produit.
