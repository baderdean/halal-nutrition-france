# Pipeline complet de la couche 1. Rejouable sur machine vierge :
#   make install && make couche1
#
# Variable HNF_DATA : repertoire de travail des gros fichiers
# (dump, parquets intermediaires). Hors depot, non versionne.

HNF_DATA ?= $(CURDIR)/data
PY       := HNF_DATA=$(HNF_DATA) python3
SRC      := src

.PHONY: install couche1 source france perimetre assertions analyse rapport \
        couche3 couche4 couche5 couche6 couche7 couche8 marques \
        certificateurs classement halal emblematiques reperes additifs prix paires \
        etablissements homogeneite allegations resultats couche9 couche10 \
        couche11 couche12 couche13 site amorce figer propre

install:
	pip install -r requirements.txt

couche1: source france perimetre assertions analyse rapport
	@echo "\nCouche 1 terminee. Rapport : sorties/rapport_couche1.md"

source:
	$(PY) $(SRC)/etape0_source.py

france:
	$(PY) $(SRC)/etape0_extraction_france.py

# Etape de decouverte. Ne produit aucun resultat d'etude : sa sortie sert a
# figer config/perimetre.yaml a la main. Hors du pipeline principal.
amorce:
	$(PY) $(SRC)/etape1_amorce.py

perimetre:
	$(PY) $(SRC)/etape1_perimetre.py

assertions:
	$(PY) $(SRC)/etape1_assertions.py

analyse:
	$(PY) $(SRC)/etape1_analyse.py

rapport:
	$(PY) $(SRC)/etape1_rapport.py

couche3:
	$(PY) $(SRC)/etape3_appariement.py

couche4: marques certificateurs classement halal

marques:
	$(PY) $(SRC)/etape4_marques.py

certificateurs:
	$(PY) $(SRC)/etape4_certificateurs.py

# Ne relisent que des CSV de sorties/ : ne demandent pas le dump.
classement:
	$(PY) $(SRC)/etape4_classement_complet.py

halal:
	$(PY) $(SRC)/etape4_classement_halal.py

couche5: emblematiques

# Demande le parquet de perimetre (make perimetre), pas seulement des CSV.
emblematiques:
	$(PY) $(SRC)/etape5_produits_emblematiques.py

couche6: reperes

reperes:
	$(PY) $(SRC)/etape6_reperes_consommateur.py

couche7: additifs

additifs:
	$(PY) $(SRC)/etape7_additifs_transformation.py

# La COLLECTE des prix ne tourne pas ici : prices.openfoodfacts.org est refuse
# par la politique de sortie reseau. Elle passe par le workflow couche8-prix.
# Cette cible n'analyse que le releve deja commite.
couche8: prix

prix:
	$(PY) $(SRC)/etape8_prix.py

couche9: paires

paires:
	$(PY) $(SRC)/etape9_podiums.py

couche10: etablissements

etablissements:
	$(PY) $(SRC)/etape10_etablissements.py

couche11: homogeneite

homogeneite:
	$(PY) $(SRC)/etape11_homogeneite.py

couche12: allegations

allegations:
	$(PY) $(SRC)/etape12_allegations.py

couche13: site

site:
	$(PY) $(SRC)/etape13_site_ou_marque.py

# RESULTATS.md est GENERE : ne relit que sorties/, jamais le dump.
resultats:
	$(PY) $(SRC)/rapport_hypotheses.py

# A n'utiliser que pour acter volontairement un changement de dump ou de
# perimetre. Jamais pour faire passer un pipeline rouge.
figer:
	$(PY) $(SRC)/etape0_source.py --figer
	$(PY) $(SRC)/etape1_assertions.py --figer

propre:
	rm -f $(HNF_DATA)/france.parquet $(HNF_DATA)/perimetre_carne_fr.parquet
