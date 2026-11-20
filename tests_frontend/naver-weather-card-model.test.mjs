import assert from "node:assert/strict";
import test from "node:test";

import * as model from "../custom_components/naver_weather_custom/frontend/naver-weather-card-model.js";

const SEOUL = "Asia/Seoul";
const ENTITIES = ["weather.first", "weather.second"];

test("current states preserve the sensor precision while forecast numbers are formatted", () => {
  assert.equal(model.stateText("21.50"), "21.50");
  assert.equal(model.stateWithUnit("21.50", "°"), "21.50°");
  assert.equal(model.temperatureRange("24", "14.50"), "최고 24°, 최저 14.50°");
  assert.equal(model.temperatureRange("unknown", null), "최고 -, 최저 -");
  assert.equal(model.tempOneDecimal(-2), "-2.0°");
  assert.equal(model.tempOneDecimal("21.46"), "21.5°");
  assert.equal(model.percentText("55.6"), "56%");
  assert.equal(model.percentText(0), "0%");
  for (const value of [undefined, null, "", "unknown", "unavailable", "NaN", NaN, Infinity]) {
    assert.equal(model.stateText(value), "-");
    assert.equal(model.stateWithUnit(value, "°"), "-");
    assert.equal(model.tempOneDecimal(value), "-");
    assert.equal(model.percentText(value), "-");
  }
  for (const value of [" ", "맑음", -Infinity, false]) {
    assert.equal(model.tempOneDecimal(value), "-");
    assert.equal(model.percentText(value), "-");
  }
});

test("weather cast, grade colors, and sunrise or sunset use the original readings", () => {
  assert.equal(model.weathercastSentence("맑음, 어제보다 2.5° 낮아요, 남는 문장"), "어제보다 2.5° 낮아요");
  assert.equal(model.weathercastSentence("어제보다 2.5° 낮아요"), "어제보다 2.5° 낮아요");
  assert.equal(model.weathercastSentence("맑음,"), "-");
  assert.equal(model.weathercastSentence("unavailable"), "-");
  assert.deepEqual(["좋음", "보통", "나쁨", "매우나쁨", "모름", "constructor"].map(model.gradeColor),
    ["blue", "green", "orange", "red", null, null]);
  const rise = "2026-11-19T22:00:00Z";
  const set = "2026-11-20T08:18:00Z";
  assert.deepEqual(model.sunChip(rise, set, "2026-11-19T21:00:00Z", SEOUL),
    { text: "일출-07:00", icon: "mdi:weather-sunset-up" });
  assert.deepEqual(model.sunChip(rise, set, "2026-11-20T08:18:00Z", SEOUL),
    { text: "일몰-17:18", icon: "mdi:weather-sunset-down" });
  assert.equal(model.sunChip(rise, set, "2026-11-20T08:19:00Z", SEOUL).text, "일출-07:00");
  assert.equal(model.sunChip(undefined, undefined, "2026-11-20T08:19:00Z", SEOUL).text, "-");
});

test("forecast labels follow the local date, including a first item after today", () => {
  const beforeMidnight = "2026-11-20T14:59:00Z";
  const afterMidnight = "2026-11-20T15:01:00Z";
  const saturday = "2026-11-20T15:00:00Z";
  const sunday = "2026-11-21T15:00:00Z";
  assert.equal(model.formatHour("2026-11-20T00:00:00Z", SEOUL), "09시");
  assert.equal(model.formatHour(saturday, SEOUL), "00시");
  assert.equal(model.dayLabel(saturday, beforeMidnight, SEOUL), "내일");
  assert.equal(model.dayLabel(saturday, afterMidnight, SEOUL), "오늘");
  assert.equal(model.dayLabel(sunday, beforeMidnight, SEOUL), "일");
  assert.equal(model.dayLabel(sunday, afterMidnight, SEOUL), "내일");
  assert.equal(model.dayLabel("2026-11-19T15:00:00Z", afterMidnight, SEOUL), "금");
  assert.equal(model.dateLabel(saturday, SEOUL), "11.21.");
  assert.equal(model.dateLabel(saturday, "UTC"), "11.20.");
  assert.deepEqual(model.calendarDay(saturday, SEOUL), { number: 20778, weekday: 6, date: "11.21." });
  for (const value of ["invalid", null, undefined]) {
    assert.equal(model.formatHour(value, SEOUL), "-");
    assert.equal(model.dayLabel(value, afterMidnight, SEOUL), "-");
    assert.equal(model.dateLabel(value, SEOUL), "-");
  }
});

