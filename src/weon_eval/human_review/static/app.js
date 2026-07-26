"use strict";

const state = {
  config: null,
  document: null,
  currentCaseIndex: 0,
  activeItemId: null,
  mode: "crop",
  draftNotes: {},
  saveTimer: null,
  saveChain: Promise.resolve(),
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function itemById(itemId) {
  return state.config.items.find((item) => item.item_id === itemId);
}

function itemsForCase(caseData) {
  return caseData.item_ids.map(itemById);
}

function completedCount() {
  return Object.keys(state.document.ratings).length;
}

function caseIsComplete(caseData) {
  return caseData.item_ids.every((itemId) => Object.hasOwn(state.document.ratings, itemId));
}

function setSaveStatus(text, kind = "") {
  const element = $("#save-status");
  element.textContent = text;
  element.className = `save-status ${kind}`.trim();
}

function scheduleSave() {
  setSaveStatus("Unsaved", "is-pending");
  window.clearTimeout(state.saveTimer);
  state.saveTimer = window.setTimeout(saveNow, 180);
}

function saveNow() {
  window.clearTimeout(state.saveTimer);
  state.saveTimer = null;
  const snapshot = JSON.stringify(state.document);
  setSaveStatus("Saving…", "is-pending");
  state.saveChain = state.saveChain
    .then(async () => {
      const response = await fetch("/api/review", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: snapshot,
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({ error: "Save failed" }));
        throw new Error(detail.error || "Save failed");
      }
      setSaveStatus("Saved", "is-saved");
    })
    .catch((error) => setSaveStatus(error.message, "is-error"));
  return state.saveChain;
}

function updateProgress() {
  $("#progress-text").textContent = `${completedCount()} of ${state.config.items.length} rated`;
}

function evidenceUrl(caseId, pane, mode) {
  const effectiveMode = pane === "source" ? "crop" : mode;
  return `/evidence/${caseId}/${pane}/${effectiveMode}.png`;
}

function setActiveItem(caseData) {
  const items = itemsForCase(caseData);
  const currentIsValid = items.some((item) => item.item_id === state.activeItemId);
  if (currentIsValid && !Object.hasOwn(state.document.ratings, state.activeItemId)) return;
  const unanswered = items.find((item) => !Object.hasOwn(state.document.ratings, item.item_id));
  state.activeItemId = unanswered ? unanswered.item_id : items[0].item_id;
}

function scoreButton(item, option) {
  const current = state.document.ratings[item.item_id]?.score;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "score-button";
  button.dataset.score = String(option.value);
  button.setAttribute("aria-pressed", current === option.value ? "true" : "false");
  if (current === option.value) button.classList.add("is-selected");

  const value = document.createElement("strong");
  value.textContent = String(option.value);
  const label = document.createElement("span");
  label.textContent = option.label;
  button.append(value, label);
  button.addEventListener("click", () => rateItem(item.item_id, option.value));
  return button;
}

function buildEvidenceCard({ caseData, item = null, pane, label, source = false }) {
  const card = document.createElement("article");
  card.className = source ? "evidence-card source-card" : "evidence-card candidate-card";
  if (item?.item_id === state.activeItemId) card.classList.add("is-active");
  if (item && Object.hasOwn(state.document.ratings, item.item_id)) card.classList.add("is-rated");

  const header = document.createElement("header");
  const heading = document.createElement("h3");
  heading.textContent = label;
  const status = document.createElement("span");
  status.className = "card-status";
  status.textContent = source
    ? "Reference"
    : Object.hasOwn(state.document.ratings, item.item_id)
      ? `Rated ${state.document.ratings[item.item_id].score}`
      : "Needs rating";
  header.append(heading, status);

  const imageButton = document.createElement("button");
  imageButton.type = "button";
  imageButton.className = "image-stage";
  imageButton.title = `Open ${label} full-screen`;
  const image = document.createElement("img");
  image.src = evidenceUrl(caseData.case_id, pane, state.mode);
  image.alt = `${caseData.case_id} ${label} ${state.mode} evidence`;
  image.draggable = false;
  imageButton.append(image);
  imageButton.addEventListener("click", () => openLightbox(image.src, `${caseData.case_id} · ${label}`));

  card.append(header, imageButton);
  if (!source) {
    const controls = document.createElement("div");
    controls.className = "candidate-controls";
    const scores = document.createElement("div");
    scores.className = "score-grid";
    scores.setAttribute("aria-label", `Rate ${label}`);
    state.config.score_options.forEach((option) => scores.append(scoreButton(item, option)));

    const note = document.createElement("input");
    note.type = "text";
    note.className = "note-input";
    note.maxLength = 180;
    note.placeholder = "Optional note, e.g. logo unreadable";
    note.setAttribute("aria-label", `Optional note for ${label}`);
    note.value = state.document.ratings[item.item_id]?.note || state.draftNotes[item.item_id] || "";
    note.addEventListener("input", () => {
      state.draftNotes[item.item_id] = note.value;
      if (Object.hasOwn(state.document.ratings, item.item_id)) {
        state.document.ratings[item.item_id].note = note.value;
        scheduleSave();
      }
    });
    controls.append(scores, note);
    card.append(controls);
  }
  return card;
}

