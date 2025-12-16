package com.example

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._

/**
 * Spark WordCount Job (Scala)
 *
 * 텍스트 파일 또는 입력 텍스트에서 단어별 빈도수를 계산하는 Spark Job
 *
 * [실행 방법]
 *   # 로컬 모드 - 샘플 텍스트로 실행
 *   spark-submit --class com.example.WordCount \
 *     --master local[*] \
 *     target/scala-2.12/spark-wordcount-assembly-1.0.0.jar
 *
 *   # 파일 입력으로 실행
 *   spark-submit --class com.example.WordCount \
 *     --master local[*] \
 *     target/scala-2.12/spark-wordcount-assembly-1.0.0.jar \
 *     /path/to/input.txt
 *
 *   # 클러스터 모드
 *   spark-submit --class com.example.WordCount \
 *     --master spark://localhost:7077 \
 *     target/scala-2.12/spark-wordcount-assembly-1.0.0.jar \
 *     hdfs://path/to/input.txt
 */
object WordCount {

  def main(args: Array[String]): Unit = {
    // SparkSession 생성
    val spark = SparkSession.builder()
      .appName("Scala WordCount")
      .getOrCreate()

    import spark.implicits._

    // 로그 레벨 설정
    spark.sparkContext.setLogLevel("WARN")

    println("=" * 60)
    println("Starting Scala WordCount Job")
    println("=" * 60)

    try {
      // 샘플 텍스트 데이터
      val sampleText = Seq(
        "Hello World Hello Spark",
        "Apache Spark is a fast and general engine",
        "Spark SQL provides a programming interface",
        "Hello Spark Hello World",
        "Scala is a powerful language for Spark",
        "Big Data processing with Apache Spark",
        "Machine Learning with Spark MLlib",
        "Spark Streaming for real-time processing"
      )
      val lines = spark.createDataset(sampleText)

      // 전체 라인 수 출력
      val lineCount = lines.count()
      println(s"\nTotal lines: $lineCount")

      // WordCount 수행
      // 1. 각 라인을 단어로 분리 (공백 기준)
      // 2. 소문자로 변환
      // 3. 단어별 그룹핑 및 카운트
      // 4. 빈도수 기준 내림차순 정렬
      val wordCounts = lines
        .flatMap(line => line.toLowerCase.split("\\s+"))  // 단어 분리
        .filter(word => word.nonEmpty)                     // 빈 문자열 제거
        .groupBy("value")                                  // 단어별 그룹핑
        .count()                                           // 카운트
        .withColumnRenamed("value", "word")               // 컬럼명 변경
        .orderBy(desc("count"))                           // 빈도수 내림차순 정렬

      // 결과 출력
      println("\n" + "=" * 60)
      println("WordCount Results (Top 20)")
      println("=" * 60)
      wordCounts.show(20, truncate = false)

      // 통계 정보
      val totalWords = wordCounts.agg(sum("count")).first().getLong(0)
      val uniqueWords = wordCounts.count()

      println(s"\nStatistics:")
      println(s"  - Total words: $totalWords")
      println(s"  - Unique words: $uniqueWords")

      println("\n" + "=" * 60)
      println("WordCount Job completed successfully!")
      println("=" * 60)

    } catch {
      case e: Exception =>
        println(s"Error: ${e.getMessage}")
        e.printStackTrace()
        throw e
    } finally {
      spark.stop()
    }
  }
}