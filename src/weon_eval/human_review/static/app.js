"use strict";

const state = {
  config: null,
  document: null,
  currentIndex: 0,
  zoom: "fit",
  saveTimer: null,
  saveChain: Promise.resolve(),
  summary: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function ratingFor(itemId) {
  const ratings = state.document.ratings;
  if (!ratings[itemId]) {
    ratings[itemId] = { scores: {}, issues: [], note: "" };
  }
  return ratings[itemId];
}

function scoreMean(scores) {
  const values = Object.values(scores).filter((value) => value !== -1);
  if (values.length === 0) return null;
  return values.reduce((total, value) => total + value, 0) / values.length;
}

function isComplete(itemId) {
  const scores = ratingFor(itemId).scores;
  return state.config.dimensions.every((dimension) => Object.hasOwn(scores, dimension.id));
}

function completedCount() {
  return state.config.items.filter((item) => isComplete(item.item_id)).length;
}

function setSaveStatus(text, kind = "") {
  const element = $("#save-status");
  element.textContent = text;
  element.className = `save-status ${kind}`.trim();
}

function scheduleSave() {
  setSaveStatus("Unsaved", "is-pending");
  window.clearTimeout(state.saveTimer);
  state.saveTimer = window.setTimeout(() => saveNow(), 220);
}

function saveNow() {
  window.clearTimeout(state.saveTimer);
  const snapshot = JSON.stringify(state.document);
  setSaveStatus("Saving…", "is-pending");
  state.saveChain = state.saveChain.then(async () => {
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
  }).catch((error) => {
    setSaveStatus(error.message, "is-error");
  });
  return state.saveChain;
}

function updateProgress() {
  const completed = completedCount();
  const total = state.config.items.length;
  $("#progress-text").textContent = `${completed} of ${total} complete`;
}

function setZoom(mode) {
  state.zoom = mode;
  const frame = $("#evidence-frame");
  frame.className = `evidence-frame zoom-${mode}`;
  $$(".zoom-button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.zoom === mode);
  });
}

function createScoreButton(item, dimension, option, selected) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "score-button";
  button.textContent = option.label;
  button.title = option.description;
  button.dataset.value = String(option.value);
  button.setAttribute("role", "radio");
  button.setAttribute("aria-checked", selected ? "true" : "false");
  if (selected) button.classList.add("is-selected");
  button.addEventListener("click", () => {
    ratingFor(item.item_id).scores[dimension.id] = option.value;
    scheduleSave();
    renderScoring(item);
    updateProgress();
  });
  return button;
}

function renderDimensions(item) {
  const list = $("#dimension-list");
  list.replaceChildren();
  const rating = ratingFor(item.item_id);
  for (const dimension of state.config.dimensions) {
    const fragment = $("#dimension-template").content.cloneNode(true);
    fragment.querySelector(".dimension-name").textContent = dimension.label;
    const options = fragment.querySelector(".score-options");
    for (const option of state.config.score_options) {
      const selected = rating.scores[dimension.id] === option.value;
      options.append(createScoreButton(item, dimension, option, selected));
    }
    list.append(fragment);
  }
}

function renderIssues(item) {
  const container = $("#issue-tags");
  container.replaceChildren();
  const rating = ratingFor(item.item_id);
  for (const tag of state.config.issue_tags) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tag-button";
    button.textContent = tag;
    const selected = rating.issues.includes(tag);
    button.classList.toggle("is-selected", selected);
    button.setAttribute("aria-pressed", selected ? "true" : "false");
    button.addEventListener("click", () => {
      if (rating.issues.includes(tag)) {
        rating.issues = rating.issues.filter((value) => value !== tag);
      } else {
        rating.issues.push(tag);
      }
      scheduleSave();
      renderIssues(item);
    });
    container.append(button);
  }
  $("#note").value = rating.note;
}

function renderScoring(item) {
  renderDimensions(item);
  renderIssues(item);
  const mean = scoreMean(ratingFor(item.item_id).scores);
  $("#current-mean").textContent = mean === null ? "Mean —" : `Mean ${mean.toFixed(2)}`;
}

function renderCurrent() {
  const item = state.config.items[state.currentIndex];
  $("#split-label").textContent = item.split === "development" ? "Development" : "Frozen holdout";
  $("#target-title").textContent = `${item.case_id} · Candidate ${item.label}`;
  const image = $("#evidence-image");
  image.src = item.evidence_url;
  image.alt = `${item.case_id} high-resolution review sheet for candidate ${item.label}`;
  const focusList = $("#focus-list");
  focusList.replaceChildren(...item.focus.map((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    return li;
  }));
  renderScoring(item);
  updateProgress();
  $("#previous-button").disabled = state.currentIndex === 0;
  $("#next-button").textContent = state.currentIndex === state.config.items.length - 1 ? "Save & summary" : "Save & next";
}

function advance() {
  if (state.currentIndex < state.config.items.length - 1) {
    state.currentIndex += 1;
    renderCurrent();
    window.scrollTo({ top: 0, behavior: "smooth" });
  } else {
    showSummary();
  }
}

function saveAndAdvance() {
  scheduleSave();
  advance();
}

function applyPreset(value) {
  const item = state.config.items[state.currentIndex];
  const rating = ratingFor(item.item_id);
  for (const dimension of state.config.dimensions) {
    rating.scores[dimension.id] = value;
  }
  scheduleSave();
  updateProgress();
  advance();
}

function formatMetric(value) {
  return typeof value === "number" ? value.toFixed(4) : "Pending";
}

