const app = document.getElementById("app");
const $streak = document.getElementById("streak");
let words = [], theme = {}, today = "", setNo = 0;
let gameScores = {};   // first-try correct counts per game for the current set

const RANKS = [
  [0, "Rookie", "🥚"], [200, "Word Scout", "🔍"], [600, "Word Ninja", "🥷"], [1200, "Lexicon Knight", "⚔️"],
  [2200, "Vocab Master", "🧙"], [4000, "Word Legend", "👑"], [8000, "Dictionary God", "⚡"],
];
const POINTS = { meaning: [10, 3], picture: [10, 3], spell: [20, 5] };  // [first try, got there eventually]
const LEVELS = { 1: "Easy ★", 2: "Medium ★★", 3: "Hard ★★★" };
const GAME_NAMES = { meaning: "Word Match", picture: "Picture Match", spell: "Spell It" };

const shuffle = a => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const pad = n => String(n).padStart(2, "0");
const fmt = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const say = t => { try { speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t); u.rate = .85; speechSynthesis.speak(u); } catch (e) {} };
const load = () => { try { return JSON.parse(localStorage.getItem("ww") || "{}"); } catch (e) { return {}; } };
const save = s => { try { localStorage.setItem("ww", JSON.stringify(s)); } catch (e) {} };
const rankIdx = xp => RANKS.reduce((r, x, i) => xp >= x[0] ? i : r, 0);
function showStreak() { const s = load(); $streak.textContent = s.streak ? `🔥 ${s.streak}` : ""; }

function confetti(n, pool) {
  for (let i = 0; i < n; i++) {
    const e = document.createElement("span");
    e.className = "fx"; e.textContent = pool[i % pool.length];
    e.style.left = Math.random() * 100 + "vw"; e.style.fontSize = 18 + Math.random() * 22 + "px";
    e.style.animationDuration = 1.8 + Math.random() * 2 + "s"; e.style.animationDelay = Math.random() * .8 + "s";
    document.body.append(e); setTimeout(() => e.remove(), 4800);
  }
}

// how many sets the child has already finished today = index of the next set to play
function setsDoneToday(s) { return s.day === today ? (s.done || 0) : 0; }

async function fetchSet() {
  const s = load(); setNo = setsDoneToday(s);
  const r = await fetch(`/api/today?d=${today}&set=${setNo}`);
  const data = await r.json();
  words = data.words; theme = data.theme;
}

async function start() {
  today = fmt(new Date());
  showStreak();
  await fetchSet();
  home();
}

function home() {
  const s = load(), xp = s.xp || 0, ri = rankIdx(xp), next = RANKS[ri + 1];
  const pct = next ? Math.round((xp - RANKS[ri][0]) / (next[0] - RANKS[ri][0]) * 100) : 100;
  const done = setsDoneToday(s);
  const hist = (s.history || []).slice(-5).reverse();
  app.innerHTML = `
    <div class="card"><div class="hero">${RANKS[ri][2]}</div>
      <div class="rank">${RANKS[ri][1]}</div>
      <div class="xpbar"><i style="width:${pct}%"></i></div>
      <div class="small">${xp} XP ${next ? `· ${next[0] - xp} XP to <b>${next[1]}</b>` : "· MAX RANK!"}</div>
      <div class="stats">
        <div class="stat"><b>🔥 ${s.streak || 0}</b><span>Day streak</span></div>
        <div class="stat"><b>${s.wordsLearned || 0}</b><span>Words learned</span></div>
        <div class="stat"><b>${s.perfect || 0}</b><span>Flawless sets</span></div>
        <div class="stat"><b>${s.setsDone || 0}</b><span>Quests done</span></div>
        <div class="stat"><b>${s.best || 0}</b><span>Best set score</span></div>
        <div class="stat"><b>${done}</b><span>Sets today</span></div>
      </div>
      <div class="row"><button class="${done ? "hot" : ""}" id="go">${done ? "⚡ Get 5 new words" : "▶ Start today's quest"}</button></div>
      <p class="small">${done ? "Nice! You've cleared " + done + " set" + (done > 1 ? "s" : "") + " today. Ready for more?" : "Next up: " + words.map(w => w.emoji).join(" ")}</p>
      <div class="badge">${theme.emoji} Theme: ${theme.name}</div>
    </div>
    ${hist.length ? `<div class="card"><h2>🏅 Scoreboard</h2><div class="hist">
      ${hist.map(h => `<div><span>${h.date} · ${"⭐".repeat(h.stars)}</span><b>${h.pts} pts</b></div>`).join("")}</div></div>` : ""}`;
  document.getElementById("go").onclick = async () => { if (done) await fetchSet(); gameScores = {}; learn(0); };
}

function dots(i, n) { return `<div class="dots">${Array.from({ length: n }, (_, k) => k === i ? "<b>●</b>" : "○").join("")}</div>`; }

