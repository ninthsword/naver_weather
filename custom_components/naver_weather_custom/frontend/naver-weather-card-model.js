const CONDITIONS = {
  sunny: "mdi:weather-sunny",
  "clear-night": "mdi:weather-night",
  partlycloudy: "mdi:weather-partly-cloudy",
  cloudy: "mdi:weather-cloudy",
  rainy: "mdi:weather-rainy",
  pouring: "mdi:weather-pouring",
  snowy: "mdi:weather-snowy",
  "snowy-rainy": "mdi:weather-snowy-rainy",
  fog: "mdi:weather-fog",
  lightning: "mdi:weather-lightning",
};
const GRADES = { 좋음: "blue", 보통: "green", 나쁨: "orange", 매우나쁨: "red" };
const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];
const DAY_MS = 86_400_000;
const MODES = { hourly: "시간별", daily: "일별", both: "시간별+일별" };
const SWITCHERS = { swipe: "슬라이드", buttons: "버튼" };
const DEFAULTS = {
  mode: "both", show_current: true, hours: 18, days: 10, switcher: "swipe", remember: true,
};

export function stateText(value) {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value !== "string" || ["", "unknown", "unavailable", "undefined", "null", "NaN"].includes(value)) {
    return "-";
  }
  return value;
}

export function stateWithUnit(value, unit) {
  const text = stateText(value);
  return text === "-" ? text : text + unit;
}

export function temperatureRange(max, min) {
  return `최고 ${stateWithUnit(max, "°")}, 최저 ${stateWithUnit(min, "°")}`;
}

function forecastNumber(value, digits, unit) {
  if (typeof value !== "number" && !(typeof value === "string" && value.trim())) return "-";
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) + unit : "-";
}

export function tempOneDecimal(value) {
  return forecastNumber(value, 1, "°");
}

export function percentText(value) {
  return forecastNumber(value, 0, "%");
}

function asDate(value) {
  if (value == null || value === "") return null;
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? date : null;
}

function clockText(value, timeZone, options) {
  const date = asDate(value);
  return date && new Intl.DateTimeFormat("en-GB", {
    timeZone, hour: "2-digit", hourCycle: "h23", ...options,
  }).format(date);
}

export function formatHour(iso, timeZone) {
  const hour = clockText(iso, timeZone);
  return hour ? hour + "시" : "-";
}

export function calendarDay(value, timeZone) {
  const date = asDate(value);
  if (!date) return null;
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(date);
  const { year, month, day } = Object.fromEntries(parts.map(({ type, value }) => [type, value]));
  const midnight = new Date(`${year}-${month}-${day}T00:00:00Z`);
  return { number: midnight.getTime() / DAY_MS, weekday: midnight.getUTCDay(), date: `${month}.${day}.` };
}

export function dayLabel(iso, now, timeZone) {
  const day = calendarDay(iso, timeZone);
  if (!day) return "-";
  const offset = day.number - calendarDay(now, timeZone)?.number;
  if (offset === 0) return "오늘";
  if (offset === 1) return "내일";
  return WEEKDAYS[day.weekday];
}

export function dateLabel(iso, timeZone) {
  return calendarDay(iso, timeZone)?.date ?? "-";
}

export function gradeColor(grade) {
  return Object.hasOwn(GRADES, grade) ? GRADES[grade] : null;
}

export function sunChip(nextRising, nextSetting, now, timeZone) {
  const options = { minute: "2-digit" };
  const rising = clockText(nextRising, timeZone, options);
  const setting = clockText(nextSetting, timeZone, options);
  const current = clockText(now, timeZone, options);
  return rising && setting && current && rising < current && setting >= current
    ? { text: `일몰-${setting}`, icon: "mdi:weather-sunset-down" }
    : { text: rising ? `일출-${rising}` : "-", icon: "mdi:weather-sunset-up" };
}

export function weathercastSentence(value) {
  const text = stateText(value);
  return text.includes(",") ? stateText(text.split(",")[1].trim()) : text;
}

