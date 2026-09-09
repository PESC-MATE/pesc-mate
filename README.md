# pesc-mate

AI 기반 온라인 PECS 의사소통 플랫폼입니다.

## 프로젝트 구조

## 실행 가능한 프로토타입

카테고리별 PECS 그림 카드 18종, 검색, 최대 12장 선택·삭제·순서 변경,
규칙 기반 한국어 문장 생성, 브라우저 TTS, 사용 빈도 추천과 전체 기간
이용 대시보드와 최근 7일·30일·전체 기간 필터를 제공합니다. 추천 이유를 카드에 표시하며 문장 만들기 시 MongoDB에 기록을 저장합니다.
같은 보드의 재시도는 중복 집계하지 않으며 보드를 변경하면 새 기록이 됩니다.

MongoDB 사용자 로그인, 사용자·보호자 역할 분리와 연결된 사용자의 보호자 대시보드를 지원합니다.
회원가입, 카드 업로드, TTS 성공 기록은 아직 구현하지 않았습니다.
한국어 음성 재생은 브라우저·운영체제의 한국어 TTS 지원이 필요합니다.
Qwen 모델 기능은 현재 꺼져 있으며 외부 AI API를 호출하지 않습니다.
외부 API 키나 유료 가입은 필요하지 않습니다.

사용자 데모 로그인은 `demo` / `demo1234`, 보호자 데모 로그인은
`caregiver` / `caregiver1234`입니다. 최초 로그인 시 기간 필터와 통계를 바로 시연할 수 있는
샘플 기록 4건이 생성됩니다. 운영 환경에서는
`DEMO_USERNAME`과 `DEMO_PASSWORD`를 변경하고 별도의 회원 관리 정책을 적용해야 합니다.

기록은 MongoDB의 `pesc_mate.communication_sessions` 컬렉션에 저장됩니다.
Docker 실행 시 데이터는 `mongodb_data` 볼륨에 유지됩니다. 개별 실행에서는
`MONGODB_URI`와 `MONGODB_DATABASE` 환경 변수로 연결 정보를 설정합니다.

간단한 시연: `나 → 물 → 마시다` 선택 → `문장 만들기 · 저장` →
`읽어주기` → `이용 현황`에서 저장 결과 확인.

백엔드 테스트: `cd backend` 후 `python -m unittest test_communication -v`.
프런트엔드 검증: `cd frontend` 후 `npm run build`.

### 소스 구성

### MongoDB 실행

Docker Compose는 MongoDB를 함께 실행하므로 별도 설치가 필요하지 않습니다.
개별 실행에서는 MongoDB를 먼저 시작해야 하며 기본 연결 주소는
`mongodb://127.0.0.1:27017`, 기본 데이터베이스 이름은 `pesc_mate`입니다.

VS Code MongoDB 확장에서는 다음 연결 문자열을 사용합니다.

```text
mongodb://127.0.0.1:27018/pesc_mate
```

MongoDB 포트는 로컬 PC에서만 접근할 수 있도록 `127.0.0.1`에 바인딩됩니다.
백엔드는 프로세스당 하나의 MongoDB 연결 풀을 재사용하며 컨테이너 헬스체크는
30초 간격으로 실행하여 개발 로그의 반복 출력을 줄입니다.
MongoDB 컨테이너의 내부 로그와 Uvicorn 접근 로그는 숨기고, 백엔드 터미널에는
문서 내용과 인증 정보를 제외한 `DB CRUD | 작업 | 컬렉션` 형식의 로그만 출력합니다.

- `frontend`: React와 Vite 기반 웹 클라이언트
- `backend`: FastAPI 기반 API 서버
- `ai`: 카드 추천 및 문장 생성 기능
- `docs`: 기획, API, 회의 및 개발 문서

## 로컬 실행

### Docker Compose로 한 번에 실행

Docker Desktop을 실행한 뒤 프로젝트 루트에서 다음 명령을 사용합니다.

```bash
docker compose up --build
```

- 웹 화면: `http://127.0.0.1:5173`
- API 문서: `http://127.0.0.1:8000/docs`
- 상태 확인: `http://127.0.0.1:8000/api/health`

컨테이너를 종료하려면 다음 명령을 사용합니다.

```bash
docker compose down
```

소스 디렉터리가 컨테이너에 연결되어 있어 코드 변경 시 자동으로
새로고침됩니다.

### 개별 실행

#### 백엔드

```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API 문서는 `http://127.0.0.1:8000/docs`에서 확인할 수 있습니다.

#### 프런트엔드

```bash
cd frontend
npm install
npm run dev
```

웹 화면은 `http://127.0.0.1:5173`에서 확인할 수 있습니다.

## 개발 문서

- [커밋 메시지 규칙](docs/COMMIT_CONVENTION.md)
- [API 명세서](docs/API_SPECIFICATION.md)
