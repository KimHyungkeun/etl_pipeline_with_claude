#!/bin/bash

# 1. JobID를 스크립트의 첫 번째 인자로 받습니다.
JOB_ID="$1"

# 2. 필수 인자 검사
# $# 변수는 스크립트에 전달된 인자의 총 개수를 나타냅니다.
if [ -z "$JOB_ID" ]; then
    echo "❌ 오류: Flink Job ID를 입력해야 합니다."
    echo "사용법: $0 <JobID>"
    echo "예시: $0 a4f7b3c90e1d2f4a"
    exit 1 # 오류 코드로 스크립트를 종료합니다.
fi

# 3. Job 취소 명령어 실행
echo "Cancelling Flink Job ID: $JOB_ID ..."

# Docker 환경에서 JobManager 컨테이너로 명령을 전달합니다.
docker exec -itd flink-jobmanager flink cancel "$JOB_ID"

# 4. 결과 확인 (선택 사항)
if [ $? -eq 0 ]; then
    echo "✅ Job $JOB_ID 취소 요청이 성공적으로 전송되었습니다."
else
    echo "⚠️ Job $JOB_ID 취소 요청에 실패했거나 Flink 클러스터에 문제가 있습니다."
fi
