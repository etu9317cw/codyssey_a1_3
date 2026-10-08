# 에너지인력양성센터 AI 안내 데스크

대학교 에너지인력양성센터의 소개·프로그램 안내를 한 페이지에서 보고, 문의 내용을 입력하면 AI가 **담당 부서·처리 절차·준비 서류·예상 소요·확인 필요 사항**을 먼저 알려 주는 웹서비스입니다.
2단계 1-3 미션(AI 웹서비스 제작·배포) 과제로, 순수 HTML/CSS/JavaScript 프론트와 Vercel Python Serverless Function 백엔드로 만들었습니다.

| 항목 | 값 |
|---|---|
| 배포 URL | (Vercel 배포 후 기록) |
| GitHub | `https://github.com/etu9317cw/codyssey_a1_3` (push 후 공개) |
| 서비스 기획서 | [`서비스_기획서.md`](./서비스_기획서.md) |
| 증빙 | [`캡처_체크리스트.md`](./캡처_체크리스트.md), [`증빙_AI코딩도구_로그.md`](./증빙_AI코딩도구_로그.md), `evidence/` |
| 요구사항 대조표 | [`서비스_기획서.md`](./서비스_기획서.md) 10장 (미션 원문 항목별 충족 여부·근거) |

## 왜 만들었나

B3 과제에서 구글 폼 문의를 담당자에게 자동 전달하는 자동화를 만들었습니다. 들어오는 문의의 상당수가 "이건 누구에게 물어보나요?" "뭘 준비해야 하나요?" 같은 절차 질문이었습니다. 이 페이지는 그 **앞단**입니다. 학생이 문의를 보내기 전에 AI가 1차 안내를 하고, 확정이 필요한 것(금액·날짜·승인 여부)만 "확인 필요"로 표시해 구글 폼으로 넘깁니다.

## 기능

| 섹션 | 내용 |
|---|---|
| 홈 | 센터 이름·한 줄 소개, "AI에게 물어보기" / "프로그램 보기" 버튼 |
| 센터 소개 | 센터 역할 3가지(교육·실습·네트워크) 카드 |
| 프로그램 안내 | 교육 프로그램 / 인턴십·현장실습 / 세미나·특강 카드 3개(대상·기간·신청 방법) |
| **AI 문의 도우미** | 문의 유형(프로그램 / 학생인건비 / 기타) + 문의 내용 → 결과 카드 5칸(담당 부서·처리 절차·준비 서류·예상 소요·확인 필요) |
| FAQ·문의하기 | 자주 묻는 질문 아코디언 5개, 구글 폼으로 가는 "문의하기" 버튼 |

상단 고정 메뉴로 다섯 섹션을 이동하고, 600px 이하에서는 햄버거 메뉴로 접힙니다.

### AI 문의 도우미 실패 처리 (3종 모두 구현)

| 상황 | 사용자에게 보이는 메시지 | 처리 |
|---|---|---|
| 빈 입력 | "문의 내용을 입력하세요." | 프론트에서 요청을 보내지 않음. 서버에서도 400으로 한 번 더 검증 |
| API 오류(4xx·5xx) | "안내를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요." | 서버가 500(키 미설정)·502(상위 API 오류)로 응답, 프론트가 오류 박스 표시 |
| 지연·타임아웃 | "응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요." | 프론트 20초 `AbortController`, 서버는 18초에 먼저 끊어 502 반환 |
| 길이 초과 | "문의 내용은 1,000자 이내로 입력하세요." | 글자 수 카운터 + 서버 400 |

### 보너스

- **다크 모드 토글**(미션 보너스 2 UX): 상단 🌙 버튼. `data-theme` 속성과 CSS 변수로 전환하고 선택값을 localStorage에 저장. 기본값은 시스템 설정.
- **문의하기 → 구글 폼 연결**(보너스 1 운영 자동화): 버튼이 B3 과제의 구글 폼으로 이어지고, 접수 후 Make 시나리오가 담당자에게 메일을 보냅니다. 폼 URL은 `js/main.js`의 `GOOGLE_FORM_URL` 상수에 넣습니다(비어 있으면 "준비 중" 안내).

## 기술 스택

| 구분 | 기술 | 비고 |
|---|---|---|
| 프론트 | HTML5, CSS3(변수·Grid·Flex·미디어 쿼리 900/600px), Vanilla JS(fetch, AbortController) | 프레임워크·빌드 도구 없음 |
| 백엔드 | Vercel Serverless Functions, Python, `requests` | `api/ask.py` 하나, `BaseHTTPRequestHandler` 방식 |
| LLM | 기관 제공 LLM 프록시(OpenAI 호환 Chat Completions), 모델 `gemini-3-flash` | 환경변수로 교체 가능 |
| 배포 | GitHub → Vercel 자동 배포 | 환경변수는 Vercel 프로젝트 설정에 등록 |

### 요청 흐름

```
브라우저 js/main.js ── POST /api/ask {type, question} (20초 타임아웃) ──▶ api/ask.py
api/ask.py ── 입력 검증(400) → 시스템 프롬프트 + 문의 → POST {BASE_URL}/v1/chat/completions ──▶ LLM 프록시
api/ask.py ◀── JSON 텍스트 → 코드펜스 제거 → json.loads → 필드 보정(형식 오류 시 1회 재요청)
브라우저 ◀── 200 {department, steps[], documents[], duration, notes} → 결과 카드 렌더링
```

