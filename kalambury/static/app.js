const $ = (id) => document.getElementById(id);
const ROUND_S = 60;   // seconds per drawing in game mode
const ROW = 34;       // bar row height, same as --row in CSS
const canvas = $("canvas"), ctx = canvas.getContext("2d");

// ---- language and word pack: from the URL, else the last choice, else the browser language
const params = new URLSearchParams(location.search);
const stored = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
const pick1 = (v, ok, dflt) => (ok.includes(v) ? v : dflt);
const lang = pick1(params.get("lang") || stored("lang"), ["pl", "en"],
                   (navigator.language || "").toLowerCase().startsWith("pl") ? "pl" : "en");
const pack = pick1(params.get("pack") || stored("pack"), ["quickdraw", "nerd"], "quickdraw");
try { localStorage.setItem("lang", lang); localStorage.setItem("pack", pack); } catch { /* private mode */ }
const go = (change) => { location.search = new URLSearchParams({ lang, pack, ...change }).toString(); };
const loc = lang === "pl" ? "pl-PL" : "en-US";

// plural(n, one, few, many): "few" (2-4 except 12-14) exists only in Polish
const plural = (n, one, few, many) => n === 1 ? one
  : lang === "pl" && n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? few : many;
const T = {
  pl: {
    lead: "Rysuj, a basal zgaduje spośród <b>255 haseł naraz</b>: jeden przebieg modelu, rozkład prawdopodobieństwa zamiast tekstu, <b>0 wygenerowanych tokenów</b>.",
    game: "Gra", free: "Wolne rysowanie", nerd: "IT i nerdy", draw: "Narysuj:",
    undo: "↶ Cofnij", clear: "Wyczyść", next: "Nowe hasło", busy: "basal patrzy…", start: "Zacznij rysować…",
    eye: "Tak rysunek trafia do modelu: kadrowany do kresek, 384×384 px, ten sam renderer co w benchmarku.",
    sure: (w) => `Wiem! To <b>${w}</b>.`, maybe: (w) => `Chyba <b>${w}</b>…`, hmm: (w) => `Hmm… może <b>${w}</b>?`,
    tokens: (n) => `<b>${n}</b> ${plural(n, "token", "tokeny", "tokenów")} na wejściu`,
    generated: (n) => `<b>${n}</b> wygenerowanych`, options: (n) => `<b>${n}</b> haseł w jednym pytaniu`,
    rank: (w, i, n, p) => `Twoje hasło <b>${w}</b>: miejsce ${i} z ${n} (${p})`,
    win: (w, p, n, s) => `✓ basal zgadł: <b>${w}</b>, pewność ${p} (${n} ${plural(n, "kreska", "kreski", "kresek")}, ${s} s). <kbd>N</kbd> następne hasło`,
    lose: (w) => `Czas minął. basal stawiał na: <b>${w}</b>. <kbd>N</kbd> następne hasło`, nothing: "nic",
    score: (ok, all) => `Wynik: ${ok}/${all}`, down: "● basal-serve nie działa",
    info: (m) => [m.engine && `silnik ${m.engine}`, m.mode && `tryb ${m.mode}`, m.released && `model z ${m.released}`]
      .filter(Boolean).join(" · "),
    list_quickdraw: (n) => `Lista ${n} haseł`,
    list_nerd: (n, rest) => `${n} haseł z paczki „IT i nerdy” (plus ${rest} zwykłych haseł z Quick, Draw! jako pułapki)`,
    footer: 'Rysunki do benchmarku: Google <a href="https://quickdraw.withgoogle.com/data">Quick, Draw!</a> (CC BY 4.0) · model i silnik: <a href="https://github.com/rkinas/basal">basal</a> (Apache-2.0) · skróty: <kbd>Z</kbd> cofnij, <kbd>C</kbd> wyczyść, <kbd>N</kbd> nowe hasło',
  },
  en: {
    lead: "Pictionary (<i>kalambury</i> in Polish): you draw, basal guesses among <b>255 words at once</b>. One forward pass, a probability distribution instead of text, <b>0 generated tokens</b>.",
    game: "Game", free: "Free draw", nerd: "IT & nerds", draw: "Draw:",
    undo: "↶ Undo", clear: "Clear", next: "New word", busy: "basal is looking…", start: "Start drawing…",
    eye: "What the model sees: cropped to the strokes, 384×384 px, the same renderer as in the benchmark.",
    sure: (w) => `I know: <b>${w}</b>!`, maybe: (w) => `Maybe <b>${w}</b>…`, hmm: (w) => `Hmm… <b>${w}</b>?`,
    tokens: (n) => `<b>${n}</b> input ${plural(n, "token", "tokens", "tokens")}`,
    generated: (n) => `<b>${n}</b> generated`, options: (n) => `<b>${n}</b> words in one question`,
    rank: (w, i, n, p) => `Your word <b>${w}</b>: rank ${i} of ${n} (${p})`,
    win: (w, p, n, s) => `✓ basal got it: <b>${w}</b>, ${p} sure (${n} ${plural(n, "stroke", "strokes", "strokes")}, ${s} s). <kbd>N</kbd> next word`,
    lose: (w) => `Time's up. basal's best guess: <b>${w}</b>. <kbd>N</kbd> next word`, nothing: "nothing",
    score: (ok, all) => `Score: ${ok}/${all}`, down: "● basal-serve is down",
    info: (m) => [m.engine && `${m.engine} engine`, m.mode && `${m.mode} mode`, m.released && `released ${m.released}`]
      .filter(Boolean).join(" · "),
    list_quickdraw: (n) => `All ${n} words`,
    list_nerd: (n, rest) => `The ${n} IT & nerd words (plus ${rest} everyday Quick, Draw! words as decoys)`,
    footer: 'Benchmark drawings: Google <a href="https://quickdraw.withgoogle.com/data">Quick, Draw!</a> (CC BY 4.0) · model and engine: <a href="https://github.com/rkinas/basal">basal</a> (Apache-2.0), asked in Polish · keys: <kbd>Z</kbd> undo, <kbd>C</kbd> clear, <kbd>N</kbd> new word',
  },
}[lang];