function renderMetricList(selector, entries) {
  const container = $(selector);
  container.replaceChildren();
  for (const [label, value] of entries) {
    const row = document.createElement("div");
    row.className = "metric-row";
    const name = document.createElement("span");
    name.textContent = label;
    const metric = document.createElement("strong");
    metric.textContent = formatMetric(value);
    row.append(name, metric);
    container.append(row);
  }
}

const overallSchema = [
  ["structured_outperformed", "Did structured prompting consistently outperform baseline?", ["Yes", "No", "Unclear"], "structured_reason", "Reason"],
  ["best_of_two_outperformed", "Did best-of-two consistently outperform baseline?", ["Yes", "No", "Unclear"], "best_of_two_reason", "Reason"],
  ["brand_critical_ready", "Are any outputs sufficiently faithful for brand-critical catalog use?", ["Yes", "No"], "brand_critical_reason", "Reason"],
  ["automatic_perfect_errors", "Did any automatic-perfect result contain obvious garment errors?", ["Yes", "No"], "automatic_perfect_examples", "Examples"],
  ["preferred_method", "Overall preferred development method", ["Baseline", "Structured", "Best-of-two", "No reliable winner"], "preferred_method_reason", "Reason"],
];

function renderOverallQuestions() {
  const container = $("#overall-questions");
  container.replaceChildren();
  overallSchema.forEach(([field, question, options, reasonField, reasonLabel], index) => {
    const group = document.createElement("fieldset");
    group.className = "overall-question";
    const legend = document.createElement("legend");
    legend.textContent = `${index + 1}. ${question}`;
    group.append(legend);
    const select = document.createElement("select");
    select.dataset.overallField = field;
    select.append(new Option("Select…", ""));
    for (const option of options) select.append(new Option(option, option));
    select.value = state.document.overall[field];
    select.addEventListener("change", () => {
      state.document.overall[field] = select.value;
      scheduleSave();
    });
    const input = document.createElement("textarea");
    input.rows = 2;
    input.maxLength = 500;
    input.placeholder = reasonLabel;
    input.value = state.document.overall[reasonField];
    input.addEventListener("input", () => {
      state.document.overall[reasonField] = input.value;
      scheduleSave();
    });
    group.append(select, input);
    container.append(group);
  });
}

async function showSummary() {
  await saveNow();
  const response = await fetch("/api/summary", { cache: "no-store" });
  if (!response.ok) {
    setSaveStatus("Could not load summary", "is-error");
    return;
  }
  state.summary = await response.json();
  $("#review-view").hidden = true;
  $("#summary-view").hidden = false;
  $("#summary-completion").textContent = `${state.summary.completed} of ${state.summary.total} outputs fully scored.`;
  renderMetricList("#method-summary", [
    ["Baseline", state.summary.development_method_means.baseline],
    ["Structured", state.summary.development_method_means.structured],
    ["Best-of-two", state.summary.development_method_means["best-of-two"]],
  ]);
  renderMetricList("#holdout-summary", [
    ["H01", state.summary.holdout_means.H01],
    ["H02", state.summary.holdout_means.H02],
  ]);
  $("#rater-name").value = state.document.rater.name;
  $("#review-date").value = state.document.rater.review_date;
  renderOverallQuestions();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function bindEvents() {
  $("#preserved-next").addEventListener("click", () => applyPreset(1));
  $("#partial-next").addEventListener("click", () => applyPreset(0.5));
  $("#major-next").addEventListener("click", () => applyPreset(0));
  $("#next-button").addEventListener("click", saveAndAdvance);
  $("#previous-button").addEventListener("click", () => {
    if (state.currentIndex > 0) {
      state.currentIndex -= 1;
      renderCurrent();
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });
  $("#note").addEventListener("input", (event) => {
    const item = state.config.items[state.currentIndex];
    ratingFor(item.item_id).note = event.target.value;
    scheduleSave();
  });
  $$(".zoom-button").forEach((button) => {
    button.addEventListener("click", () => setZoom(button.dataset.zoom));
  });
  $("#evidence-image").addEventListener("click", () => {
    setZoom(state.zoom === "fit" ? "native" : "fit");
  });
  $("#back-to-review").addEventListener("click", () => {
    $("#summary-view").hidden = true;
    $("#review-view").hidden = false;
    renderCurrent();
  });
  $("#rater-name").addEventListener("input", (event) => {
    state.document.rater.name = event.target.value;
    scheduleSave();
  });
  $("#review-date").addEventListener("change", (event) => {
    state.document.rater.review_date = event.target.value;
    scheduleSave();
  });
  window.addEventListener("beforeunload", () => {
    if (state.saveTimer) saveNow();
  });
  window.addEventListener("keydown", (event) => {
    if (event.target.matches("input, textarea, select")) return;
    if (event.key === "ArrowLeft" && state.currentIndex > 0) {
      state.currentIndex -= 1;
      renderCurrent();
    } else if (event.key === "ArrowRight") {
      saveAndAdvance();
    } else if (event.key.toLowerCase() === "q") {
      applyPreset(1);
    } else if (event.key.toLowerCase() === "w") {
      applyPreset(0.5);
    } else if (event.key.toLowerCase() === "e") {
      applyPreset(0);
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
    const firstIncomplete = state.config.items.findIndex((item) => !isComplete(item.item_id));
    state.currentIndex = firstIncomplete === -1 ? 0 : firstIncomplete;
    bindEvents();
    setZoom("fit");
    renderCurrent();
    setSaveStatus("Saved", "is-saved");
  } catch (error) {
    setSaveStatus(error.message, "is-error");
    $("#target-title").textContent = "Could not start the review app";
  }
}

init();
