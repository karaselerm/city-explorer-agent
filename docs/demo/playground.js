const CATEGORY_LABELS = {
  museum: "музей",
  park: "парк",
  cafe: "кафе",
  viewpoint: "смотровая площадка",
  landmark: "достопримечательность",
  gallery: "галерея",
  theatre: "театр",
  shopping: "шопинг",
  library: "библиотека",
  beach: "пляж",
  bar: "бар",
  hookah: "кальянная",
};

const TRANSPORT_LABELS = {
  walk: "пешком",
  bike: "на велосипеде",
  car: "на машине",
  transit: "на общественном транспорте",
};

const STYLE_PREFS = {
  balanced: [],
  culture: ["museum", "landmark", "gallery", "theatre", "library"],
  nature: ["park", "beach", "viewpoint"],
};

const SCENARIOS_FILE = "./data/playground-scenarios.json?v=20260414-2";

const ALL_CATEGORIES = [
  "museum",
  "park",
  "cafe",
  "viewpoint",
  "landmark",
  "gallery",
  "theatre",
  "shopping",
  "library",
  "beach",
];

let currentDoc = null;
let allScenarios = [];

function byId(id) {
  return document.getElementById(id);
}

function categoryLabel(c) {
  return CATEGORY_LABELS[c] || c;
}

function transportLabel(t) {
  return TRANSPORT_LABELS[t] || t;
}

function checkedValues(containerId) {
  return Array.from(document.querySelectorAll(`#${containerId} input[type="checkbox"]:checked`)).map((x) => x.value);
}

function renderCategoryChips(containerId, inputName) {
  const node = byId(containerId);
  node.innerHTML = ALL_CATEGORIES.map(
    (c) => `<label class="chip"><input type="checkbox" name="${inputName}" value="${c}" />${categoryLabel(c)}</label>`
  ).join("");
}

function setDefaultsFromRequest(request) {
  const mustSet = new Set((request.must_categories || []).slice(0, 5));
  const style = request.style || "balanced";
  const budget = request.budget || "medium";
  const transport = request.transport_mode || "walk";

  byId("style-select").value = style;
  byId("budget-select").value = budget;
  byId("transport-select").value = transport;

  document.querySelectorAll("#must-chips input").forEach((el) => {
    el.checked = mustSet.has(el.value);
  });
  document.querySelectorAll("#avoid-chips input").forEach((el) => {
    el.checked = false;
  });
}

function sortedStops(stops, style) {
  const preferred = new Set(STYLE_PREFS[style] || []);
  if (!preferred.size) {
    return stops;
  }
  return [...stops].sort((a, b) => {
    const pa = preferred.has(a.category) ? 1 : 0;
    const pb = preferred.has(b.category) ? 1 : 0;
    return pb - pa;
  });
}

function filterStops(stops, must, avoid) {
  const avoidSet = new Set(avoid);
  const mustSet = new Set(must);

  let out = stops.filter((s) => !avoidSet.has(s.category));
  if (mustSet.size) {
    const prioritized = out.filter((s) => mustSet.has(s.category));
    if (prioritized.length > 0) {
      out = prioritized;
    }
  }
  return out;
}

function recomputeSummary(plan, shownStops) {
  const distance = shownStops.reduce((acc, s) => acc + Number(s.distance_km_from_prev || 0), 0);
  const eta = shownStops.reduce((acc, s) => acc + Number(s.eta_minutes_from_prev || 0), 0);
  const dwell = shownStops.reduce((acc, s) => acc + Number(s.dwell_minutes || 0), 0);
  return {
    city: plan.city || "—",
    distance: distance.toFixed(2),
    duration: eta + dwell,
  };
}

function renderWarnings(planWarnings, localWarnings) {
  const warnings = [...(planWarnings || []), ...(localWarnings || [])];
  byId("warnings").innerHTML = warnings.length
    ? `<ul>${warnings.map((w) => `<li class="warn">${w}</li>`).join("")}</ul>`
    : "<p>Без предупреждений.</p>";
}

function renderStops(stops) {
  const box = byId("stops");
  if (!stops.length) {
    box.innerHTML = "<p>После выбранных фильтров остановок не осталось.</p>";
    return;
  }
  box.innerHTML = stops
    .map(
      (s, i) => `
      <article class="stop">
        <h3>${i + 1}. ${s.name}</h3>
        <p>Категория: ${categoryLabel(s.category)}</p>
        <p>Переход: ${Number(s.distance_km_from_prev || 0).toFixed(2)} км / ${s.eta_minutes_from_prev || 0} мин</p>
        <p>Остановка: ${s.dwell_minutes || 0} мин</p>
        ${s.travel_instruction ? `<p>${s.travel_instruction}</p>` : ""}
        <p>${s.segment_map_url ? `<a href="${s.segment_map_url}" target="_blank" rel="noreferrer">Как доехать</a>` : ""}</p>
      </article>`
    )
    .join("");
}