let words = [], targets = [], byKey = {}, strokes = [], cur = null;
let mode = "game", target = null, roundId = 0, roundStart = 0, roundOver = false, timerId = null, recent = [];
let inflight = false, dirty = false, version = 0, last = null;
const score = { ok: 0, all: 0 }, rows = new Map();

const pct = (p) => (p * 100).toLocaleString(loc, { maximumFractionDigits: p < 0.1 ? 1 : 0 }) + "%";
const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);

// ---- canvas: strokes live in a 0..1000 space, so resizing the window does not break them
function fit() {
  const r = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(r.width * dpr);
  canvas.height = Math.round(r.height * dpr);
  ctx.setTransform(dpr * r.width / 1000, 0, 0, dpr * r.height / 1000, 0, 0);
  redraw();
}
function pen() {
  ctx.lineWidth = 5 * 1000 / canvas.getBoundingClientRect().width;
  ctx.lineCap = ctx.lineJoin = "round";
  ctx.strokeStyle = "#111";
}
function redraw() {
  ctx.clearRect(0, 0, 1000, 1000);
  pen();
  for (const [xs, ys] of strokes) {
    ctx.beginPath();
    ctx.moveTo(xs[0], ys[0]);
    for (let i = 1; i < xs.length; i++) ctx.lineTo(xs[i], ys[i]);
    if (xs.length === 1) ctx.lineTo(xs[0] + 0.1, ys[0]);
    ctx.stroke();
  }
}
function pos(e) {
  const r = canvas.getBoundingClientRect();
  return [Math.round((e.clientX - r.left) / r.width * 1000), Math.round((e.clientY - r.top) / r.height * 1000)];
}
canvas.addEventListener("pointerdown", (e) => {
  if (mode === "game" && roundOver) return;
  canvas.setPointerCapture(e.pointerId);
  const [x, y] = pos(e);
  cur = [[x], [y]];
  strokes.push(cur);
  redraw();
});
canvas.addEventListener("pointermove", (e) => {
  if (!cur) return;
  const [x, y] = pos(e), [xs, ys] = cur, n = xs.length - 1;
  if (Math.hypot(x - xs[n], y - ys[n]) < 6) return;
  pen();
  ctx.beginPath();
  ctx.moveTo(xs[n], ys[n]);
  ctx.lineTo(x, y);
  ctx.stroke();
  xs.push(x);
  ys.push(y);
});
const endStroke = () => { if (cur) { cur = null; changed(); } };
canvas.addEventListener("pointerup", endStroke);
canvas.addEventListener("pointercancel", endStroke);

