const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const warningsEl = document.getElementById("warnings");
const cityHintsEl = document.getElementById("city-hints");
const stopsEl = document.getElementById("stops");
const traceEl = document.getElementById("trace");
const submitBtn = document.getElementById("submit-btn");
const form = document.getElementById("plan-form");
const mustCategoryList = document.getElementById("must-category-list");
const avoidCategoryList = document.getElementById("avoid-category-list");
const API_BASE = window.CITY_EXPLORER_API_BASE || "/api";

let routeMap = null;
let mapLayers = [];

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

const TRACE_STEP_LABELS = {
  safety_check: "Проверка безопасности",
  memory_load: "Загрузка памяти",
  city_resolve: "Проверка города",
  retrieve_poi: "Поиск мест",
  relax_constraints: "Ослабление ограничений",
  rank_filter: "Ранжирование",
  build_route: "Построение маршрута",
  memory_update: "Обновление памяти",
};

function categoryLabel(category) {
  return CATEGORY_LABELS[category] || category;
}

function transportLabel(mode) {
  return TRANSPORT_LABELS[mode] || mode;
}

function traceStepLabel(step) {
  return TRACE_STEP_LABELS[step] || step;
}

async function pingBackend() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) {
      statusEl.textContent = "Бэкенд недоступен.";
      return;
    }
  } catch {
    statusEl.textContent = "Бэкенд недоступен.";
  }
}

async function loadMeta() {
  try {
    const res = await fetch(`${API_BASE}/meta`);
    const data = await res.json();
    if (!res.ok) {
      return;
    }
    const categories = data.popular_categories || [];
    renderCategoryChips(categories);
  } catch {
    // no-op
  }
}

function renderCategoryChips(categories) {
  const mustDefault = new Set(["museum", "park", "cafe"]);
  mustCategoryList.innerHTML = categories
    .map((cat) => {
      const checked = mustDefault.has(cat) ? "checked" : "";
      return `<label class="chip"><input type="checkbox" name="must_category_popular" value="${cat}" ${checked} />${categoryLabel(cat)}</label>`;
    })
    .join("");

  avoidCategoryList.innerHTML = categories
    .map((cat) => `<label class="chip"><input type="checkbox" name="avoid_category_popular" value="${cat}" />${categoryLabel(cat)}</label>`)
    .join("");
}