API 키는 서버 함수에서만 쓰입니다. 브라우저는 `/api/ask`만 호출하므로 키가 클라이언트로 나가지 않습니다.

## 폴더 구조

```
.
├── index.html            # 섹션 5개 단일 페이지
├── css/style.css         # 색상 토큰, 레이아웃, 반응형, 다크 모드
├── js/main.js            # 메뉴·햄버거·FAQ·다크 모드·AI 문의(fetch, 실패 처리)
├── api/ask.py            # Vercel Python 함수: 검증 → LLM 호출 → JSON 반환
├── images/               # (예비) 이미지
├── requirements.txt      # requests
├── vercel.json           # 함수 maxDuration 30초, 보안 헤더
├── .env.example          # 환경변수 이름과 설명 (값 없음)
├── .gitignore            # .env·.vercel/·__pycache__·작업 메모 제외
├── 서비스_기획서.md
├── 증빙_AI코딩도구_로그.md
├── 캡처_체크리스트.md
├── evidence/             # 캡처 이미지
└── _작업파일/            # PRD, 로컬 서버, 테스트 입력·결과, 미션 원문
```

## 환경 변수

| 이름 | 설명 | 예 |
|---|---|---|
| `CODYSSEY_API_KEY` | 기관 LLM 프록시 키(OpenAI 호환). 콘솔에서 발급, 한 번만 표시됨 | `sk-…` (여기에 쓰지 않음) |
| `CODYSSEY_BASE_URL` | 프록시 주소 | `https://copa.codyssey.kr` |
| `CODYSSEY_MODEL` | 모델 이름 | `gemini-3-flash` |

- 로컬: `.env.example`을 `.env`로 복사해 값을 채웁니다. `.env`는 `.gitignore`에 있어 커밋되지 않습니다.
- Vercel: Project → Settings → Environment Variables에 같은 이름 3개를 등록합니다. 값을 바꾸면 재배포가 필요합니다.
- 키는 코드·README·캡처 어디에도 적지 않습니다. 유출이 의심되면 콘솔에서 즉시 폐기·재발급합니다.
- 키가 커밋에 들어갔다면 되돌리기 커밋만으로는 이력에 남으므로, `git filter-repo`(또는 BFG)로 해당 파일·문자열을 전체 이력에서 지운 뒤 강제 push하고 키를 재발급합니다. 이 저장소는 `.env`를 처음부터 `.gitignore`에 두어 커밋된 적이 없습니다(`git log --all -- .env` 0건).

## 로컬 실행

Python 3.10 이상, `requests`가 필요합니다.

```
pip install -r requirements.txt
copy .env.example .env          # 값 채우기
python _작업파일/local_server.py   # http://localhost:3000
```

`_작업파일/local_server.py`는 표준 라이브러리 `http.server`로 정적 파일을 서빙하고 `/api/ask`를 `api/ask.py`의 핸들러로 넘깁니다. Vercel과 같은 `BaseHTTPRequestHandler` 인터페이스라 코드 수정 없이 로컬에서 같은 함수를 검증할 수 있습니다. `vercel dev`를 써도 됩니다.

로컬 검증 결과(T1~T8, 정상 3·빈 입력·긴 입력·오류 유도·범위 밖·길이 초과)는 `_작업파일/테스트_결과.md`에 있습니다.

## 배포 방법 (GitHub → Vercel)

1. 이 저장소를 GitHub 저장소 `codyssey_a1_3`에 push합니다.
2. vercel.com에 GitHub 계정으로 로그인 → **Add New Project** → 이 저장소 Import.
3. Framework Preset은 **Other**(빌드 명령 없음). `vercel.json`이 `api/ask.py`의 실행 시간을 30초로 잡습니다.
4. Environment Variables에 위 3개를 등록하고 **Deploy**.
5. 배포 URL에서 메뉴 이동·모바일 레이아웃·AI 문의·실패 처리를 확인합니다. 수정이 있으면 커밋 → push → 자동 재배포.

## 한계와 운영 메모

- AI 안내는 참고용입니다. 금액·날짜·승인 여부는 단정하지 않고 "확인 필요"로 표시하도록 프롬프트에 고정했고, 담당 부서는 세 가지(프로그램 운영 담당 / 학생인건비 담당 / 센터 총괄) 중에서만 고릅니다.
- 입력은 저장·로깅하지 않습니다(오류 로그에도 본문 미기록). 입력창에 개인정보 입력 금지 안내가 있습니다.
- 프록시가 `response_format`을 지원하지 않아 JSON 출력을 프롬프트로 강제하고 서버에서 파싱·보정합니다. `max_tokens`는 사고 토큰 때문에 본문이 잘릴 수 있어 생략했습니다.
- 응답은 보통 5~13초입니다(gemini-3-flash 사고 시간 포함). 월 토큰 쿼터가 있어 버튼 비활성화·1,000자 제한·재요청 1회로 호출량을 제한합니다.
