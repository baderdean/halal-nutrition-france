# Pipeline complet de la couche 1. Rejouable sur machine vierge :
#   make install && make couche1
#
# Variable HNF_DATA : repertoire de travail des gros fichiers
# (dump, parquets intermediaires). Hors depot, non versionne.

HNF_DATA ?= $(CURDIR)/data
PY       := HNF_DATA=$(HNF_DATA) python3
SRC      := src

.PHONY: install couche1 source france perimetre assertions analyse rapport \
        couche3 couche4 marques certificateurs classement amorce figer propre

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

couche4: marques certificateurs classement

marques:
	$(PY) $(SRC)/etape4_marques.py

certificateurs:
	$(PY) $(SRC)/etape4_certificateurs.py

# Ne relit que sorties/m_toutes_nutriscore.csv : ne demande pas le dump.
classement:
	$(PY) $(SRC)/etape4_classement_complet.py

# A n'utiliser que pour acter volontairement un changement de dump ou de
# perimetre. Jamais pour faire passer un pipeline rouge.
figer:
	$(PY) $(SRC)/etape0_source.py --figer
	$(PY) $(SRC)/etape1_assertions.py --figer

propre:
	rm -f $(HNF_DATA)/france.parquet $(HNF_DATA)/perimetre_carne_fr.parquet
