"""Offline HTTP and browser lifecycle tests; Playwright is not installed."""

import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import Mock, patch
from urllib.parse import urlencode

from naver_render import Handler, Renderer, is_allowed_url

SEARCH = "https://search.naver.com/search.naver"
HTML = "<html>날씨</html>"


class AllowedURLTest(unittest.TestCase):
    def test_only_naver_search_documents_are_allowed(self) -> None:
        for url in (SEARCH, SEARCH + "?query=서울 날씨&where=nexearch"):
            with self.subTest(url=url):
                self.assertTrue(is_allowed_url(url))
        for url in (
            "", "/search.naver", "http://search.naver.com/search.naver",
            "https://example.invalid/search.naver", SEARCH + "/",
            "https://search.naver.com/", "https://search.naver.com:443/search.naver",
            "https://search.naver.com:/search.naver", "https://user@search.naver.com/search.naver",
            "https://user:password@search.naver.com/search.naver", SEARCH + "#top", SEARCH + "#",
            "https://search.naver.com.evil.invalid/search.naver", "https://[bad/search.naver",
            " " + SEARCH, SEARCH + "?query=secret\n",
        ):
            with self.subTest(url=url):
                self.assertFalse(is_allowed_url(url))


class HandlerTest(unittest.TestCase):
    def _request(self, request: bytes) -> tuple[bytes, str, Mock]:
        connection = Mock()
        connection.makefile.return_value = io.BytesIO(request)
        renderer = Mock(render=Mock(return_value=(200, HTML)))
        stderr = io.StringIO()
        with patch.object(Handler, "renderer", renderer), redirect_stderr(stderr):
            Handler(connection, ("client", 0), Mock())
        response = b"".join(call.args[0] for call in connection.sendall.call_args_list)
        return response, stderr.getvalue(), renderer

    def test_health_and_unknown_path(self) -> None:
        for path, status, body in (("/health", 200, b"ok"), ("/missing", 404, None)):
            with self.subTest(path=path):
                response, log, renderer = self._request(f"GET {path} HTTP/1.1\r\n\r\n".encode())
                self.assertIn(f"HTTP/1.0 {status}".encode(), response)
                self.assertEqual(log.splitlines(), [f"GET {path} {status}"])
                renderer.render.assert_not_called()
                if body is not None:
                    self.assertEqual(response.split(b"\r\n\r\n", 1)[1], body)

    def test_render_returns_html_and_logs_only_the_path(self) -> None:
        url = SEARCH + "?query=private-area"
        query = urlencode({"url": url})
        response, log, renderer = self._request(f"GET /render?{query} HTTP/1.1\r\n\r\n".encode())
        renderer.render.assert_called_once_with(url)
        self.assertIn(b"HTTP/1.0 200", response)
        self.assertIn(b"Content-Type: text/html; charset=utf-8", response)
        self.assertEqual(response.split(b"\r\n\r\n", 1)[1], HTML.encode())
        self.assertEqual(log.splitlines(), ["GET /render 200"])
        for secret in ("private-area", query, "url=", "query="):
            self.assertNotIn(secret, log)

    def test_invalid_or_duplicate_url_is_not_rendered(self) -> None:
        for query in ("", "url=", "url=https://example.invalid/", urlencode({"url": [SEARCH, SEARCH]}, doseq=True)):
            with self.subTest(query=query):
                response, log, renderer = self._request(f"GET /render?{query} HTTP/1.1\r\n\r\n".encode())
                self.assertIn(b"HTTP/1.0 400", response)
                self.assertIn(b"Content-Type: text/plain; charset=utf-8", response)
                self.assertEqual(log.splitlines(), ["GET /render 400"])
                renderer.render.assert_not_called()

    def test_write_methods_are_refused_and_other_methods_keep_501(self) -> None:
        for method, status in (("POST", 405), ("PUT", 405), ("DELETE", 405), ("PATCH", 405), ("OPTIONS", 501), ("HEAD", 501)):
            with self.subTest(method=method):
                response, log, renderer = self._request(f"{method} /render?private-area HTTP/1.1\r\n\r\n".encode())
                self.assertIn(f"HTTP/1.0 {status}".encode(), response)
                self.assertEqual(log.splitlines(), [f"{method} /render {status}"])
                self.assertNotIn("private-area", log)
                renderer.render.assert_not_called()

    def test_malformed_request_logs_one_line_without_query_or_traceback(self) -> None:
        response, log, renderer = self._request(b"GET /render?private-area HTTP/1.1 extra\r\n\r\n")
        self.assertIn(b"400", response)
        self.assertEqual(log.splitlines(), ["- - 400"])
        self.assertNotIn("private-area", log)
        self.assertNotIn("Traceback", log)
        renderer.render.assert_not_called()

    def test_upstream_error_is_plain_text(self) -> None:
        with patch.object(Renderer, "render", return_value=(502, "네이버 응답 상태: 403")):
            connection = Mock()
            connection.makefile.return_value = io.BytesIO(
                f"GET /render?{urlencode({'url': SEARCH})} HTTP/1.1\r\n\r\n".encode()
            )
            with redirect_stderr(io.StringIO()):
                Handler(connection, ("client", 0), Mock())
        response = b"".join(call.args[0] for call in connection.sendall.call_args_list)
        self.assertIn(b"HTTP/1.0 502", response)
        self.assertIn(b"Content-Type: text/plain; charset=utf-8", response)
        self.assertNotIn(HTML.encode(), response)

    def test_query_in_an_invalid_method_is_not_logged(self) -> None:
        response, log, _ = self._request(b"GET?private-area /render?private-area HTTP/1.1\r\n\r\n")
        self.assertIn(b"HTTP/1.0 501", response)
        self.assertEqual(log.splitlines(), ["GET /render 501"])
        self.assertNotIn("private-area", log)


