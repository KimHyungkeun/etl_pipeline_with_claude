import json
import random
import time
from datetime import datetime, timezone
from kafka import KafkaProducer

KAFKA_BOOTSTRAP_SERVERS = ["localhost:9092"]
TOPIC = "sensor-raw"

SENSORS = [
    {"sensor_id": "TEMP-001", "type": "temperature", "location": "factory-A", "unit": "celsius"},
    {"sensor_id": "TEMP-002", "type": "temperature", "location": "factory-B", "unit": "celsius"},
    {"sensor_id": "HUMID-001", "type": "humidity", "location": "factory-A", "unit": "percent"},
    {"sensor_id": "HUMID-002", "type": "humidity", "location": "factory-B", "unit": "percent"},
    {"sensor_id": "PRESS-001", "type": "pressure", "location": "factory-A", "unit": "hPa"},
]

THRESHOLDS = {
    "temperature": {"min": 15.0, "max": 35.0, "normal_min": 20.0, "normal_max": 30.0},
    "humidity": {"min": 20.0, "max": 90.0, "normal_min": 40.0, "normal_max": 70.0},
    "pressure": {"min": 990.0, "max": 1030.0, "normal_min": 1000.0, "normal_max": 1020.0},
}


def generate_sensor_reading(sensor: dict) -> dict:
    sensor_type = sensor["type"]
    threshold = THRESHOLDS[sensor_type]

    # 90% 확률로 정상 범위, 10% 확률로 이상치
    if random.random() < 0.9:
        value = random.uniform(threshold["normal_min"], threshold["normal_max"])
    else:
        # 이상치: 정상 범위 밖
        if random.random() < 0.5:
            value = random.uniform(threshold["min"], threshold["normal_min"])
        else:
            value = random.uniform(threshold["normal_max"], threshold["max"])

    return {
        "sensor_id": sensor["sensor_id"],
        "sensor_type": sensor_type,
        "location": sensor["location"],
        "value": round(value, 2),
        "unit": sensor["unit"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )

    print(f"Starting sensor data generation to topic: {TOPIC}")
    print(f"Kafka servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print("-" * 50)

    message_count = 0
    try:
        while True:
            sensor = random.choice(SENSORS)
            reading = generate_sensor_reading(sensor)

            producer.send(
                TOPIC,
                key=reading["sensor_id"],
                value=reading,
            )

            message_count += 1
            print(f"[{message_count}] {reading['sensor_id']}: {reading['value']} {reading['unit']}")

            time.sleep(0.5)  # 0.5초마다 데이터 생성

    except KeyboardInterrupt:
        print(f"\nStopped. Total messages sent: {message_count}")
    finally:
        producer.close()


if __name__ == "__main__":
    main()
