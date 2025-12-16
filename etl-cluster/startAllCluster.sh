# !/bin/bash

docker compose -f docker-compose-minio.yaml up -d
docker compose -f docker-compose-postgresql.yaml up -d
docker compose -f docker-compose-kafka.yaml up -d
# docker compose -f docker-compose-flink.yaml up -d
docker compose -f docker-compose-spark.yaml up -d