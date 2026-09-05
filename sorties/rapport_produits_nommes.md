# Produits nommes — codes-barres

Genere par `src/etape9_podiums.py`. **Trois niveaux de solidite, du
plus sur au moins sur. Ne pas les melanger.**

Les valeurs nutritionnelles sont DECLAREES par le fabricant et
saisies par des contributeurs Open Food Facts. Elles ne sont pas
dosees. Un produit nomme ici peut avoir change de recette depuis la
saisie, ou avoir ete mal saisi.

## Niveau 1 — paires appariees (le plus sur)

Meme marque, meme nom, meme gamme, meme espece : le fabricant vend le
meme produit en deux versions. La comparaison ne depend pas de la
qualite des categories Open Food Facts, qui est le point faible de
tout le reste.

29 paires comparables : 15 identiques, 9 defavorables au halal, 5 favorables.

### Defavorables au halal

| marque | produit | EAN halal | EAN non halal | Nutri-Score halal | non halal | ecart | sel halal | sel non halal |
|:--|:--|:--|:--|--:|--:|--:|--:|--:|
| carrefour | blanc dinde fum | `3560070503735` | `3560071013837` | +12.0 | +2.0 | **+10.0** | 2.30 | 1.70 |
| carrefour | merguez volaille | `3560070569212` | `3560070756568` | +15.0 | +8.0 | **+7.0** | 1.80 | 1.65 |
| carrefour | blanc poulet | `3560071488086` | `3560071449605` | +3.0 | +0.0 | **+3.0** | 1.90 | 1.30 |
| carrefour | saucisses volaille | `3560070569182` | `3560070756629` | +15.0 | +12.0 | **+3.0** | 1.70 | 2.00 |
| duc | aiguillettes poulet | `0225019031955` | `3531940163007` | -4.0 | -6.0 | **+2.0** | 0.25 | 0.10 |
| isla-mondial | blanc poulet | `15825889` | `3459860005750` | +12.0 | +11.0 | **+1.0** | 2.10 | 2.16 |
| fleury-michon | blanc poulet | `3095759626011` | `06636074` | +2.0 | +1.0 | **+1.0** | 1.80 | 1.50 |
| leader-price | nuggets poulet | `3255790616581` | `3263859581916` | +13.0 | +12.0 | **+1.0** | 1.62 | 1.30 |
| jack-link-s | beef jerky sweet hot | `4251097403106` | `4251097402918` | +24.5 | +24.0 | **+0.5** | 3.15 | 3.00 |

### Favorables au halal ou identiques

| marque | produit | EAN halal | EAN non halal | Nutri-Score halal | non halal | ecart | sel halal | sel non halal |
|:--|:--|:--|:--|--:|--:|--:|--:|--:|
| bongou | magret canard fum entier s v | `3665902203019` | `3665902203002` | +27.0 | +27.0 | +0.0 | 2.70 | 2.70 |
| carrefour | poulet cuit fum | `3560070649594` | `0276382062589` | +0.0 | +0.0 | +0.0 | 1.10 | 1.10 |
| fleury-michon | blanc dinde | `3095757228019` | `3302749746025` | +2.0 | +2.0 | +0.0 | 1.75 | 1.70 |
| berni | salami dinde | `3264057554542` | `3264057554061` | +16.0 | +16.0 | +0.0 | 1.30 | 1.30 |
| bongou | magret canard fum tranch s v | `3665902203026` | `3665902201381` | +27.0 | +27.0 | +0.0 | 2.70 | 2.70 |
| aldi | filets poulet | `3531940601004` | `2167705005346` | -6.0 | -6.0 | +0.0 | 0.12 | 0.10 |
| socopa | steak hach fa on bouch re | `3039050337238` | `3039050330161` | +7.0 | +7.0 | +0.0 | 0.22 | 0.22 |
| seara | chicken nuggets | `7894904572205` | `7894904218929` | +2.0 | +2.0 | +0.0 | 0.50 | 0.60 |
| duc | filets poulet | `3531940200009` | `3531940160006` | -6.0 | -6.0 | +0.0 | 0.10 | 0.10 |
| fleury-michon | blanc poulet | `3095752622010` | `3095756799015` | +2.0 | +2.0 | +0.0 | 1.80 | 1.80 |
| fleury-michon | blanc poulet sel | `3095758403019` | `3302740075025` | +0.0 | +0.0 | +0.0 | 1.40 | 1.40 |
| fleury-michon | filet poulet r ti | `3095757199012` | `3302740057502` | +2.0 | +2.0 | +0.0 | 1.80 | 1.70 |
| foo-seng | nems au poulet | `3760195545515` | `3760195541524` | +7.0 | +7.0 | +0.0 | 1.27 | 1.27 |
| klein-karoo | pav filet d autruche pr grill | `6008123006187` | `6008123005203` | -3.0 | -3.0 | +0.0 | 0.80 | 0.80 |
| volaille-francaise | filets poulet | `3531940369003` | `2600497071040` | -6.0 | -6.0 | +0.0 | 0.11 | 0.10 |
| carrefour | saucisson sec | `3700141402790` | `3560071014681` | +32.0 | +34.0 | -2.0 | 3.60 | 4.70 |
| carrefour | filets poulet | `3560070486892` | `3270190209614` | -6.0 | -2.0 | -4.0 | 0.14 | 0.55 |
| herta | lardons fum s | `3512690003379` | `7613036113281` | +16.0 | +20.0 | -4.0 | 2.60 | 2.20 |
| fleury-michon | fleury michon | `3095752586015` | `3095757119010` | +2.0 | +7.0 | -5.0 | 1.77 | 1.80 |
| fleury-michon | blanc poulet fum | `3095759627018` | `3095759625014` | +2.0 | +10.5 | -8.5 | 1.80 | 2.77 |

