# Skema Development Makefile
# Provides convenient commands for development and deployment

.PHONY: help build start stop restart logs clean test backup deploy

# Default target
help: ## Show this help message
	@echo "Skema Development Commands"
	@echo "=========================="
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Quick Start:"
	@echo "  make start    # Start the development environment"
	@echo "  make logs     # View application logs"
	@echo "  make stop     # Stop all services"

# Development Environment
start: ## Start the development environment
	@echo "🚀 Starting Skema development environment..."
	@chmod +x scripts/start.sh
	@./scripts/start.sh

stop: ## Stop all services
	@echo "🛑 Stopping Skema services..."
	@docker-compose down

restart: ## Restart all services
	@echo "🔄 Restarting Skema services..."
	@docker-compose restart

build: ## Build all Docker images
	@echo "🔨 Building Skema Docker images..."
	@docker-compose build --no-cache

# Logging and Monitoring
logs: ## Show logs from all services
	@docker-compose logs -f

logs-backend: ## Show backend logs only
	@docker-compose logs -f backend

logs-frontend: ## Show frontend logs only
	@docker-compose logs -f frontend

logs-db: ## Show database logs only
	@docker-compose logs -f postgres

# Database Operations
db-shell: ## Access PostgreSQL shell
	@docker-compose exec postgres psql -U skema_user -d skema

db-migrate: ## Run database migrations
	@docker-compose exec backend alembic upgrade head

db-downgrade: ## Downgrade database by one migration
	@docker-compose exec backend alembic downgrade -1

db-reset: ## Reset database (WARNING: destroys all data)
	@echo "⚠️  WARNING: This will destroy all database data!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker-compose down
	@docker volume rm skema_postgres_data || true
	@docker-compose up -d postgres
	@sleep 10
	@docker-compose up -d

backup: ## Create database backup
	@echo "💾 Creating database backup..."
	@chmod +x scripts/backup.sh
	@docker-compose exec -T postgres /backup.sh

# Development Tools
shell-backend: ## Access backend container shell
	@docker-compose exec backend /bin/bash

shell-frontend: ## Access frontend container shell
	@docker-compose exec frontend /bin/bash

shell-db: ## Access database container shell
	@docker-compose exec postgres /bin/bash

# Testing
test: ## Run all tests
	@echo "🧪 Running tests..."
	@make test-backend
	@make test-frontend

test-backend: ## Run backend tests
	@echo "🧪 Running backend tests..."
	@docker-compose exec backend python -m pytest tests/ -v

test-frontend: ## Run frontend tests
	@echo "🧪 Running frontend tests..."
	@docker-compose exec frontend npm test

test-e2e: ## Run end-to-end tests
	@echo "🧪 Running E2E tests..."
	@docker-compose exec frontend npm run test:e2e

# Code Quality
lint: ## Run linters
	@echo "🔍 Running linters..."
	@make lint-backend
	@make lint-frontend

lint-backend: ## Run backend linter
	@docker-compose exec backend flake8 app/
	@docker-compose exec backend black --check app/

lint-frontend: ## Run frontend linter
	@docker-compose exec frontend npm run lint

format: ## Format code
	@echo "🎨 Formatting code..."
	@docker-compose exec backend black app/
	@docker-compose exec backend isort app/
	@docker-compose exec frontend npm run format

typecheck: ## Run type checking
	@echo "🔍 Running type checks..."
	@docker-compose exec backend mypy app/
	@docker-compose exec frontend npm run typecheck

# Security
security-scan: ## Run security scans
	@echo "🔒 Running security scans..."
	@docker-compose exec backend bandit -r app/
	@docker-compose exec frontend npm audit

# Cleanup
clean: ## Clean up containers, images, and volumes
	@echo "🧹 Cleaning up Docker resources..."
	@docker-compose down --remove-orphans
	@docker system prune -f
	@docker volume prune -f

clean-all: ## Clean up everything including images and volumes (DESTRUCTIVE)
	@echo "⚠️  WARNING: This will remove all containers, images, and volumes!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker-compose down --remove-orphans
	@docker system prune -af
	@docker volume prune -f

