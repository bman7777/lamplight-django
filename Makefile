# Simple Makefile for running scripted commands

# Define default target (what happens when you just type 'make')
.PHONY: all
all: help

# Help command to show available targets
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make seed-data       - Seed Redis + haystack index from bible data"
	@echo "  make lint            - Lint everything"
	@echo "  make py-deps         - Update python dependencies"

.PHONY: seed-data
seed-data:
	@echo "Seeding bible data..."
	python manage.py bible_to_redis apps/bible/data/bible.csv
	sudo mkdir -p /var/lib/lamplight/whoosh
  	sudo chown -R django:django /var/lib/lamplight
	su django -c '. /etc/conf.d/granian && python manage.py bible_to_haystack'

.PHONY: lint
lint:
	@echo "Linting..."
	black .
	isort .
	find . -path ./.venv -prune -o -path '*/migrations/*' -prune -o -name '*.py' -exec pylint {} +


.PHONY: py-deps
py-deps:
	@echo "Updating dependencies..."
	pip-compile requirements.in
	pip install -r requirements.txt


.PHONY: status-check
status-check:
	@echo "Checking status..."
	sudo systemctl status grafana-server | head -n 4
	sudo systemctl status nginx | head -n 4
	sudo systemctl status granian | head -n 4
	sudo systemctl status redis | head -n 4
