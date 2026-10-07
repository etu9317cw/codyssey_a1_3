"""로컬 검증용 간이 서버 (표준 라이브러리만 사용).

- 정적 파일: 프로젝트 루트(index.html, css/, js/)를 그대로 서빙
- /api/ask : api/ask.py 의 handler 로 위임 (Vercel 과 같은 BaseHTTPRequestHandler 인터페이스)
- .env 를 읽어 환경변수로 넣는다 (python-dotenv 없이 직접 파싱)

실행:  python _작업파일/local_server.py  [포트, 기본 3000]
"""
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "api"))


def load_env(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env(os.path.join(ROOT, ".env"))
import ask  # noqa: E402  (api/ask.py)


class Router(SimpleHTTPRequestHandler):
    _send = ask.handler._send   # api 핸들러의 응답 메서드를 그대로 빌려 쓴다

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def _is_api(self):
        return self.path.split("?")[0] == "/api/ask"

    def do_POST(self):
        if self._is_api():
            return ask.handler.do_POST(self)
        self.send_error(404)

    def do_GET(self):
        if self._is_api():
            return ask.handler.do_GET(self)
        super().do_GET()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    print(f"http://localhost:{port}  (root={ROOT}, key={'set' if os.environ.get('CODYSSEY_API_KEY') else 'MISSING'})")
    ThreadingHTTPServer(("127.0.0.1", port), Router).serve_forever()
