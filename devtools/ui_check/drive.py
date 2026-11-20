"""Drive Home Assistant's own frontend like a user, assert its Korean texts and keep screenshots."""

from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import (
    APIRequestContext,
    Browser,
    ConsoleMessage,
    Error,
    Locator,
    Page,
    ViewportSize,
    expect,
    sync_playwright,
)

USER, PASSWORD = "verifier", "synthetic-pass-123"
AREA = "검증동"
SECOND_AREA = "검증2동"
DEVICE = f"Naver Weather Custom {AREA} 날씨"
SENSORS = ("현재온도", "미세먼지", "자외선등급")
UNRELATED_ROW = "강수확률"  # visible in the entity list until the search filters it out
WAIT_MS = 30_000
DESKTOP: ViewportSize = {"width": 1440, "height": 900}
PHONE: ViewportSize = {"width": 390, "height": 844}
ADD_INTEGRATION = re.compile(r"통합 ?구성 ?요소 추가")
CARD_NAME = "네이버 날씨 카드"
SEOUL = ZoneInfo("Asia/Seoul")
# HA 2026.10 opens its 둘러보기 home dashboard at "/", so the check uses its own storage-mode dashboard.
DASHBOARD = "naver-weather-check"
WEATHER_VIEW = f"/{DASHBOARD}/weather-check"


class StepError(RuntimeError):
    """A browser step did not reach its screen or a named text was not visible."""


def _post(
    api: APIRequestContext,
    path: str,
    *,
    data: dict[str, object] | None = None,
    form: dict[str, str | float | bool] | None = None,
    token: str | None = None,
) -> dict[str, object]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if form is not None:
        response = api.post(path, form=form, headers=headers, timeout=WAIT_MS)
    else:
        response = api.post(path, data=data or {}, headers=headers, timeout=WAIT_MS)
    if not response.ok:
        raise StepError(f"onboarding: POST {path} answered {response.status}")
    body = response.json() if response.body() else {}
    return body if isinstance(body, dict) else {}


def onboard(api: APIRequestContext, base: str) -> None:
    """Create the first user and finish onboarding so the frontend shows its login page."""
    client = base + "/"
    user = _post(
        api,
        "/api/onboarding/users",
        data={
            "client_id": client,
            "name": "검증 사용자",
            "username": USER,
            "password": PASSWORD,
            "language": "ko",
        },
    )
    token = _post(
        api,
        "/auth/token",
        form={
            "grant_type": "authorization_code",
            "code": str(user["auth_code"]),
            "client_id": client,
        },
    )
    access = str(token["access_token"])
    for step in ("core_config", "analytics"):
        _post(api, f"/api/onboarding/{step}", token=access)
    _post(
        api,
        "/api/onboarding/integration",
        data={"client_id": client, "redirect_uri": base + "/?auth_callback=1"},
        token=access,
    )


def see(locator: Locator, text: str, screen: str) -> None:
    """Fail the step with the text in the reason unless it becomes visible within 30 s."""
    try:
        expect(locator.filter(visible=True).first).to_be_visible(timeout=WAIT_MS)
    except AssertionError as err:
        raise StepError(f"{screen}: '{text}' not visible") from err


def unseen(locator: Locator, text: str, screen: str) -> None:
    """Fail the step with the text in the reason unless no match is visible within 30 s."""
    try:
        expect(locator.filter(visible=True)).to_have_count(0, timeout=WAIT_MS)
    except AssertionError as err:
        raise StepError(f"{screen}: '{text}' still visible") from err


def see_text(page: Page, text: str, screen: str, *, exact: bool = False) -> None:
    see(page.get_by_text(text, exact=exact), text, screen)


def see_field_value(page: Page, label: str, value: str, screen: str) -> None:
    """Wait until a visible field labelled `label` holds `value` (editable device names)."""
    deadline = time.monotonic() + WAIT_MS / 1000
    while time.monotonic() < deadline:
        for box in page.get_by_role("textbox", name=label).all():
            if box.is_visible() and box.input_value() == value:
                return
        page.wait_for_timeout(500)
    raise StepError(f"{screen}: '{value}' not visible")


class Shots:
    def __init__(self, out: Path) -> None:
        self.out = out

    def take(self, page: Page, name: str) -> None:
        page.wait_for_timeout(1000)
        page.screenshot(path=str(self.out / f"{name}.png"), full_page=True)

    def card(self, card: Locator, name: str) -> None:
        card.page.wait_for_timeout(1000)
        card.screenshot(path=str(self.out / f"{name}.png"))


