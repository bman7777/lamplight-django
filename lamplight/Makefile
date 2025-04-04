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

.PHONY: version-consume
version-consume:
	@echo "Consuming a version..."
	python lamplight/scripts/version_to_redis.py

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


.PHONY: status-check
status-check:
	@echo "Checking status..."
	sudo systemctl status grafana-server | head -n 4
	sudo systemctl status nginx | head -n 4
	sudo systemctl status gunicorn | head -n 4
	sudo systemctl status solr.service | head -n 4
	sudo systemctl status zookeeper.service | head -n 4
	sudo systemctl status redis | head -n 4
