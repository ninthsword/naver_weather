const cardUrl = new URL(import.meta.url);
const modelUrl = new URL("./naver-weather-card-model.js", cardUrl);
modelUrl.search = cardUrl.search;
const model = await import(modelUrl.href);

const PAGE_SIZE = { hourly: 6, daily: 5 };
const SECTION_NAMES = { hourly: "시간별 예보", daily: "일별 예보" };
const STATE_TEXT = {
  nodata: "현재 데이터 없음",
  foreign: "이 엔티티는 네이버 날씨 통합의 날씨 엔티티가 아닙니다",
  loading: "불러오는 중",
  waiting: "예보 대기",
  empty: "예보 없음",
  error: "예보를 불러오지 못했습니다",
};
const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";
const ONSET_PX = 8;
const SUPPRESS_CLICK_PX = 40;
const FALLBACK_MS = 400;

const STYLE = `
  :host { display: block; }
  .body {
    --naver-warm: rgba(255, 87, 34, 1);
    --naver-cool: rgba(33, 150, 243, 1);
    padding: 10px;
    box-sizing: border-box;
    container-type: inline-size;
    color: var(--primary-text-color);
    font: inherit;
    overflow: hidden;
    overflow: clip;
  }
  .section { padding: 6px 0; min-width: 0; }
  .swipe { touch-action: pan-y; user-select: none; }
  .location-label {
    font-size: 15px;
    font-weight: 500;
    line-height: 1.4;
    text-align: center;
    overflow-wrap: anywhere;
  }
  .location-buttons, .chip-row, .dots {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-wrap: wrap;
    gap: 2px 8px;
  }
  .location-buttons { padding-bottom: 5px; }
  .button {
    border: 0;
    margin: 0;
    padding: 0;
    background: none;
    color: inherit;
    font: inherit;
    line-height: inherit;
    cursor: pointer;
  }
  .location-button {
    padding: 4px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 16px;
    max-width: 100%;
    overflow-wrap: anywhere;
  }
  .active-location { border-color: var(--primary-color); color: var(--primary-color); font-weight: 600; }
  .dots { gap: 2px; margin: 2px 0; }
  .dot { display: grid; place-items: center; width: 22px; height: 22px; }
  .dot-mark { width: 7px; height: 7px; border-radius: 50%; background: var(--secondary-text-color); opacity: .5; }
  .active-dot { background: var(--primary-color); opacity: 1; }
  .current-grid {
    display: grid;
    grid-template-columns: 25% 25% 50%;
    align-items: center;
    padding: 6px 0;
  }
  .current-picture, .current-temperature { text-align: center; }
  .current-picture-size {
    --mdc-icon-size: min(80px, 100%);
    width: min(80px, 100%);
    height: auto;
    aspect-ratio: 1;
    object-fit: contain;
    vertical-align: middle;
  }
  .current-temperature-value {
    display: block;
    font-size: clamp(22px, 10.5cqw, 42px);
    letter-spacing: -.045em;
    line-height: 1.12;
    white-space: nowrap;
  }
  .high-low { display: block; font-size: 12px; color: var(--secondary-text-color); }
  .conditions { display: grid; justify-items: start; line-height: 1.35; padding-inline-start: 8px; }
  .condition { font-size: 20px; }
  .cast { font-size: 15px; }
  .condition, .cast { text-align: start; overflow-wrap: anywhere; }
  .chip { display: inline-flex; align-items: center; gap: 4px; min-height: 27px; font-size: 12px; }
  .chip-icon { --mdc-icon-size: 17px; }
  .chip-row { column-gap: clamp(4px, 2cqw, 12px); }
  .rainfall { text-align: start; color: var(--secondary-text-color); }
  .hourly-grid, .daily-list { display: block; overflow: hidden; overflow: clip; touch-action: pan-y; }
  .pages-track { display: flex; align-items: flex-start; direction: ltr; touch-action: pan-y; transition: transform 300ms ease-out; }
  .hourly-page { flex: 0 0 100%; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); }
  .daily-page { flex: 0 0 100%; display: block; }
  .slide-content { transition: transform var(--slide-ms, 200ms) ease-out; }
  @media (prefers-reduced-motion: reduce) {
    .pages-track, .slide-content { transition-duration: 0s; }
  }
  .hour, .day-cell { display: grid; justify-items: center; align-items: center; text-align: center; }
  .hour { gap: 2px; font-size: 12px; line-height: 1.2; }
  .unit { font-size: 9px; color: var(--secondary-text-color); }
  .forecast-picture { --mdc-icon-size: 30px; width: 30px; max-width: 100%; height: 30px; object-fit: contain; }
  .day {
    display: grid;
    grid-template-columns: 18% 18% 16% 16% 16% 16%;
    align-items: center;
    min-height: 46px;
    font-size: 12px;
    line-height: 1.35;
  }
  .warm, .deep-orange { color: var(--naver-warm); }
  .cool, .blue { color: var(--naver-cool); }
  .green { color: #4caf50; }
  .orange { color: #ff9800; }
  .red { color: #f44336; }
  .status { color: var(--secondary-text-color); text-align: center; padding: 8px 0; font-size: 13px; }
`;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  if (tag === "button") node.type = "button";
  return node;
}

