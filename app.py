import csv
import difflib
import json
import re
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config


app = Flask(__name__)
app.config.from_object(Config)
app.config["DEMO_DATA_READY"] = False
MATCH_THRESHOLD = 0.45


def get_db_connection():
    connection = sqlite3.connect(app.config["DATABASE_PATH"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    database_path = Path(app.config["DATABASE_PATH"])
    database_path.parent.mkdir(parents=True, exist_ok=True)

    schema_path = Path(__file__).resolve().parent / "database" / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    connection = get_db_connection()
    try:
        connection.executescript(schema_sql)
        connection.commit()
    finally:
        connection.close()


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped_view


def tokenize(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def similarity_score(user_question, saved_question):
    normalized_user_question = " ".join(sorted(tokenize(user_question)))
    normalized_saved_question = " ".join(sorted(tokenize(saved_question)))

    if not normalized_user_question or not normalized_saved_question:
        return 0

    return difflib.SequenceMatcher(
        None,
        normalized_user_question,
        normalized_saved_question,
    ).ratio()


def find_best_match(question, faq_rows):
    best_faq = None
    best_score = 0

    for faq in faq_rows:
        score = similarity_score(question, faq["question"])
        if score > best_score:
            best_score = score
            best_faq = faq

    return best_faq, best_score


def parse_faq_import_file(uploaded_file):
    filename = (uploaded_file.filename or "").strip().lower()

    if not filename:
        return [], 0, "Please choose a file to upload."

    try:
        content = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], 0, "The file must use UTF-8 encoding."

    entries = []
    skipped_rows = 0

    if filename.endswith(".csv"):
        reader = csv.DictReader(content.splitlines())
        normalized_fields = {
            field.strip().lower(): field
            for field in (reader.fieldnames or [])
            if field and field.strip()
        }

        if "question" not in normalized_fields or "answer" not in normalized_fields:
            return [], 0, "CSV files must include 'question' and 'answer' columns."

        for row in reader:
            question = (row.get(normalized_fields["question"], "") or "").strip()
            answer = (row.get(normalized_fields["answer"], "") or "").strip()

            if not question or not answer:
                skipped_rows += 1
                continue

            entries.append((question, answer))

    elif filename.endswith(".json"):
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return [], 0, "The JSON file is not valid."

        if not isinstance(payload, list):
            return [], 0, "JSON files must contain an array of FAQ objects."

        for item in payload:
            if not isinstance(item, dict):
                skipped_rows += 1
                continue

            question = str(item.get("question", "") or "").strip()
            answer = str(item.get("answer", "") or "").strip()

            if not question or not answer:
                skipped_rows += 1
                continue

            entries.append((question, answer))
    else:
        return [], 0, "Only CSV and JSON files are supported."

    if not entries:
        return [], skipped_rows, "No valid FAQs were found in the uploaded file."

    return entries, skipped_rows, None


def ensure_demo_data():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT id FROM users LIMIT 1")
        existing_user = cursor.fetchone()

        if existing_user:
            return

        cursor.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (?, ?, ?)
            """,
            ("Demo Admin", "admin@faqbox.com", generate_password_hash("admin123")),
        )
        user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO websites (user_id, site_name, site_key)
            VALUES (?, ?, ?)
            """,
            (user_id, "Demo Store", "demo-store"),
        )

        demo_faqs = [
            ("What are your delivery charges?", "Delivery is free for orders above Rs. 500."),
            ("How can I track my order?", "You can track your order from the Orders page after logging in."),
            ("What is your return policy?", "Products can be returned within 7 days in original condition."),
        ]

        for question, answer in demo_faqs:
            cursor.execute(
                """
                INSERT INTO faqs (user_id, question, answer)
                VALUES (?, ?, ?)
                """,
                (user_id, question, answer),
            )

        connection.commit()
    finally:
        cursor.close()
        connection.close()


def get_current_website(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id, user_id, site_name, site_key
            FROM websites
            WHERE user_id = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (user_id,),
        )
        website = cursor.fetchone()

        if website:
            return website

        fallback_key = f"site-{user_id}"
        cursor.execute(
            """
            INSERT INTO websites (user_id, site_name, site_key)
            VALUES (?, ?, ?)
            """,
            (user_id, "My Website", fallback_key),
        )
        connection.commit()

        return {
            "id": cursor.lastrowid,
            "user_id": user_id,
            "site_name": "My Website",
            "site_key": fallback_key,
        }
    finally:
        cursor.close()
        connection.close()


def get_widget_preview(site_key):
    if not site_key:
        return {
            "site_name": "Support Widget",
            "suggestions": [],
            "welcome_message": "Hi! Ask a question and I'll look for the best saved answer.",
        }

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT user_id, site_name
            FROM websites
            WHERE site_key = ?
            LIMIT 1
            """,
            (site_key,),
        )
        website = cursor.fetchone()

        if not website:
            return {
                "site_name": "Support Widget",
                "suggestions": [],
                "welcome_message": "Hi! Ask a question and I'll look for the best saved answer.",
            }

        cursor.execute(
            """
            SELECT question
            FROM faqs
            WHERE user_id = ?
            ORDER BY id ASC
            LIMIT 3
            """,
            (website["user_id"],),
        )
        suggestions = [row["question"] for row in cursor.fetchall()]

        welcome_message = "Hi! Ask a question and I'll look for the best saved answer."
        if suggestions:
            welcome_message = f'Hi! Try asking something like "{suggestions[0]}"'

        return {
            "site_name": website["site_name"],
            "suggestions": suggestions,
            "welcome_message": welcome_message,
        }
    finally:
        cursor.close()
        connection.close()


def create_user_account(name, email, password):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (?, ?, ?)
            """,
            (name, email, generate_password_hash(password)),
        )
        user_id = cursor.lastrowid

        safe_name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or f"user-{user_id}"
        site_key = f"{safe_name}-{user_id}"

        cursor.execute(
            """
            INSERT INTO websites (user_id, site_name, site_key)
            VALUES (?, ?, ?)
            """,
            (user_id, f"{name}'s Website", site_key),
        )
        connection.commit()
        return user_id
    finally:
        cursor.close()
        connection.close()


