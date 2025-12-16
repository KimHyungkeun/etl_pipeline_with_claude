# Spark WordCount (Scala)

Scala로 작성된 Spark WordCount Job입니다.

## 프로젝트 구조

```
scala-jobs/
├── build.sbt                    # SBT 빌드 설정
├── project/
│   ├── build.properties         # SBT 버전
│   └── plugins.sbt              # SBT 플러그인 (assembly)
└── src/main/scala/com/example/
    └── WordCount.scala          # WordCount 메인 클래스
```

## 빌드

### 사전 요구사항
- JDK 11 이상
- SBT 1.x

### SBT 설치 (Ubuntu/WSL)
```bash
# SDKMAN 사용
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install sbt
```

### JAR 빌드
```bash
cd /home/hkkim/etl-cluster-test/iot-pipeline/spark-jobs/scala-jobs

# 일반 빌드
sbt package

# Fat JAR 빌드 (의존성 포함)
sbt assembly
```

빌드 결과:
- `target/scala-2.12/spark-wordcount_2.12-1.0.0.jar` (일반)
- `target/scala-2.12/spark-wordcount-assembly-1.0.0.jar` (Fat JAR)

## 실행

### 로컬 모드 (샘플 텍스트)
```bash
spark-submit \
  --class com.example.WordCount \
  --master local[*] \
  target/scala-2.12/spark-wordcount-assembly-1.0.0.jar
```

### 파일 입력
```bash
spark-submit \
  --class com.example.WordCount \
  --master local[*] \
  target/scala-2.12/spark-wordcount-assembly-1.0.0.jar \
  /path/to/input.txt
```

### 결과 파일로 저장
```bash
spark-submit \
  --class com.example.WordCount \
  --master local[*] \
  target/scala-2.12/spark-wordcount-assembly-1.0.0.jar \
  /path/to/input.txt \
  /path/to/output
```

### Spark 클러스터 모드
```bash
spark-submit \
  --class com.example.WordCount \
  --master spark://localhost:7077 \
  target/scala-2.12/spark-wordcount-assembly-1.0.0.jar \
  /path/to/input.txt
```

## 출력 예시

```
============================================================
Starting Scala WordCount Job
============================================================
No input file provided. Using sample text.

Total lines: 8

============================================================
WordCount Results (Top 20)
============================================================
+----------+-----+
|word      |count|
+----------+-----+
|spark     |7    |
|hello     |4    |
|a         |3    |
|with      |2    |
|world     |2    |
|apache    |2    |
|for       |2    |
|is        |2    |
|processing|2    |
|...       |...  |
+----------+-----+

Statistics:
  - Total words: 45
  - Unique words: 30

============================================================
WordCount Job completed successfully!
============================================================
```