test("a configured workday list replaces the weekend coloring", () => {
  assert.equal(model.labelRed(0, undefined, 6), true);
  assert.equal(model.labelRed(1, undefined, 0), true);
  assert.equal(model.labelRed(2, undefined, 1), false);
  assert.equal(model.labelRed(1, ["on", "off"], 1), true);
  assert.equal(model.labelRed(0, ["on", "off"], 6), false);
  assert.equal(model.labelRed(3, ["off"], 0), false);
  assert.equal(model.labelRed(0, [], 6), false);
});

test("six-hour and five-day paging clamps the page after a shorter or empty message", () => {
  const rows = Array.from({ length: 13 }, (_, index) => index);
  for (const size of [6, 5]) {
    const result = model.pages(rows, size);
    assert.deepEqual(result.map((page) => page.length), [size, size, rows.length - size * 2]);
    assert.deepEqual(result.flat(), rows);
    assert.equal(model.pageAfterRows(1, 13, size), 1);
    assert.equal(model.pageAfterRows(2, size + 1, size), 1);
    assert.equal(model.pageAfterRows(2, 0, size), 0);
    assert.deepEqual(model.pages([], size), []);
  }
});

test("card picker selects the first visible Naver weather entity by entity ID", () => {
  assert.deepEqual(model.stubConfig({
    "weather.second": { platform: "naver_weather_custom" },
    "sensor.naver": { platform: "naver_weather_custom" },
    "weather.a_foreign": { platform: "another_integration" },
    "weather.a_hidden": { platform: "naver_weather_custom", hidden: true },
    "weather.first": { platform: "naver_weather_custom", hidden: false },
  }), { entities: ["weather.first"] });
  assert.deepEqual(model.stubConfig({}), { entities: [] });
  assert.deepEqual(model.cardDescriptor(), {
    type: "naver-weather-card", name: "네이버 날씨 카드",
    description: "여러 지역의 현재 날씨와 시간별·일별 예보를 표시합니다.", preview: true,
  });
});

test("editor schema offers the eight Korean fields and configuration defaults", () => {
  const { schema, computeLabel } = model.configForm();
  assert.deepEqual(schema.map(({ name }) => name),
    ["entities", "mode", "show_current", "hours", "days", "switcher", "remember", "icon_path"]);
  assert.deepEqual(schema.map(computeLabel), [
    "날씨 엔티티", "표시 방식", "현재 날씨 표시", "시간별 개수",
    "일별 일수", "지역 전환", "마지막 지역 기억", "아이콘 폴더",
  ]);
  assert.deepEqual(schema[0].selector.entity, {
    filter: [{ domain: "weather", integration: "naver_weather_custom" }], multiple: true,
  });
  assert.deepEqual(schema[1].selector.select.options, [
    { value: "hourly", label: "시간별" }, { value: "daily", label: "일별" }, { value: "both", label: "시간별+일별" },
  ]);
  assert.deepEqual(schema[5].selector.select.options, [
    { value: "swipe", label: "슬라이드" }, { value: "buttons", label: "버튼" },
  ]);
  assert.deepEqual(schema[3].selector.number, { min: 1, max: 24, mode: "box" });
  assert.deepEqual(schema[4].selector.number, { min: 1, max: 10, mode: "box" });
  assert.deepEqual(model.validateConfig({ entities: ENTITIES }), {
    entities: ENTITIES, mode: "both", show_current: true, hours: 18, days: 10,
    switcher: "swipe", remember: true,
  });
  for (const invalid of [
    { entities: [] }, { entities: ["sensor.first"] }, { entities: [null] }, { mode: "invalid" },
    { mode: "toString" }, { switcher: "invalid" }, { hours: 0 }, { hours: 25 }, { hours: 1.5 },
    { days: 0 }, { days: 11 }, { days: "5" },
  ]) {
    assert.throws(() => model.validateConfig({ entities: ENTITIES, ...invalid }), /[가-힣]/);
  }
  assert.throws(() => model.validateConfig({}), /[가-힣]/);
});

