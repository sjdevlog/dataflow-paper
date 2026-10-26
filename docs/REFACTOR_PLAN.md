# DateFlow 논문용 리팩터링 계획

마감: **2026-11-30** · 범위: `frontend/f2`, `backend/B1`, `backend/B2`, `ai` 전체 · 방식: 구조 리팩터링(기능 유지)

---

## 1단계 — 프론트↔백엔드 계약 통일, 코스 1회 생성 ✅ (10/26)

### 고친 버그
| 위치 | 문제 | 수정 |
|---|---|---|
| f2 페이지 5곳 | `/course/generate`를 페이지마다 다시 호출 → 고른 코스와 예약/완료 화면 코스가 달라질 수 있음 | 온보딩에서 **1번만** 생성 → `PlanContext`(sessionStorage)로 모든 페이지 공유 |
| f2 → B1 요청 | 프론트는 `budget`, 백엔드는 `budget_max` → 예산이 항상 10만원 | `budget_max`/`budget_min` 전송 (2인 합산) |
| f2 → B1 요청 | 취향 태그 미전송, B님 취향 하드코딩 `["맛집 탐방"]` | `tags_a`/`tags_b` 전송, 백엔드는 요청 > DB > 기본값 |
| B1 `course.py` | `make_place`가 `else` 블록 안에서 정의 → **AI 추천 성공 시 B안 생성에서 NameError(500)** | 모듈 함수로 분리, 테스트로 고정 |
| B1 `course.py` | AI 경로 `~/DateFlow/ai` 하드코딩 | repo 상대경로 + `AI_PATH` 환경변수 |
| B1 `course.py` | 날씨 조회에 선택 날짜 미반영 | `req.date` 전달 |
| f2 결과 화면 | 만족도를 장소 이름 글자 코드로 **가짜 계산** | 백엔드 `satisfaction_a/b` 사용 |
| f2 `todayStr` | `toISOString()`(UTC) → KST 오전 9시 전엔 어제 날짜 | 로컬 날짜 |
| f2 로그인 | API 기본값 `8001`(B2) — `/auth`는 B1(8000)에 있음 | 공통 `API_BASE` |
| f2 지역 검색 | 결과 클릭 시 input blur → 직접입력 확정 → 레이아웃 이동으로 **클릭이 빗나감**, Enter 후 늦은 결과가 드롭다운 재오픈 | 결과 버튼 `mousedown` 기본동작 차단, 확정 시 디바운스 취소 |

### 구조
```
frontend/f2/src
├── config.ts                 API_BASE, 카카오 키, 기본 좌표
├── api/                      http(타임아웃·에러), course(어댑터 1벌), weather, kakaoPlaces, auth, prefs
├── contexts/PlanContext.tsx  온보딩 입력 + 생성된 A/B 코스 + 선택 상태
├── components/onboarding/    OnboardingPage 1004줄 → 컴포넌트 9개 (~200줄 페이지)
├── components/common/        PageHeader, AiBubble, SampleDataNotice
└── utils/                    date, budget, tags, share(공유 링크 인코딩)

backend/B1/app
├── routers/course.py         흐름만 (338줄 → 오케스트레이션)
└── services/
    ├── scoring.py            만족도·공정성 지표 (논문 수식 위치)
    ├── kakao.py              좌표 조회, 이동시간 (+직선거리 폴백)
    ├── places.py             B2 장소 조회
    └── ai_bridge.py          AI 파이프라인 호출
```

### 새로 생긴 측정값 (논문용)
- 코스별 `avg_satisfaction_a`, `avg_satisfaction_b`, `fairness_gap = |평균A − 평균B|`
- 코스별 `source`: `ai` / `b2` / `mock` → AI 성공률 집계 가능, 샘플 데이터는 화면에 경고 표시

### 동작이 바뀐 부분 (확인 필요)
- **코스 예산 = A·B 1인 최대 예산 합** (결과 화면 'A+B 합산'과 같은 기준). 기존에는 백엔드가 예산을 무시하고 10만원 고정이었음.
- 공유 링크는 URL 파라미터 대신 `/complete?share=<코스 요약>` 형식. 받는 사람도 로그인은 필요(기존과 동일).
- 온보딩 STEP 5(쓰이지 않던 미리보기 화면·`MOCK_COURSES`)는 삭제.

### 검증
- `backend/B1/tests/test_course.py` 5개 통과 (외부 API 목 처리). pytest 미설치 상태 → `pip install pytest` 후 `python -m pytest tests`
- f2 `tsc -b`, `vite build` 통과. 남은 eslint 3건은 Context 파일에서 훅을 함께 export하는 기존 패턴(`react-refresh/only-export-components`)
- 브라우저 E2E (10/27, headless Chromium): 로그인 → 온보딩 → 이벤트 → 코스 선택 → 결과(새로고침 유지) → 예약 → 완료, 콘솔 에러 0. 당시 백엔드 키 없음 → 장소명 기본값

---

## 2단계 — AI 파이프라인 정리 (~11/2)
- [ ] **pipeline2(코스 설계 에이전트)가 백엔드에서 안 쓰이고 있음** → 이벤트 선택 → pipeline2 → A/B안 흐름으로 연결
- [ ] 이벤트 선택 화면의 이벤트가 하드코딩 목업 → pipeline1 결과로 대체, 선택 이벤트를 백엔드로 전달
- [ ] 정규식 JSON 파싱 → 구조화 출력(pydantic 스키마)으로 교체, `_parse_status` 실패율 측정
- [ ] 동기 에이전트 호출이 FastAPI 이벤트 루프를 막음 → `run_in_threadpool`
- [ ] `ai/main.py`·`shared.py` LLM 설정 중복 제거, `tools/logger.py`에 지연시간·툴 호출 수 기록

## 3단계 — 데이터/백엔드 정리 (~11/9)
- [ ] `backend/B1/requirements.txt`가 비어 있음 → 의존성 고정
- [ ] B2 카테고리 오분류(예: 헤어샵 → 바/펍) 수정
- [ ] B1·B2 DB 통합 여부 결정, `.env.example` 정리
- [ ] 장소 가격: 예산 비율 고정 배분(15/50/35%) → 실제 메뉴 가격 반영

## 4단계 — 실험 하네스 (~11/16)
- [ ] 시나리오 배치 실행 스크립트: 지역 × 취향 쌍 × 날씨 × 예산
- [ ] 비교군: B2 규칙 기반 vs AI 추천 vs (선택) 공정성 고려 재정렬
- [ ] 지표: 평균 만족도, 공정성 격차, 예산 적합도, 총 이동시간, 영업시간 위반 수, 응답 시간, AI 성공률/파싱 성공률
- [ ] 결과 CSV → 논문 표·그래프

## 5단계 — 논문 작성 (11/16 ~ 11/30)
- 기여점 후보: ① 2인 취향 융합 + 공정성 지표 ② 영업시간 검증 툴을 쓰는 LLM 에이전트 + 규칙 기반 폴백 ③ 전체 시스템 아키텍처
- ⚠ 한계로 명시할 것: 현재 만족도는 태그-카테고리 매칭 **대리 지표**이지 실제 사용자 만족도가 아님 → 소규모 사용자 평가를 하거나 한계로 서술