def accept_http_config(page: Page) -> None:
    """Confirm HA 2026.10's new-HTTP-settings dialog when it appears; skip it otherwise."""
    title = page.get_by_text("새 HTTP 서버 구성 확인")
    try:
        title.wait_for(timeout=8000)
    except Exception:
        return
    page.get_by_role("button", name="확인", exact=True).click()
    title.wait_for(state="hidden", timeout=WAIT_MS)


def login(page: Page, base: str, shots: Shots | None = None) -> None:
    page.goto(base + "/")
    user = page.get_by_label("사용자 이름")
    password = page.locator('input[type="password"]')
    see(user, "사용자 이름", "login")
    see(password, "비밀번호", "login")
    user.fill(USER)
    password.fill(PASSWORD)
    if shots:
        shots.take(page, "00-login")
    page.get_by_role("button", name="로그인").click()
    page.wait_for_url(lambda url: "auth" not in url, timeout=WAIT_MS)
    if shots:
        # The phone-width touch context has its sidebar (and "설정") collapsed; its card steps follow.
        see_text(page, "설정", "home", exact=True)
        shots.take(page, "01-home")


def steps(page: Page, base: str, shots: Shots) -> None:
    login(page, base, shots)
    page.goto(base + "/config/integrations/dashboard")
    add = page.get_by_role("button", name=ADD_INTEGRATION)
    see(add, "통합 구성 요소 추가", "integrations")
    accept_http_config(page)
    shots.take(page, "02-integrations")

    add.click()
    page.wait_for_timeout(1500)
    page.keyboard.type("Naver")
    see_text(page, "Naver Weather Custom", "integration search")
    shots.take(page, "03-search")
    page.get_by_text("Naver Weather Custom").filter(visible=True).first.click()

    screen = "config flow user step"
    see_text(page, "네이버 날씨 설정하기", screen, exact=True)
    see_text(page, "네이버 날씨를 추가하시겠습니까?", screen)
    area = page.get_by_role("textbox", name=re.compile("지역"))
    see(area, "지역 : 날씨를 알고싶은 지역의 이름", screen)
    see_text(page, "주간예보에 오늘날씨 포함", screen)
    area.fill(AREA)
    shots.take(page, "04-flow-user")
    page.get_by_role("button", name=re.compile("^(확인|제출)$")).click()

    screen = "config flow device step"
    see_text(page, "이름 지정 및 할당", screen)
    see_field_value(page, "기기 이름", DEVICE, screen)
    finish = page.get_by_role("button", name="건너뛰고 완료")
    see(finish, "건너뛰고 완료", screen)
    shots.take(page, "05-flow-device")
    finish.click()

    page.goto(base + "/config/integrations/integration/naver_weather_custom")
    see_text(page, "1개 기기", "Naver Weather Custom integration page")
    shots.take(page, "06-integration")

    screen = "options flow"
    page.get_by_role("button", name=re.compile("^(구성|설정)$")).filter(visible=True).first.click()
    see_text(page, "네이버 날씨 사용자설정.", screen, exact=True)
    see_text(page, "주간예보에 오늘날씨 포함", screen)
    shots.take(page, "07-options")
    page.get_by_role("button", name=re.compile("^(확인|제출)$")).click()
    page.wait_for_timeout(1500)

    screen = f"device page {DEVICE}"
    page.goto(base + "/config/devices/dashboard")
    see_text(page, DEVICE, "device list", exact=True)
    page.get_by_text(DEVICE, exact=True).filter(visible=True).first.click()
    page.wait_for_url(re.compile(r"/config/devices/device/"), timeout=WAIT_MS)
    see_text(page, DEVICE, screen, exact=True)
    for name in SENSORS:
        see_text(page, name, screen, exact=True)
    shots.take(page, "08-device")
    page.set_viewport_size(PHONE)
    see_text(page, DEVICE, f"{screen} at 390 px", exact=True)
    shots.take(page, "09-device-390")
    page.set_viewport_size(DESKTOP)

    page.goto(base + "/config/entities?domain=naver_weather_custom")
    see_text(page, DEVICE, "entity list", exact=True)
    see_text(page, UNRELATED_ROW, "entity list", exact=True)
    shots.take(page, "10-entities")
    search = page.get_by_placeholder(re.compile("엔티티 검색"))
    see(search, "엔티티 검색", "entity list")
    search.fill(SENSORS[0])
    see_text(page, SENSORS[0], "entity search", exact=True)
    unseen(page.get_by_text(UNRELATED_ROW, exact=True), UNRELATED_ROW, "entity search")
    shots.take(page, "11-entity-search")


