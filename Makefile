.PHONY: setup start stop logs build test stress-test clean

# ============================================================
# AI Video Matrix — Makefile
# ============================================================

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

# Health check all services
health:
	@echo "Content Planner:" && curl -s http://localhost:8010/health | python -m json.tool
	@echo "Video Mutator:" && curl -s http://localhost:8011/health | python -m json.tool
	@echo "Content Router:" && curl -s http://localhost:8012/health | python -m json.tool
	@echo "Publisher:" && curl -s http://localhost:8013/health | python -m json.tool

# View publishing stats
stats:
	@curl -s http://localhost:8012/stats | python -m json.tool

# View accounts
accounts:
	@curl -s http://localhost:8012/accounts | python -m json.tool

# Database shell
db-shell:
	docker compose exec postgres psql -U matrix -d ai_video_matrix

# Clean all data (DESTRUCTIVE)
clean:
	docker compose down -v
	rm -rf storage/minio/data storage/postgres/data
