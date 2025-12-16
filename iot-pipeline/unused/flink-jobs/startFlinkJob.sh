#!/bin/bash

docker exec -itd flink-jobmanager flink run /opt/flink/flink-anomaly-detection-1.0.0.jar
