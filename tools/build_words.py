"""Merge data/*.txt theme files (plus the legacy list) into words.json.

Line format:  word|emoji|level(1-3)|meaning|example      First line of a file: "# Theme name|emoji"
Run:  python tools/build_words.py
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEGACY = os.path.join(ROOT, "data", "legacy_words.json")


def emoji_fix(e):
    return e + "️" if len(e) == 1 else e   # force emoji (not text) presentation


def main():
    out, seen, themes = [], set(), []
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "*.txt"))):
        theme = None
        for n, line in enumerate(open(path, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                name, icon = line[1:].strip().split("|")
                theme = name.strip()
                themes.append({"name": theme, "emoji": emoji_fix(icon.strip())})
                continue
            parts = line.split("|")
            if len(parts) != 5:
                print(f"SKIP bad line {os.path.basename(path)}:{n}: {line[:50]}")
                continue
            word, emoji, level, meaning, example = [p.strip() for p in parts]
            word = word.lower()
            if not word.isalpha() or word in seen or level not in "123":
                if word in seen:
                    print(f"dup skipped: {word}")
                else:
                    print(f"invalid skipped: {word!r}")
                continue
            seen.add(word)
            out.append(dict(word=word, emoji=emoji_fix(emoji), level=int(level), theme=theme,
                            meaning=meaning, example=example))
    themes.append({"name": "Mixed Bag", "emoji": "🎁"})
    for w in json.load(open(LEGACY, encoding="utf-8")):
        if w["word"] in seen:
            continue
        seen.add(w["word"])
        L = len(w["word"])
        out.append(dict(w, emoji=emoji_fix(w["emoji"]), theme="Mixed Bag",
                        level=1 if L <= 6 else 2 if L <= 9 else 3))
    json.dump({"themes": themes, "words": out}, open(os.path.join(ROOT, "words.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(out), "words")
    for t in themes:
        c = Counter(w["level"] for w in out if w["theme"] == t["name"])
        print(f'{t["emoji"]} {t["name"]:<26} {sum(c.values()):>4}  L1={c[1]} L2={c[2]} L3={c[3]}')


if __name__ == "__main__":
    main()