@app.before_request
def prepare_demo_data():
    if app.config["DEMO_DATA_READY"]:
        return

    init_db()

    if app.config["DEMO_DATA_ENABLED"]:
        ensure_demo_data()

    app.config["DEMO_DATA_READY"] = True


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                SELECT id, name, email, password
                FROM users
                WHERE email = ?
                LIMIT 1
                """,
                (email,),
            )
            user = cursor.fetchone()
        finally:
            cursor.close()
            connection.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))

        error = "Invalid email or password."

    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm_password:
            error = "All fields are required."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        else:
            connection = get_db_connection()
            cursor = connection.cursor()

            try:
                cursor.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE email = ?
                    LIMIT 1
                    """,
                    (email,),
                )
                existing_user = cursor.fetchone()
            finally:
                cursor.close()
                connection.close()

            if existing_user:
                error = "An account with this email already exists."
            else:
                user_id = create_user_account(name, email, password)
                session["user_id"] = user_id
                session["user_name"] = name
                return redirect(url_for("dashboard"))

    return render_template("signup.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    website = get_current_website(session["user_id"])
    embed_url = request.host_url.rstrip("/") + "/embed.js"
    return render_template(
        "dashboard.html",
        website=website,
        embed_url=embed_url,
        user_name=session.get("user_name", "Admin"),
    )


@app.route("/api/faqs", methods=["GET", "POST"])
@login_required
def faq_collection():
    user_id = session["user_id"]
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        if request.method == "GET":
            cursor.execute(
                """
                SELECT id, question, answer, created_at
                FROM faqs
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            )
            faqs = cursor.fetchall()
            return jsonify([dict(faq) for faq in faqs])

        payload = request.get_json(silent=True) or {}
        question = payload.get("question", "").strip()
        answer = payload.get("answer", "").strip()

        if not question or not answer:
            return jsonify({"error": "Question and answer are required."}), 400

        cursor.execute(
            """
            INSERT INTO faqs (user_id, question, answer)
            VALUES (?, ?, ?)
            """,
            (user_id, question, answer),
        )
        connection.commit()

        return jsonify(
            {
                "message": "FAQ created successfully.",
                "id": cursor.lastrowid,
            }
        ), 201
    finally:
        cursor.close()
        connection.close()


@app.route("/api/faqs/<int:faq_id>", methods=["PUT", "DELETE"])
@login_required
def faq_item(faq_id):
    user_id = session["user_id"]
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT id
            FROM faqs
            WHERE id = ? AND user_id = ?
            LIMIT 1
            """,
            (faq_id, user_id),
        )
        faq = cursor.fetchone()

        if not faq:
            return jsonify({"error": "FAQ not found."}), 404

        if request.method == "PUT":
            payload = request.get_json(silent=True) or {}
            question = payload.get("question", "").strip()
            answer = payload.get("answer", "").strip()

            if not question or not answer:
                return jsonify({"error": "Question and answer are required."}), 400

            cursor.execute(
                """
                UPDATE faqs
                SET question = ?, answer = ?
                WHERE id = ? AND user_id = ?
                """,
                (question, answer, faq_id, user_id),
            )
            connection.commit()
            return jsonify({"message": "FAQ updated successfully."})

        cursor.execute(
            """
            DELETE FROM faqs
            WHERE id = ? AND user_id = ?
            """,
            (faq_id, user_id),
        )
        connection.commit()
        return jsonify({"message": "FAQ deleted successfully."})
    finally:
        cursor.close()
        connection.close()


@app.route("/api/faqs/import", methods=["POST"])
@login_required
def import_faqs():
    uploaded_file = request.files.get("file")

    if not uploaded_file:
        return jsonify({"error": "Please choose a CSV or JSON file."}), 400

    entries, skipped_rows, error = parse_faq_import_file(uploaded_file)

    if error:
        return jsonify({"error": error}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.executemany(
            """
            INSERT INTO faqs (user_id, question, answer)
            VALUES (?, ?, ?)
            """,
            [(session["user_id"], question, answer) for question, answer in entries],
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    message = f"Imported {len(entries)} FAQs successfully."
    if skipped_rows:
        message += f" Skipped {skipped_rows} incomplete rows."

    return jsonify(
        {
            "message": message,
            "imported_count": len(entries),
            "skipped_count": skipped_rows,
        }
    ), 201


@app.route("/api/widget/ask", methods=["POST"])
def ask_question():
    payload = request.get_json(silent=True) or {}
    question = payload.get("question", "").strip()
    site_key = payload.get("site_key", "").strip()

    if not question or not site_key:
        return jsonify({"error": "Question and site key are required."}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT user_id
            FROM websites
            WHERE site_key = ?
            LIMIT 1
            """,
            (site_key,),
        )
        website = cursor.fetchone()

        if not website:
            return jsonify({"answer": "This widget is not connected to a website yet."}), 404

        cursor.execute(
            """
            SELECT id, question, answer
            FROM faqs
            WHERE user_id = ?
            """,
            (website["user_id"],),
        )
        faqs = cursor.fetchall()

        best_faq, score = find_best_match(question, faqs)

        if not best_faq or score == 0:
            return jsonify(
                {
                    "answer": "Sorry, I could not find a matching answer. Please contact support.",
                    "matched_question": None,
                    "score": 0,
                }
            )

        if score < MATCH_THRESHOLD:
            return jsonify(
                {
                    "answer": "Sorry, I could not find a matching answer. Please contact support.",
                    "matched_question": None,
                    "score": round(score, 2),
                }
            )

        return jsonify(
            {
                "answer": best_faq["answer"],
                "matched_question": best_faq["question"],
                "score": round(score, 2),
            }
        )
    finally:
        cursor.close()
        connection.close()


@app.route("/api/widget/config")
def widget_config():
    site_key = request.args.get("site_key", "").strip()
    return jsonify(get_widget_preview(site_key))


@app.route("/widget")
def widget():
    return render_template("widget.html")


@app.route("/embed.js")
def embed_script():
    base_url = request.host_url.rstrip("/")
    script = f"""
(function () {{
  var currentScript = document.currentScript;
  if (!currentScript) return;

  var siteKey = currentScript.dataset.siteKey;
  if (!siteKey) {{
    console.error("FAQ widget: data-site-key is missing.");
    return;
  }}

  var frame = document.createElement("iframe");
  frame.src = "{base_url}/widget?site_key=" + encodeURIComponent(siteKey);
  frame.title = "FAQ Widget";
  frame.style.position = "fixed";
  frame.style.bottom = "88px";
  frame.style.right = "16px";
  frame.style.width = "min(420px, calc(100vw - 32px))";
  frame.style.height = "min(680px, calc(100vh - 112px))";
  frame.style.maxWidth = "calc(100vw - 32px)";
  frame.style.maxHeight = "calc(100vh - 112px)";
  frame.style.border = "0";
  frame.style.borderRadius = "18px";
  frame.style.boxShadow = "0 18px 45px rgba(15, 23, 42, 0.25)";
  frame.style.display = "none";
  frame.style.zIndex = "999998";
  frame.style.background = "#ffffff";

  var button = document.createElement("button");
  button.type = "button";
  button.innerText = "FAQ";
  button.setAttribute("aria-label", "Open FAQ widget");
  button.style.position = "fixed";
  button.style.bottom = "24px";
  button.style.right = "16px";
  button.style.width = "56px";
  button.style.height = "56px";
  button.style.border = "0";
  button.style.borderRadius = "9999px";
  button.style.background = "#0f172a";
  button.style.color = "#ffffff";
  button.style.fontSize = "16px";
  button.style.fontWeight = "700";
  button.style.cursor = "pointer";
  button.style.boxShadow = "0 12px 30px rgba(15, 23, 42, 0.25)";
  button.style.zIndex = "999999";

  button.addEventListener("click", function () {{
    frame.style.display = frame.style.display === "none" ? "block" : "none";
  }});

  document.body.appendChild(frame);
  document.body.appendChild(button);
}})();
"""
    return Response(script, mimetype="application/javascript")


if __name__ == "__main__":
    app.run(debug=True)