// ---- requests: at most one at a time; strokes drawn meanwhile go in the next one
function changed() {
  version++;
  if (strokes.length) send();
  else resetMind();
}
async function send() {
  if (inflight) { dirty = true; return; }
  inflight = true; dirty = false;
  $("busy").hidden = false;
  const v = version, rid = roundId;
  try {
    const r = await fetch("/api/guess", { method: "POST", headers: { "content-type": "application/json" },
                                          body: JSON.stringify({ strokes, pack }) });
    const res = await r.json();
    if (!r.ok) throw new Error(res.error || r.statusText);
    if (rid === roundId && (v === version || strokes.length)) {
      last = res;
      show(res);
      if (mode === "game" && roundOver !== true) judge(res);
    }
  } catch (err) {
    $("say").innerHTML = `<span class="err">${esc(String(err.message || err))}</span>`;
  }
  inflight = false;
  $("busy").hidden = true;
  if (dirty && strokes.length && !(mode === "game" && roundOver)) send();
}

// ---- what the model thinks
function show(res) {
  const p = res.confidence, name = esc(byKey[res.choice]);
  $("say").innerHTML = p >= 0.8 ? T.sure(name) : p >= 0.4 ? T.maybe(name) : T.hmm(name);
  $("say").parentElement.classList.toggle("sure", p >= 0.8);
  bars(res.ranking.slice(0, 10));
  const u = res.usage;
  $("stats").innerHTML = [
    `<b>${(res.wall_ms / 1000).toLocaleString(loc, { maximumFractionDigits: 1 })} s</b>`,
    T.tokens(u.input_tokens), T.generated(u.output_tokens), T.options(res.ranking.length),
  ].map((s) => `<span>${s}</span>`).join("");
  $("seen").src = res.image;
  if (target) {
    const i = res.ranking.findIndex((t) => t.key === target);
    $("tline").innerHTML = T.rank(esc(byKey[target]), i + 1, res.ranking.length, pct(res.ranking[i].p));
  }
}
function bars(top) {
  const keep = new Set(top.map((t) => t.key));
  for (const [k, el] of rows) {
    if (!keep.has(k)) { el.style.opacity = 0; setTimeout(() => el.remove(), 300); rows.delete(k); }
  }
  top.forEach((t, i) => {
    let el = rows.get(t.key);
    if (!el) {
      el = document.createElement("div");
      el.className = "bar";
      el.innerHTML = `<span class="name"></span><span class="track"><i class="fill"></i></span><span class="pct"></span>`;
      el.querySelector(".name").textContent = byKey[t.key];
      el.style.opacity = 0;
      el.style.transform = `translateY(${i * ROW}px)`;
      $("bars").append(el);
      rows.set(t.key, el);
      el.getBoundingClientRect();  // a new row starts from zero, so its bar grows with the animation
      el.style.opacity = 1;
    }
    el.style.transform = `translateY(${i * ROW}px)`;
    el.classList.toggle("top", i === 0);
    el.classList.toggle("target", t.key === target);
    el.querySelector(".fill").style.width = Math.max(t.p * 100, 0.4) + "%";
    el.querySelector(".pct").textContent = pct(t.p);
  });
}
function resetMind() {
  $("say").textContent = T.start;
  $("say").parentElement.classList.remove("sure");
  for (const el of rows.values()) el.remove();
  rows.clear();
  $("stats").innerHTML = "";
  $("tline").innerHTML = "";
  $("seen").removeAttribute("src");
  last = null;
}

