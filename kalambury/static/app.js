const $ = (id) => document.getElementById(id);
const ROUND_S = 60;   // czas na rysunek w trybie gry
const ROW = 34;       // wysokość wiersza słupka, jak --row w CSS
const canvas = $("canvas"), ctx = canvas.getContext("2d");

let words = [], byKey = {}, strokes = [], cur = null;
let mode = "game", target = null, roundId = 0, roundStart = 0, roundOver = false, timerId = null, recent = [];
let inflight = false, dirty = false, version = 0, last = null;
const score = { ok: 0, all: 0 }, rows = new Map();

const pct = (p) => (p * 100).toLocaleString("pl-PL", { maximumFractionDigits: p < 0.1 ? 1 : 0 }) + "%";
const plural = (n, one, few, many) =>
  n === 1 ? one : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? few : many;
const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);

// ---- płótno: kreski trzymamy w układzie 0..1000, więc zmiana rozmiaru okna ich nie psuje
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

// ---- zapytania: najwyżej jedno naraz; kreski dorysowane w trakcie idą w następnym
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
                                          body: JSON.stringify({ strokes }) });
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

// ---- co myśli model
function show(res) {
  const p = res.confidence, name = esc(byKey[res.choice]);
  $("say").innerHTML = p >= 0.8 ? `Wiem! To <b>${name}</b>.` : p >= 0.4 ? `Chyba <b>${name}</b>…` : `Hmm… może <b>${name}</b>?`;
  $("say").parentElement.classList.toggle("sure", p >= 0.8);
  bars(res.ranking.slice(0, 10));
  const u = res.usage;
  $("stats").innerHTML = [
    `<b>${(res.wall_ms / 1000).toLocaleString("pl-PL", { maximumFractionDigits: 1 })} s</b>`,
    `<b>${u.input_tokens}</b> ${plural(u.input_tokens, "token", "tokeny", "tokenów")} na wejściu`,
    `<b>${u.output_tokens}</b> wygenerowanych`, `<b>${res.ranking.length}</b> haseł w jednym pytaniu`,
  ].map((s) => `<span>${s}</span>`).join("");
  $("seen").src = res.image;
  if (target) {
    const i = res.ranking.findIndex((t) => t.key === target);
    $("tline").innerHTML = `Twoje hasło <b>${esc(byKey[target])}</b>: miejsce ${i + 1} z ${res.ranking.length} (${pct(res.ranking[i].p)})`;
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
      el.querySelector(".name").textContent = t.pl;
      el.style.opacity = 0;
      el.style.transform = `translateY(${i * ROW}px)`;
      $("bars").append(el);
      rows.set(t.key, el);
      el.getBoundingClientRect();  // nowy wiersz startuje od zera, żeby słupek wyrósł z animacją
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
  $("say").textContent = "Zacznij rysować…";
  $("say").parentElement.classList.remove("sure");
  for (const el of rows.values()) el.remove();
  rows.clear();
  $("stats").innerHTML = "";
  $("tline").innerHTML = "";
  $("seen").removeAttribute("src");
  last = null;
}

// ---- gra: hasło, minuta na rysunek, model ma trafić hasło jako swój pierwszy wybór
function pick() {
  const pool = words.filter((w) => !recent.includes(w.key));
  const w = pool[Math.floor(Math.random() * pool.length)].key;
  recent = [w, ...recent].slice(0, 30);
  return w;
}
function newRound() {
  clearInterval(timerId);
  roundId++;
  roundOver = false;
  target = pick();
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
  if (inflight) roundOver = "waiting";  // ostatnie zgadywanie jeszcze się liczy
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
  const secs = ((performance.now() - roundStart) / 1000).toLocaleString("pl-PL", { maximumFractionDigits: 0 });
  const b = $("banner");
  b.className = "banner" + (ok ? "" : " fail");
  b.innerHTML = ok
    ? `✓ basal zgadł: <b>${esc(byKey[target])}</b>, pewność ${pct(res.confidence)} (${strokes.length} ${plural(strokes.length, "kreska", "kreski", "kresek")}, ${secs} s). <kbd>N</kbd> następne hasło`
    : `Czas minął. basal stawiał na: <b>${last ? esc(byKey[last.choice]) : "nic"}</b>. <kbd>N</kbd> następne hasło`;
  b.hidden = false;
  $("score").textContent = `Wynik: ${score.ok}/${score.all}`;
}

// ---- tryby, przyciski, klawisze
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
  fit();
  const r = await (await fetch("/api/words")).json();
  words = r.words;
  for (const w of words) byKey[w.key] = w.pl;
  $("wordlist").textContent = words.map((w) => w.pl).sort((a, b) => a.localeCompare(b, "pl")).join(", ");
  const m = $("model");
  m.textContent = r.model ? `● ${r.model}` : "● basal-serve nie działa";
  m.className = "badge " + (r.model ? "ok" : "off");
  newRound();
})();
