#!/bin/bash
# IoT Pipeline Teardown Script

set -e

echo "=========================================="
echo "IoT Pipeline Teardown"
echo "=========================================="

cd ${HOME}/etl-cluster-test/etl-cluster

echo "Stopping all containers..."
docker compose -p kafka -f docker-compose-kafka.yaml down
docker compose -p flink -f docker-compose-flink.yaml down
docker compose -p postgresql -f docker-compose-postgresql.yaml down
docker compose -p minio -f docker-compose-minio.yaml down

echo ""
read -p "Delete Docker volumes? (y/N): " delete_volumes

if [[ "$delete_volumes" =~ ^[Yy]$ ]]; then
    echo "Deleting volumes..."
    docker volume rm kafka-data-1 2>/dev/null || true
    docker volume rm kafka-secrets-1 2>/dev/null || true
    docker volume rm kafka-config-1 2>/dev/null || true
    docker volume rm postgresql-data 2>/dev/null || true
    echo "Volumes deleted"
fi

echo ""
echo "Teardown complete!"