def add_second_entry(page: Page, base: str) -> None:
    screen = "second weather entry"
    page.goto(base + "/config/integrations/dashboard")
    page.get_by_role("button", name=ADD_INTEGRATION).click()
    page.wait_for_timeout(1500)
    page.keyboard.type("Naver")
    page.get_by_text("Naver Weather Custom", exact=True).filter(visible=True).first.click()
    see_text(page, "네이버 날씨 설정하기", screen, exact=True)
    page.get_by_role("textbox", name=re.compile("지역")).fill(SECOND_AREA)
    today = page.get_by_text("주간예보에 오늘날씨 포함", exact=True).filter(visible=True)
    see(today, "주간예보에 오늘날씨 포함", screen)
    today.first.click()
    page.get_by_role("button", name=re.compile("^(확인|제출)$")).click()
    see_field_value(page, "기기 이름", f"Naver Weather Custom {SECOND_AREA} 날씨", screen)
    page.get_by_role("button", name="건너뛰고 완료").click()


def weather_ids(page: Page) -> list[str]:
    """Read the weather entity IDs of the two synthetic devices from the frontend."""
    handle = page.wait_for_function(
        """(areas) => {
            const hass = document.querySelector("home-assistant")?.hass;
            if (!hass?.entities || !hass.devices) return null;
            const ids = areas.map((area) => Object.keys(hass.entities).find((id) => {
                const entry = hass.entities[id];
                return id.startsWith("weather.") && entry.platform === "naver_weather_custom"
                    && hass.devices[entry.device_id]?.name === `Naver Weather Custom ${area} 날씨`
                    && hass.states[id]?.state === "sunny";
            }));
            return ids.every(Boolean) ? ids : null;
        }""",
        arg=[AREA, SECOND_AREA],
        timeout=WAIT_MS,
    )
    return handle.json_value()


def create_dashboard(page: Page) -> None:
    page.evaluate(
        """(urlPath) => document.querySelector("home-assistant").hass.callWS({
            type: "lovelace/dashboards/create", url_path: urlPath, title: "날씨 검증",
            mode: "storage", show_in_sidebar: true, require_admin: false,
        })""",
        DASHBOARD,
    )


def save_dashboard(page: Page, cards: list[dict[str, object]]) -> None:
    page.evaluate(
        """([urlPath, cards]) => document.querySelector("home-assistant").hass.callWS({
            type: "lovelace/config/save", url_path: urlPath,
            config: { views: [{ title: "날씨 검증", path: "weather-check", type: "masonry", cards }] },
        })""",
        [DASHBOARD, cards],
    )


def open_weather_view(page: Page, base: str) -> None:
    """Open the check's dashboard and wait until HA's launch screen has left the page.

    The launch screen fades out over the dashboard (class 'removing') before HA removes it;
    a pointer or touch gesture made during the fade lands on it and the browser cancels it.
    """
    page.goto(base + WEATHER_VIEW)
    page.locator("#ha-launch-screen").wait_for(state="detached", timeout=WAIT_MS)


def add_card_from_picker(page: Page, base: str, shots: Shots) -> None:
    create_dashboard(page)
    save_dashboard(page, [])
    open_weather_view(page, base)
    page.get_by_role("button", name=re.compile(r"대시보드 (편집|수정)")).click()
    page.get_by_role("button", name=re.compile(r"카드 ?추가")).click()
    # HA 2026.10's add-card dialog opens on its entity tab; the card search is on the "카드별" tab.
    page.get_by_text("카드별", exact=True).filter(visible=True).first.click()
    picker = page.locator("hui-card-picker")
    picker.locator("input").filter(visible=True).first.fill(CARD_NAME)
    result = picker.get_by_text(CARD_NAME, exact=True)
    see(result, CARD_NAME, "card picker")
    shots.take(page, "12-card-picker")
    # Each picker entry is a div.card whose transparent .overlay receives the click.
    picker.locator("div.card", has=page.locator(".card-header", has_text=CARD_NAME)).locator(
        ".overlay"
    ).first.click()
    editor = page.locator("hui-dialog-edit-card")
    for label in ("날씨 엔티티", "표시 방식"):
        see(editor.get_by_text(label), label, "card editor")
    shots.take(page, "13-card-editor")
    editor.get_by_role("button", name="저장", exact=True).click()
    editor.wait_for(state="hidden", timeout=WAIT_MS)


