---
title: "PESC MATE API 명세서"
date: "2026년 9월 9일"
lang: ko-KR
---

# 1. 개요

| 항목 | 내용 |
|---|---|
| API 이름 | PESC MATE API |
| 버전 | 0.1.0 |
| 개발 기본 URL | `http://127.0.0.1:8000` |
| API 기본 경로 | `/api` |
| 데이터 형식 | JSON |
| 문자 인코딩 | UTF-8 |
| 인증 방식 | Bearer 세션 토큰 |
| API 자동 문서 | `/docs` |
| OpenAPI JSON | `/openapi.json` |

본 명세서는 현재 구현된 API를 기준으로 한다. Qwen 모델 기능은 비활성화되어 있으며 문장은 서버의 규칙으로 생성된다.

# 2. 공통 규칙

## 2.1 요청 헤더

JSON 본문을 전송하는 요청은 다음 헤더를 사용한다.

```http
Content-Type: application/json
```

인증이 필요한 API는 로그인 응답으로 받은 토큰을 전송한다.

```http
Authorization: Bearer {access_token}
```

토큰은 로그인 시 생성되며 기본 12시간 동안 유효하다. 로그아웃하면 해당 토큰이 즉시 삭제된다.

## 2.2 날짜와 시간

날짜와 시간은 ISO 8601 문자열로 반환한다. 서버 저장 기준은 UTC이며 `Z` 또는 `+00:00` 시간대가 포함될 수 있다.

```text
2026-09-09T01:30:00.000000+00:00
```

## 2.3 공통 오류 응답

```json
{
  "detail": "오류 설명"
}
```

| HTTP 상태 | 의미 |
|---|---|
| 401 Unauthorized | 토큰이 없거나 유효하지 않음, 로그인 실패 또는 세션 만료 |
| 403 Forbidden | 계정 역할에 허용되지 않은 기능 또는 연결되지 않은 사용자 기록 접근 |
| 404 Not Found | 보호자 계정에 연결된 사용자가 없음 |
| 409 Conflict | 같은 요청 ID가 다른 카드 조합에 사용됨 |
| 422 Unprocessable Entity | 요청 형식, 길이, UUID 또는 조회 기간이 유효하지 않음 |
| 502 Bad Gateway | 현재 미사용. 향후 외부 AI 응답 오류에 사용 가능 |
| 503 Service Unavailable | MongoDB 연결 또는 저장 실패 |

# 3. API 목록

| 구분 | 메서드 | 경로 | 인증 | 설명 |
|---|---|---|---|---|
| 시스템 | GET | `/` | 불필요 | API 기본 응답 |
| 시스템 | GET | `/api/health` | 불필요 | 서버 상태 확인 |
| 인증 | POST | `/api/auth/login` | 불필요 | 로그인 및 세션 생성 |
| 인증 | POST | `/api/auth/register` | 불필요 | 일반 사용자 가입 및 로그인 |
| 인증 | GET | `/api/auth/me` | 필요 | 현재 사용자 조회 |
| 인증 | POST | `/api/auth/logout` | 필요 | 전달된 토큰의 세션 삭제 |
| 보호자 | GET | `/api/care/linked-users` | 필요 | 보호자에게 연결된 사용자 조회 |
| 카드 | GET | `/api/cards` | 필요 | 전체 카드 조회 |
| 문장 | POST | `/api/sentences` | 필요 | 문장 생성 및 기록 저장 |
| 추천 | GET | `/api/recommendations` | 필요 | 사용자별 추천 카드 조회 |
| 통계 | GET | `/api/dashboard` | 필요 | 본인 또는 연결 사용자 이용 통계 조회 |

# 4. 데이터 모델

## 4.1 User

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `id` | string | 예 | 사용자 식별자 |
| `username` | string | 예 | 로그인 아이디 |
| `name` | string | 예 | 화면 표시 이름 |
| `role` | string | 예 | 사용자 역할. `user` 또는 `caregiver` |

```json
{
  "id": "demo",
  "username": "demo",
  "name": "데모 사용자",
  "role": "user"
}
```

## 4.2 Card

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `id` | string | 예 | 카드 식별자 |
| `label` | string | 예 | 한글 카드 이름 |
| `symbol` | string | 예 | 카드 그림 기호 |
| `category` | string | 예 | `사람`, `음식`, `행동`, `장소`, `감정` 중 하나 |
| `image_index` | integer | 예 | 카드 이미지 스프라이트 위치 인덱스(0~17) |
| `count` | integer | 아니요 | 추천·통계 응답의 사용자 사용 횟수 |
| `reason` | string | 아니요 | 추천 응답에 표시할 추천 근거 |

