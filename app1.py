from flask import Flask, render_template, request, redirect
from groq import Groq
from dotenv import load_dotenv
import os, csv
import urllib.parse

load_dotenv()


client = Groq(api_key=os.getenv("GROQ_API_KEY"))

load_dotenv()

app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
@app.route("/whatsapp/<phone>")

def whatsapp(phone):
    message = "Hello, I am interested in your services."
    encoded_message = urllib.parse.quote(message)

    whatsapp_url = f"https://wa.me/91{phone}?text={encoded_message}"

    return redirect(whatsapp_url)

CSV_FILE = "leads.csv"

# CSV create if missing
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Phone", "Service", "Status", "Source"])


@app.route("/", methods=["GET", "POST"])
def home():
    reply = ""

    if request.method == "POST":
        message = request.form.get("message", "").strip().lower()

        try:
            # RULE BASED
            if any(w in message for w in ["hi", "hello", "hey"]):
                reply = (
                    "Hello 👋\n"
                    "Main *Satyavardhan ka AI Business Assistant* hoon 🤖\n\n"
                    "Aap **Sales** ke liye aaye ho ya **Support** ke liye?"
                )

            elif "sales" in message:
                reply = (
                    "Great 😊\n"
                    "Please details is format me bheje:\n\n"
                    "Name, Phone, Service (Basic / Premium)"
                )

            elif "support" in message:
                reply = (
                    "Sorry for the inconvenience 🙏\n"
                    "Please apna **Order ID** share kare."
                )

            elif "," in message:
                data = [x.strip() for x in message.split(",")]

                if len(data) == 3:
                    name, phone, service = data

                    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow([name, phone, service, "NEW", "Website Bot"])

                    reply = (
                        f"✅ Thank you {name}!\n"
                        "Aapki request successfully save ho gayi hai.\n"
                        "Satyavardhan ki team aapse contact karegi 📞"
                    )
                else:
                    reply = "❌ Galat format. Use: Name, Phone, Service"

            else:
                # AI RESPONSE (Groq)
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a professional AI business assistant "
                                "created and managed by Satyavardhan. "
                                "Reply in polite Hinglish. "
                                "Be concise, friendly, and business-focused."
                            )
                        },
                        {"role": "user", "content": message}
                    ]
                )

                reply = response.choices[0].message.content

        except Exception as e:
            reply = (
                "⚠️ System temporarily busy hai.\n"
                "Please thodi der baad try kare.\n\n"
                "— Satyavardhan Team"
            )

    return render_template("index.html", reply=reply)
@app.route("/update/<int:index>", methods=["POST"])
def update(index):
    status = request.form["status"]

    with open("leads.csv", "r", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    rows[index + 1][3] = status  # skip header

    with open("leads.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return "Status Updated ✅ <a href='/admin'>Go Back</a>"

@app.route("/admin")
def admin():
    leads = []

    with open("leads.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # skip header

        for row in reader:
            leads.append(row)

    return render_template("admin.html", leads=leads)


if __name__ == "__main__":
    app.run(debug=True)