def drag_points(locator: Locator) -> tuple[float, float, float]:
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    if box is None or box["width"] <= 50:
        raise StepError("swipe surface is absent or too narrow for a 40 px drag")
    return box["x"] + box["width"] - 4, box["x"] + 4, box["y"] + box["height"] / 2


def mouse_drag(page: Page, locator: Locator) -> None:
    start, end, y = drag_points(locator)
    page.mouse.move(start, y)
    page.mouse.down()
    page.mouse.move(end, y, steps=8)
    page.mouse.up()


def temperature(locator: Locator, text: str, screen: str) -> None:
    see(locator.get_by_text(text, exact=True), text, screen)


def absent_temperature(locator: Locator, text: str) -> None:
    expect(locator.get_by_text(text, exact=True)).to_have_count(0, timeout=WAIT_MS)


def verify_switched(current: Locator, hourly: Locator, screen: str) -> None:
    temperature(current, "71.5°", screen)
    temperature(hourly, "71.0°", screen)
    absent_temperature(current, "21.5°")
    absent_temperature(hourly, "21.0°")


def verify_hourly_page(page: Page, current: Locator, hourly: Locator) -> None:
    first_hour = hourly.locator(".hour-label").first.inner_text(timeout=WAIT_MS)
    next_hour = f"{(int(first_hour.removesuffix('시')) + 6) % 24:02d}시"
    mouse_drag(page, hourly)
    label = hourly.get_by_text(next_hour, exact=True)
    see(label, next_hour, "hourly page 2")
    box, grid = label.bounding_box(), hourly.bounding_box()
    if not (
        box and grid and grid["x"] <= box["x"] and grid["y"] <= box["y"]
        and box["x"] + box["width"] <= grid["x"] + grid["width"]
        and box["y"] + box["height"] <= grid["y"] + grid["height"]
    ):
        raise StepError("hourly page 2 label is outside the hourly grid")
    see(current.get_by_text("검증2동 · 검증시 검증2동", exact=True), SECOND_AREA, "hourly page 2")


def verify_daily(page: Page, daily: Locator, start_date: date, second_entity: str) -> None:
    first_label, second_label = "오늘", "내일"
    if datetime.now(SEOUL).date() != start_date:
        # Keep the fixture's dates and view it from the preceding day in this browser only.
        entity_date = page.evaluate(
            """async (id) => {
                const hass = document.querySelector("home-assistant").hass;
                const { entities } = await hass.callWS({type: "naver_weather_custom/card_entities", entity_id: id});
                return hass.states[entities.publicTimeW].state;
            }""",
            second_entity,
        )
        day_before = datetime.fromisoformat(entity_date).astimezone(SEOUL) - timedelta(days=1)
        page.clock.set_fixed_time(day_before)
        page.reload()
        first_label = "내일"
        second_label = "월화수목금토일"[(day_before + timedelta(days=2)).weekday()]
        print("Card C: Asia/Seoul date changed during the card steps; asserting 내일 for the first row.")
    first, second = daily.locator(".day").nth(0), daily.locator(".day").nth(1)
    for text in (first_label, "63.0°", "오전", "오후"):
        see(first.get_by_text(text, exact=True), text, "first daily row")
    see(second.get_by_text(second_label, exact=True), second_label, "second daily row")


