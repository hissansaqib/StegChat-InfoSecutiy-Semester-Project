
# Makefile

# ------------------------------------------------------------
# Project wide make targets (Windows PowerShell wrapper: make.ps1)
# ------------------------------------------------------------

.PHONY: install dev backend frontend test lint check migrate e2e api-types

# Install both backend (Python) and frontend (Node) dependencies
install:
	@echo "Installing backend and frontend dependencies..."
	@cd backend && pip install -r requirements.txt || true
	@cd frontend && npm ci

# Run development servers concurrently (requires GNU Make on Windows or PowerShell wrapper)
dev:
	@$(MAKE) -j2 backend frontend

# Backend development server (uvicorn)
backend:
	@cd backend && uvicorn app.main:create_app --reload

# Frontend development server (Vite)
frontend:
	@cd frontend && npm run dev

# Run backend tests
test:
	@cd backend && pytest

# Run linters (ruff for backend, eslint for frontend)
lint:
	@cd backend && ruff .
	@cd frontend && npm run lint

# Combined lint + test for both stacks
check: lint test

# Apply Alembic migrations (ensure DB is up‑to‑date)
migrate:
	@cd backend && alembic upgrade head

# End‑to‑end placeholder (to be filled later)
 e2e:
	@echo "E2E tests placeholder – implement with Playwright or Cypress"

# Generate API TypeScript types from OpenAPI schema (requires backend running)
api-types:
	@cd frontend && npm run api:types

# ------------------------------------------------------------
# End of Makefile

