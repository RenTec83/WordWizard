# Word Wizard

Daily vocabulary app for kids: 5 new words a day, picture + meaning, two matching games and a
letter-unscramble spelling game. Flask backend, plain HTML/JS frontend, no database
(streak/stars are stored in the browser).

## Run on your Mac
    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    python app.py          # open http://localhost:5001
(Port 5001 because macOS AirPlay uses 5000.) To test on a phone on the same Wi-Fi, change the
last line of app.py to `app.run(host="0.0.0.0", port=5001)` and open `http://<mac-ip>:5001`.

## Add words
Edit `words.json` (fields: word, emoji, meaning, example). The daily set cycles through the list.

## Deploy to PythonAnywhere via GitHub
1. Push this folder to a GitHub repo.
2. On PythonAnywhere open a **Bash console**:
       git clone https://github.com/<you>/<repo>.git word-wizard
       mkvirtualenv ww --python=python3.10 && pip install -r word-wizard/requirements.txt
3. **Web** tab -> Add a new web app -> Manual configuration -> same Python version.
   - Source code / working dir: `/home/<user>/word-wizard`
   - Virtualenv: `/home/<user>/.virtualenvs/ww`
   - Edit the WSGI file: replace its contents with
         import sys
         sys.path.insert(0, "/home/<user>/word-wizard")
         from app import app as application
   - Static files: URL `/static/` -> `/home/<user>/word-wizard/static`
4. Click **Reload**. To update later: `cd word-wizard && git pull`, then Reload.
