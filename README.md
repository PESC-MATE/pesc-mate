# pesc-mate

AI 기반 온라인 PECS 의사소통 플랫폼입니다.

## 프로젝트 구조

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
