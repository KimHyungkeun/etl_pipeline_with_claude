# !/bin/bash

docker compose -f docker-compose-minio.yaml down
docker compose -f docker-compose-postgresql.yaml down
docker compose -f docker-compose-kafka.yaml down
# docker compose -f docker-compose-flink.yaml down
docker compose -f docker-compose-spark.yaml down