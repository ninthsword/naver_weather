"""Render Naver search pages with a lazily started, shared Chromium browser."""

import sys
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Playwright, Route


def is_allowed_url(url: str) -> bool:
    """Accept only HTTPS Naver search documents, without credentials or a port."""
    if url != url.lstrip() or "#" in url or any(ord(char) < 32 or ord(char) == 127 for char in url):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and parts.netloc.lower() == "search.naver.com"
        and parts.path == "/search.naver"
    )


def _start_playwright() -> "Playwright":
    """Import the optional runtime dependency only when rendering starts."""
    from playwright.sync_api import sync_playwright

    return sync_playwright().start()


class Renderer:
    """Reuse one browser and context, closing each request's page."""

    def __init__(self, start: "Callable[[], Playwright] | None" = None) -> None:
        self._start = start or _start_playwright
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def _drop_browser(self) -> None:
        browser, self._browser = self._browser, None
        self._context = None
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass

    @staticmethod
    def _route(route: "Route") -> None:
        request = route.request
        if request.resource_type in {"image", "media", "font"} or (
            request.is_navigation_request() and not is_allowed_url(request.url)
        ):
            route.abort()
        else:
            route.continue_()

    def render(self, url: str) -> tuple[int, str]:
        """Return HTML or a query-free error, resetting Chromium after an error."""
        page = None
        try:
            if self._browser is not None and not self._browser.is_connected():
                raise ConnectionError
            if self._browser is None:
                if self._playwright is None:
                    self._playwright = self._start()
                self._browser = self._playwright.chromium.launch(headless=True)
                self._context = self._browser.new_context(locale="ko-KR")
            assert self._context is not None
            page = self._context.new_page()
            page.route("**/*", self._route)
            response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            if response is None:
                return 502, "네이버 응답 없음"
            if not is_allowed_url(response.url):
                return 502, "허용되지 않은 이동(redirect)"
            if response.status != 200:
                return 502, f"네이버 응답 상태: {response.status}"
            if not is_allowed_url(page.url):
                return 502, "허용되지 않은 이동(redirect)"
            return 200, page.content()
        except Exception as error:
            self._drop_browser()
            return 502, f"브라우저 오류: {type(error).__name__}"
        finally:
            if page is not None:
                try:
                    page.close()
                except Exception:
                    self._drop_browser()


class Handler(BaseHTTPRequestHandler):
    """Expose health and rendering without logging the user's search query."""

    renderer = Renderer()

    def _send(self, status: int, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        try:
            parts = urlsplit(self.path)
        except ValueError:
            self._send(400, "잘못된 요청 주소")
            return
        if parts.path == "/health":
            self._send(200, "ok")
        elif parts.path == "/render":
            urls = parse_qs(parts.query, keep_blank_values=True).get("url", [])
            if len(urls) != 1 or not is_allowed_url(urls[0]):
                self._send(400, "허용되지 않은 네이버 검색 주소")
                return
            status, body = self.renderer.render(urls[0])
            content_type = "text/html; charset=utf-8" if status == 200 else "text/plain; charset=utf-8"
            self._send(status, body, content_type)
        else:
            self._send(404, "찾을 수 없는 경로")

    def do_POST(self) -> None:
        self._send(405, "허용되지 않은 요청 방식")

    do_PUT = do_POST
    do_DELETE = do_POST
    do_PATCH = do_POST

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        method = (getattr(self, "command", None) or "-").split("?", 1)[0]
        path = (getattr(self, "path", None) or "-").split("?", 1)[0]
        sys.stderr.write(f"{method} {path} {code}\n")

    def log_message(self, format: str, *args: object) -> None:
        """Suppress error messages, which can contain the raw request line."""


def main() -> None:
    """Serve one request at a time on the container's published port."""
    with HTTPServer(("0.0.0.0", 8765), Handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
