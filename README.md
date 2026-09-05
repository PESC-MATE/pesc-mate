# pesc-mate

AI 기반 온라인 PECS 의사소통 플랫폼입니다.

## 프로젝트 구조

- `frontend`: React와 Vite 기반 웹 클라이언트
- `backend`: FastAPI 기반 API 서버
- `ai`: 카드 추천 및 문장 생성 기능
- `docs`: 기획, API, 회의 및 개발 문서

## 로컬 실행

### 백엔드

```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API 문서는 `http://localhost:8000/docs`에서 확인할 수 있습니다.

### 프런트엔드

```bash
cd frontend
npm install
npm run dev
```

웹 화면은 `http://localhost:5173`에서 확인할 수 있습니다.

## 개발 문서

- [커밋 메시지 규칙](docs/COMMIT_CONVENTION.md)