function icon(name, className) {
  const node = element("ha-icon", className);
  node.setAttribute("icon", name);
  node.setAttribute("aria-hidden", "true");
  return node;
}

function pictureNode(picture, className) {
  if (picture.src) {
    const image = element("img", className);
    image.alt = "";
    image.src = picture.src;
    return image;
  }
  return picture.icon ? icon(picture.icon, className) : element("span", "", picture.text);
}

function pageTransform(page, offset) {
  return `translateX(calc(${-page * 100}% + ${offset}px))`;
}

function reducedMotion() {
  return Boolean(window.matchMedia?.(REDUCED_MOTION).matches);
}

function dots(count, active, label, choose) {
  const row = element("div", "dots");
  for (let index = 0; index < count; index++) {
    const dot = element("button", "button dot");
    dot.setAttribute("aria-label", `${label} ${index + 1}`);
    dot.setAttribute("aria-pressed", String(index === active));
    dot.append(element("span", index === active ? "dot-mark active-dot" : "dot-mark"));
    dot.addEventListener("click", () => choose(index));
    row.append(dot);
  }
  return row;
}

class NaverWeatherCard extends HTMLElement {
  #hass;
  #config;
  #body;
  #connection;
  #entityId;
  // One entry per configured location, filled in the background, so a switch renders at once.
  #entries = new Map();
  #nextToken = 0;
  #heightRecord = null;
  #renderFrame = 0;
  #renderInputs = [];
  #drag;
  #slides = {};
  #suppressClick = false;

