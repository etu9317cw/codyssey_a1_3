"""Vercel Python Serverless Function: POST /api/ask

입력  {"type": "프로그램 문의|학생인건비 문의|기타 문의", "question": "..."}
출력  {"department": str, "steps": [str], "documents": [str], "duration": str, "notes": str}
오류  {"error": str}  + 상태 코드 (400 입력 오류 / 405 메서드 / 502 상위 API·형식 오류 / 500 서버 설정)

기관 제공 LLM 프록시(OpenAI 호환 /v1/chat/completions)를 requests 로 호출한다.
키·주소·모델은 환경변수 CODYSSEY_API_KEY / CODYSSEY_BASE_URL / CODYSSEY_MODEL 로만 받는다.
"""
import json
import os
import re
from http.server import BaseHTTPRequestHandler

import requests

ALLOWED_TYPES = ("프로그램 문의", "학생인건비 문의", "기타 문의")
MAX_QUESTION_LENGTH = 1000
UPSTREAM_TIMEOUT = 18          # 프론트 타임아웃(20초)보다 먼저 끊어 502로 알린다
DEPARTMENTS = ("프로그램 운영 담당", "학생인건비 담당", "센터 총괄")

SYSTEM_PROMPT = """당신은 대학교 에너지인력양성센터의 안내 담당자입니다. 학생의 문의를 읽고 아래 JSON 형식으로만 답합니다.

센터 구조:
- 프로그램 운영 담당: 교육 프로그램, 인턴십·현장실습 신청·선발·수료증
- 학생인건비 담당: 출근부, 학생인건비 지급, 통장 사본
- 센터 총괄: 세미나·특강, 공간 대여, 그 밖의 모든 문의

규칙:
1. department 는 "프로그램 운영 담당", "학생인건비 담당", "센터 총괄" 중 하나만 쓴다.
2. 사람 이름, 이메일, 전화번호를 만들어 쓰지 않는다.
3. 금액, 정확한 날짜, 승인 여부는 단정하지 않는다. 확정이 필요한 내용은 notes 에 "담당자 확인 필요"로 적는다.
4. steps 는 3단계 내외의 짧은 문장, documents 는 서류 이름만, duration 은 한 줄.
5. 센터 안내 범위 밖의 질문이면 department 는 "센터 총괄", steps 와 documents 는 빈 배열, notes 에 센터 안내 범위 밖임을 적는다.
6. 존댓말로 간결하게 쓴다. JSON 바깥에 다른 글을 쓰지 않는다.

출력 형식:
{"department": "...", "steps": ["...", "...", "..."], "documents": ["..."], "duration": "...", "notes": "..."}"""


# ---------- 유틸 ----------

def _extract_json(text: str) -> dict:
    """```json 펜스나 앞뒤 설명을 제거하고 첫 번째 JSON 객체를 파싱한다."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("JSON 객체를 찾을 수 없음")
    return json.loads(cleaned[start:end + 1])


def _str_list(value) -> list:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def _normalize(data: dict) -> dict:
    """모델 출력의 필드를 화면 계약에 맞게 보정한다."""
    dept = str(data.get("department", "")).strip()
    if dept not in DEPARTMENTS:
        dept = next((d for d in DEPARTMENTS if d in dept), "센터 총괄")
    return {
        "department": dept,
        "steps": _str_list(data.get("steps"))[:5],
        "documents": _str_list(data.get("documents"))[:8],
        "duration": str(data.get("duration", "")).strip() or "담당자 확인 필요",
        "notes": str(data.get("notes", "")).strip() or "정확한 내용은 담당자 확인이 필요합니다.",
    }


def _call_llm(inquiry_type: str, question: str) -> dict:
    """기관 프록시 호출 → 정규화된 dict. 실패는 RuntimeError 로 통일."""
    api_key = os.environ.get("CODYSSEY_API_KEY", "")
    base_url = os.environ.get("CODYSSEY_BASE_URL", "https://copa.codyssey.kr").rstrip("/")
    model = os.environ.get("CODYSSEY_MODEL", "gemini-3-flash")
    if not api_key:
        raise RuntimeError("config:CODYSSEY_API_KEY 가 설정되지 않았습니다")

    user_msg = f"문의 유형: {inquiry_type}\n문의 내용: {question}"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        # max_tokens 생략: gemini-3-flash 는 사고 토큰이 상한에 포함되어 본문이 잘릴 수 있음
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    last_error = None
    for attempt in range(2):   # JSON 형식 오류·일시 오류는 1회 재시도
        try:
            res = requests.post(f"{base_url}/v1/chat/completions", headers=headers, json=body,
                                timeout=UPSTREAM_TIMEOUT)
        except requests.Timeout:
            raise RuntimeError("upstream:LLM 응답 시간 초과")
        except requests.RequestException as e:
            raise RuntimeError(f"upstream:LLM 연결 실패 ({type(e).__name__})")

        if res.status_code >= 400:
            last_error = f"upstream:LLM HTTP {res.status_code}"
            if res.status_code in (401, 403, 404):
                break   # 재시도 의미 없음
            continue

        try:
            text = res.json()["choices"][0]["message"]["content"] or ""
            return _normalize(_extract_json(text))
        except (ValueError, KeyError, IndexError, TypeError) as e:
            last_error = f"format:응답 형식 오류 ({type(e).__name__})"
            continue

    raise RuntimeError(last_error or "upstream:알 수 없는 오류")


# ---------- 핸들러 ----------

class handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(405, {"error": "POST 요청만 받습니다."})

    def do_POST(self):
        # 1) 본문 파싱
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError):
            return self._send(400, {"error": "요청 본문이 JSON 형식이 아닙니다."})
        if not isinstance(payload, dict):
            return self._send(400, {"error": "요청 본문이 JSON 객체가 아닙니다."})

        # 2) 입력 검증 (실패 처리 ①: 빈 입력 / 길이 제한 / 유형)
        inquiry_type = str(payload.get("type", "")).strip()
        question = str(payload.get("question", "")).strip()
        if inquiry_type not in ALLOWED_TYPES:
            return self._send(400, {"error": "문의 유형을 선택하세요."})
        if not question:
            return self._send(400, {"error": "문의 내용을 입력하세요."})
        if len(question) > MAX_QUESTION_LENGTH:
            return self._send(400, {"error": "문의 내용은 1,000자 이내로 입력하세요."})

        # 3) LLM 호출 (실패 처리 ②: 상위 API 오류 → 502 / 설정 오류 → 500)
        try:
            result = _call_llm(inquiry_type, question)
        except RuntimeError as e:
            kind, _, _detail = str(e).partition(":")
            status = 500 if kind == "config" else 502
            # 문의 본문은 로그에 남기지 않는다 (개인정보 보호)
            print(f"[ask] error={e}")
            return self._send(status, {"error": "안내를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요."})

        self._send(200, result)

    def log_message(self, fmt, *args):   # 기본 접근 로그 억제 (본문·IP 미기록)
        return
