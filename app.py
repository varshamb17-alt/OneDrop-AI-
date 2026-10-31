from flask import Flask, render_template, request
import sqlite3
import requests

app = Flask(__name__)


# Create the database and tables
def create_database():
    connection = sqlite3.connect("onedrop.db")
    cursor = connection.cursor()

    # Create donors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            city TEXT NOT NULL
        )
    """)

    # Create blood requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blood_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            city TEXT NOT NULL,
            units INTEGER NOT NULL,
            hospital TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Register a blood donor
@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    blood_group = request.form.get("blood_group", "").strip()
    city = request.form.get("city", "").strip()

    if not all([name, phone, blood_group, city]):
        return "Please complete all fields.", 400

    connection = sqlite3.connect("onedrop.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO donors (name, phone, blood_group, city)
        VALUES (?, ?, ?, ?)
    """, (name, phone, blood_group, city))

    connection.commit()
    connection.close()

    return f"""
        <h1>Registration Successful!</h1>
        <p>Thank you for registering, {name}!</p>
        <p>Your donor details have been saved.</p>
        <a href="/">Back to Home</a>
    """


# Search for blood donors
@app.route("/search", methods=["GET", "POST"])
def search():
    donors = []

    if request.method == "POST":
        blood_group = request.form.get("blood_group", "").strip()
        city = request.form.get("city", "").strip()

        connection = sqlite3.connect("onedrop.db")
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        cursor.execute("""
            SELECT name, blood_group, city
            FROM donors
            WHERE blood_group = ?
              AND LOWER(city) = LOWER(?)
        """, (blood_group, city))

        donors = cursor.fetchall()
        connection.close()

    return render_template("search.html", donors=donors)


# Submit a blood request
@app.route("/request-blood", methods=["POST"])
def request_blood():
    patient_name = request.form.get("patient_name", "").strip()
    phone = request.form.get("phone", "").strip()
    blood_group = request.form.get("blood_group", "").strip()
    city = request.form.get("city", "").strip()
    units = request.form.get("units", "").strip()
    hospital = request.form.get("hospital", "").strip()

    if not all([
        patient_name, phone, blood_group,
        city, units, hospital
    ]):
        return "Please complete all fields.", 400

    try:
        units = int(units)

        if units < 1:
            return "Units must be at least 1.", 400

    except ValueError:
        return "Please enter a valid number of units.", 400

    connection = sqlite3.connect("onedrop.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO blood_requests
        (patient_name, phone, blood_group, city, units, hospital)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        patient_name,
        phone,
        blood_group,
        city,
        units,
        hospital
    ))

    connection.commit()
    connection.close()

    return """
        <h1>Blood Request Submitted Successfully!</h1>
        <p>Your blood request has been saved.</p>
        <p>Note: This does not confirm blood availability.</p>
        <a href="/">Back to Home</a>
    """


# AI Chatbot using Ollama
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.form.get("message", "").strip()

    if not user_message:
        return "Please enter a message.", 400

    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen2.5:0.5b",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are the OneDrop AI assistant. "
                            "Provide simple information about blood donation. "
                            "Do not diagnose medical conditions or decide "
                            "whether someone is eligible to donate blood. "
                            "For medical decisions, advise users to consult "
                            "a qualified healthcare professional."
                        )
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()
        answer = response.json()["message"]["content"]

        return answer

    except requests.RequestException:
        return (
            "The AI assistant is temporarily unavailable. "
            "Please make sure Ollama is running and try again."
        ), 503


# Run the application
if __name__ == "__main__":
    create_database()
    app.run(host="0.0.0.0", port=5000, debug=True)
