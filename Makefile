# SchemaFlow v2 — Makefile

PYTHON := python
BACKEND_DIR := backend
FRONTEND_DIR := frontend

.PHONY: dev-backend dev-frontend dev test reset-db lint install

## Start backend dev server
dev-backend:
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --port 8000

## Start frontend dev server  
dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

## Run backend tests
test:
	cd $(BACKEND_DIR) && pytest -v

## Reset database (with confirmation)
reset-db:
	cd $(BACKEND_DIR) && $(PYTHON) scripts/reset_db.py

## Reset database without confirmation
reset-db-force:
	cd $(BACKEND_DIR) && $(PYTHON) scripts/reset_db.py --yes

## Install all dependencies
install:
	cd $(BACKEND_DIR) && pip install -r requirements.txt
	cd $(FRONTEND_DIR) && npm install

## Type-check frontend
type-check:
	cd $(FRONTEND_DIR) && npx tsc --noEmit

## Lint frontend
lint-frontend:
	cd $(FRONTEND_DIR) && npm run build 2>&1 | head -50
