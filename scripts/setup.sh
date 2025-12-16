#!/bin/bash
# IoT Pipeline Setup Script

set -e

echo "=========================================="
echo "IoT Pipeline Setup"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Create Docker network
echo -e "${YELLOW}[1/5] Creating Docker network...${NC}"
docker network create etl-network 2>/dev/null || echo "Network 'etl-network' already exists"

# 2. Create Docker volumes
echo -e "${YELLOW}[2/5] Creating Docker volumes...${NC}"
volumes=(
    "kafka-data-1" 
    "kafka-secrets-1" 
    "kafka-config-1" 
    "postgresql-data"
    "pgadmin-data"
)

for vol in "${volumes[@]}"; do
    docker volume create "$vol" 2>/dev/null || echo "Volume '$vol' already exists"
done

# 3. Create MinIO data directory
echo -e "${YELLOW}[3/5] Creating MinIO data directory...${NC}"
mkdir -p ${HOME}/etl-cluster-test/etl-cluster/minio-data
chmod 755 ${HOME}/etl-cluster-test/etl-cluster/minio-data

# 4. Start all services
echo -e "${YELLOW}[4/5] Starting Docker containers...${NC}"
cd ${HOME}/etl-cluster-test/etl-cluster

docker compose -p kafka -f docker-compose-kafka.yaml up -d
docker compose -p flink -f docker-compose-flink.yaml up -d
docker compose -p postgresql -f docker-compose-postgresql.yaml up -d
docker compose -p minio -f docker-compose-minio.yaml up -d

# 5. PostgreSQL 초기화 대기 및 스크립트 실행
echo ""
echo -e "${YELLOW}[5/5] Initializing PostgreSQL...${NC}"
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# PostgreSQL 초기화 스크립트 실행
INIT_SQL_PATH="${HOME}/etl-cluster-test/iot-pipeline/config/init-postgresql.sql"

if [ -f "$INIT_SQL_PATH" ]; then
    echo "Running PostgreSQL initialization script..."
    docker exec -i postgresql psql -U etl_user -d etl_db < "$INIT_SQL_PATH"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}PostgreSQL initialization completed successfully${NC}"
    else
        echo -e "\033[0;31mWarning: PostgreSQL initialization failed${NC}"
    fi
else
    echo -e "\033[0;31mWarning: init-postgresql.sql not found at $INIT_SQL_PATH${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Services:"
echo "  - Kafka:      localhost:9092"
echo "  - Flink UI:   http://localhost:8083"
echo "  - PostgreSQL: localhost:5432"
echo "  - pgAdmin:    http://localhost:5050 (admin@admin.com / admin)"
echo "  - MinIO API:  http://localhost:9000"
echo "  - MinIO UI:   http://localhost:9001 (minioadmin / minioadmin123)"
echo ""
echo "Next steps:"
echo "  1. Create Kafka topic: cd ${HOME}/etl-cluster-test && ./scripts/create-kafka-topic.sh"
echo "  2. Create MinIO bucket: cd ${HOME}/etl-cluster-test && ./scripts/create-minio-bucket.sh"
echo "  3. Run sensor generator: cd ${HOME}/etl-cluster-test/iot-pipeline/generator && poetry install && poetry run python sensor_producer.py"
echo -e "${NC}"