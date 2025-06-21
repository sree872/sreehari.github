import os
import sqlite3
import threading
from datetime import datetime
import requests
from flask import Flask, request, jsonify
import spacy

# Initialize app and NLP
app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")  # Make sure to run: python -m spacy download en_core_web_sm

# Database setup
DB_PATH = "reminders.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message TEXT NOT NULL,
    remind_time TEXT NOT NULL
)
""")
conn.commit()

# Use your real API key here
WEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "<YOUR_OPENWEATHERMAP_KEY>")

def fetch_weather(city: str) -> str:
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={WEATHER_API_KEY}&units=metric"
    )
    resp = requests.get(url)
    if resp.status_code != 200:
        return "Sorry, couldn't retrieve weather."
    data = resp.json()
    temp = data["main"]["temp"]
    desc = data["weather"][0]["description"]
    return f"The weather in {city} is {temp}°C with {desc}."

def add_reminder(message: str, t: datetime):
    c.execute("INSERT INTO reminders (message, remind_time) VALUES (?, ?)", (message, t.isoformat()))
    conn.commit()

def check_reminders():
    while True:
        now = datetime.now()
        c.execute("SELECT id, message, remind_time FROM reminders")
        rows = c.fetchall()
        for rid, msg, rt in rows:
            rt_dt = datetime.fromisoformat(rt)
            if now >= rt_dt:
                print(f"[Reminder] {msg}")  # In real use, you'd email, push, etc.
                c.execute("DELETE FROM reminders WHERE id=?", (rid,))
                conn.commit()
        threading.Event().wait(60)  # check every minute

def parse_intent(user_input: str):
    doc = nlp(user_input.lower())
    # Weather intent
    if any(token.lemma_ == "weather" for token in doc):
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC"):
                return ("weather", ent.text)
    # Reminder intent
    if "remind" in user_input:
        # Expect format "remind me to [action] at [time]"
        parts = user_input.split(" ")
        if "at" in parts:
            at_i = parts.index("at")
            msg = " ".join(parts[3:at_i])
            time_str = " ".join(parts[at_i + 1:])
            try:
                dt = datetime.strptime(time_str, "%H:%M")
                # Use today’s date
                now = datetime.now()
                dt = now.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
                return ("reminder", (msg, dt))
            except ValueError:
                pass
    # Factual: Who is X?
    if user_input.startswith("who is"):
        subject = user_input[6:].strip("? ")
        return ("fact", subject)
    return ("smalltalk", None)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message", "")
    intent, val = parse_intent(user_input)

    if intent == "weather":
        response = fetch_weather(val)

    elif intent == "reminder":
        msg, dt = val
        add_reminder(msg, dt)
        response = f"Got it! I'll remind you: '{msg}' at {dt.strftime('%H:%M')}."

    elif intent == "fact":
        # Simple: fetch from Wikipedia API
        resp = requests.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/" + val
        )
        if resp.status_code == 200:
            summary = resp.json()["extract"]
            response = summary.split(".")[0] + "."
        else:
            response = "Sorry, I couldn't find info on that."

    else:
        response = "Hello! I'm assist. Ask me about weather, set reminders, or ask facts!"

    return jsonify({"response": response})

if __name__ == "__main__":
    threading.Thread(target=check_reminders, daemon=True).start()
    app.run(debug=True, port=5000)
