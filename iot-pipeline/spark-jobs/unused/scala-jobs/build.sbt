name := "spark-wordcount"
version := "1.0.0"
scalaVersion := "2.12.18"

// Spark 3.5.3 의존성
val sparkVersion = "3.5.3"

libraryDependencies ++= Seq(
  "org.apache.spark" %% "spark-core" % sparkVersion % "provided",
  "org.apache.spark" %% "spark-sql" % sparkVersion % "provided"
)

// JAR 패키징 설정
assembly / assemblyMergeStrategy := {
  case PathList("META-INF", xs @ _*) => MergeStrategy.discard
  case x => MergeStrategy.first
}

// 메인 클래스 설정
Compile / mainClass := Some("com.example.WordCount")