function renderCaseProgress() {
  const container = $("#case-progress");
  container.replaceChildren();
  state.config.cases.forEach((caseData, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = caseData.case_id;
    button.title = caseData.title;
    button.className = "case-dot";
    if (index === state.currentCaseIndex) button.classList.add("is-current");
    if (caseIsComplete(caseData)) button.classList.add("is-complete");
    button.addEventListener("click", () => {
      state.currentCaseIndex = index;
      renderCase();
    });
    container.append(button);
  });
}

function renderCase() {
  const caseData = state.config.cases[state.currentCaseIndex];
  setActiveItem(caseData);
  $("#split-label").textContent = caseData.split === "development"
    ? "Blinded development comparison"
    : "Frozen holdout";
  $("#case-title").textContent = `${caseData.case_id} · ${caseData.title}`;
  $("#case-counter").textContent = `Case ${state.currentCaseIndex + 1} of ${state.config.cases.length}`;

  const focus = $("#focus-list");
  focus.replaceChildren(...caseData.focus.map((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    return item;
  }));

  const grid = $("#comparison-grid");
  grid.className = `comparison-grid ${caseData.split === "development" ? "development-grid" : "holdout-grid"}`;
  grid.replaceChildren();
  grid.append(buildEvidenceCard({
    caseData,
    pane: "source",
    label: "Source garment",
    source: true,
  }));
  itemsForCase(caseData).forEach((item) => {
    grid.append(buildEvidenceCard({
      caseData,
      item,
      pane: caseData.split === "development" ? item.label : "output",
      label: caseData.split === "development" ? `Candidate ${item.label}` : "Generated output",
    }));
  });

  $$("#mode-tabs button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.mode === state.mode);
  });
  $("#previous-case").disabled = state.currentCaseIndex === 0;
  $("#next-case").textContent = state.currentCaseIndex === state.config.cases.length - 1
    ? "View summary →"
    : "Next case →";
  updateProgress();
  renderCaseProgress();
}

function rateItem(itemId, score) {
  const note = state.document.ratings[itemId]?.note || state.draftNotes[itemId] || "";
  state.document.ratings[itemId] = { score, note };
  const caseData = state.config.cases[state.currentCaseIndex];
  const unanswered = itemsForCase(caseData).find(
    (item) => !Object.hasOwn(state.document.ratings, item.item_id),
  );
  state.activeItemId = unanswered ? unanswered.item_id : itemId;
  renderCase();
  saveNow();
}

function changeCase(delta) {
  const next = state.currentCaseIndex + delta;
  if (next >= 0 && next < state.config.cases.length) {
    state.currentCaseIndex = next;
    state.activeItemId = null;
    renderCase();
    window.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }
  if (delta > 0) showSummary();
}

function formatMetric(value) {
  return typeof value === "number" ? value.toFixed(3) : "Pending";
}

function renderMetricList(selector, entries) {
  const container = $(selector);
  container.replaceChildren();
  entries.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "metric-row";
    const name = document.createElement("span");
    name.textContent = label;
    const metric = document.createElement("strong");
    metric.textContent = formatMetric(value);
    row.append(name, metric);
    container.append(row);
  });
}

function renderRanking(ranking) {
  const container = $("#ranking-summary");
  container.replaceChildren();
  ranking.forEach((group) => {
    const row = document.createElement("div");
    row.className = "ranking-row";
    const rank = document.createElement("strong");
    rank.textContent = `#${group.rank}`;
    const methods = document.createElement("span");
    methods.textContent = group.methods.join(" = ");
    const mean = document.createElement("b");
    mean.textContent = formatMetric(group.mean);
    row.append(rank, methods, mean);
    container.append(row);
  });
}

