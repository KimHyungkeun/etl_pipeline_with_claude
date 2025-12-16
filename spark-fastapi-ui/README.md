# Spark Cluster Manager UI

Spark 클러스터를 모니터링하고 Job을 제출할 수 있는 React 기반 웹 UI입니다.

## 기술 스택

- **React 19** + **TypeScript**
- **Vite** - 빌드 도구
- **Tailwind CSS v4** - 스타일링
- **FSD (Feature-Sliced Design)** - 아키텍처

## 주요 기능

- **클러스터 모니터링**: 클러스터 상태, Worker 목록, Application 목록 조회
- **Job 제출**: PySpark 스크립트 실행 요청
- **자동 갱신**: 5초 간격 폴링 (on/off 가능)
- **수동 새로고침**: Refresh 버튼

## 프로젝트 구조 (FSD Architecture)

```
src/
├── app/
│   └── App.tsx                   # 메인 App 컴포넌트
│
├── features/
│   ├── cluster/ui/
│   │   ├── ClusterStatusCard.tsx # 클러스터 상태 카드
│   │   ├── WorkerList.tsx        # Worker 목록
│   │   └── AppList.tsx           # Application 목록
│   │
│   └── job-submit/ui/
│       └── JobSubmitForm.tsx     # Job 제출 폼
│
├── shared/
│   ├── api/
│   │   └── spark.ts              # Spark REST API 클라이언트
│   │
│   ├── lib/
│   │   ├── usePolling.ts         # 폴링 커스텀 훅
│   │   └── format.ts             # 포맷팅 유틸리티
│   │
│   └── types/
│       └── types.ts              # TypeScript 타입 정의
│
├── main.tsx                      # React 진입점
└── index.css                     # 글로벌 스타일 (Tailwind)
```

### FSD 레이어 설명

| 레이어 | 역할 | 의존성 규칙 |
|--------|------|-------------|
| `app` | 앱 초기화, 라우팅, 전역 상태 | features, shared 사용 가능 |
| `features` | 비즈니스 기능 단위 모듈 | shared만 사용 가능, 다른 feature 참조 불가 |
| `shared` | 공통 유틸, API, 타입 | 외부 라이브러리만 사용 |

### Path Alias

`@/` 경로를 사용하여 src 폴더를 참조합니다:

```typescript
import { ClusterStatusCard } from '@/features/cluster/ui/ClusterStatusCard';
import { usePolling } from '@/shared/lib/usePolling';
import type { ClusterStatus } from '@/shared/types/types';
```

## 시작하기

### 설치

```bash
npm install
```

### 개발 서버 실행

```bash
npm run dev
```

http://localhost:5173 에서 확인할 수 있습니다.

### 빌드

```bash
npm run build
```

## API 연동

백엔드 서버 (`spark-fastapi`)가 http://localhost:8000 에서 실행 중이어야 합니다.

### 사용되는 API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/cluster/status` | 클러스터 상태 조회 |
| GET | `/api/v1/cluster/workers` | Worker 목록 조회 |
| GET | `/api/v1/jobs/apps` | Application 목록 조회 |
| POST | `/api/v1/jobs/submit` | Job 제출 |
| DELETE | `/api/v1/jobs/apps/{app_id}` | Job 실행 중지 |

---

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