def verify_cards(page: Page, width: int, shots: Shots, start_date: date, second_entity: str) -> None:
    cards = page.locator("naver-weather-card")
    card_a, card_b, card_c = (cards.nth(index) for index in range(3))
    current = card_a.locator(".current-section")
    hourly = card_a.locator(".hourly-grid")
    humidity = current.get_by_role("button", name=re.compile("습도"))
    temperature(current, "21.5°", "card A")
    temperature(hourly, "21.0°", "card A")
    for text in ("습도", "체감", "미세-좋음", "1시간 강수량"):
        see(current.get_by_text(text), text, "card A")
    shots.card(card_a, f"card-a-first-{width}")

    temperature(current, "21.5°", "card A before mouse swipe")
    mouse_drag(page, current.locator(".current-temperature-value"))
    verify_switched(current, hourly, "card A after mouse swipe")
    see(current.get_by_text("검증2동 · 검증시 검증2동", exact=True), SECOND_AREA, "card A")
    # HA's more-info dialog heads every entity of the integration with its device name.
    more_info = page.locator("ha-more-info-dialog")
    dialog = more_info.get_by_text(re.compile("Naver Weather Custom"))
    unseen(dialog, "more-info dialog", "card A after mouse swipe")
    shots.card(card_a, f"card-a-second-{width}")
    verify_hourly_page(page, current, hourly)
    # A more-info dialog that renders late after the swipe would show up by now.
    unseen(dialog, "more-info dialog", "card A after hourly page drag")
    shots.card(card_a, f"card-a-hourly-page-2-{width}")

    humidity.click()
    see(dialog, "Naver Weather Custom", "more-info dialog")
    see(more_info.get_by_text("현재습도"), "현재습도", "more-info dialog")
    page.keyboard.press("Escape")
    unseen(dialog, "more-info dialog", "card A after closing more-info")

    button_hourly = card_b.locator(".hourly-grid")
    temperature(button_hourly, "21.0°", "card B")
    expect(card_b.locator(".daily-section")).to_have_count(0)
    shots.card(card_b, f"card-b-first-{width}")
    temperature(button_hourly, "21.0°", "card B before button switch")
    card_b.get_by_role("button", name=SECOND_AREA, exact=True).click()
    temperature(button_hourly, "71.0°", "card B after button switch")
    absent_temperature(button_hourly, "21.0°")
    shots.card(card_b, f"card-b-second-{width}")

    expect(card_c.locator(".hourly-section")).to_have_count(0)
    daily = card_c.locator(".daily-list")
    verify_daily(page, daily, start_date, second_entity)
    shots.card(card_c, f"card-c-{width}")


def watch_card_errors(page: Page, errors: list[str]) -> None:
    def on_console(message: ConsoleMessage) -> None:
        if message.type == "error" and "naver-weather-card" in message.text:
            errors.append(message.text)

    def on_error(error: Error) -> None:
        if "naver-weather-card" in str(error.stack):
            errors.append(str(error.stack))

    page.on("console", on_console)
    page.on("pageerror", on_error)


def verify_touch(browser: Browser, base: str, shots: Shots, errors: list[str]) -> None:
    context = browser.new_context(viewport=PHONE, locale="ko-KR", timezone_id="Asia/Seoul",
                                  has_touch=True, is_mobile=True)
    try:
        page = context.new_page()
        watch_card_errors(page, errors)
        login(page, base)
        open_weather_view(page, base)
        card = page.locator("naver-weather-card").first
        current = card.locator(".current-section")
        hourly = card.locator(".hourly-grid")
        temperature(hourly, "21.0°", "card A before touch swipe")
        temperature(current, "21.5°", "card A before touch swipe")
        start, end, y = drag_points(current)
        session = context.new_cdp_session(page)
        session.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": start, "y": y}]})
        for step in range(1, 9):
            x = start + (end - start) * step / 8
            session.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y}]})
        session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        verify_switched(current, hourly, "card A after touch swipe")
        shots.card(card, "card-a-touch-390")
    finally:
        context.close()


def card_steps(page: Page, browser: Browser, base: str, shots: Shots, errors: list[str]) -> None:
    start_date = datetime.now(SEOUL).date()
    add_second_entry(page, base)
    first, second = weather_ids(page)
    add_card_from_picker(page, base, shots)
    common = {"type": "custom:naver-weather-card", "remember": False}
    save_dashboard(page, [
        {**common, "entities": [first, second], "mode": "both", "switcher": "swipe"},
        {**common, "entities": [first, second], "mode": "hourly", "switcher": "buttons"},
        {**common, "entities": [second], "mode": "daily", "show_current": False},
    ])
    for viewport in (DESKTOP, PHONE):
        page.set_viewport_size(viewport)
        open_weather_view(page, base)
        verify_cards(page, viewport["width"], shots, start_date, second)
    verify_touch(browser, base, shots, errors)
    if errors:
        raise StepError("Weather card browser errors:\n" + "\n".join(errors))


def run(base: str, out: Path) -> None:
    """Onboard through the API, then drive the screens; raise on the first failed step."""
    shots = Shots(out)
    with sync_playwright() as p:
        api = p.request.new_context(base_url=base)
        try:
            onboard(api, base)
        finally:
            api.dispose()
        browser = p.chromium.launch()
        try:
            context = browser.new_context(
                viewport=DESKTOP,
                locale="ko-KR",
                timezone_id="Asia/Seoul",
            )
            page = context.new_page()
            errors: list[str] = []
            watch_card_errors(page, errors)
            try:
                steps(page, base, shots)
                card_steps(page, browser, base, shots, errors)
            except BaseException:
                try:
                    page.screenshot(path=str(out / "failure.png"), full_page=True)
                except Exception:
                    pass
                raise
        finally:
            browser.close()
