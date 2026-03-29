#!/bin/bash
# AI Video Matrix — Initial Setup Script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== AI Video Matrix Setup ==="

# 1. Create .env if not exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "Created .env from template — EDIT IT before starting services"
    echo "  vi $PROJECT_DIR/.env"
    exit 1
fi

# 2. Create data directories
mkdir -p "$PROJECT_DIR/storage/minio/data"
mkdir -p "$PROJECT_DIR/storage/postgres/data"

# 3. Start infrastructure services first
echo "Starting infrastructure (postgres, redis, rabbitmq, minio)..."
cd "$PROJECT_DIR"
docker compose up -d postgres redis rabbitmq minio
echo "Waiting for services to be healthy..."
sleep 10

# 4. Verify PostgreSQL
echo "Checking PostgreSQL..."
docker compose exec postgres pg_isready -U matrix || {
    echo "PostgreSQL not ready, waiting 10s more..."
    sleep 10
    docker compose exec postgres pg_isready -U matrix
}

# 5. Create MinIO bucket
echo "Creating MinIO bucket..."
docker compose exec minio mc alias set local http://localhost:9000 \
    "$(grep MINIO_ROOT_USER .env | cut -d= -f2)" \
    "$(grep MINIO_ROOT_PASSWORD .env | cut -d= -f2)" 2>/dev/null || true
docker compose exec minio mc mb local/videos --ignore-existing 2>/dev/null || true

# 6. Start orchestration and generation services
echo "Starting n8n, moneyprinter..."
docker compose up -d n8n moneyprinter

# 7. Build and start custom services
echo "Building custom services..."
docker compose build content-planner video-mutator content-router publisher

echo "Starting custom services..."
docker compose up -d content-planner video-mutator content-router publisher

# 8. Start monitoring
echo "Starting Grafana..."
docker compose up -d grafana

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Services:"
echo "  n8n:              http://localhost:5678"
echo "  MoneyPrinterTurbo: http://localhost:8501"
echo "  Content Planner:  http://localhost:8010"
echo "  Video Mutator:    http://localhost:8011"
echo "  Content Router:   http://localhost:8012"
echo "  Publisher:         http://localhost:8013"
echo "  MinIO Console:    http://localhost:9001"
echo "  RabbitMQ:         http://localhost:15672"
echo "  Grafana:          http://localhost:3000"
echo ""
echo "Next steps:"
echo "  1. Open MoneyPrinterTurbo and test video generation"
echo "  2. Create a product: curl -X POST http://localhost:8010/products -H 'Content-Type: application/json' -d '{\"name\":\"智能手表\", \"description\":\"...\"}'"
echo "  3. Register accounts via Content Router API"
echo "  4. Import n8n workflow from n8n-workflows/video-matrix-pipeline.json"