// ---- game: a word, a minute per drawing, the model has to put the word first
function pickWord() {
  const pool = targets.filter((k) => !recent.includes(k));
  const w = pool[Math.floor(Math.random() * pool.length)];
  recent = [w, ...recent].slice(0, Math.min(30, targets.length - 1));
  return w;
}
function newRound() {
  clearInterval(timerId);
  roundId++;
  roundOver = false;
  target = pickWord();
  strokes = [];
  version++;
  redraw();
  resetMind();
  $("banner").hidden = true;
  $("target").textContent = byKey[target];
  roundStart = performance.now();
  timerId = setInterval(tick, 100);
}
function tick() {
  const left = 1 - (performance.now() - roundStart) / (ROUND_S * 1000);
  $("timer").style.width = Math.max(0, left) * 100 + "%";
  if (left > 0) return;
  clearInterval(timerId);
  if (inflight) roundOver = "waiting";  // the guess in flight still counts
  else finish(false);
}
function judge(res) {
  if (res.choice === target) finish(true, res);
  else if (roundOver === "waiting") finish(false);
}
function finish(ok, res) {
  clearInterval(timerId);
  roundOver = true;
  score.all++;
  if (ok) score.ok++;
  const secs = ((performance.now() - roundStart) / 1000).toLocaleString(loc, { maximumFractionDigits: 0 });
  const b = $("banner");
  b.className = "banner" + (ok ? "" : " fail");
  b.innerHTML = ok ? T.win(esc(byKey[target]), pct(res.confidence), strokes.length, secs)
                   : T.lose(last ? esc(byKey[last.choice]) : T.nothing);
  b.hidden = false;
  $("score").textContent = T.score(score.ok, score.all);
}

// ---- modes, buttons, keys
function setMode(m) {
  mode = m;
  document.body.classList.toggle("free", m === "free");
  document.querySelectorAll(".modes button").forEach((b) => b.classList.toggle("on", b.dataset.mode === m));
  if (m === "game") return newRound();
  clearInterval(timerId);
  roundId++;
  roundOver = false;
  target = null;
  strokes = [];
  version++;
  redraw();
  resetMind();
  $("banner").hidden = true;
}
function undo() { if (!(mode === "game" && roundOver) && strokes.pop()) { redraw(); changed(); } }
function clear() { if (!(mode === "game" && roundOver)) { strokes = []; redraw(); changed(); } }
document.querySelectorAll(".modes button").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
document.querySelectorAll(".packs button").forEach((b) => {
  b.classList.toggle("on", b.dataset.pack === pack);
  b.addEventListener("click", () => b.dataset.pack !== pack && go({ pack: b.dataset.pack }));
});
document.querySelectorAll(".langs button").forEach((b) => {
  b.classList.toggle("on", b.dataset.lang === lang);
  b.addEventListener("click", () => b.dataset.lang !== lang && go({ lang: b.dataset.lang }));
});
$("undo").addEventListener("click", undo);
$("clear").addEventListener("click", clear);
$("next").addEventListener("click", newRound);
document.addEventListener("keydown", (e) => {
  if (e.key === "z" || e.key === "Z") undo();
  else if (e.key === "c" || e.key === "C") clear();
  else if ((e.key === "n" || e.key === "N") && mode === "game") newRound();
});
window.addEventListener("resize", fit);

(async () => {
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-t]").forEach((el) => { el.innerHTML = T[el.dataset.t]; });
  fit();
  const r = await (await fetch(`/api/words?pack=${pack}`)).json();
  words = r.words;
  targets = r.targets;
  for (const w of words) byKey[w.key] = w[lang];
  $("wordsum").textContent = pack === "nerd" ? T.list_nerd(targets.length, words.length - targets.length)
                                             : T.list_quickdraw(targets.length);
  $("wordlist").textContent = targets.map((k) => byKey[k]).sort((a, b) => a.localeCompare(b, lang)).join(", ");
  const m = $("model"), info = r.model;
  if (info) {  // the exact model: its Hugging Face id, size, engine version, mode and release date
    const id = `Remek/${info.name}`;
    m.innerHTML = `● <a href="https://huggingface.co/${esc(id)}" target="_blank" rel="noopener">${esc(id)}</a>`
      + (info.params ? ` · ${esc(info.params)}` : "");
    $("modelinfo").textContent = T.info(info);
  } else {
    m.textContent = T.down;
  }
  m.className = "badge " + (info ? "ok" : "off");
  newRound();
})();