**Une paire n'est pas un test.** La plupart reposent sur une
reference de chaque cote : c'est une observation, pas une mesure
avec un intervalle.

## Niveau 2 — candidats contre le marche (a verifier)

Comparateur : meme produit emblematique, meme espece, bras temoin,
au moins 30 produits. Le `percentile` situe le produit
halal dans cette distribution ; 100 = pire que tous les temoins.

**Ces lignes ne sont pas un palmares.** Le comparateur vient des
categories Open Food Facts, et trois tentatives ont chacune produit
une comparaison truquee : des allumettes de poulet fumees comparees
a du filet cru, des cachir cuits comparés a du saucisson sec, des
lardons de dinde compares a du jambon cuit. Avant de nommer un
produit, verifier :

1. le produit est-il l'aliment que sa categorie annonce ;
2. le comparateur est-il le meme aliment ;
3. la valeur est-elle plausible, ou est-ce une erreur de saisie.

### Les plus eloignes vers le haut (moins bons)

| EAN | produit | marque | comparateur | n ref | grade | Nutri-Score | ref | ecart | percentile | sel | sel ref |
|:--|:--|:--|:--|--:|:-:|--:|--:|--:|--:|--:|--:|
| `3760238430785` | Delice de poulet | Arabi | jambon_cuit / poulet | 723 | E | +27.0 | +2.0 | **+25.0** | 100.0 | 6.00 | 1.80 |
| `3222475503979` | Lardons de dinde fumés halal | Wassila | jambon_cuit / dinde | 191 | E | +26.0 | +2.0 | **+24.0** | 99.5 | 3.50 | 1.78 |
| `3760059780106` | Burgers de dinde épicés | Mahdia | escalope_panee / dinde | 464 | D | +18.0 | -3.0 | **+21.0** | 99.6 | 2.40 | 0.78 |
| `3266980474065` | Lardons de volaille fumés au bois de hêtre | Réghalal | jambon_cuit / dinde | 191 | E | +22.0 | +2.0 | **+20.0** | 99.0 | 2.66 | 1.78 |
| `5411431834006` | Blanc de poulet mechouia | nan | jambon_cuit / poulet | 723 | E | +22.0 | +2.0 | **+20.0** | 99.3 | 3.50 | 1.80 |
| `8711659430057` | Tranchés goût bœuf piquant | Sibel | jambon_cuit / poulet | 723 | E | +22.0 | +2.0 | **+20.0** | 99.3 | 2.50 | 1.80 |
| `3760114535207` | Délicr de poulet | Al Jadid | jambon_cuit / poulet | 723 | E | +21.0 | +2.0 | **+19.0** | 98.8 | 5.00 | 1.80 |
| `3700483801060` | Chorizo dinde halal | Mosaic | jambon_cuit / dinde | 191 | E | +21.0 | +2.0 | **+19.0** | 97.4 | 3.24 | 1.78 |
| `3276447824005` | Allumettes de Dinde, Halal | Médina Halal | jambon_cuit / dinde | 191 | E | +20.0 | +2.0 | **+18.0** | 97.4 | 3.70 | 1.78 |
| `4047187001358` | Selam hindi dilim | nan | jambon_cuit / indetermine | 6820 | E | +30.0 | +12.0 | **+18.0** | 99.2 | 3.30 | 1.90 |

### Les plus eloignes vers le bas (meilleurs)

