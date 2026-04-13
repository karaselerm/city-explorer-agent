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

function categoryLabel(value) {
  return CATEGORY_LABELS[value] || value || "—";
}

function transportLabel(value) {
  return TRANSPORT_LABELS[value] || value || "—";
}

function byId(id) {
  return document.getElementById(id);
}

function renderWarnings(warnings) {
  const box = byId("warnings");
  if (!warnings || warnings.length === 0) {
    box.innerHTML = "<p>Без предупреждений.</p>";
    return;
  }
  box.innerHTML = `<ul>${warnings.map((w) => `<li class="warn">${w}</li>`).join("")}</ul>`;
}

function renderStops(stops) {
  const box = byId("stops");
  if (!stops || stops.length === 0) {
    box.innerHTML = "<p>Остановки отсутствуют.</p>";
    return;
  }

  box.innerHTML = stops
    .map(
      (s) => `
      <article class="stop">
        <h3>${s.order}. ${s.name}</h3>
        <p>Категория: ${categoryLabel(s.category)}</p>
        <p>Переход: ${s.distance_km_from_prev ?? s.distance_km ?? 0} км / ${s.eta_minutes_from_prev ?? s.eta_min ?? 0} мин</p>
        <p>Остановка: ${s.dwell_minutes ?? s.dwell_min ?? 0} мин</p>
        ${s.travel_instruction ? `<p>${s.travel_instruction}</p>` : ""}
        <p>
          ${s.segment_map_url ? `<a href="${s.segment_map_url}" target="_blank" rel="noreferrer">Как доехать</a>` : ""}
          ${s.wiki_url ? ` · <a href="${s.wiki_url}" target="_blank" rel="noreferrer">Подробнее</a>` : ""}
        </p>
      </article>
    `
    )
    .join("");
}

function render(doc) {
  const response = doc.response || {};
  const plan = response.plan || {};
  const cityMeta = plan.city_meta || {};
  const request = doc.request || {};

  byId("title").textContent = doc.title || "Демо-сценарий";
  byId("request").innerHTML = `
    <span class="pill">Город: ${request.city || "—"}</span>
    <span class="pill">Длительность: ${request.duration_hours ?? "—"} ч</span>
    <span class="pill">Дистанция: ${request.max_distance_km ?? "—"} км</span>
    <span class="pill">Транспорт: ${transportLabel(request.transport_mode)}</span>
  `;

  byId("summary").innerHTML = `
    <div class="summary-grid">
      <p><strong>Итоговая длительность:</strong> ${plan.total_duration_minutes ?? 0} мин</p>
      <p><strong>Итоговая дистанция:</strong> ${plan.total_distance_km ?? 0} км</p>
      <p><strong>Город:</strong> ${plan.city || "—"}</p>
      <p><strong>Проверка города:</strong> ${cityMeta.canonical_name || "—"} (${cityMeta.country || "—"})</p>
      <p><strong>Fallback:</strong> ${response.used_fallback ? "да" : "нет"}</p>
    </div>
    ${plan.map_overview_url ? `<p><a href="${plan.map_overview_url}" target="_blank" rel="noreferrer">Открыть маршрут в картах</a></p>` : ""}
    <p>${plan.explanation || ""}</p>
  `;

  renderWarnings(plan.warnings || []);
  renderStops(plan.stops || []);
}

async function bootstrap() {
  const path = window.DEMO_DATA_FILE;
  if (!path) {
    byId("status").textContent = "Не задан путь к JSON-данным демо.";
    return;
  }
  try {
    const res = await fetch(path);
    const json = await res.json();
    render(json);
    byId("status").textContent = "Демо-страница загружена.";
  } catch (e) {
    byId("status").textContent = `Не удалось загрузить данные: ${e}`;
  }
}

bootstrap();
