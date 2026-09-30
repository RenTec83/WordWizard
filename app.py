import json
import os
from datetime import date

from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

with open(os.path.join(BASE_DIR, "words.json"), encoding="utf-8") as f:
    DATA = json.load(f)
THEMES = DATA["themes"]
BY_THEME = {t["name"]: {lvl: [w for w in DATA["words"] if w["theme"] == t["name"] and w["level"] == lvl]
                        for lvl in (1, 2, 3)} for t in THEMES}

SETS_PER_DAY = 4  # sets a child can play per day before the rotation moves on
# Each set has one theme and a mix of difficulty: 2 easy, 2 medium, 1 hard word.
LEVEL_PLAN = (1, 1, 2, 2, 3)


def words_for(day: date, set_no: int = 0):
    """Same 5 words for everyone on a given day/set. Themes rotate; words within a theme cycle."""
    k = day.toordinal() * SETS_PER_DAY + set_no % SETS_PER_DAY
    theme = THEMES[k % len(THEMES)]
    round_no = k // len(THEMES)
    pools, picked, taken = BY_THEME[theme["name"]], [], set()
    for slot, lvl in enumerate(LEVEL_PLAN):
        pool = pools[lvl] or pools[2] or pools[1] or pools[3]
        # the n-th word of this level in this round; step forward if its emoji/word is already in the set
        n = round_no * LEVEL_PLAN.count(lvl) + LEVEL_PLAN[:slot].count(lvl)
        for step in range(len(pool)):
            w = pool[(n + step) % len(pool)]
            if w["word"] not in taken and w["emoji"] not in taken:
                picked.append(w)
                taken.update((w["word"], w["emoji"]))
                break
    return theme, picked


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/today")
def today():
    # The browser sends its own local date so "today" matches the child's timezone.
    try:
        day = date.fromisoformat(request.args.get("d", ""))
    except ValueError:
        day = date.today()
    set_no = request.args.get("set", 0, type=int)
    theme, words = words_for(day, set_no)
    return jsonify({"date": day.isoformat(), "set": set_no, "theme": theme, "words": words})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