function parseCsv(value) {
  return value
    .split(",")
    .map((x) => x.trim().toLowerCase())
    .filter(Boolean);
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function collectCategories(popularSelector, customInputName) {
  const selected = Array.from(document.querySelectorAll(popularSelector + ":checked")).map((el) => el.value);
  const customRaw = String(form.elements[customInputName].value || "");
  const custom = parseCsv(customRaw);
  return unique([...selected, ...custom]);
}

function renderWarnings(warnings) {
  if (!warnings || warnings.length === 0) {
    warningsEl.classList.add("hidden");
    warningsEl.innerHTML = "";
    return;
  }
  warningsEl.classList.remove("hidden");
  warningsEl.innerHTML = `
    <strong>Предупреждения</strong>
    <ul>${warnings.map((w) => `<li>${w}</li>`).join("")}</ul>
  `;
}

function renderCityHints(cityMeta) {
  if (!cityMeta) {
    cityHintsEl.classList.add("hidden");
    cityHintsEl.innerHTML = "";
    return;
  }

  const suggestions = cityMeta.suggestions || [];
  const hintRows = [`Актуальный город: <strong>${cityMeta.canonical_name || "не определен"}</strong>`];
  if (cityMeta.country) {
    hintRows.push(`Страна: ${cityMeta.country}`);
  }
  if (suggestions.length > 0) {
    hintRows.push(`Похожие варианты: ${suggestions.join(", ")}`);
  }

  cityHintsEl.classList.remove("hidden");
  cityHintsEl.innerHTML = `<strong>Проверка города</strong><p>${hintRows.join("<br />")}</p>`;
}

function cityHintsFromError(data) {
  const trace = data.trace || [];
  const cityStep = trace.find((t) => t.step === "city_resolve");
  const meta = (cityStep && cityStep.meta) || {};
  const suggestions = meta.suggestions || [];
  if (!suggestions.length) {
    return null;
  }
  return {
    canonical_name: "не определен",
    country: "",
    suggestions,
  };
}

function renderSummary(data) {
  const plan = data.plan;
  summaryEl.classList.remove("hidden");
  summaryEl.innerHTML = `
    <strong>Итог:</strong> ${plan.total_duration_minutes} мин, ${plan.total_distance_km} км
    <br />
    <strong>Транспорт:</strong> ${transportLabel(plan.transport_mode)}
    <br />
    <strong>Использован fallback:</strong> ${data.used_fallback ? "да" : "нет"}
    <br />
    <strong>Файлы экспорта:</strong> ${(data.exports || []).join(", ") || "нет"}
    ${plan.map_overview_url ? `<br /><a href="${plan.map_overview_url}" target="_blank" rel="noreferrer">Открыть полный маршрут в картах</a>` : ""}
    <p>${plan.explanation || ""}</p>
  `;
}

function photoHtml(url, alt) {
  if (!url) {
    return "";
  }
  return `<img src="${url}" alt="${alt}" class="poi-photo" loading="lazy" />`;
}

function renderStops(stops, alternatives) {
  stopsEl.innerHTML = "<h2>Маршрут</h2>";
  stops.forEach((stop) => {
    const node = document.createElement("article");
    node.className = "stop-card";
    node.innerHTML = `
      <h3>${stop.order}. ${stop.name}</h3>
      <p>Категория: ${categoryLabel(stop.category)}</p>
      <p>Переход: ${stop.distance_km} км / ${stop.eta_min} мин</p>
      <p>${stop.travel_instruction || ""}</p>
      <p>Остановка: ${stop.dwell_min} мин</p>
      ${stop.description ? `<p class="desc">${stop.description}</p>` : ""}
      ${photoHtml(stop.photo_url, stop.name)}
      <div class="links">
        <a href="${stop.map_url}" target="_blank" rel="noreferrer">Точка на карте</a>
        ${stop.segment_map_url ? `<a href="${stop.segment_map_url}" target="_blank" rel="noreferrer">Как доехать</a>` : ""}
        ${stop.wiki_url ? `<a href="${stop.wiki_url}" target="_blank" rel="noreferrer">Подробнее</a>` : ""}
      </div>
    `;
    stopsEl.appendChild(node);
  });

  if (alternatives && alternatives.length > 0) {
    const alt = document.createElement("article");
    alt.className = "stop-card";
    alt.innerHTML = `
      <h3>Запасной план</h3>
      <ul>
        ${alternatives
          .map(
            (x) =>
              `<li>${x.name} (${categoryLabel(x.category)})${x.description ? ` — ${x.description}` : ""}${x.wiki_url ? ` <a href="${x.wiki_url}" target="_blank" rel="noreferrer">ссылка</a>` : ""}</li>`
          )
          .join("")}
      </ul>
    `;
    stopsEl.appendChild(alt);
  }
}

function renderTrace(trace) {
  traceEl.innerHTML = "<h2>Трассировка</h2>";
  const rows = trace
    .map((t) => {
      const cls = t.ok ? "ok" : "fail";
      return `
        <tr>
          <td>${traceStepLabel(t.step)}</td>
          <td class="${cls}">${t.ok ? "да" : "нет"}</td>
          <td><code>${JSON.stringify(t.meta)}</code></td>
        </tr>
      `;
    })
    .join("");

  traceEl.innerHTML += `
    <table>
      <thead>
        <tr><th>Шаг</th><th>Успех</th><th>Данные</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderMap(stops) {
  if (!window.L) {
    return;
  }

  if (!routeMap) {
    routeMap = window.L.map("map", { zoomControl: true }).setView([55.75, 37.61], 12);
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(routeMap);
  }

  mapLayers.forEach((layer) => layer.remove());
  mapLayers = [];

  if (!stops || stops.length === 0) {
    return;
  }

  const latlngs = stops.map((s) => [s.lat, s.lon]);
  latlngs.forEach((latlng, idx) => {
    const marker = window.L.marker(latlng)
      .bindPopup(`<strong>${stops[idx].order}. ${stops[idx].name}</strong><br/>${categoryLabel(stops[idx].category)}`)
      .addTo(routeMap);
    mapLayers.push(marker);
  });

  const polyline = window.L.polyline(latlngs, { color: "#0f766e", weight: 4 }).addTo(routeMap);
  mapLayers.push(polyline);

  routeMap.fitBounds(polyline.getBounds(), { padding: [20, 20] });
}

function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  submitBtn.textContent = isLoading ? "Строю маршрут..." : "Собрать маршрут";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);

  statusEl.textContent = "Строю маршрут...";
  stopsEl.innerHTML = "";
  traceEl.innerHTML = "";

  const fd = new FormData(form);
  const wantsIcs = fd.get("export_ics") === "on";

  const mustCategories = collectCategories("input[name='must_category_popular']", "must_categories_custom");
  const avoidCategoriesRaw = collectCategories("input[name='avoid_category_popular']", "avoid_categories_custom");
  const overlap = mustCategories.filter((x) => avoidCategoriesRaw.includes(x));
  const avoidCategories = avoidCategoriesRaw.filter((x) => !mustCategories.includes(x));

  if (overlap.length > 0) {
    statusEl.textContent = `Убраны конфликтующие категории из нежелательных: ${overlap.map((x) => categoryLabel(x)).join(", ")}.`;
  }

  const payload = {
    user_id: fd.get("user_id"),
    city: String(fd.get("city") || "").trim(),
    duration_hours: Number(fd.get("duration_hours")),
    max_distance_km: Number(fd.get("max_distance_km")),
    must_categories: mustCategories,
    avoid_categories: avoidCategories,
    style: fd.get("style"),
    budget: fd.get("budget"),
    transport_mode: fd.get("transport_mode"),
    quiet: fd.get("quiet") === "on",
    with_plan_b: fd.get("with_plan_b") === "on",
    confirm_side_effects: fd.get("confirm_side_effects") === "on",
    export_formats: wantsIcs ? ["markdown", "json", "ics"] : ["markdown", "json"],
  };

  try {
    const res = await fetch(`${API_BASE}/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      const topError = data.error || (data.errors || []).join("; ") || "не удалось построить маршрут";
      statusEl.textContent = `Ошибка: ${topError}`;
      renderWarnings(data.errors || []);
      renderCityHints(cityHintsFromError(data));
      renderMap([]);
      return;
    }

    statusEl.textContent = "Маршрут успешно построен.";
    renderSummary(data);
    renderWarnings(data.plan.warnings);
    renderCityHints(data.plan.city_meta);
    renderStops(data.plan.stops, data.plan.alternatives);
    renderTrace(data.trace || []);
    renderMap(data.plan.stops || []);
  } catch (error) {
    statusEl.textContent = `Ошибка сети: ${error}`;
  } finally {
    setLoading(false);
  }
});

pingBackend();
loadMeta();
