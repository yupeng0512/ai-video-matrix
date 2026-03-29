.PHONY: setup start stop logs build test stress-test clean health

# ============================================================
# AI Video Matrix — Makefile
# ============================================================

HOST_IP ?= 9.135.86.144

setup:
	bash scripts/setup.sh

build:
	docker compose build

start:
	docker compose up -d

stop:
	docker compose down

restart:
	docker compose down && docker compose up -d

logs:
	docker compose logs -f --tail=100

logs-service:
	docker compose logs -f --tail=100 $(SERVICE)

# Start only infrastructure
infra:
	docker compose up -d postgres redis rabbitmq minio

# Start only custom services
services:
	docker compose up -d content-planner video-mutator content-router publisher

# Rebuild and restart a specific service
rebuild:
	docker compose build $(SERVICE) && docker compose up -d $(SERVICE) --force-recreate

# Run stress test
stress-test:
	python scripts/stress_test.py --hours 0.5

# Run full 72-hour stress test
stress-test-full:
	python scripts/stress_test.py --hours 72

# Test video API
test-kling:
	python scripts/test_video_api.py --provider kling --api-key $(API_KEY) --secret-key $(SECRET_KEY)

test-jimeng:
	python scripts/test_video_api.py --provider jimeng --api-key $(API_KEY)

# Health check — uses container-internal networking via docker exec
health:
	@echo "=== Content Planner ===" && docker compose exec -T content-planner wget -qO- http://localhost:8000/health 2>/dev/null || echo "  DOWN"
	@echo "=== Video Mutator ===" && docker compose exec -T video-mutator wget -qO- http://localhost:8000/health 2>/dev/null || echo "  DOWN"
	@echo "=== Content Router ===" && docker compose exec -T content-router wget -qO- http://localhost:8000/health 2>/dev/null || echo "  DOWN"
	@echo "=== Publisher ===" && docker compose exec -T publisher wget -qO- http://localhost:8000/health 2>/dev/null || echo "  DOWN"

# View publishing stats (via content-router internal)
stats:
	@docker compose exec -T content-router wget -qO- http://localhost:8000/stats 2>/dev/null | python3 -m json.tool || echo "content-router not running"

# View accounts
accounts:
	@docker compose exec -T content-router wget -qO- http://localhost:8000/accounts 2>/dev/null | python3 -m json.tool || echo "content-router not running"

# Database shell (port 5434 on host, mapped to 127.0.0.1)
db-shell:
	docker compose exec postgres psql -U matrix -d ai_video_matrix

# Show Traefik domain routes
domains:
	@echo "=== AI Video Matrix — Domain Routes ==="
	@echo "  n8n Workflow:    http://vm-n8n.dev.local"
	@echo "  MoneyPrinter:    http://vm-mpt.dev.local"
	@echo "  MinIO Console:   http://vm-minio.dev.local"
	@echo "  Grafana:         http://vm-grafana.dev.local"
	@echo "  RabbitMQ Mgmt:   http://vm-rabbitmq.dev.local"
	@echo ""
	@echo "=== Mac /etc/hosts ==="
	@echo "  $(HOST_IP) vm-n8n.dev.local vm-mpt.dev.local vm-minio.dev.local vm-grafana.dev.local vm-rabbitmq.dev.local"

# ── Test Harness ──────────────────────────────────────────────

test-harness-up:
	docker compose -f docker-compose.yml -f docker-compose.test.yml up -d

test-harness-down:
	docker compose -f docker-compose.yml -f docker-compose.test.yml down

test-harness-run:
	docker compose -f docker-compose.yml -f docker-compose.test.yml up -d
	@echo "Waiting for services..." && sleep 15
	python3 tests/e2e/run_all.py
	docker compose -f docker-compose.yml -f docker-compose.test.yml down

# Clean all data (DESTRUCTIVE)
clean:
	docker compose down -v
	rm -rf storage/minio/data storage/postgres/data
