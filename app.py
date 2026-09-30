import json
import os
from datetime import date

from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORDS_PER_DAY = 5

app = Flask(__name__)

with open(os.path.join(BASE_DIR, "words.json"), encoding="utf-8") as f:
    WORDS = json.load(f)


SETS_PER_DAY = 4  # each day owns this many distinct sets before overlapping tomorrow's


def words_for(day: date, set_no: int = 0):
    """Same 5 words for everyone on a given day/set; cycles through the whole list."""
    set_no %= SETS_PER_DAY
    start = (day.toordinal() * WORDS_PER_DAY * SETS_PER_DAY + set_no * WORDS_PER_DAY) % len(WORDS)
    return [WORDS[(start + i) % len(WORDS)] for i in range(WORDS_PER_DAY)]


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
    return jsonify({"date": day.isoformat(), "set": set_no, "words": words_for(day, set_no)})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