```json
{
  "id": "water",
  "label": "물",
  "symbol": "💧",
  "category": "음식",
  "image_index": 2,
  "count": 3
}
```

## 4.3 CommunicationSession

| 필드 | 형식 | 필수 | 설명 |
|---|---|---|---|
| `id` | UUID string | 예 | 요청 및 의사소통 기록 식별자 |
| `user_id` | string | 예 | 기록 소유 사용자 ID |
| `cards` | string array | 예 | 선택 순서가 보존된 카드 ID 목록 |
| `sentence` | string | 예 | 생성된 한국어 문장 |
| `created_at` | ISO 8601 string | 예 | 생성 시각 |

```json
{
  "id": "56d46f5e-824e-48cc-968f-9ed97dfcddab",
  "user_id": "demo",
  "cards": ["me", "water", "drink"],
  "sentence": "저는 물을 마시고 싶어요.",
  "created_at": "2026-09-09T01:30:00.000000+00:00"
}
```

# 5. 시스템 API

## 5.1 API 기본 응답

```http
GET /
```

인증은 필요하지 않다.

### 성공 응답: 200 OK

```json
{
  "message": "PESC MATE API"
}
```

## 5.2 상태 확인

```http
GET /api/health
```

백엔드 프로세스가 HTTP 요청을 처리할 수 있는지 확인한다. 인증은 필요하지 않다. 현재 응답은 MongoDB 연결 상태까지 검사하지 않는다.

### 성공 응답: 200 OK

```json
{
  "status": "ok"
}
```

# 6. 인증 API

## 6.1 로그인

```http
POST /api/auth/login
```

아이디와 비밀번호를 검증하고 불투명 세션 토큰을 생성한다. 기본 데모 계정은 실행 환경 변수로 구성된다.

### 요청 본문

| 필드 | 형식 | 제약 | 설명 |
|---|---|---|---|
| `username` | string | 1~64자 | 로그인 아이디. 앞뒤 공백은 제거됨 |
| `password` | string | 1~128자 | 로그인 비밀번호 |

```json
{
  "username": "demo",
  "password": "demo1234"
}
```

### 성공 응답: 200 OK

| 필드 | 형식 | 설명 |
|---|---|---|
| `access_token` | string | 이후 요청에 사용할 Bearer 토큰 |
| `token_type` | string | `bearer` |
| `expires_at` | ISO 8601 string | 세션 만료 시각 |
| `user` | User | 로그인 사용자 |

```json
{
  "access_token": "발급된-세션-토큰",
  "token_type": "bearer",
  "expires_at": "2026-09-09T13:30:00.000000+00:00",
  "user": {
    "id": "demo",
    "username": "demo",
    "name": "데모 사용자",
    "role": "user"
  }
}
```

### 오류 응답

- `401`: 아이디 또는 비밀번호가 올바르지 않음
- `422`: 아이디·비밀번호 누락 또는 길이 위반
- `503`: 로그인 저장소 연결 실패

## 6.2 사용자 가입

```http
POST /api/auth/register
Content-Type: application/json
```

영문, 숫자, `_`, `-`로 구성된 4~32자 아이디와 8자 이상 비밀번호,
1~30자 이름으로 일반 사용자 계정을 만든다. 성공하면 로그인과 같은 세션 정보를 반환한다.

### 성공 응답: 201 Created

응답 형식은 `LoginResponse`이다.

### 오류 응답

- `409`: 이미 사용 중인 아이디
- `422`: 입력 형식 또는 길이가 올바르지 않음
- `503`: MongoDB 연결 실패

## 6.3 현재 사용자 조회

```http
GET /api/auth/me
Authorization: Bearer {access_token}
```

### 성공 응답: 200 OK

응답 형식은 `User`이다.

### 오류 응답

- `401`: 토큰 누락, 유효하지 않은 토큰, 세션 만료 또는 사용자 없음
- `503`: 로그인 저장소 연결 실패

## 6.4 로그아웃

```http
POST /api/auth/logout
Authorization: Bearer {access_token}  # 토큰이 있을 때
```

토큰이 전달되면 대응하는 로그인 세션을 삭제한다. 유효한 로그인이 필요하다.

### 성공 응답: 204 No Content

응답 본문은 없다.

### 오류 응답

- `503`: 로그인 저장소 연결 실패

## 6.5 보호 대상 사용자 조회