function renderPreview() {
  if (!currentDoc) {
    return;
  }
  const response = currentDoc.response || {};
  const plan = response.plan || {};
  const request = currentDoc.request || {};
  const cityMeta = plan.city_meta || {};

  const style = byId("style-select").value;
  const budget = byId("budget-select").value;
  const transport = byId("transport-select").value;
  const must = checkedValues("must-chips");
  const avoidRaw = checkedValues("avoid-chips");
  const avoid = avoidRaw.filter((x) => !must.includes(x));

  const localWarnings = [];
  const conflict = avoidRaw.filter((x) => must.includes(x));
  if (conflict.length) {
    localWarnings.push(
      `Категории ${conflict.map(categoryLabel).join(", ")} одновременно в обязательных и исключениях. Приоритет у обязательных.`
    );
  }

  let shownStops = filterStops(plan.stops || [], must, avoid);
  shownStops = sortedStops(shownStops, style).slice(0, 6);

  const summary = recomputeSummary(plan, shownStops);

  byId("title").textContent = currentDoc.title || "Демо-сценарий";
  byId("request").innerHTML = `
    <span class="pill">Город: ${request.city || "—"}</span>
    <span class="pill">Стиль: ${style === "culture" ? "культура" : style === "nature" ? "природа" : "сбалансированный"}</span>
    <span class="pill">Бюджет: ${budget === "low" ? "низкий" : budget === "high" ? "высокий" : "средний"}</span>
    <span class="pill">Транспорт: ${transportLabel(transport)}</span>
  `;

  byId("summary").innerHTML = `
    <div class="summary-grid">
      <p><strong>Город:</strong> ${summary.city}</p>
      <p><strong>Проверка города:</strong> ${cityMeta.canonical_name || "—"} (${cityMeta.country || "—"})</p>
      <p><strong>Дистанция (демо):</strong> ${summary.distance} км</p>
      <p><strong>Длительность (демо):</strong> ${summary.duration} мин</p>
      <p><strong>Fallback в исходном кейсе:</strong> ${response.used_fallback ? "да" : "нет"}</p>
    </div>
    ${plan.map_overview_url ? `<p><a href="${plan.map_overview_url}" target="_blank" rel="noreferrer">Открыть маршрут в картах</a></p>` : ""}
    <p>${plan.explanation || ""}</p>
  `;

  renderWarnings(plan.warnings || [], localWarnings);
  renderStops(shownStops);
  byId("status").textContent = "Параметры применены.";
}

function fillCitySelect() {
  const select = byId("city-select");
  select.innerHTML = allScenarios
    .map((s, idx) => `<option value="${idx}">${s.title}</option>`)
    .join("");
}

async function loadScenario(indexLike) {
  const index = Number(indexLike);
  const scenario = allScenarios[index];
  if (!scenario) {
    byId("status").textContent = "Неизвестный сценарий.";
    return;
  }
  byId("status").textContent = "Загрузка сценария...";
  currentDoc = scenario;
  setDefaultsFromRequest(currentDoc.request || {});
  renderPreview();
}

function bindEvents() {
  byId("city-select").addEventListener("change", (e) => {
    loadScenario(e.target.value).catch((err) => {
      byId("status").textContent = `Ошибка загрузки: ${err}`;
    });
  });

  ["style-select", "budget-select", "transport-select"].forEach((id) => {
    byId(id).addEventListener("change", renderPreview);
  });

  byId("must-chips").addEventListener("change", renderPreview);
  byId("avoid-chips").addEventListener("change", renderPreview);
}

async function bootstrap() {
  byId("status").textContent = "Загрузка 100 сценариев...";
  const res = await fetch(SCENARIOS_FILE);
  if (!res.ok) {
    throw new Error(`не удалось загрузить файл сценариев (${res.status})`);
  }
  const text = await res.text();
  if (text.trim().startsWith("<!DOCTYPE") || text.trim().startsWith("<html")) {
    throw new Error("вместо JSON получен HTML. Обычно это означает, что Pages еще не обновился.");
  }
  allScenarios = JSON.parse(text);
  if (!Array.isArray(allScenarios) || allScenarios.length === 0) {
    throw new Error("файл сценариев пуст");
  }

  renderCategoryChips("must-chips", "must_category");
  renderCategoryChips("avoid-chips", "avoid_category");
  fillCitySelect();
  bindEvents();
  await loadScenario(0);
}

bootstrap().catch((err) => {
  byId("status").textContent = `Ошибка инициализации: ${err}`;
});