async function showSummary() {
  if (completedCount() !== state.config.items.length) {
    const firstIncomplete = state.config.cases.findIndex((caseData) => !caseIsComplete(caseData));
    state.currentCaseIndex = firstIncomplete === -1 ? 0 : firstIncomplete;
    renderCase();
    setSaveStatus(`${state.config.items.length - completedCount()} ratings left`, "is-error");
    return;
  }
  await saveNow();
  const response = await fetch("/api/summary", { cache: "no-store" });
  if (!response.ok) {
    setSaveStatus("Could not load summary", "is-error");
    return;
  }
  const summary = await response.json();
  $("#review-view").hidden = true;
  $("#summary-view").hidden = false;
  $("#summary-completion").textContent = `${summary.completed} of ${summary.total} outputs rated.`;
  renderRanking(summary.development_ranking);
  renderMetricList("#method-summary", [
    ["Baseline", summary.development_method_means.baseline],
    ["Structured", summary.development_method_means.structured],
    ["Best-of-two", summary.development_method_means["best-of-two"]],
  ]);
  renderMetricList("#holdout-summary", [
    ["H01", summary.holdout_scores.H01],
    ["H02", summary.holdout_scores.H02],
  ]);
  $("#rater-name").value = state.document.rater.name;
  $("#review-date").value = state.document.rater.review_date;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function setLightboxZoom(zoom) {
  const image = $("#lightbox-image");
  image.classList.toggle("is-fit", zoom === 1);
  image.style.width = zoom === 1 ? "auto" : `${zoom * 100}%`;
  image.style.height = "auto";
  $$("[data-lightbox-zoom]").forEach((button) => {
    button.classList.toggle("is-active", Number(button.dataset.lightboxZoom) === zoom);
  });
}

function openLightbox(src, title) {
  $("#lightbox-title").textContent = title;
  const image = $("#lightbox-image");
  image.src = src;
  image.alt = `${title} enlarged evidence`;
  setLightboxZoom(1);
  $("#lightbox").showModal();
}

function bindEvents() {
  $$("#mode-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      state.mode = button.dataset.mode;
      renderCase();
    });
  });
  $("#previous-case").addEventListener("click", () => changeCase(-1));
  $("#next-case").addEventListener("click", () => changeCase(1));
  $("#back-to-review").addEventListener("click", () => {
    $("#summary-view").hidden = true;
    $("#review-view").hidden = false;
    renderCase();
  });
  $("#rater-name").addEventListener("input", (event) => {
    state.document.rater.name = event.target.value;
    scheduleSave();
  });
  $("#review-date").addEventListener("change", (event) => {
    state.document.rater.review_date = event.target.value;
    scheduleSave();
  });
  $("#close-lightbox").addEventListener("click", () => $("#lightbox").close());
  $$("[data-lightbox-zoom]").forEach((button) => {
    button.addEventListener("click", () => setLightboxZoom(Number(button.dataset.lightboxZoom)));
  });
  $("#lightbox").addEventListener("click", (event) => {
    if (event.target === $("#lightbox")) $("#lightbox").close();
  });
  window.addEventListener("beforeunload", () => {
    if (state.saveTimer) saveNow();
  });
  window.addEventListener("keydown", (event) => {
    if (event.target.matches("input, textarea, select") || $("#lightbox").open) return;
    const scoreByKey = { "1": 1, "2": 0.5, "3": 0 };
    if (Object.hasOwn(scoreByKey, event.key)) {
      rateItem(state.activeItemId, scoreByKey[event.key]);
    } else if (event.key === "ArrowLeft") {
      changeCase(-1);
    } else if (event.key === "ArrowRight") {
      changeCase(1);
    }
  });
}

async function init() {
  try {
    const [configResponse, reviewResponse] = await Promise.all([
      fetch("/api/config", { cache: "no-store" }),
      fetch("/api/review", { cache: "no-store" }),
    ]);
    if (!configResponse.ok || !reviewResponse.ok) throw new Error("Could not load review data");
    state.config = await configResponse.json();
    state.document = await reviewResponse.json();
    const firstIncomplete = state.config.cases.findIndex((caseData) => !caseIsComplete(caseData));
    state.currentCaseIndex = firstIncomplete === -1 ? 0 : firstIncomplete;
    bindEvents();
    renderCase();
    setSaveStatus("Saved", "is-saved");
  } catch (error) {
    setSaveStatus(error.message, "is-error");
    $("#case-title").textContent = "Could not start the review app";
  }
}

init();