test("pictures choose a same-origin named file or a Home Assistant icon", () => {
  const path = "/local/icons/naver_weather";
  for (const value of [path, path + "/", "", undefined, null, "/"]) {
    assert.doesNotThrow(() => model.validateConfig({ entities: ENTITIES, icon_path: value }));
  }
  for (const value of ["http://x", "//x", "x/y", "/a/../b", "/a/%2e%2e/b", "/a?x", "/a\\b", "/a\n", true]) {
    assert.throws(() => model.validateConfig({ entities: ENTITIES, icon_path: value }), /[가-힣]/);
    assert.equal(model.iconUrl(value, "wt1"), null);
  }
  assert.equal(model.iconUrl(path + "/", "wt12"), path + "/icon_flat_wt12.svg");
  assert.deepEqual(model.picture(path, "wt1", "sunny"), { src: path + "/icon_flat_wt1.svg" });
  assert.deepEqual(model.hourlyPicture(path, { weathertype_hour: "wt5", condition: "sunny", weathertype: "wt1" }),
    { src: path + "/icon_flat_wt5.svg" });
  assert.deepEqual(model.picture(path, "wt100", "snowy-rainy"), { icon: "mdi:weather-snowy-rainy" });
  assert.deepEqual(model.picture("", "wt4", "clear-night"), { icon: "mdi:weather-night" });
  for (const value of [null, undefined, "", "unknown", "unavailable"]) {
    assert.deepEqual(model.picture(path, null, value), { text: "-" });
  }
  for (const [condition, name] of Object.entries({
    sunny: "sunny", "clear-night": "night", partlycloudy: "partly-cloudy", cloudy: "cloudy",
    rainy: "rainy", pouring: "pouring", snowy: "snowy", "snowy-rainy": "snowy-rainy",
    fog: "fog", lightning: "lightning", windy: "cloudy", toString: "cloudy",
  })) {
    assert.equal(model.conditionIcon(condition), "mdi:weather-" + name);
  }
});

test("remembered locations take precedence over user defaults and labels remove the device prefix", () => {
  assert.equal(model.startEntity(ENTITIES, "weather.second", { user: "weather.first" }, "user"), "weather.second");
  assert.equal(model.startEntity(ENTITIES, "weather.gone", { user: "weather.second" }, "user"), "weather.second");
  assert.equal(model.startEntity(ENTITIES, null, { user: "weather.gone" }, "user"), "weather.first");
  assert.equal(model.startEntity(ENTITIES, null, {}, "constructor"), "weather.first");
  assert.equal(model.locationLabel("기기 이름 현재 위치", "기기 이름", "검증시 검증구"), "현재 위치 · 검증시 검증구");
  assert.equal(model.locationLabel("기기 이름 검증동", "기기 이름", "검증동"), "검증동");
  assert.equal(model.locationLabel("검증2동", "기기 이름", "unavailable"), "검증2동");
});

test("current-weather tap targets use the integration's companion IDs", () => {
  const targets = {
    temperature: "NowTemp", weather: "NowWeather", cast: "WeatherCast", rainfall: "Rainfall",
    humidity: "Humidity", feel: "TodayFeelTemp", wind: "WindSpeed", fine: "FineDust",
    ultraFine: "UltraFineDust", uv: "TodayUVGrade",
  };
  const entities = Object.fromEntries(Object.values(targets).map((key) => [key, "sensor." + key.toLowerCase()]));
  for (const [target, key] of Object.entries(targets)) {
    assert.equal(model.tapTarget(target, ENTITIES[0], entities), entities[key]);
  }
  assert.equal(model.tapTarget("picture", ENTITIES[0], entities), ENTITIES[0]);
  assert.equal(model.tapTarget("sun", ENTITIES[0], entities), "sun.sun");
  assert.equal(model.tapTarget("fine", ENTITIES[0], {}), undefined);
  assert.equal(model.tapTarget("hour", ENTITIES[0], entities), undefined);
});