# Production Deployment
deploy-prod: ## Deploy to production
	@echo "🚀 Deploying to production..."
	@docker-compose -f docker-compose.prod.yml build
	@docker-compose -f docker-compose.prod.yml up -d

deploy-staging: ## Deploy to staging
	@echo "🚀 Deploying to staging..."
	@docker-compose -f docker-compose.staging.yml build
	@docker-compose -f docker-compose.staging.yml up -d

# Health Checks
health: ## Check service health
	@echo "🏥 Checking service health..."
	@curl -f http://localhost:8000/health || echo "❌ Backend unhealthy"
	@curl -f http://localhost:3000/api/health || echo "❌ Frontend unhealthy"
	@docker-compose exec postgres pg_isready -U skema_user -d skema || echo "❌ Database unhealthy"

status: ## Show service status
	@echo "📊 Service Status:"
	@docker-compose ps

# Environment Management
env-setup: ## Set up environment file from example
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file from .env.example"; \
		echo "📝 Please review and update the .env file with your settings"; \
	else \
		echo "ℹ️  .env file already exists"; \
	fi

env-validate: ## Validate environment configuration
	@echo "🔍 Validating environment configuration..."
	@docker-compose config >/dev/null && echo "✅ Environment configuration is valid" || echo "❌ Environment configuration is invalid"

# Documentation
docs: ## Generate and serve documentation
	@echo "📚 Generating documentation..."
	@docker-compose exec backend python -c "import app.main; print('Backend API docs: http://localhost:8000/docs')"
	@echo "📖 Frontend Storybook: http://localhost:6006 (if running)"

# Monitoring with additional tools
monitor: ## Start monitoring services
	@echo "📊 Starting monitoring services..."
	@docker-compose --profile monitoring up -d

monitor-stop: ## Stop monitoring services
	@docker-compose --profile monitoring down

# Development utilities
seed-data: ## Seed database with sample data
	@echo "🌱 Seeding database with sample data..."
	@docker-compose exec postgres psql -U skema_user -d skema -f /docker-entrypoint-initdb.d/02-seed.sql

reset-frontend: ## Reset frontend dependencies
	@echo "🔄 Resetting frontend dependencies..."
	@docker-compose exec frontend rm -rf node_modules package-lock.json
	@docker-compose exec frontend npm install

reset-backend: ## Reset backend dependencies
	@echo "🔄 Resetting backend dependencies..."
	@docker-compose exec backend pip install --force-reinstall -r requirements.txt

# Performance testing
perf-test: ## Run performance tests
	@echo "⚡ Running performance tests..."
	@docker-compose exec backend python -m pytest tests/performance/ -v

load-test: ## Run load tests
	@echo "🏋️  Running load tests..."
	@docker-compose exec backend locust --host=http://localhost:8000

# SSL certificate generation (for development HTTPS)
ssl-cert: ## Generate self-signed SSL certificate for development
	@echo "🔐 Generating self-signed SSL certificate..."
	@mkdir -p docker/ssl
	@openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
		-keyout docker/ssl/privkey.pem \
		-out docker/ssl/fullchain.pem \
		-subj "/C=US/ST=Development/L=Local/O=Skema/OU=Development/CN=localhost"
	@echo "✅ SSL certificate generated at docker/ssl/"

# Database utilities
db-dump: ## Create database dump
	@echo "💾 Creating database dump..."
	@mkdir -p backup
	@docker-compose exec postgres pg_dump -U skema_user skema > backup/skema_dump_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database dump created in backup/ directory"

db-restore: ## Restore database from dump (specify DUMP_FILE=path/to/dump.sql)
	@echo "📥 Restoring database from $(DUMP_FILE)..."
	@docker-compose exec -T postgres psql -U skema_user -d skema < $(DUMP_FILE)
	@echo "✅ Database restored successfully"

# Quick development shortcuts
dev: start ## Alias for start command

up: start ## Alias for start command

down: stop ## Alias for stop command