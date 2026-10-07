"""T1~T7 테스트 실행 → _작업파일/테스트_결과_raw/*.json 저장 + 요약 출력 (6단계 로컬 검증)."""
import io
import json
import os
import sys
import time

import requests

URL = "http://localhost:3000/api/ask"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "테스트_결과_raw")
os.makedirs(OUT, exist_ok=True)

LONG = ("안녕하세요. 저는 현재 대학원 석사 과정에 있고 센터 프로그램에 두 가지를 동시에 참여하고 있습니다. "
        "하나는 교육 프로그램이고 다른 하나는 기업 연계 인턴십인데, 두 프로그램의 출석 확인 방식이 서로 달라서 "
        "어디에 어떤 서류를 내야 하는지 헷갈립니다. 또 인턴십 기간 중에는 학생인건비가 별도로 지급되는지, "
        "지급된다면 출근부를 센터와 기업 양쪽에 모두 제출해야 하는지도 궁금합니다. 마지막으로 두 프로그램의 "
        "수료증이 각각 발급되는지, 아니면 통합으로 한 장이 나오는지 알려 주시면 감사하겠습니다. "
        "가능하면 담당 부서별로 나누어 안내해 주세요.")

TESTS = [
    ("T1", "프로그램 문의", "4학년 1학기에 현장실습을 신청하려면 언제 무엇을 제출해야 하나요?"),
    ("T2", "학생인건비 문의", "9월 출근부를 10월 3일에 냈는데 인건비 지급이 언제 되나요?"),
    ("T3", "기타 문의", "센터 세미나실을 학회 준비 모임 장소로 빌릴 수 있나요?"),
    ("T4", "프로그램 문의", "   "),
    ("T5", "기타 문의", LONG),
    ("T7", "기타 문의", "오늘 점심 메뉴 추천해 주세요"),
    ("T8", "프로그램 문의", "a" * 1001),
]
only = sys.argv[1:]

for tid, typ, q in TESTS:
    if only and tid not in only:
        continue
    t0 = time.time()
    try:
        r = requests.post(URL, json={"type": typ, "question": q}, timeout=40)
        status, body = r.status_code, (r.json() if r.content else {})
    except Exception as e:   # noqa: BLE001
        status, body = "EXC", {"error": repr(e)}
    sec = round(time.time() - t0, 1)
    rec = {"id": tid, "type": typ, "question": q[:60] + ("…" if len(q) > 60 else ""), "status": status, "seconds": sec, "response": body}
    with io.open(os.path.join(OUT, f"{tid}.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    print(f"{tid} {status} {sec}s", json.dumps(body, ensure_ascii=False)[:160].encode("utf-8", "replace").decode("utf-8", "replace"))
