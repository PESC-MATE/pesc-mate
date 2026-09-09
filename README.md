# pesc-mate

AI 기반 온라인 PECS 의사소통 플랫폼입니다.

## 프로젝트 구조


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
