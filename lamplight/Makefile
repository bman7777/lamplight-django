# Simple Makefile for running scripted commands

# Define default target (what happens when you just type 'make')
.PHONY: all
all: help

# Help command to show available targets
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make chapter-consume - Process chapter data"
	@echo "  make lint            - Lint everything"
	@echo "  make py-deps         - Update python dependencies"

.PHONY: chapter-consume
chapter-consume:
	@echo "Consuming a chapter..."
	python lamplight/scripts/bible_to_redis.py lamplight/scripts/bible.csv
	python lamplight/scripts/biblecsv_to_solrdoc.py lamplight/scripts/bible.csv -o lamplight/scripts/bible.json
	python lamplight/scripts/doc_to_solr.py lamplight/scripts/bible.json -c verses

.PHONY: lint
lint:
	@echo "Linting..."
	black .
	isort .
	pylint ../**/*/*.py


.PHONY: py-deps
py-deps:
	@echo "Updating dependencies..."
	pip-compile ../requirements.in
	pip install -r ../requirements.txt
