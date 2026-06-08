from flask import Flask, redirect, render_template, request, session, url_for, send_file
from dotenv import load_dotenv
from groq import Groq
import csv
import os
import re
import urllib.parse

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "leads.csv")
CSV_HEADERS = ["Name", "Phone", "Service", "Status", "Source"]
STATUS_OPTIONS = ["NEW", "CONTACTED", "CONVERTED", "HOT"]
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def normalize_lead(row):
    row = [cell.strip() for cell in row]
    if len(row) < len(CSV_HEADERS):
        row.extend([""] * (len(CSV_HEADERS) - len(row)))
    return row[:len(CSV_HEADERS)]


def write_leads(leads):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)
        writer.writerows(normalize_lead(row) for row in leads)


def ensure_csv_file():
    if not os.path.exists(CSV_FILE):
        write_leads([])
        return

    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    if not rows:
        write_leads([])
        return

    leads = [normalize_lead(row) for row in rows[1:] if row]
    has_bad_header = rows[0] != CSV_HEADERS
    has_bad_rows = any(len(row) != len(CSV_HEADERS) for row in rows[1:])
    if has_bad_header or has_bad_rows:
        write_leads(leads)


def read_leads():
    ensure_csv_file()

    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    return [normalize_lead(row) for row in rows[1:] if row]


def save_lead(name, phone, service):
    leads = read_leads()
    leads.append([name, phone, service, "NEW", "Website Bot"])
    write_leads(leads)


def is_logged_in():
    return session.get("admin_logged_in") is True


def parse_lead_message(message):
    parts = [part.strip() for part in message.split(",")]
    if len(parts) != 3 or not all(parts):
        return None

    name, phone, service = parts
    phone_digits = re.sub(r"\D", "", phone)
    if len(phone_digits) < 10:
        return None

    return name, phone_digits, service


@app.route("/whatsapp/<phone>")
def whatsapp(phone):
    message = "Hello, I am interested in your services."
    encoded_message = urllib.parse.quote(message)
    phone_digits = re.sub(r"\D", "", phone)

    if len(phone_digits) == 10:
        phone_digits = f"91{phone_digits}"

    whatsapp_url = f"https://wa.me/{phone_digits}?text={encoded_message}"
    return redirect(whatsapp_url)


@app.route("/", methods=["GET", "POST"])
def home():
    reply = ""

    if request.method == "POST":
        message = request.form.get("message", "").strip()
        message_lower = message.lower()

        try:
            if not message:
                reply = "Please apna message type kare."

            elif re.fullmatch(r"(hi|hello|hey|hii|namaste)", message_lower):
                reply = (
                    "Hello 👋\n"
                    "Main *Satyavardhan ka AI Business Assistant* hoon 🤖\n\n"
                    "Aap **Sales** ke liye aaye ho ya **Support** ke liye?"
                )

            elif "sales" in message_lower:
                reply = (
                    "Great 😊\n"
                    "Please details is format me bheje:\n\n"
                    "Name, Phone, Service (Basic / Premium)"
                )

            elif "support" in message_lower:
                reply = (
                    "Sorry for the inconvenience 🙏\n"
                    "Please apna **Order ID** share kare."
                )

            elif "," in message:
                lead = parse_lead_message(message)

                if lead:
                    name, phone, service = lead
                    save_lead(name, phone, service)
                    reply = (
                        f"✅ Thank you {name}!\n"
                        "Aapki request successfully save ho gayi hai.\n"
                        "Satyavardhan ki team aapse contact karegi 📞"
                    )
                else:
                    reply = "❌ Galat format. Use: Name, Phone, Service"

            elif client is None:
                reply = (
                    "Main aapki help kar sakta hoon. "
                    "Sales ke liye 'sales' type kare ya support ke liye 'support'."
                )

            else:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a professional AI business assistant "
                                "created and managed by Satyavardhan.Also I solve queries related to sales and support By open AI "
                                "Reply in polite Hinglish. "
                                "Be concise, friendly, and business-focused."
                            )
                        },
                        {"role": "user", "content": message}
                    ]
                )
                reply = response.choices[0].message.content

        except Exception:
            reply = (
                "⚠️ System temporarily busy hai.\n"
                "Please thodi der baad try kare.\n\n"
                "— Satyavardhan Team"
            )

    return render_template("index.html", reply=reply)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))

        error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("login"))


@app.route("/update/<int:index>", methods=["POST"])
def update(index):
    if not is_logged_in():
        return redirect(url_for("login"))

    status = request.form.get("status", "").strip().upper()
    if status not in STATUS_OPTIONS:
        return "Invalid status", 400

    leads = read_leads()
    if index < 0 or index >= len(leads):
        return "Lead not found", 404

    leads[index][3] = status
    write_leads(leads)

    return redirect(url_for("admin"))

@app.route("/export")
def export():
    return send_file(
        "leads.csv",
        as_attachment=True,
        download_name="RVIRAT_Leads.csv"
    )

@app.route("/admin")
def admin():
    if not is_logged_in():
        return redirect(url_for("login"))

    leads = read_leads()
    status_counts = {
        status.lower(): sum(1 for row in leads if row[3] == status)
        for status in STATUS_OPTIONS
    }

    return render_template(
        "admin.html",
        rows=leads,
        status_options=STATUS_OPTIONS,
        total=len(leads),
        new_count=status_counts["new"],
        contacted=status_counts["contacted"],
        converted=status_counts["converted"],
        hot_count=status_counts["hot"],
    )


ensure_csv_file()


if __name__ == "__main__":
    app.run(debug=True, port=5001)