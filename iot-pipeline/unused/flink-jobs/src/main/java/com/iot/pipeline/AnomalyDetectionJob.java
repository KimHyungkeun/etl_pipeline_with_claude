package com.iot.pipeline;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.FilterFunction;
import org.apache.flink.api.common.functions.MapFunction;
import org.apache.flink.api.common.serialization.SimpleStringEncoder;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.configuration.Configuration;
import org.apache.flink.connector.file.sink.FileSink;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.core.fs.Path;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.functions.sink.filesystem.rollingpolicies.DefaultRollingPolicy;
import org.apache.flink.streaming.api.functions.sink.filesystem.bucketassigners.DateTimeBucketAssigner;
import org.apache.flink.streaming.api.functions.sink.filesystem.OutputFileConfig;
import org.apache.flink.configuration.MemorySize;

import com.iot.pipeline.dto.AlertEvent;
import com.iot.pipeline.dto.SensorReading;

import java.time.Duration;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public class AnomalyDetectionJob {

    // Threshold configuration
    private static final Map<String, double[]> THRESHOLDS = new HashMap<>();
    static {
        // {normalMin, normalMax}
        THRESHOLDS.put("temperature", new double[]{20.0, 30.0});
        THRESHOLDS.put("humidity", new double[]{40.0, 70.0});
        THRESHOLDS.put("pressure", new double[]{1000.0, 1020.0});
    }

    // MinIO Configuration
    private static final String MINIO_ENDPOINT = "http://minio:9000";
    private static final String MINIO_ACCESS_KEY = "minioadmin";
    private static final String MINIO_SECRET_KEY = "minioadmin123";
    private static final String ALERT_OUTPUT_PATH = "s3a://flinkalert/alert";

    public static void main(String[] args) throws Exception {
        // Hadoop S3A 설정
        Configuration conf = new Configuration();
        conf.setString("fs.s3a.endpoint", MINIO_ENDPOINT);
        conf.setString("fs.s3a.access.key", MINIO_ACCESS_KEY);
        conf.setString("fs.s3a.secret.key", MINIO_SECRET_KEY);
        conf.setString("fs.s3a.path.style.access", "true");
        conf.setString("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem");

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment(conf);
        env.setParallelism(2);
        env.enableCheckpointing(60000); // 1분마다 체크포인트 (파일 커밋에 필요)

        // Kafka Source
        KafkaSource<String> kafkaSource = KafkaSource.<String>builder()
                .setBootstrapServers("kafka-broker-1:29092")
                .setTopics("sensor-raw")
                .setGroupId("flink-anomaly-detection")
                .setStartingOffsets(OffsetsInitializer.latest())
                .setValueOnlyDeserializer(new SimpleStringSchema())
                .build();

        // Read from Kafka
        DataStream<String> rawStream = env.fromSource(
                kafkaSource,
                WatermarkStrategy.noWatermarks(),
                "Kafka Source"
        );

        // Parse JSON to SensorReading
        DataStream<SensorReading> sensorStream = rawStream
                .map(new JsonToSensorReading())
                .name("Parse JSON");

        // Detect anomalies
        DataStream<AlertEvent> alertStream = sensorStream
                .filter(new AnomalyFilter())
                .map(new CreateAlert())
                .name("Anomaly Detection");

        // Alert를 JSON 문자열로 변환
        DataStream<String> alertJsonStream = alertStream
                .map(new AlertToJson())
                .name("Convert to JSON");

        // MinIO에 파일로 저장 (날짜별 폴더 + .json 확장자)
        FileSink<String> sink = FileSink
                .forRowFormat(new Path(ALERT_OUTPUT_PATH), new SimpleStringEncoder<String>("UTF-8"))
                .withBucketAssigner(new DateTimeBucketAssigner<>("yyyy-MM-dd"))  // 2025-12-09 형식 폴더
                .withRollingPolicy(
                        DefaultRollingPolicy.builder()
                                .withRolloverInterval(Duration.ofMinutes(5))  // 5분마다 새 파일
                                .withInactivityInterval(Duration.ofMinutes(2)) // 2분 비활성 시 롤오버
                                .withMaxPartSize(MemorySize.ofMebiBytes(1))  // 1MB
                                .build()
                )
                .withOutputFileConfig(
                        OutputFileConfig.builder()
                                .withPartPrefix("alert")
                                .withPartSuffix(".json")
                                .build()
                )
                .build();

        alertJsonStream.sinkTo(sink).name("MinIO Sink");

        // 콘솔에도 출력 (디버깅용)
        alertStream.print("ALERT");

        env.execute("IoT Anomaly Detection");
    }

    // AlertEvent를 JSON 문자열로 변환
    public static class AlertToJson implements MapFunction<AlertEvent, String> {
        private transient ObjectMapper mapper;

        @Override
        public String map(AlertEvent alert) throws Exception {
            if (mapper == null) {
                mapper = new ObjectMapper();
            }
            return mapper.writeValueAsString(alert);
        }
    }

    public static class JsonToSensorReading implements MapFunction<String, SensorReading> {
        private transient ObjectMapper mapper;

        @Override
        public SensorReading map(String json) throws Exception {
            if (mapper == null) {
                mapper = new ObjectMapper();
            }
            JsonNode node = mapper.readTree(json);

            SensorReading reading = new SensorReading();
            reading.setSensorId(node.get("sensor_id").asText());
            reading.setSensorType(node.get("sensor_type").asText());
            reading.setLocation(node.get("location").asText());
            reading.setValue(node.get("value").asDouble());
            reading.setUnit(node.get("unit").asText());
            reading.setTimestamp(node.get("timestamp").asText());

            return reading;
        }
    }

    public static class AnomalyFilter implements FilterFunction<SensorReading> {
        @Override
        public boolean filter(SensorReading reading) {
            double[] threshold = THRESHOLDS.get(reading.getSensorType());
            if (threshold == null) return false;

            double value = reading.getValue();
            return value < threshold[0] || value > threshold[1];
        }
    }

    public static class CreateAlert implements MapFunction<SensorReading, AlertEvent> {
        @Override
        public AlertEvent map(SensorReading reading) {
            double[] threshold = THRESHOLDS.get(reading.getSensorType());

            AlertEvent alert = new AlertEvent();
            alert.setAlertId(UUID.randomUUID().toString());
            alert.setSensorId(reading.getSensorId());
            alert.setSensorType(reading.getSensorType());
            alert.setLocation(reading.getLocation());
            alert.setValue(reading.getValue());
            alert.setUnit(reading.getUnit());
            alert.setTimestamp(reading.getTimestamp());
            alert.setDetectedAt(Instant.now().toString());

            if (reading.getValue() < threshold[0]) {
                alert.setAlertType("LOW");
                alert.setThreshold(threshold[0]);
            } else {
                alert.setAlertType("HIGH");
                alert.setThreshold(threshold[1]);
            }

            return alert;
        }
    }
}