.DEFAULT_GOAL := help
SHELL := /bin/bash

VENV    := .venv
PY      := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
PYTEST  := $(VENV)/bin/pytest

BOOK  ?=
THEME ?=

.PHONY: help setup check-tools preflight extract catalog pilot plan validate \
        web pptx render-pptx batch release test lint clean clean-build

help: ## Toon de beschikbare commando's
	@echo "New Ace 3 / New Strike 3 — pipeline"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "Variabelen:"
	@echo "  BOOK=ace3|strike3   THEME=<theme-id>   FORCE=1 (negeer de cache)"
	@echo "  SKIP_MISSING=1      batch: thema's zonder content overslaan"
	@echo "  ALLOW_PARTIAL=1     release: publiceer ondanks falende thema's"

# ---------------------------------------------------------------------------
# Installatie
# ---------------------------------------------------------------------------

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -r requirements.txt
	@touch $(VENV)/bin/activate

setup: $(VENV)/bin/activate check-tools ## Installeer alle afhankelijkheden
	@if [ -f package.json ]; then npm install --silent --no-audit --no-fund; fi
	@echo "Klaar. Draai nu: make preflight"

check-tools: ## Controleer of de systeemtools aanwezig zijn
	@missing=0; \
	for tool in pdftoppm tesseract soffice; do \
	  if ! command -v $$tool >/dev/null 2>&1; then \
	    echo "ONTBREEKT: $$tool"; missing=1; \
	  fi; \
	done; \
	if ! command -v ffmpeg >/dev/null 2>&1; then \
	  echo "optioneel niet gevonden: ffmpeg (alleen nodig voor echte audio/video)"; \
	fi; \
	if [ $$missing -eq 1 ]; then \
	  echo; \
	  echo "Installeer op Debian/Ubuntu:"; \
	  echo "  sudo apt-get install -y poppler-utils tesseract-ocr tesseract-ocr-eng tesseract-ocr-nld libreoffice"; \
	  exit 1; \
	fi; \
	echo "Alle vereiste systeemtools gevonden."

# ---------------------------------------------------------------------------
# Fase A — bron naar curriculumkaart
# ---------------------------------------------------------------------------

preflight: $(VENV)/bin/activate ## Inventariseer sources/ (read-only)
	$(PY) scripts/preflight.py

extract: $(VENV)/bin/activate ## Render en OCR een boek. Vereist BOOK=
	@if [ -z "$(BOOK)" ]; then echo "Gebruik: make extract BOOK=ace3"; exit 2; fi
	$(PY) scripts/extract.py --book $(BOOK) $(if $(THEME),--theme $(THEME),)

catalog: $(VENV)/bin/activate ## Bouw de curriculumkaart en schaalberekening
	$(PY) scripts/catalog.py $(if $(BOOK),--book $(BOOK),)

# ---------------------------------------------------------------------------
# Contentproductie
# ---------------------------------------------------------------------------

plan: $(VENV)/bin/activate ## Maak werkorder en blueprints. Vereist THEME=
	@if [ -z "$(THEME)" ]; then echo "Gebruik: make plan THEME=ace3-u1"; exit 2; fi
	$(PY) scripts/plan_theme.py --theme $(THEME)

pilot: plan ## Bereid het pilootthema voor en valideer wat er al is
	@echo
	@echo "Werkorder klaar. Schrijf de content en draai daarna:"
	@echo "  make validate THEME=$(THEME)"

validate: $(VENV)/bin/activate ## Valideer content tegen schema's en quota
	$(PY) scripts/validate.py $(if $(THEME),--theme $(THEME),)

# ---------------------------------------------------------------------------
# Builds
# ---------------------------------------------------------------------------

web: validate ## Bouw de statische leeromgeving
	npm run build:web

pptx: validate ## Genereer leerling- en leerkrachtdeck. Vereist BOOK= en THEME=
	@if [ -z "$(BOOK)" ] || [ -z "$(THEME)" ]; then \
	  echo "Gebruik: make pptx BOOK=ace3 THEME=ace3-u1"; exit 2; fi
	npm run build:pptx -- --book $(BOOK) --theme $(THEME)

answers: ## Bouw het correctiedeck bij de boekoefeningen. Vereist THEME=
	@if [ -z "$(THEME)" ]; then echo "Gebruik: make answers THEME=ace3-u1"; exit 2; fi
	npm run build:answers -- --theme $(THEME)

render-pptx: ## Render decks naar afbeeldingen voor visuele QA
	@if [ -z "$(BOOK)" ] || [ -z "$(THEME)" ]; then \
	  echo "Gebruik: make render-pptx BOOK=ace3 THEME=ace3-u1"; exit 2; fi
	@mkdir -p build/pptx-render/$(BOOK)/$(THEME)
	@for deck in dist/pptx/$(BOOK)/$(THEME)-student.pptx dist/pptx/$(BOOK)/$(THEME)-teacher.pptx; do \
	  if [ -f "$$deck" ]; then \
	    echo "Renderen: $$deck"; \
	    soffice --headless --convert-to pdf --outdir build/pptx-render/$(BOOK)/$(THEME) "$$deck" >/dev/null; \
	  else \
	    echo "Niet gevonden: $$deck"; exit 1; \
	  fi; \
	done
	@for pdf in build/pptx-render/$(BOOK)/$(THEME)/*.pdf; do \
	  pdftoppm -png -r 110 "$$pdf" "$${pdf%.pdf}-slide"; \
	done
	@echo "Renders in build/pptx-render/$(BOOK)/$(THEME)/"

batch: $(VENV)/bin/activate ## Valideer alle thema's van een boek. Vereist BOOK=
	@if [ -z "$(BOOK)" ]; then echo "Gebruik: make batch BOOK=ace3"; exit 2; fi
	$(PY) scripts/batch.py --book $(BOOK) $(if $(SKIP_MISSING),--skip-missing,)

release: $(VENV)/bin/activate ## Publiceer alleen gevalideerde artefacten naar dist/
	$(PY) scripts/release.py $(if $(ALLOW_PARTIAL),--allow-partial,)

# ---------------------------------------------------------------------------
# Kwaliteit
# ---------------------------------------------------------------------------

test: $(VENV)/bin/activate ## Draai de Python-testsuite
	$(PYTEST) tests -q

test-web: $(VENV)/bin/activate ## Draai de browser- en toegankelijkheidstests
	npm run test:e2e

lint: $(VENV)/bin/activate ## Typecheck de TypeScript
	npx tsc --noEmit

clean-build: ## Wis build/ (reproduceerbaar)
	rm -rf build/

clean: clean-build ## Wis build/ en de virtualenv
	rm -rf $(VENV) node_modules
