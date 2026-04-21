# FAQCanvas

FAQCanvas is a simple final year project for website support. It does not generate answers with AI. Instead, the admin saves frequently asked questions and answers, and the widget finds the closest matching saved question.

## Simple idea

1. Admin logs in.
2. Admin adds FAQs.
3. Customer asks a question in the website widget.
4. Flask searches FAQ questions stored in SQLite.
5. The best saved answer is shown.

## Tech stack

- HTML
- Tailwind CSS
- Vanilla JavaScript
- Flask
- SQLite

## Project structure

```text
faqagent/
|- app.py
|- config.py
|- wsgi.py
|- requirements.txt
|- .env.example
|- database/
|  |- schema.sql
|- static/
|  |- js/
|     |- dashboard.js
|     |- widget.js
|- templates/
   |- dashboard.html
   |- login.html
   |- widget.html
```

## Database setup

No manual database setup is required.

When you run the app for the first time:

- Flask creates the SQLite database file automatically
- Tables are created from `database/schema.sql`
- Demo login and sample FAQs are added automatically

If you want, you can change the database file path in `.env` using `.env.example` as reference.

## Environment file

Create a `.env` file using `.env.example`.

Example:

```env
SECRET_KEY=replace-this-with-a-random-secret-key
DATABASE_PATH=/home/yourusername/faqagent/database/faqcanvas.db
DEMO_DATA_ENABLED=true
```

- `SECRET_KEY` keeps login sessions secure.
- `DATABASE_PATH` should be an absolute path on PythonAnywhere.
- `DEMO_DATA_ENABLED=true` adds the demo admin and sample FAQs automatically.

## Install and run

1. Create a virtual environment.
2. Install packages:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python app.py
```

4. Open `http://127.0.0.1:5000`

## Demo login

- Email: `admin@faqbox.com`
- Password: `admin123`

The app creates demo data automatically the first time it runs.

## How the widget works

Paste this code into any website:

```html
<script src="http://127.0.0.1:5000/embed.js" data-site-key="demo-store"></script>
```

The script adds a floating FAQ button. When a visitor asks a question, the widget sends the question to Flask, Flask searches SQLite, and the closest saved answer is returned.

## Deploy on PythonAnywhere

This is the simplest hosting option for this project because everything stays in one place:

- Flask backend
- HTML pages
- JavaScript files
- SQLite database
- Widget script

### 1. Upload the project

Upload the full `faqagent` folder to your PythonAnywhere account.

Example final path:

```text
/home/yourusername/faqagent
```

### 2. Open a Bash console on PythonAnywhere

Run these commands:

```bash
cd ~/faqagent
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Create the `.env` file

Create a `.env` file in your project folder:

```bash
nano .env
```

Paste this and replace `yourusername`:

```env
SECRET_KEY=replace-this-with-a-random-secret-key
DATABASE_PATH=/home/yourusername/faqagent/database/faqcanvas.db
DEMO_DATA_ENABLED=true
```

Save the file.

### 4. Create the web app in PythonAnywhere

In the PythonAnywhere dashboard:

1. Go to the `Web` tab.
2. Click `Add a new web app`.
3. Choose `Manual configuration`.
4. Choose your Python version.

### 5. Set the virtualenv

In the `Web` tab, set the virtualenv path to:

```text
/home/yourusername/faqagent/.venv
```

### 6. Edit the WSGI file

Open the WSGI configuration file from the `Web` tab and replace its content with:

```python
import sys
from pathlib import Path

project_home = Path("/home/yourusername/faqagent")
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

from wsgi import application
```

### 7. Reload the web app

Click the `Reload` button in the `Web` tab.

When the app loads for the first time:

- the SQLite database file will be created
- the tables will be created
- the demo admin account will be added
- sample FAQs will be added

### 8. Open your live app

Your project will be available at:

```text
https://yourusername.pythonanywhere.com
```

### 9. Use the live widget script

After deployment, use this script on any website:

```html
<script src="https://yourusername.pythonanywhere.com/embed.js" data-site-key="demo-store"></script>
```

## Very simple explanation for presentation

You can explain deployment like this:

1. I uploaded my Flask project to PythonAnywhere.
2. PythonAnywhere runs my Flask app online.
3. The app stores FAQs in SQLite.
4. The widget sends the user question to Flask.
5. Flask finds the closest FAQ using `difflib`.
6. The answer is shown in the widget.

## Search logic

The matching is intentionally simple and uses Python's built-in `difflib` library:

- Convert both questions to lowercase-style simple words
- Compare the customer question with each saved FAQ question
- `difflib` gives a similarity score between the two texts
- Return the answer of the question with the highest score
- If the score is too low, show a fallback support message

This makes the project easy to implement and easy to explain in a college presentation because it is still a normal text comparison, not AI.
