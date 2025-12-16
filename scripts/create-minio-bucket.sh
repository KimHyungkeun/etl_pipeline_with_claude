#!/bin/bash
# Create MinIO bucket for Iceberg warehouse

echo "Configuring MinIO client..."

# Using MinIO client inside container
docker exec minio mc alias set local http://localhost:9000 minioadmin minioadmin123

echo "Creating warehouse bucket..."
docker exec minio mc mb local/warehouse --ignore-existing

echo "Listing buckets:"
docker exec minio mc ls local