| EAN | produit | marque | comparateur | n ref | grade | Nutri-Score | ref | ecart | percentile | sel | sel ref |
|:--|:--|:--|:--|--:|:-:|--:|--:|--:|--:|--:|--:|
| `3459860004364` | Saucisson à l'ail fumé | Isla Mondial | saucisson_sec / indetermine | 4208 | D | +12.0 | +34.0 | **-22.0** | 0.6 | 2.20 | 4.40 |
| `8416820004364` | Saucisson à l'ail | nan | saucisson_sec / indetermine | 4208 | D | +12.0 | +34.0 | **-22.0** | 0.6 | 2.20 | 4.40 |
| `3760114530073` | Mortadelle fumé | Essafa Halal | mortadelle / indetermine | 219 | B | +1.0 | +22.0 | **-21.0** | 0.0 | 1.28 | 2.33 |
| `3436598132637` | Cachir SoKid's au fromage | Oriental Viandes | saucisson_sec / indetermine | 4208 | D | +13.0 | +34.0 | **-21.0** | 0.8 | 1.90 | 4.40 |
| `4260467592043` | Birbeli Salam | Destan | saucisson_sec / indetermine | 4208 | D | +13.0 | +34.0 | **-21.0** | 0.8 | 2.40 | 4.40 |
| `3760114530363` | Chorizo les gourmets | Al Jadid | saucisson_sec / porc | 906 | D | +14.0 | +34.0 | **-20.0** | 0.8 | 2.36 | 4.40 |
| `3760114530882` | Chorizo pur boeuf | Al Jadid | saucisson_sec / indetermine | 4208 | D | +14.0 | +34.0 | **-20.0** | 1.0 | 2.36 | 4.40 |
| `3512690000095` | Sauciss Delice Fume, | Isla delice | saucisson_sec / porc | 906 | D | +14.0 | +34.0 | **-20.0** | 0.8 | 2.00 | 4.40 |
| `3512690002686` | Saveur'délice goût boeuf piquant | Isla Délice | saucisson_sec / indetermine | 4208 | D | +15.0 | +34.0 | **-19.0** | 1.5 | 2.19 | 4.40 |
| `3512690004390` | Cachir | Isla delice | saucisson_sec / indetermine | 4208 | D | +15.0 | +34.0 | **-19.0** | 1.5 | 2.40 | 4.40 |

## Niveau 3 — ecartes, et pourquoi

Ces produits ne sont PAS mauvais : ils sont incomparables en
l'etat. Les publier comme mauvais serait une erreur.

### Sel invraisemblable (> 6.0 g/100 g)

Au-dela de ce seuil c'est une erreur de saisie, pas un produit.

| EAN | produit | marque | sel declare |
|:--|:--|:--|--:|
| `3253880000036` | 35 Boulettes Orientales Halal Surgelées | Al jayid | 11.00 |
| `4251871704313` | Mortadelle de poulet | nan | 7.00 |
| `3760114530066` | Cachir gout poulet | Essafa | 8.00 |
| `2763907002567` | Saucisson Pur Bœuf Halal | nan | 6.20 |
| `2763907002673` | Saucisson pur Bœuf sélection Halal | nan | 6.20 |
| `2763907003038` | Saucisson pur boeuf | nan | 6.20 |
| `3683080570372` | Salami de boeuf | H.market  sélection | 10.00 |
| `3095757195014` | Blanc de Poulet  - 25% de sel* Halal | Fleury Michon | 13.77 |
| `3770022585546` | Cordon bleu de poulet halal | nan | 12.00 |
| `4040328070633` | Mini saucissons de poulet | Suntat | 6.30 |

### Forme incoherente avec la categorie

Une decoupe crue ne porte pas 2 a 3 g de sel. Ces produits sont
cuits ou tranches, mais leur categorie Open Food Facts ne le dit
pas : les comparer a du filet cru serait truquer la comparaison
a leur detriment.

29 produits halal concernes. Extrait :

| EAN | produit | marque | sel |
|:--|:--|:--|--:|
| `2463498031228` | Filet de poulet rôti | nan | 1.20 |
| `2463498032218` | Filet de poulet rôti | nan | 1.20 |
| `2463498034045` | filet de poulet rôti halal | nan | 1.20 |
| `2463498034243` | Filets de poulet Rôti | Réghalal | 1.20 |
| `2463498034441` | Filets de poulet rôti | nan | 1.20 |
| `2463498036865` | Filet de poulet rôti | nan | 1.20 |
| `2463498041784` | Filets de poulet rôti | Réghalal | 1.70 |
| `2463498049599` | Filet de poulet roti | nan | 1.20 |
| `2900541001109` | Blanc de dinde au 3 poivre | nan | 3.39 |
| `3266980011475` | Blanc de dinde | Réghalal | 2.90 |
| `3760383400190` | Aiguilette de poulet | nan | 1.60 |
| `3459860005767` | Blanc de dinde goût fumé | Isla Mondial | 2.40 |
| `5901664003695` | Emince de filet de poulet halal cuit tikka surgele | nan | 2.10 |
| `6312130764399` | Burger de filet de poulet | nan | 1.14 |
| `2850227073602` | Filet de poulet Paprika | Réghalal | 1.90 |

---

Les marques et produits nommes le sont sur la foi d'une base
collaborative. Rien ici ne dit quoi que ce soit de la halalite, de
la conformite ou de la securite sanitaire d'un produit.