```http
GET /api/care/linked-users
Authorization: Bearer {access_token}
```

보호자 계정에 연결된 일반 사용자 목록을 `User[]` 형식으로 반환한다. 일반 사용자는 호출할 수 없다.

# 7. 카드 API

## 7.1 카드 목록 조회

```http
GET /api/cards
Authorization: Bearer {access_token}
```

현재 활성화된 기본 카드 18개를 반환한다. 서버에 정의된 순서대로 제공된다.

### 성공 응답: 200 OK

응답 형식은 `Card[]`이다. 카드 목록 응답에는 `count`가 포함되지 않는다.

```json
[
  {
    "id": "me",
    "label": "나",
    "symbol": "🙋",
    "category": "사람"
  },
  {
    "id": "water",
    "label": "물",
    "symbol": "💧",
    "category": "음식"
  }
]
```

### 오류 응답

- `401`: 인증 실패

# 8. 문장 API

## 8.1 문장 생성 및 저장

```http
POST /api/sentences
Authorization: Bearer {access_token}
Content-Type: application/json
```

카드 ID와 순서를 바탕으로 문장을 생성하고 로그인 사용자의 MongoDB 기록으로 저장한다. `request_id`는 클라이언트가 생성하는 UUID이며 네트워크 재시도의 중복 저장을 방지한다.

### 요청 본문

| 필드 | 형식 | 제약 | 설명 |
|---|---|---|---|
| `cards` | string array | 1~12개 | 선택 순서가 보존된 카드 ID |
| `request_id` | UUID string | UUID 형식 | 요청의 멱등 식별자 |

```json
{
  "cards": ["me", "water", "drink"],
  "request_id": "56d46f5e-824e-48cc-968f-9ed97dfcddab"
}
```

### 성공 응답: 200 OK

응답 형식은 `CommunicationSession`이다. 같은 사용자가 동일한 `request_id`와 카드 목록으로 재요청하면 새 기록을 생성하지 않고 기존 응답을 반환한다.

### 문장 생성 규칙

| 카드 순서 | 생성 예시 |
|---|---|
| `me, water, drink` | 저는 물을 마시고 싶어요. |
| `me, rice, eat` | 저는 밥을 먹고 싶어요. |
| `me, toilet, go` | 저는 화장실에 가고 싶어요. |
| 정의되지 않은 조합 | 카드 이름을 ` · `로 연결 |

### 오류 응답

- `401`: 인증 실패
- `409`: 같은 `request_id`가 다른 카드 목록 또는 다른 사용자 기록과 충돌
- `422`: 카드 개수, UUID 형식 또는 카드 ID가 유효하지 않음
- `503`: MongoDB 연결 실패

# 9. 추천 API

## 9.1 추천 카드 조회

```http
GET /api/recommendations
Authorization: Bearer {access_token}
```

로그인 사용자의 전체 기간 카드 사용 횟수를 집계하여 최대 6개를 반환한다. 사용 이력이 부족하면 기본 카드 순서로 채우며 각 카드에 추천 근거인 `reason`을 포함한다.

### 성공 응답: 200 OK

응답 형식은 `Card[]`이다. 사용 이력으로 추천된 카드에는 `count`가 포함되고 기본으로 채운 카드에는 포함되지 않는다.

```json
[
  {
    "id": "water",
    "label": "물",
    "symbol": "💧",
    "category": "음식",
    "count": 3
  },
  {
    "id": "me",
    "label": "나",
    "symbol": "🙋",
    "category": "사람"
  }
]
```

### 오류 응답

- `401`: 인증 실패
- `503`: MongoDB 연결 실패

# 10. 이용 현황 API

## 10.1 사용자 통계 조회

```http
GET /api/dashboard
GET /api/dashboard?days=7
GET /api/dashboard?days=30
GET /api/dashboard?days=30&user_id=demo
Authorization: Bearer {access_token}
```

일반 사용자는 본인의 기록만 집계한다. 보호자는 `user_id`로 연결 사용자의 기록을 조회하며, 생략하면 첫 연결 사용자를 조회한다. `days`가 없으면 전체 기간을 조회한다.

### 쿼리 매개변수

| 이름 | 형식 | 필수 | 기본값 | 제약 | 설명 |
|---|---|---|---|---|---|
| `days` | integer | 아니요 | 없음 | 1~365 | 최근 N일 기록만 조회 |
| `user_id` | string | 아니요 | 본인 또는 첫 연결 사용자 | 최대 64자 | 보호자가 조회할 연결 사용자 ID |