class RendererTest(unittest.TestCase):
    def setUp(self) -> None:
        self.response = Mock(status=200, url=SEARCH)
        self.page = Mock(url=SEARCH)
        self.page.goto.return_value = self.response
        self.page.content.return_value = HTML
        self.context = Mock()
        self.context.new_page.return_value = self.page
        self.browser = Mock()
        self.browser.is_connected.return_value = True
        self.browser.new_context.return_value = self.context
        self.chromium = Mock()
        self.chromium.launch.return_value = self.browser
        self.playwright = Mock(chromium=self.chromium)
        self.start = Mock(return_value=self.playwright)
        self.renderer = Renderer(self.start)

    def test_lazy_launch_reuses_browser_and_context_with_new_pages(self) -> None:
        self.start.assert_not_called()
        second_page = Mock(url=SEARCH)
        second_page.goto.return_value = self.response
        second_page.content.return_value = HTML
        self.context.new_page.side_effect = [self.page, second_page]
        self.assertEqual(self.renderer.render(SEARCH), (200, HTML))
        self.assertEqual(self.renderer.render(SEARCH + "?query=weather"), (200, HTML))
        self.start.assert_called_once_with()
        self.chromium.launch.assert_called_once_with(headless=True)
        self.browser.new_context.assert_called_once_with(locale="ko-KR")
        self.assertEqual(self.context.new_page.call_count, 2)
        for page in (self.page, second_page):
            page.route.assert_called_once()
            page.close.assert_called_once_with()
        self.page.goto.assert_called_once_with(SEARCH, wait_until="domcontentloaded", timeout=30_000)
        self.browser.close.assert_not_called()

    def test_request_routes_block_heavy_resources_and_unapproved_navigations(self) -> None:
        self.renderer.render(SEARCH)
        pattern, handler = self.page.route.call_args.args
        self.assertEqual(pattern, "**/*")
        for resource, navigation, url, aborted in (
            ("image", False, SEARCH, True),
            ("media", False, SEARCH, True),
            ("font", False, SEARCH, True),
            ("document", True, "https://example.invalid/", True),
            ("document", True, "http://search.naver.com/search.naver", True),
            ("document", True, SEARCH, False),
            ("script", False, "https://example.invalid/script.js", False),
            ("xhr", False, "https://example.invalid/data", False),
            ("stylesheet", False, "https://example.invalid/style.css", False),
        ):
            with self.subTest(resource=resource, navigation=navigation, url=url):
                request = Mock(resource_type=resource, url=url)
                request.is_navigation_request.return_value = navigation
                route = Mock(request=request)
                handler(route)
                (route.abort if aborted else route.continue_).assert_called_once_with()
                (route.continue_ if aborted else route.abort).assert_not_called()

    def test_upstream_status_and_missing_response_never_return_html(self) -> None:
        for response, expected in ((Mock(status=403, url=SEARCH), "403"), (None, "응답 없음")):
            with self.subTest(response=response):
                self.page.reset_mock()
                self.page.goto.return_value = response
                status, body = self.renderer.render(SEARCH)
                self.assertEqual(status, 502)
                self.assertIn(expected, body)
                self.assertNotIn(HTML, body)
                self.page.content.assert_not_called()
                self.page.close.assert_called_once_with()
        self.browser.close.assert_not_called()

    def test_both_response_and_serialized_document_must_stay_on_naver_search(self) -> None:
        for response_url, page_url in (("https://example.invalid/", SEARCH), (SEARCH, "https://example.invalid/")):
            with self.subTest(response_url=response_url, page_url=page_url):
                self.page.reset_mock()
                self.response.url = response_url
                self.page.url = page_url
                status, body = self.renderer.render(SEARCH)
                self.assertEqual(status, 502)
                self.assertIn("redirect", body)
                self.assertNotIn(HTML, body)
                self.page.content.assert_not_called()
                self.page.close.assert_called_once_with()

    def test_browser_errors_drop_browser_and_next_render_relaunches(self) -> None:
        for operation in ("new_page", "route", "goto", "content"):
            with self.subTest(operation=operation):
                self.setUp()
                method = self.context.new_page if operation == "new_page" else getattr(self.page, operation)
                method.side_effect = TimeoutError(SEARCH + "?query=private-area")
                self.browser.close.side_effect = RuntimeError("closing failed")
                status, body = self.renderer.render(SEARCH)
                self.assertEqual(status, 502)
                self.assertIn("TimeoutError", body)
                self.assertNotIn("private-area", body)
                self.assertNotIn(SEARCH, body)
                self.browser.close.assert_called_once_with()
                if operation != "new_page":
                    self.page.close.assert_called_once_with()
                method.side_effect = None
                self.assertEqual(self.renderer.render(SEARCH), (200, HTML))
                self.assertEqual(self.chromium.launch.call_count, 2)

    def test_disconnected_browser_is_closed_then_next_render_relaunches(self) -> None:
        self.assertEqual(self.renderer.render(SEARCH), (200, HTML))
        self.browser.is_connected.return_value = False
        status, body = self.renderer.render(SEARCH)
        self.assertEqual(status, 502)
        self.assertIn("ConnectionError", body)
        self.browser.close.assert_called_once_with()
        self.assertEqual(self.context.new_page.call_count, 1)
        self.browser.is_connected.return_value = True
        self.assertEqual(self.renderer.render(SEARCH), (200, HTML))
        self.assertEqual(self.chromium.launch.call_count, 2)


if __name__ == "__main__":
    unittest.main()