export function pages(items, size) {
  return Array.from({ length: Math.ceil(items.length / size) }, (_, page) =>
    items.slice(page * size, (page + 1) * size));
}

export function pageAfterRows(page, rowCount, size) {
  return Math.min(page, Math.max(0, Math.ceil(rowCount / size) - 1));
}

export function dragOffset(dx, index, count) {
  if (!Number.isFinite(dx)) return 0;
  const pastEnd = count <= 1 || (dx > 0 && index <= 0) || (dx < 0 && index >= count - 1);
  return pastEnd ? dx / 3 : dx;
}

export function settleTarget(dx, index, count) {
  const target = !Number.isFinite(dx) ? index : dx < -40 ? index + 1 : dx > 40 ? index - 1 : index;
  return Math.min(Math.max(target, 0), Math.max(count - 1, 0));
}

function validIconPath(value) {
  return typeof value === "string"
    && /^\/(?!\/)[A-Za-z0-9_./-]*$/.test(value)
    && !value.split("/").includes("..");
}

export function validateConfig(config) {
  const result = { ...DEFAULTS, ...config };
  if (!Array.isArray(result.entities) || !result.entities.length
      || [...result.entities].some((id) => typeof id !== "string" || !id.startsWith("weather."))) {
    throw new Error("날씨 엔티티를 하나 이상 선택하세요.");
  }
  if (typeof result.mode !== "string" || !Object.hasOwn(MODES, result.mode)) {
    throw new Error("표시 방식을 확인하세요.");
  }
  if (typeof result.switcher !== "string" || !Object.hasOwn(SWITCHERS, result.switcher)) {
    throw new Error("지역 전환 방식을 확인하세요.");
  }
  if (!Number.isInteger(result.hours) || result.hours < 1 || result.hours > 24) {
    throw new Error("시간별 개수는 1부터 24까지 입력하세요.");
  }
  if (!Number.isInteger(result.days) || result.days < 1 || result.days > 10) {
    throw new Error("일별 일수는 1부터 10까지 입력하세요.");
  }
  if (result.icon_path != null && result.icon_path !== "" && !validIconPath(result.icon_path)) {
    throw new Error("아이콘 폴더는 /로 시작하는 이 서버의 경로를 입력하세요.");
  }
  return result;
}

function options(labels) {
  return Object.entries(labels).map(([value, label]) => ({ value, label }));
}

export function configForm() {
  const labels = {
    entities: "날씨 엔티티", mode: "표시 방식", show_current: "현재 날씨 표시",
    hours: "시간별 개수", days: "일별 일수", switcher: "지역 전환",
    remember: "마지막 지역 기억", icon_path: "아이콘 폴더",
  };
  const helpers = {
    hours: "시간별 예보에 표시할 개수입니다.",
    days: "일별 예보에 표시할 일수입니다.",
  };
  return {
    schema: [
      {
        name: "entities", required: true,
        selector: { entity: { filter: [{ domain: "weather", integration: "naver_weather_custom" }], multiple: true } },
      },
      { name: "mode", default: DEFAULTS.mode, selector: { select: { options: options(MODES) } } },
      { name: "show_current", default: DEFAULTS.show_current, selector: { boolean: {} } },
      { name: "hours", default: DEFAULTS.hours, selector: { number: { min: 1, max: 24, mode: "box" } } },
      { name: "days", default: DEFAULTS.days, selector: { number: { min: 1, max: 10, mode: "box" } } },
      { name: "switcher", default: DEFAULTS.switcher, selector: { select: { options: options(SWITCHERS) } } },
      { name: "remember", default: DEFAULTS.remember, selector: { boolean: {} } },
      { name: "icon_path", selector: { text: {} } },
    ],
    computeLabel: ({ name }) => labels[name],
    computeHelper: ({ name }) => helpers[name],
  };
}

export function stubConfig(entities) {
  const ids = Object.keys(entities ?? {}).filter((id) => id.startsWith("weather.")
    && entities[id].platform === "naver_weather_custom" && !entities[id].hidden);
  return { entities: ids.sort().slice(0, 1) };
}