test("current weather and each forecast section resolve their own states", () => {
  const current = (entitiesReply, entityState = "sunny", entityPresent = true) =>
    model.currentState({ entityPresent, entityState, entitiesReply });
  for (const reply of ["pending", "ok", "not_found", "error"]) {
    assert.equal(current(reply, undefined, false), "nodata");
    assert.equal(current(reply, "unavailable"), "nodata");
  }
  assert.equal(current("not_found"), "foreign");
  assert.equal(current("pending"), "loading");
  assert.equal(current("error"), "loading");
  assert.equal(current("ok"), "ready");
  assert.equal(current("ok", "unknown"), "ready");
  const rows = [{ temperature: 21 }];
  for (const state of ["nodata", "foreign", "loading"]) {
    for (const subscription of ["pending", "ok", "error"]) {
      assert.equal(model.forecastState({ current: state, subscription, messageReceived: true, rows }), state);
    }
  }
  const forecast = (subscription, messageReceived, data = rows) =>
    model.forecastState({ current: current("ok"), subscription, messageReceived, rows: data });
  assert.equal(forecast("error", true), "error");
  assert.equal(forecast("pending", true), "waiting");
  assert.equal(forecast("ok", false), "waiting");
  assert.equal(forecast("ok", true, []), "empty");
  assert.equal(forecast("ok", true), "rows");
});

test("a foreign or failed lookup and a forecast subscription failure can retry when due", () => {
  assert.equal(model.retryDue(undefined, 0), true);
  assert.equal(model.retryDue(0, 0), false);
  assert.equal(model.retryDue(0, 59999), false);
  assert.equal(model.retryDue(0, 60000), true);
  for (const reply of ["not_found", "error"]) {
    assert.equal(model.lookupRetryDue(reply, 0, 59999), false);
    assert.equal(model.lookupRetryDue(reply, 0, 60000), true);
  }
  assert.equal(model.lookupRetryDue("pending", 0, 60000), false);
  assert.equal(model.lookupRetryDue("ok", 0, 60000), false);
});

test("new generations dispose active and late subscriptions and reject stale callbacks", () => {
  const hourly = () => {};
  const daily = () => {};
  const initial = { number: 1, subscriptions: [] };
  const active = model.subscriptionResolved(initial, 1, hourly);
  assert.deepEqual(active.dispose, []);
  const location = model.nextGeneration(active.state);
  assert.deepEqual(location.dispose, [hourly]);
  assert.deepEqual(location.state, { number: 2, subscriptions: [] });
  assert.equal(model.isCurrent(location.state, 1), false);
  assert.equal(model.isCurrent(location.state, 2), true);
  assert.deepEqual(model.subscriptionResolved(location.state, 1, daily),
    { state: location.state, dispose: [daily] });
});

test("reconnect clears visible forecasts while keeping their page and active subscription", () => {
  const state = { number: 3, subscriptions: [() => {}] };
  const original = { hourly: { subscription: "ok", messageReceived: true, rows: [21], page: 1 } };
  const waiting = model.reconnectForecasts(original);
  assert.deepEqual(waiting.hourly, {
    subscription: "ok", messageReceived: false, rows: [], page: 1, reconnecting: true,
  });
  assert.equal(model.forecastState({ ...waiting.hourly, current: "ready" }), "waiting");
  assert.equal(model.forecastState({ ...waiting.hourly, current: "ready", subscription: "error" }), "waiting");
  assert.deepEqual(original.hourly.rows, [21]);
  assert.equal(model.isCurrent(state, 3), true);
  assert.equal(state.subscriptions.length, 1);
});