function learn(i) {
  const w = words[i];
  app.innerHTML = `${dots(i, words.length)}<div class="card">
    <div class="badge">${theme.emoji} ${theme.name} · ${LEVELS[w.level]}</div>
    <div class="big-emoji">${w.emoji}</div><div class="word">${w.word}</div>
    <button class="speak" id="sp">🔊 Hear it</button>
    <p class="meaning">${w.meaning}</p><p class="example">“${w.example}”</p></div>
    <div class="row">${i ? '<button class="alt" id="bk">◀ Back</button>' : ""}
    <button id="nx">${i < words.length - 1 ? "Next ▶" : "Play games! 🎮"}</button></div>`;
  document.getElementById("sp").onclick = () => say(w.word);
  if (i) document.getElementById("bk").onclick = () => learn(i - 1);
  document.getElementById("nx").onclick = () => i < words.length - 1 ? learn(i + 1) : intro("meaning");
}

function intro(kind) {
  const info = { meaning: ["🧠", "Round 1: Word Match", "Tap a word, then tap its meaning."],
    picture: ["🖼️", "Round 2: Picture Match", "Tap a word, then tap its picture."],
    spell: ["🔤", "Round 3: Spell It!", "Tap the jumbled letters in the right order."] }[kind];
  app.innerHTML = `<div class="card"><div class="hero">${info[0]}</div><h2>${info[1]}</h2><p class="meaning">${info[2]}</p>
    <p class="small">Get it right on the first try for max points!</p>
    <div class="row"><button id="go">Start</button></div></div>`;
  document.getElementById("go").onclick = () => kind === "spell" ? spell(0, []) : matchGame(kind);
}

// ---- game result feedback: depends on how many words were right on the first attempt ----
const TIERS = {
  5: { hero: "🏆", title: "FLAWLESS VICTORY!", line: "5 out of 5 first try! You are UNSTOPPABLE!", fx: ["🎉", "⭐", "🏆", "✨", "🔥", "💎"], n: 60 },
  4: { hero: "🔥", title: "ON FIRE!", line: "Just one slip. Absolutely crushing it!", fx: ["🔥", "⭐", "✨"], n: 36 },
  3: { hero: "💪", title: "NICE WORK!", line: "3 first-try hits. Solid! Push for 5 next time.", fx: ["⭐", "✨"], n: 18 },
  2: { hero: "🛡️", title: "GETTING STRONGER!", line: "You're levelling up. Keep training!", fx: ["✨"], n: 8 },
  1: { hero: "🌱", title: "GOOD EFFORT!", line: "Every legend starts somewhere. You finished it!", fx: [], n: 0 },
  0: { hero: "🌱", title: "YOU DID IT!", line: "You stuck with it, and that's what counts. Try again!", fx: [], n: 0 },
};

function gameResult(kind, firstTry, next) {
  const n = words.length, t = TIERS[Math.min(firstTry, 5)];
  const [hi, lo] = POINTS[kind], pts = firstTry * hi + (n - firstTry) * lo;
  gameScores[kind] = { firstTry, pts };
  app.innerHTML = `<div class="card"><div class="hero">${t.hero}</div><h1>${t.title}</h1>
    <div class="big-score">${firstTry}/${n}</div><p class="small">right on the first try</p>
    <p class="meaning">${t.line}</p><div class="rank">+${pts} XP</div>
    <div class="row"><button id="nx">${kind === "spell" ? "See my rewards 🎁" : "Next round ▶"}</button></div></div>`;
  if (t.n) confetti(t.n, t.fx);
  document.getElementById("nx").onclick = next;
}

function matchGame(kind) {
  const left = shuffle(words.map((w, i) => ({ i, w })));
  const right = shuffle(words.map((w, i) => ({ i, w })));
  const missed = new Set();
  let selL = null, solved = 0;
  app.innerHTML = `<div class="msg" id="m">Match them all!</div><div class="cols" id="c"></div>`;
  const c = document.getElementById("c"), m = document.getElementById("m"), btns = [];
  const mk = (cls, html, side, item) => { const b = document.createElement("button"); b.className = "tile " + cls; b.innerHTML = html; b.dataset.side = side; b.dataset.i = item.i; return b; };
  left.forEach((l, k) => {
    const bl = mk("", l.w.word, "L", l), rr = right[k];
    const br = mk(kind === "picture" ? "emoji" : "", kind === "picture" ? rr.w.emoji : rr.w.meaning, "R", rr);
    if (kind === "meaning") br.style.fontSize = ".9rem";
    btns.push(bl, br); c.append(bl, br);
  });
  c.onclick = e => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.side === "L") {
      btns.forEach(x => x.dataset.side === "L" && x.classList.remove("sel"));
      selL = b; b.classList.add("sel");
    } else if (selL) {
      if (selL.dataset.i === b.dataset.i) {
        selL.classList.remove("sel"); selL.classList.add("done"); b.classList.add("done");
        selL = null; solved++; m.className = "msg good"; m.textContent = "Yes! 🎉";
        if (solved === words.length) setTimeout(() => gameResult(kind, words.length - missed.size,
          () => intro(kind === "meaning" ? "picture" : "spell")), 700);
      } else {
        missed.add(selL.dataset.i); b.classList.add("wrong"); m.className = "msg bad"; m.textContent = "Not quite, try again!";
        setTimeout(() => b.classList.remove("wrong"), 450);
      }
    }
  };
}