export function cardDescriptor() {
  return {
    type: "naver-weather-card",
    name: "네이버 날씨 카드",
    description: "여러 지역의 현재 날씨와 시간별·일별 예보를 표시합니다.",
    preview: true,
  };
}

export function iconUrl(path, code) {
  return validIconPath(path) && typeof code === "string" && /^wt[0-9]{1,2}$/.test(code)
    ? `${path.replace(/\/+$/, "")}/icon_flat_${code}.svg`
    : null;
}

export function conditionIcon(condition) {
  if (typeof condition !== "string" || !condition || condition === "unknown" || condition === "unavailable") {
    return null;
  }
  return Object.hasOwn(CONDITIONS, condition) ? CONDITIONS[condition] : CONDITIONS.cloudy;
}

export function picture(path, code, condition) {
  const src = iconUrl(path, code);
  const icon = conditionIcon(condition);
  return src ? { src } : icon ? { icon } : { text: "-" };
}

export function hourlyPicture(path, row) {
  return picture(path, row.weathertype_hour, row.condition);
}

export function startEntity(entities, remembered, users, userName) {
  if (entities.includes(remembered)) return remembered;
  const userEntity = users && Object.hasOwn(users, userName) ? users[userName] : null;
  return entities.includes(userEntity) ? userEntity : entities[0];
}

export function labelRed(offset, workdayStates, weekday) {
  return workdayStates == null ? weekday === 0 || weekday === 6 : workdayStates[offset] === "off";
}

export function locationLabel(entityName, deviceName, locationInfo) {
  const fullName = stateText(entityName);
  const prefix = deviceName ? deviceName + " " : "";
  const name = prefix && fullName.startsWith(prefix) ? fullName.slice(prefix.length) : fullName;
  const location = stateText(locationInfo);
  return location !== "-" && location !== name ? `${name} · ${location}` : name;
}

export function tapTarget(element, weatherId, entities) {
  const target = {
    picture: weatherId, temperature: entities.NowTemp, weather: entities.NowWeather,
    cast: entities.WeatherCast, rainfall: entities.Rainfall, humidity: entities.Humidity,
    feel: entities.TodayFeelTemp, wind: entities.WindSpeed, fine: entities.FineDust,
    ultraFine: entities.UltraFineDust, uv: entities.TodayUVGrade, sun: "sun.sun",
  };
  return Object.hasOwn(target, element) ? target[element] : undefined;
}

export function currentState({ entityPresent, entityState, entitiesReply }) {
  if (!entityPresent || entityState === "unavailable") return "nodata";
  if (entitiesReply === "not_found") return "foreign";
  return entitiesReply === "ok" ? "ready" : "loading";
}

export function forecastState({ current, subscription, messageReceived, rows, reconnecting }) {
  if (current !== "ready") return current;
  if (reconnecting) return "waiting";
  if (subscription === "error") return "error";
  if (subscription === "pending" || !messageReceived) return "waiting";
  return rows.length ? "rows" : "empty";
}

export function retryDue(lastAttemptMs, nowMs) {
  return lastAttemptMs == null || nowMs - lastAttemptMs >= 60_000;
}

export function lookupRetryDue(reply, lastAttemptMs, nowMs) {
  return (reply === "not_found" || reply === "error") && retryDue(lastAttemptMs, nowMs);
}

export function nextGeneration(previous) {
  return { state: { number: previous.number + 1, subscriptions: [] }, dispose: previous.subscriptions };
}

export function isCurrent(state, generation) {
  return generation === state.number;
}

export function subscriptionResolved(state, generation, unsubscribe) {
  return isCurrent(state, generation)
    ? { state: { ...state, subscriptions: [...state.subscriptions, unsubscribe] }, dispose: [] }
    : { state, dispose: [unsubscribe] };
}

export function reconnectForecasts(forecasts) {
  return Object.fromEntries(Object.entries(forecasts).map(([type, section]) => [
    type, { ...section, messageReceived: false, rows: [], reconnecting: true },
  ]));
}