### 성공 응답: 200 OK

| 필드 | 형식 | 설명 |
|---|---|---|
| `sessions` | integer | 선택 기간에 저장된 문장 수 |
| `selections` | integer | 선택 기간에 사용된 전체 카드 수 |
| `top_cards` | Card[] | 사용 횟수 순 카드 목록. `count` 포함 |
| `categories` | object | 카테고리 이름별 사용 횟수 |
| `recent` | CommunicationSession[] | 최신순 기록 최대 10개 |
| `period_days` | integer 또는 null | 적용된 기간. 전체 기간이면 `null` |
| `today_sessions` | integer | 오늘 생성한 문장 수 |
| `today_selections` | integer | 오늘 선택한 카드 수 |
| `primary_emotion` | Card 또는 null | 선택 기간에 가장 많이 사용한 감정 카드 |
| `last_activity` | ISO 8601 또는 null | 가장 최근 의사소통 시각 |
| `daily_activity` | object[] | 최근 7일 날짜별 문장 수 |
| `attention` | Card[] | `아파요`, `도와주세요`, `싫어요` 사용 횟수와 최근 시각 |

```json
{
  "sessions": 2,
  "selections": 6,
  "top_cards": [
    {
      "id": "me",
      "label": "나",
      "symbol": "🙋",
      "category": "사람",
      "count": 2
    }
  ],
  "categories": {
    "사람": 2,
    "음식": 2,
    "행동": 2
  },
  "recent": [
    {
      "id": "56d46f5e-824e-48cc-968f-9ed97dfcddab",
      "user_id": "demo",
      "cards": ["me", "water", "drink"],
      "sentence": "저는 물을 마시고 싶어요.",
      "created_at": "2026-09-09T01:30:00.000000+00:00"
    }
  ],
  "period_days": 7
}
```

데이터가 없으면 수치는 `0`, 목록은 `[]`, 카테고리는 `{}`로 반환한다.

```json
{
  "sessions": 0,
  "selections": 0,
  "top_cards": [],
  "categories": {},
  "recent": [],
  "period_days": 7
}
```

### 오류 응답

- `401`: 인증 실패
- `422`: `days`가 정수가 아니거나 1~365 범위를 벗어남
- `503`: MongoDB 연결 실패

# 11. 호출 예시

## 11.1 PowerShell

```powershell
$login = Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/auth/login `
  -ContentType 'application/json' `
  -Body '{"username":"demo","password":"demo1234"}'

$headers = @{ Authorization = "Bearer $($login.access_token)" }

Invoke-RestMethod `
  -Uri 'http://127.0.0.1:8000/api/dashboard?days=7' `
  -Headers $headers
```

## 11.2 cURL

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo1234"}'

curl "http://127.0.0.1:8000/api/dashboard?days=7" \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

# 12. 데이터 저장 관계

| API | MongoDB 컬렉션 | 작업 |
|---|---|---|
| 로그인 | `users` | 데모 사용자 동기화 및 조회 |
| 보호 대상 조회 | `caregiver_links`, `users` | 보호자-사용자 연결 조회 |
| 로그인 | `auth_sessions` | 인증 세션 생성 |
| 현재 사용자 | `auth_sessions`, `users` | 세션 및 사용자 조회 |
| 로그아웃 | `auth_sessions` | 세션 삭제 |
| 문장 생성 | `communication_sessions` | 중복 확인 및 문장 기록 생성 |
| 추천 | `communication_sessions` | 로그인 사용자 전체 기록 조회 |
| 이용 현황 | `communication_sessions` | 사용자 및 기간 조건 조회 |

백엔드 로그는 문서 내용, 비밀번호 및 토큰을 출력하지 않고 다음 형식으로 작업만 기록한다.

```text
DB CRUD | READ | communication_sessions | 사용자 통계 조회 (최근 7일)
```

# 13. 현재 제약사항

1. 비밀번호 변경 및 계정 탈퇴 API는 구현되지 않았다.
2. 기본 데모 계정은 개발·시연용이며 운영 배포 전에 교체해야 한다.
3. MongoDB 자체 인증은 현재 개발 구성에 적용되지 않았다.
4. 카드 등록·수정·삭제 API는 구현되지 않았다.
5. Qwen 문장 생성 API는 비활성화되어 있다.
6. 음성 출력은 프런트엔드의 Web Speech API로 처리하므로 백엔드 TTS API는 없다.
7. `/api/health`는 백엔드 상태만 반환하며 MongoDB 준비 상태를 응답에 포함하지 않는다.