  constructor() {
    super();
    const root = this.attachShadow({ mode: "open" });
    const style = element("style", "", STYLE);
    const card = element("ha-card");
    this.#body = element("div", "body");
    card.append(this.#body);
    root.append(style, card);

    card.addEventListener("pointerdown", this.#startDrag);
    this.addEventListener("click", (event) => {
      if (this.#suppressClick && event.detail !== 0) {
        event.preventDefault();
        event.stopImmediatePropagation();
        this.#suppressClick = false;
      }
    }, true);
  }

  static getStubConfig(hass) {
    return model.stubConfig(hass.entities);
  }

  static getConfigForm() {
    return model.configForm();
  }

  setConfig(config) {
    this.#config = model.validateConfig(config);
    for (const slide of Object.values(this.#slides)) slide.drop();
    this.#disposeEntries();
    this.#entityId = undefined;
    this.#sync();
  }

  set hass(hass) {
    this.#hass = hass;
    if (this.isConnected) this.#listenToConnection(hass.connection);
    this.#sync();
  }

  connectedCallback() {
    this.#listenToConnection(this.#hass?.connection);
    this.#sync();
  }

  disconnectedCallback() {
    this.#listenToConnection(undefined);
    this.#disposeEntries();
    this.#cancelDrag();
    for (const slide of Object.values(this.#slides)) slide.drop();
    cancelAnimationFrame(this.#renderFrame);
    this.#renderFrame = 0;
    this.#renderInputs = [];
    this.#body.replaceChildren();
  }

  #listenToConnection(connection) {
    if (this.#connection === connection) return;
    this.#connection?.removeEventListener("ready", this.#onReconnect);
    this.#connection = connection;
    connection?.addEventListener("ready", this.#onReconnect);
  }

  #onReconnect = () => {
    this.#cancelDrag();
    for (const entry of this.#entries.values()) entry.forecasts = model.reconnectForecasts(entry.forecasts);
    this.#scheduleRender();
  };

  #unsubscribe(unsubscribes) {
    for (const unsubscribe of unsubscribes) {
      try {
        Promise.resolve(unsubscribe()).catch(() => {});
      } catch {
        // HA can already have dropped the connection during removal.
      }
    }
  }

  #disposeEntry(entry) {
    this.#entries.delete(entry.id);
    this.#unsubscribe(entry.subscriptions);
    entry.subscriptions = [];
  }

  #disposeEntries() {
    for (const entry of [...this.#entries.values()]) this.#disposeEntry(entry);
    this.#heightRecord = null;
    this.#body.style.removeProperty("min-height");
  }

  #isCurrent(entry, token) {
    return this.#entries.get(entry.id)?.token === token;
  }

  get #entry() {
    return this.#entries.get(this.#entityId);
  }

  get #storageKey() {
    return `naver-weather-card:${JSON.stringify(this.#config.entities)}`;
  }

  #initialEntity() {
    let remembered;
    if (this.#config.remember) {
      try {
        remembered = window.localStorage.getItem(this.#storageKey);
      } catch {
        // Storage is optional in HA's embedded frontend as well.
      }
    }
    return model.startEntity(this.#config.entities, remembered, this.#config.users, this.#hass.user?.name);
  }

  #chooseLocation(index) {
    const id = this.#config.entities[index];
    if (!id || id === this.#entityId) return;
    // A drag still held from the previous location must not override this choice on release.
    this.#cancelDrag();
    this.#entityId = id;
    if (this.#config.remember) {
      try {
        window.localStorage.setItem(this.#storageKey, id);
      } catch {
        // The selection still works for this visit.
      }
    }
    const entry = this.#entry;
    if (entry) {
      entry.forecasts = Object.fromEntries(Object.entries(entry.forecasts).map(([type, forecast]) => [
        type, { ...forecast, page: 0 },
      ]));
    }
    this.#scheduleRender();
  }

  get #weather() {
    return this.#hass.states[this.#entityId];
  }

  #availabilityOf(id) {
    const weather = this.#hass.states[id];
    return !weather ? "missing" : weather.state === "unavailable" ? "unavailable" : "available";
  }

  #currentStateOf(entry) {
    const weather = this.#hass.states[entry.id];
    return model.currentState({
      entityPresent: Boolean(weather),
      entityState: weather?.state,
      entitiesReply: entry.entitiesReply,
    });
  }

  #sync() {
    if (!this.isConnected || !this.#hass || !this.#config) return;
    this.#entityId ??= this.#initialEntity();
    for (const id of this.#config.entities) {
      const entry = this.#entries.get(id);
      const availability = this.#availabilityOf(id);
      if (!entry || entry.availability !== availability) {
        if (entry) this.#disposeEntry(entry);
        if (id === this.#entityId) this.#cancelDrag();
        void this.#lookupEntities(this.#createEntry(id, availability));
        continue;
      }
      if (model.lookupRetryDue(entry.entitiesReply, entry.lookupAttempt, Date.now())) {
        void this.#lookupEntities(entry);
      } else if (entry.entitiesReply === "ok") {
        // A companion entity that was shown before has gone (renamed or removed): ask again,
        // keeping the shown data meanwhile. Entities never present (disabled) do not trigger this.
        entry.seen ??= new Set();
        let gone = false;
        for (const entityId of Object.values(entry.entities)) {
          if (this.#hass.states[entityId]) entry.seen.add(entityId);
          else if (entry.seen.has(entityId)) gone = true;
        }
        if (gone && model.retryDue(entry.lookupAttempt, Date.now())) {
          entry.seen = new Set();
          void this.#lookupEntities(entry, { keepShown: true });
        }
      }
      this.#subscribeForecasts(entry);
    }
    this.#scheduleRender();
  }

  #createEntry(id, availability) {
    const types = this.#config.mode === "both" ? ["hourly", "daily"] : [this.#config.mode];
    const entry = {
      id,
      token: ++this.#nextToken,
      availability,
      entities: {},
      entitiesReply: "pending",
      lookupAttempt: undefined,
      forecasts: Object.fromEntries(types.map((type) => [
        type, { subscription: "pending", messageReceived: false, rows: [], page: 0 },
      ])),
      subscriptions: [],
    };
    this.#entries.set(id, entry);
    return entry;
  }

  async #lookupEntities(entry, { keepShown = false } = {}) {
    const { token } = entry;
    entry.lookupAttempt = Date.now();
    if (!keepShown) entry.entitiesReply = "pending";
    try {
      const reply = await this.#hass.callWS({
        type: "naver_weather_custom/card_entities", entity_id: entry.id,
      });
      if (!this.#isCurrent(entry, token)) return;
      entry.entities = reply.entities;
      entry.entitiesReply = "ok";
    } catch (error) {
      if (!this.#isCurrent(entry, token)) return;
      entry.entitiesReply = error?.code === "not_found" ? "not_found" : "error";
    }
    this.#subscribeForecasts(entry);
    this.#scheduleRender();
  }

  // Only an entry whose weather entity is present, available and recognised subscribes.
  #subscribeForecasts(entry) {
    if (this.#currentStateOf(entry) !== "ready") return;
    for (const [type, forecast] of Object.entries(entry.forecasts)) {
      if (forecast.lastAttempt == null
          || (forecast.subscription === "error" && model.retryDue(forecast.lastAttempt, Date.now()))) {
        void this.#subscribe(entry, type);
      }
    }
  }

  #updateForecast(entry, type, changes) {
    entry.forecasts = { ...entry.forecasts, [type]: { ...entry.forecasts[type], ...changes } };
    this.#scheduleRender();
  }

  async #subscribe(entry, type) {
    const { token } = entry;
    this.#updateForecast(entry, type, { subscription: "pending", lastAttempt: Date.now() });
    try {
      const unsubscribe = await this.#connection.subscribeMessage((message) => {
        if (!this.#isCurrent(entry, token)) return;
        const limit = type === "hourly" ? this.#config.hours : this.#config.days;
        const rows = Array.isArray(message?.forecast) ? message.forecast.slice(0, limit) : [];
        const page = model.pageAfterRows(entry.forecasts[type].page, rows.length, PAGE_SIZE[type]);
        this.#updateForecast(entry, type, { messageReceived: true, reconnecting: false, rows, page });
      }, { type: "weather/subscribe_forecast", entity_id: entry.id, forecast_type: type });
      if (!this.#isCurrent(entry, token)) {
        this.#unsubscribe([unsubscribe]);
        return;
      }
      entry.subscriptions.push(unsubscribe);
      this.#updateForecast(entry, type, { subscription: "ok" });
    } catch {
      if (this.#isCurrent(entry, token)) {
        this.#updateForecast(entry, type, { subscription: "error", reconnecting: false });
      }
    }
  }

