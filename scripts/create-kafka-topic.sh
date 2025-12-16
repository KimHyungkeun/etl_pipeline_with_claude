#!/bin/bash
# Create Kafka topics for IoT Pipeline

echo "Creating Kafka topics..."

docker exec kafka-broker-1 /opt/kafka/bin/kafka-topics.sh \
    --create \
    --topic sensor-raw \
    --partitions 3 \
    --replication-factor 3 \
    --bootstrap-server localhost:29092 \
    2>/dev/null || echo "Topic 'sensor-raw' already exists"

echo ""
echo "Listing topics:"
docker exec kafka-broker-1 /opt/kafka/bin/kafka-topics.sh \
    --list \
    --bootstrap-server localhost:29092