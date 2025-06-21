from flask import Flask, render_template, request
import requests
import sqlite3
import nltk

nltk.download('punkt')
from nltk.tokenize import word_tokenize

app = Flask(__name__)

# --- Weather API Configuration ---
WEATHER_API_KEY = "YOUR_API_KEY"
WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather"

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, text TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- Helper Functions ---
def get_weather(city):
    params = {
        'q': city,
        'appid': WEATHER_API_KEY,
        'units': 'metric'
    }
    response = requests.get(WEATHER_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        temp = data['main']['temp']
        description = data['weather'][0]['description']
        return f"The weather in {city} is {temp}°C with {description}."
    else:
        return "Sorry, I couldn't fetch the weather info."

def save_reminder(text):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO reminders (text) VALUES (?)", (text,))
    conn.commit()
    conn.close()
    return "Reminder saved!"

def get_reminders():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT text FROM reminders")
    rows = c.fetchall()
    conn.close()
    if rows:
        return "\n".join([f"- {row[0]}" for row in rows])
    else:
        return "No reminders found."

def basic_qa(user_input):
    qna = {
        "who is the prime minister of india": "The Prime Minister of India is Narendra Modi.",
        "what is the capital of france": "The capital of France is Paris.",
        "what is ai": "AI stands for Artificial Intelligence. It's about machines doing smart things."
    }
    return qna.get(user_input.lower(), "Sorry, I don't know the answer to that.")

# --- Main Agent Logic ---
def process_input(user_input):
    tokens = word_tokenize(user_input.lower())

    if "weather" in tokens or "temperature" in tokens:
        for word in tokens:
            if word.istitle():
                return get_weather(word)
        return "Which city do you want the weather for?"

    elif "remind" in tokens or "reminder" in tokens:
        return save_reminder(user_input)

    elif "show" in tokens and "reminder" in tokens:
        return get_reminders()

    elif any(greet in tokens for greet in ["hi", "hello", "hey"]):
        return "Hello! I’m Assist, your personal AI agent. How can I help you?"

    else:
        return basic_qa(user_input)

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    response = ""
    if request.method == "POST":
        user_input = request.form["message"]
        response = process_input(user_input)
    return render_template("index.html", response=response)

if __name__ == "__main__":
    app.run(debug=True)
