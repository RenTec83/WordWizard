import json
import os
import random
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta

from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("WORDQUEST_DB", os.path.join(BASE_DIR, "wordquest.db"))

app = Flask(__name__)

with open(os.path.join(BASE_DIR, "words.json"), encoding="utf-8") as f:
    DATA = json.load(f)
WORDS = DATA["words"]
THEMES = DATA["themes"]
WORD_BY_NAME = {w["word"]: w for w in WORDS}
THEME_BY_NAME = {t["name"]: t for t in THEMES}
POOLS = {t["name"]: {lvl: [w for w in WORDS if w["theme"] == t["name"] and w["level"] == lvl]
                     for lvl in (1, 2, 3)} for t in THEMES}

WORDS_PER_SET = 5
RANK_XP = [0, 200, 600, 1200, 2200, 4000, 8000]
# Difficulty mix of a set (easy=1 ... hard=3). Stronger players get a harder mix.
PLAN_BEGINNER = (1, 1, 2, 2, 3)
PLAN_ADVANCED = (1, 2, 2, 3, 3)
NAME_RE = re.compile(r"^\w[\w -]{1,19}$")

# ---------------------------------------------------------------- database
@contextmanager
def tx():
    con = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    con.row_factory = sqlite3.Row
    try:
        con.execute("BEGIN IMMEDIATE")
        yield con
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise
    finally:
        con.close()


def init_db():
    with tx() as con:
        con.execute("CREATE TABLE IF NOT EXISTS users (key TEXT PRIMARY KEY, name TEXT NOT NULL, "
                    "created TEXT NOT NULL, profile TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS seen (user TEXT NOT NULL, word TEXT NOT NULL, "
                    "PRIMARY KEY (user, word))")


init_db()


def new_profile():
    return dict(xp=0, streak=0, last=None, day=None, done=0, words_learned=0, sets_done=0, perfect=0,
                best=0, history=[], achievements=[], cycle=0, current=None, themes_seen=[])


def clean_name(raw):
    name = " ".join(str(raw or "").split())
    return name if NAME_RE.match(name) else None


def parse_day(raw):
    try:
        return date.fromisoformat(raw or "")
    except ValueError:
        return date.today()


def get_user(con, name):
    row = con.execute("SELECT * FROM users WHERE key=?", (name.lower(),)).fetchone()
    return (row["name"], json.loads(row["profile"])) if row else (None, None)


def save_profile(con, name, p):
    con.execute("UPDATE users SET profile=? WHERE key=?", (json.dumps(p), name.lower()))


# ---------------------------------------------------------------- achievements
ACHIEVEMENTS = [
    ("first_quest", "🚀", "First Quest", "Finish your first set of words", lambda p, c: p["sets_done"] >= 1),
    ("flawless", "🏆", "Flawless Victory", "Get every answer right first try in one set", lambda p, c: c["first_try"] == c["max_ft"]),
    ("spelling_ace", "🔤", "Spelling Ace", "Spell all 5 words right first try", lambda p, c: c["spell"] == c["n"]),
    ("sharp_eyes", "🎯", "Sharp Eyes", "Get both matching games perfect", lambda p, c: c["meaning"] == c["n"] and c["picture"] == c["n"]),
    ("triple", "⚡", "Triple Threat", "Finish 3 sets in one day", lambda p, c: p["done"] >= 3),
    ("streak3", "🔥", "On a Roll", "Play 3 days in a row", lambda p, c: p["streak"] >= 3),
    ("streak7", "🌋", "Week Warrior", "Play 7 days in a row", lambda p, c: p["streak"] >= 7),
    ("streak30", "☄️", "Unstoppable", "Play 30 days in a row", lambda p, c: p["streak"] >= 30),
    ("words25", "📗", "25 Words", "Learn 25 words", lambda p, c: p["words_learned"] >= 25),
    ("words100", "📘", "100 Words", "Learn 100 words", lambda p, c: p["words_learned"] >= 100),
    ("words500", "📙", "500 Words", "Learn 500 words", lambda p, c: p["words_learned"] >= 500),
    ("words1000", "📕", "1000 Words", "Learn 1000 words", lambda p, c: p["words_learned"] >= 1000),
    ("explorer", "🧭", "Theme Explorer", "Learn words from 8 different themes", lambda p, c: len(p["themes_seen"]) >= 8),
    ("high_score", "💎", "High Roller", "Score 180+ points in one set", lambda p, c: c["pts"] >= 180),
]


def stars_for(first_try, max_ft):
    return 3 if first_try >= max_ft - 1 else 2 if first_try >= max_ft * .6 else 1


# ---------------------------------------------------------------- picking words
def rank_index(xp):
    return max(i for i, need in enumerate(RANK_XP) if xp >= need)


def pick_set(key, p, seen):
    """Pick 5 words this child has never finished: one theme, a mix of easy..hard.
    Returns (theme, [words]) or None when fewer than 5 unseen words remain."""
    rng = random.Random(f"{key}:order")
    order = THEMES[:]
    rng.shuffle(order)
    theme = order[p["sets_done"] % len(order)]
    plan = PLAN_ADVANCED if rank_index(p["xp"]) >= 2 else PLAN_BEGINNER

    def shuffled(pool, tag):
        pool = pool[:]
        random.Random(f"{key}:{p['cycle']}:{tag}").shuffle(pool)
        return pool

    picked, names, emojis = [], set(), set()

    def take(cands):
        for w in cands:
            if w["word"] not in seen and w["word"] not in names and w["emoji"] not in emojis:
                picked.append(w)
                names.add(w["word"])
                emojis.add(w["emoji"])
                return True
        return False

    pools = POOLS[theme["name"]]
    for lvl in plan:
        if take(shuffled(pools[lvl], f"{theme['name']}:{lvl}")):
            continue
        for alt in sorted((1, 2, 3), key=lambda x: abs(x - lvl)):       # same theme, nearest level
            if take(shuffled(pools[alt], f"{theme['name']}:{alt}")):
                break
        else:                                                           # any theme, same level
            if not take(shuffled([w for w in WORDS if w["level"] == lvl], f"all:{lvl}")):
                take(shuffled(WORDS, "all"))
    if len(picked) < WORDS_PER_SET:
        return None
    return theme, sorted(picked, key=lambda w: w["level"])