  #choosePage(type, page) {
    const entry = this.#entry;
    const forecast = entry.forecasts[type];
    const next = model.pageAfterRows(Math.max(0, page), forecast.rows.length, PAGE_SIZE[type]);
    if (next !== forecast.page) this.#updateForecast(entry, type, { page: next });
  }

  #startDrag = (event) => {
    this.#suppressClick = false;
    if (!event.isPrimary || event.button !== 0 || this.#drag) return;
    const surface = event.target.closest("[data-swipe]")?.dataset.swipe;
    if (!surface) return;
    this.#finishSlides();
    this.#drag = { id: event.pointerId, x: event.clientX, y: event.clientY, surface, onset: false, dx: 0 };
    window.addEventListener("pointermove", this.#moveDrag);
    window.addEventListener("pointerup", this.#finishDrag);
    window.addEventListener("pointercancel", this.#abortDrag);
  };

  #dragFrame(surface) {
    if (surface === "location") {
      const node = this.#body.querySelector(".slide-content");
      const { entities } = this.#config;
      return node && { node, index: entities.indexOf(this.#entityId), count: entities.length };
    }
    // Use the track as drawn: rows that changed since the last render are drawn after the drag.
    const node = this.#body.querySelector(`.${surface}-section .pages-track`);
    return node && { node, index: Number(node.dataset.page), count: node.childElementCount };
  }

  #dragTransform(surface, index, offset) {
    return surface === "location" ? `translateX(${offset}px)` : pageTransform(index, offset);
  }

  #moveDrag = (event) => {
    const drag = this.#drag;
    if (!drag || drag.id !== event.pointerId) return;
    const dx = event.clientX - drag.x;
    if (!drag.onset) {
      if (Math.abs(dx) <= ONSET_PX || Math.abs(dx) <= Math.abs(event.clientY - drag.y)) return;
      drag.onset = true;
      drag.frame = this.#dragFrame(drag.surface);
    }
    drag.dx = dx;
    if (!drag.frame) return;
    const { node, index, count } = drag.frame;
    node.style.transition = "none";
    node.style.transform = this.#dragTransform(drag.surface, index, model.dragOffset(dx, index, count));
  };

  #finishDrag = (event) => {
    const drag = this.#drag;
    if (!drag || drag.id !== event.pointerId) return;
    this.#moveDrag(event);
    this.#cancelDrag();
    if (!drag.onset) return;
    this.#suppressClick = Math.abs(drag.dx) > SUPPRESS_CLICK_PX;
    if (!drag.frame) return;
    const { node, index, count } = drag.frame;
    const target = model.settleTarget(drag.dx, index, count);
    if (drag.surface !== "location") {
      this.#slidePage(drag.surface, target);
    } else if (target !== index) {
      this.#slideLocation(target);
    } else {
      this.#slide("location", node, "translateX(0px)", 300);
    }
  };

  #abortDrag = (event) => {
    const drag = this.#drag;
    if (!drag || drag.id !== event.pointerId) return;
    this.#cancelDrag();
    if (!drag.frame) return;
    const { node, index } = drag.frame;
    this.#slide(drag.surface, node, this.#dragTransform(drag.surface, index, 0), 300);
  };

  #cancelDrag = () => {
    if (!this.#drag) return;
    this.#drag = undefined;
    window.removeEventListener("pointermove", this.#moveDrag);
    window.removeEventListener("pointerup", this.#finishDrag);
    window.removeEventListener("pointercancel", this.#abortDrag);
    this.#scheduleRender();
  };

  // One running slide per key ("location", "hourly", "daily"); it ends on its own transform's
  // transitionend or after FALLBACK_MS, and finish(true) jumps it to its target at once.
  #slide(key, node, transform, ms, done = () => this.#scheduleRender()) {
    this.#slides[key]?.finish(true);
    const reduced = reducedMotion();
    void getComputedStyle(node).transform;
    node.style.transition = reduced ? "none" : "";
    node.style.setProperty("--slide-ms", `${ms}ms`);
    node.style.transform = transform;
    const onEnd = (event) => {
      if (event.target === node && event.propertyName === "transform") slide.finish(false);
    };
    const slide = {
      drop: () => {
        if (this.#slides[key] !== slide) return false;
        delete this.#slides[key];
        clearTimeout(slide.timer);
        node.removeEventListener("transitionend", onEnd);
        return true;
      },
      finish: (jump) => {
        if (!slide.drop()) return;
        if (jump) node.style.transition = "none";
        done(jump);
      },
    };
    this.#slides[key] = slide;
    if (reduced || !parseFloat(getComputedStyle(node).transitionDuration)) {
      slide.finish(false);
      return;
    }
    node.addEventListener("transitionend", onEnd);
    slide.timer = setTimeout(() => slide.finish(false), FALLBACK_MS);
  }

  #finishSlides() {
    for (const slide of Object.values(this.#slides)) slide.finish(true);
  }

  #slidePage(type, page) {
    this.#choosePage(type, page);
    const track = this.#body.querySelector(`.${type}-section .pages-track`);
    if (track) this.#slide(type, track, pageTransform(this.#entry.forecasts[type].page, 0), 300);
  }

  #pickPage(type, page) {
    this.#finishSlides();
    this.#render();
    this.#slidePage(type, page);
  }

  // Out phase, then the switch and one immediate render at the midpoint, then the in phase.
  #slideLocation(index) {
    this.#finishSlides();
    const { entities } = this.#config;
    const from = entities.indexOf(this.#entityId);
    if (!entities[index] || index === from) return;
    const content = this.#body.querySelector(".slide-content");
    if (!content || reducedMotion()) {
      this.#chooseLocation(index);
      this.#render();
      return;
    }
    const side = index > from ? 100 : -100;
    this.#slide("location", content, `translateX(${-side}%)`, 200, (jump) => {
      this.#chooseLocation(index);
      this.#render();
      const incoming = this.#body.querySelector(".slide-content");
      if (jump || !incoming) {
        this.#scheduleRender();
        return;
      }
      incoming.style.transition = "none";
      incoming.style.transform = `translateX(${side}%)`;
      this.#slide("location", incoming, "translateX(0px)", 200);
    });
  }

  #scheduleRender() {
    if (this.#renderFrame || !this.isConnected) return;
    this.#renderFrame = requestAnimationFrame(() => {
      this.#renderFrame = 0;
      if (!this.#drag && !Object.keys(this.#slides).length) this.#render();
    });
  }

  #locationName(id, locationInfo) {
    const name = this.#hass.states[id]?.attributes.friendly_name ?? id;
    const device = this.#hass.devices?.[this.#hass.entities?.[id]?.device_id];
    return model.locationLabel(name, device?.name_by_user || device?.name, locationInfo);
  }

  #tap(target, className, text) {
    const id = model.tapTarget(target, this.#entityId, this.#entry.entities);
    const node = element(id ? "button" : "div", id ? `button ${className}` : className, text);
    if (id) {
      node.addEventListener("click", () => this.dispatchEvent(new CustomEvent("hass-more-info", {
        detail: { entityId: id }, bubbles: true, composed: true,
      })));
    }
    return node;
  }

  #chip(parent, target, text, name, color) {
    if (!model.tapTarget(target, this.#entityId, this.#entry.entities)) return;
    const chip = this.#tap(target, target === "rainfall" ? "chip rainfall" : "chip");
    chip.append(icon(name, color ? `chip-icon ${color}` : "chip-icon"), element("span", "", text));
    parent.append(chip);
  }

  #currentWeather(section, state, now, zone) {
    const weather = this.#weather;
    const { entities } = this.#entry;
    const sensor = (key) => state === "ready" ? this.#hass.states[entities[key]]?.state : undefined;
    const raw = model.stateWithUnit;
    const code = state === "ready" ? model.stateText(weather.attributes.attribution).split(",")[0] : null;
    const picture = model.picture(this.#config.icon_path, code, weather.state);

    const top = element("div", "current-grid");
    const pictureButton = this.#tap("picture", "current-picture");
    pictureButton.setAttribute("aria-label", "날씨 상태");
    pictureButton.append(pictureNode(picture, "current-picture-size"));
    const temperature = this.#tap("temperature", "current-temperature");
    temperature.append(
      element("span", "current-temperature-value", raw(sensor("NowTemp"), "°")),
      element("span", "high-low", model.temperatureRange(sensor("TodayMaxTemp"), sensor("TodayMinTemp"))),
    );
    const details = element("div", "conditions");
    details.append(
      this.#tap("weather", "condition", model.stateText(sensor("NowWeather"))),
      this.#tap("cast", "cast", model.weathercastSentence(sensor("WeatherCast"))),
    );
    this.#chip(details, "rainfall", `1시간 강수량 - ${raw(sensor("Rainfall"), " mm")}`, "mdi:weather-pouring", "blue");
    top.append(pictureButton, temperature, details);

    const chips = element("div", "chip-row");
    this.#chip(chips, "humidity", `습도 ${raw(sensor("Humidity"), " %")}`, "mdi:water-percent", "blue");
    this.#chip(chips, "feel", `체감 ${raw(sensor("TodayFeelTemp"), "°")}`, "mdi:thermometer", "deep-orange");
    this.#chip(chips, "wind", `${raw(sensor("WindBearing"), "풍")} ${raw(sensor("WindSpeed"), "m/s")}`, "mdi:weather-windy", "green");

    const air = element("div", "chip-row");
    for (const [target, text, key, name] of [
      ["fine", "미세", "FineDustGrade", "mdi:blur"],
      ["ultraFine", "초미세", "UltraFineDustGrade", "mdi:blur-linear"],
      ["uv", "UV", "TodayUVGrade", "mdi:sun-wireless"],
    ]) {
      const grade = sensor(key);
      this.#chip(air, target, `${text}-${model.stateText(grade)}`, name, model.gradeColor(grade));
    }
    const sun = this.#hass.states["sun.sun"];
    if (sun) {
      const { next_rising, next_setting } = state === "ready" ? sun.attributes : {};
      const { text, icon } = model.sunChip(next_rising, next_setting, now, zone);
      this.#chip(air, "sun", text, icon, "orange");
    }
    section.append(top, chips, air);
  }

  #hour(row, zone) {
    const column = element("div", "hour");
    column.append(
      element("span", "hour-label", model.formatHour(row.datetime, zone)),
      pictureNode(model.hourlyPicture(this.#config.icon_path, row), "forecast-picture"),
      element("span", "warm", model.tempOneDecimal(row.temperature)),
      element("span", "cool", model.percentText(row.humidity)),
      element("span", "", model.stateText(row.precipitation)),
      element("span", "unit", model.stateText(this.#weather.attributes.precipitation_unit)),
    );
    return column;
  }

  #day(row, now, zone, workdays) {
    const item = element("div", "day");
    const day = model.calendarDay(row.datetime, zone);
    const offset = day ? day.number - model.calendarDay(now, zone).number : null;
    const label = model.dayLabel(row.datetime, now, zone);
    const red = model.labelRed(offset, workdays, day?.weekday);
    const cell = (...contents) => {
      const cell = element("div", "day-cell");
      cell.append(...contents);
      return cell;
    };
    const path = this.#config.icon_path;
    item.append(
      cell(element("span", red ? "red" : "", label), element("span", "", model.dateLabel(row.datetime, zone))),
      cell(element("span", "cool", model.tempOneDecimal(row.templow)), element("span", "warm", model.tempOneDecimal(row.temperature))),
      cell(element("span", "", "오전"), element("span", "cool", model.percentText(row.rain_rate_am))),
      cell(pictureNode(model.picture(path, row.weathertype_am, row.condition_am), "forecast-picture")),
      cell(element("span", "", "오후"), element("span", "cool", model.percentText(row.rain_rate_pm))),
      cell(pictureNode(model.picture(path, row.weathertype_pm, row.condition_pm), "forecast-picture")),
    );
    return item;
  }

  #forecastSection(type, forecast, current, now, zone, workdays) {
    const section = element("section", `section forecast-section swipe ${type}-section`);
    section.dataset.swipe = type;
    section.setAttribute("aria-label", SECTION_NAMES[type]);
    const state = model.forecastState({ ...forecast, current });
    if (state !== "rows") {
      section.append(element("div", "status", STATE_TEXT[state]));
      return section;
    }
    const pages = model.pages(forecast.rows, PAGE_SIZE[type]);
    const grid = element("div", type === "hourly" ? "hourly-grid" : "daily-list");
    const track = element("div", "pages-track");
    track.style.transform = pageTransform(forecast.page, 0);
    track.dataset.page = String(forecast.page);
    for (const [index, rows] of pages.entries()) {
      const page = element("div", `${type}-page`);
      // Pages outside the viewport are only clipped visually; keep them from screen readers too.
      if (index !== forecast.page) page.setAttribute("aria-hidden", "true");
      for (const row of rows) {
        page.append(type === "hourly" ? this.#hour(row ?? {}, zone) : this.#day(row ?? {}, now, zone, workdays));
      }
      track.append(page);
    }
    grid.append(track);
    section.append(grid, dots(pages.length, forecast.page, SECTION_NAMES[type], (page) => this.#pickPage(type, page)));
    return section;
  }

  #render() {
    const entry = this.#entry;
    if (!this.#hass || !this.#config || !entry) return;
    const { entities, switcher, show_current: showCurrent, workday_entities: workdayEntities } = this.#config;
    const { states } = this.#hass;
    const workdays = Array.isArray(workdayEntities) ? workdayEntities.map((id) => states[id]?.state) : undefined;
    const zone = this.#hass.config.time_zone;
    const now = new Date();
    const names = entities.map((id) => this.#locationName(id));
    const current = this.#currentStateOf(entry);
    const inputs = [
      this.#config, this.#entityId, current, this.#weather, entry.forecasts, entry.entities,
      states["sun.sun"], zone, Math.floor(now.getTime() / 60_000), ...names, ...(workdays ?? []),
      ...Object.values(entry.entities).map((id) => states[id]),
    ];
    if (inputs.length === this.#renderInputs.length && inputs.every((input, index) => input === this.#renderInputs[index])) return;
    this.#renderInputs = inputs;

    const content = document.createDocumentFragment();
    const selected = entities.indexOf(this.#entityId);
    const swipe = entities.length > 1 && switcher === "swipe";
    const label = this.#locationName(this.#entityId, current === "ready" ? states[entry.entities.LocationInfo]?.state : null);
    if (entities.length > 1 && switcher === "buttons") {
      const locations = element("div", "location-buttons");
      for (const [index, name] of names.entries()) {
        const button = element("button", index === selected ? "button location-button active-location" : "button location-button", name);
        button.setAttribute("aria-pressed", String(index === selected));
        button.addEventListener("click", () => this.#slideLocation(index));
        locations.append(button);
      }
      content.append(locations);
    }
    const location = element("div", "location-row");
    location.append(element("div", "location-label", label));
    if (swipe) location.append(dots(entities.length, selected, "지역", (index) => this.#slideLocation(index)));
    const section = showCurrent ? element("section", "section current-section") : location;
    if (swipe) {
      section.classList.add("swipe");
      section.dataset.swipe = "location";
    }
    if (showCurrent) {
      section.setAttribute("aria-label", "현재 날씨");
      section.append(location);
      if (current !== "ready") section.append(element("div", "status", STATE_TEXT[current]));
      if (current === "ready" || entry.availability === "unavailable") this.#currentWeather(section, current, now, zone);
    }
    const slide = element("div", "slide-content");
    slide.append(section);
    const forecastStates = [];
    for (const [type, forecast] of Object.entries(entry.forecasts)) {
      forecastStates.push(model.forecastState({ ...forecast, current }));
      slide.append(this.#forecastSection(type, forecast, current, now, zone, workdays));
    }
    content.append(slide);
    this.#body.replaceChildren(content);
    this.#holdHeight(showCurrent ? [current, ...forecastStates] : forecastStates);
  }

  // While a section is loading or waiting, keep the height of the last fully drawn render at the
  // same width; a fully drawn render records its natural height.
  #holdHeight(states) {
    const width = this.#body.offsetWidth;
    const height = model.holdHeight(states, this.#heightRecord, width);
    if (height == null) {
      this.#body.style.removeProperty("min-height");
    } else {
      this.#body.style.minHeight = `${height}px`;
    }
    if (states.every((state) => state === "ready" || state === "rows")) {
      this.#heightRecord = { height: this.#body.offsetHeight, width: this.#body.offsetWidth };
    }
  }
}

if (!customElements.get("naver-weather-card")) {
  customElements.define("naver-weather-card", NaverWeatherCard);
  window.customCards ??= [];
  window.customCards.push(model.cardDescriptor());
}