function scramble(word) {
  let s, n = 0;
  do { s = shuffle(word.split("")); n++; } while (s.join("") === word && n < 20);
  return s;
}

function spell(i, firstTries) {
  if (i >= words.length) return gameResult("spell", firstTries.filter(Boolean).length, finish);
  const w = words[i], letters = scramble(w.word), placed = Array(w.word.length).fill(null);
  let clean = true, locked = false;
  app.innerHTML = `${dots(i, words.length)}<div class="card">
    <div class="big-emoji" style="font-size:80px">${w.emoji}</div>
    <p class="meaning">${w.meaning}</p></div>
    <div class="slots" id="sl"></div><div class="pool" id="pl"></div><div class="msg" id="m"></div>
    <div class="row"><button class="alt" id="hint">💡 Hint</button><button class="alt" id="clr">↺ Clear</button></div>`;
  const sl = document.getElementById("sl"), pl = document.getElementById("pl"), m = document.getElementById("m");
  function draw() {
    sl.innerHTML = placed.map((p, k) => `<button class="slot ${p !== null ? "filled" : ""}" data-k="${k}">${p !== null ? letters[p].toUpperCase() : ""}</button>`).join("");
    pl.innerHTML = letters.map((ch, k) => `<button class="letter ${placed.includes(k) ? "used" : ""}" data-k="${k}">${ch.toUpperCase()}</button>`).join("");
  }
  function check() {
    const guess = placed.map(p => letters[p]).join(""), slots = [...sl.children];
    locked = true;
    if (guess === w.word) {
      slots.forEach(s => s.classList.add("ok")); m.className = "msg good"; m.textContent = "Perfect spelling! 🌟";
      setTimeout(() => spell(i + 1, firstTries.concat(clean)), 1200);
    } else {
      clean = false; slots.forEach(s => s.classList.add("no")); m.className = "msg bad"; m.textContent = "Almost! Try again.";
      setTimeout(() => { placed.fill(null); locked = false; m.textContent = ""; draw(); }, 900);
    }
  }
  pl.onclick = e => {
    const b = e.target.closest("button"); if (!b || locked) return;
    const k = +b.dataset.k, slot = placed.indexOf(null);
    if (slot < 0 || placed.includes(k)) return;
    placed[slot] = k; draw(); if (!placed.includes(null)) check();
  };
  sl.onclick = e => { const b = e.target.closest("button"); if (!b || locked) return; placed[+b.dataset.k] = null; draw(); };
  document.getElementById("clr").onclick = () => { if (!locked) { placed.fill(null); draw(); } };
  document.getElementById("hint").onclick = () => {
    if (locked) return; clean = false; placed.fill(null);
    const used = new Set();
    for (let n = 0; n < Math.min(2, w.word.length); n++) {
      const k = letters.findIndex((l, x) => l === w.word[n] && !used.has(x)); used.add(k); placed[n] = k;
    }
    draw();
  };
  draw();
}

function finish() {
  const total = Object.values(gameScores).reduce((a, g) => a + g.pts, 0);
  const firstTry = Object.values(gameScores).reduce((a, g) => a + g.firstTry, 0), maxFT = words.length * 3;
  const stars = firstTry >= maxFT - 1 ? 3 : firstTry >= maxFT * .6 ? 2 : 1;
  const s = load(), oldRank = rankIdx(s.xp || 0);
  const y = new Date(); y.setDate(y.getDate() - 1);
  if (s.last !== today) s.streak = s.last === fmt(y) ? (s.streak || 0) + 1 : 1;
  s.last = today;
  s.day = today; s.done = setsDoneToday(s) + 1;
  s.xp = (s.xp || 0) + total; s.wordsLearned = (s.wordsLearned || 0) + words.length;
  s.setsDone = (s.setsDone || 0) + 1; s.best = Math.max(s.best || 0, total);
  if (firstTry === maxFT) s.perfect = (s.perfect || 0) + 1;
  s.history = (s.history || []).concat({ date: today, pts: total, stars }).slice(-20);
  save(s); showStreak();
  const newRank = rankIdx(s.xp), up = newRank > oldRank;
  app.innerHTML = `<div class="card"><div class="hero">${stars === 3 ? "👑" : "🎁"}</div><h1>Quest complete!</h1>
    <div class="stars">${"⭐".repeat(stars)}</div>
    <div class="big-score">${total} XP</div>
    <p class="small">${firstTry} of ${maxFT} answers right on the first try</p>
    ${up ? `<p class="rankup">🚀 RANK UP! You are now a ${RANKS[newRank][2]} ${RANKS[newRank][1]}!</p>` : ""}
    <p class="meaning">Words mastered:<br><b>${words.map(w => w.emoji + " " + w.word).join("<br>")}</b></p>
    <div class="row"><button id="hm">🏅 Scoreboard</button></div></div>`;
  confetti(up || stars === 3 ? 70 : 25, ["🎉", "⭐", "🚀", "💎", "✨"]);
  document.getElementById("hm").onclick = home;
}

start();