def current_set(con, key, name, p):
    """The child's active set; creates it when there is none. Words are only marked as seen once
    the set is finished, so refreshing the page does not use up words."""
    restarted = False
    if not p["current"]:
        seen = {r["word"] for r in con.execute("SELECT word FROM seen WHERE user=?", (key,))}
        result = pick_set(key, p, seen)
        if result is None:                       # every word has been learned: start a new round
            con.execute("DELETE FROM seen WHERE user=?", (key,))
            p["cycle"] += 1
            restarted = True
            result = pick_set(key, p, set())
        theme, words = result
        p["current"] = {"theme": theme["name"], "words": [w["word"] for w in words]}
        save_profile(con, name, p)
    cur = p["current"]
    return THEME_BY_NAME[cur["theme"]], [WORD_BY_NAME[w] for w in cur["words"]], restarted


def view(name, p, d):
    """What the browser needs to draw the home screen."""
    yesterday = (d - timedelta(days=1)).isoformat()
    streak = p["streak"] if p["last"] in (d.isoformat(), yesterday) else 0
    return {
        "name": name, "xp": p["xp"], "streak": streak, "wordsLearned": p["words_learned"],
        "setsDone": p["sets_done"], "perfect": p["perfect"], "best": p["best"],
        "doneToday": p["done"] if p["day"] == d.isoformat() else 0,
        "history": p["history"][-5:], "totalWords": len(WORDS), "cycle": p["cycle"],
        "achievements": [{"id": a[0], "emoji": a[1], "name": a[2], "desc": a[3],
                          "unlocked": a[0] in p["achievements"]} for a in ACHIEVEMENTS],
    }


# ---------------------------------------------------------------- routes
@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/login")
def login():
    body = request.get_json(silent=True) or {}
    name = clean_name(body.get("username"))
    if not name:
        return jsonify(error="Use 2-20 letters, numbers, spaces, - or _"), 400
    d = parse_day(body.get("d"))
    with tx() as con:
        existing, p = get_user(con, name)
        is_new = existing is None
        if is_new:
            p = new_profile()
            con.execute("INSERT INTO users (key, name, created, profile) VALUES (?,?,?,?)",
                        (name.lower(), name, date.today().isoformat(), json.dumps(p)))
        else:
            name = existing
    return jsonify(profile=view(name, p, d), new=is_new)


@app.get("/api/set")
def get_set():
    name = clean_name(request.args.get("u"))
    d = parse_day(request.args.get("d"))
    if not name:
        return jsonify(error="unknown player"), 404
    with tx() as con:
        name, p = get_user(con, name)
        if p is None:
            return jsonify(error="unknown player"), 404
        theme, words, restarted = current_set(con, name.lower(), name, p)
    return jsonify(theme=theme, words=words, restarted=restarted, doneToday=view(name, p, d)["doneToday"])


def _int(v, lo, hi):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return lo


@app.post("/api/complete")
def complete():
    body = request.get_json(silent=True) or {}
    name = clean_name(body.get("username"))
    d = parse_day(body.get("d"))
    if not name:
        return jsonify(error="unknown player"), 404
    with tx() as con:
        name, p = get_user(con, name)
        if p is None:
            return jsonify(error="unknown player"), 404
        if not p["current"]:
            return jsonify(error="no active set"), 409      # already submitted
        key, cur = name.lower(), p["current"]
        n = len(cur["words"])
        scores = {k: _int((body.get("scores") or {}).get(k), 0, n) for k in ("meaning", "picture", "spell")}
        pts = _int(body.get("pts"), 0, 40 * n)
        first_try, max_ft = sum(scores.values()), 3 * n
        stars = stars_for(first_try, max_ft)

        yesterday = (d - timedelta(days=1)).isoformat()
        if p["last"] != d.isoformat():
            p["streak"] = p["streak"] + 1 if p["last"] == yesterday else 1
            p["last"] = d.isoformat()
        if p["day"] != d.isoformat():
            p["day"], p["done"] = d.isoformat(), 0
        p["done"] += 1
        p["xp"] += pts
        p["words_learned"] += n
        p["sets_done"] += 1
        p["best"] = max(p["best"], pts)
        p["perfect"] += first_try == max_ft
        p["history"] = (p["history"] + [{"date": d.isoformat(), "pts": pts, "stars": stars,
                                         "theme": cur["theme"]}])[-20:]
        if cur["theme"] not in p["themes_seen"]:
            p["themes_seen"].append(cur["theme"])
        con.executemany("INSERT OR IGNORE INTO seen (user, word) VALUES (?,?)", [(key, w) for w in cur["words"]])
        p["current"] = None

        ctx = dict(scores, n=n, pts=pts, first_try=first_try, max_ft=max_ft)
        new = [a for a in ACHIEVEMENTS if a[0] not in p["achievements"] and a[4](p, ctx)]
        p["achievements"] += [a[0] for a in new]
        save_profile(con, name, p)
    return jsonify(profile=view(name, p, d), stars=stars, pts=pts,
                   newAchievements=[{"id": a[0], "emoji": a[1], "name": a[2], "desc": a[3]} for a in new])


if __name__ == "__main__":
    app.run(debug=True, port=5001)
