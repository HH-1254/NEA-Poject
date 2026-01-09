import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for, session
from datetime import datetime, timedelta
import calendar
import random

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Temporary storage for password reset
user_email_temp = {"email": "", "code": ""}

# Initialise Database
connection = sqlite3.connect("NEA.db")
cursor = connection.cursor()

# Table for login system
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        security_code TEXT NOT NULL
    )
""")

# Table for Task management
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        due_date TEXT NOT NULL,
        label TEXT,
        progress INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")

# Table for Completed Tasks
cursor.execute("""
    CREATE TABLE IF NOT EXISTS completed_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        due_date TEXT NOT NULL,
        label TEXT,
        progress INTEGER DEFAULT 100,
        completed_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")

# Events table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")

connection.commit()
connection.close()

# Login form
login_form = """
<!doctype html>
<html>
<head>
    <title>Login</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
        <h2>Login</h2>
        <form method="POST">
            <label>Email:</label><br>
            <input type="text" name="email" required><br><br>

            <label>Password:</label><br>
            <input type="password" name="password" required><br><br>

            <input type="submit" value="Login">
        </form>
        <p style="color:red;">{{ message }}</p>
        <p>Don't have an account? <a href="/register">Register here</a></p>
        <p><a href="/verify">Forgot Password?</a></p>
</body>
</html>
"""

# Register form (updated: removed security code, added confirm password)
register_form = """
<!doctype html>
<html>
<head>
    <title>Register</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
    <h2>Create an Account</h2>
    <form method="POST">
        <label>Email:</label><br>
        <input type="text" name="email" required><br><br>

        <label>Password (min 8 chars):</label><br>
        <input type="password" name="password" required><br><br>

        <label>Confirm Password:</label><br>
        <input type="password" name="confirm_password" required><br><br>

        <input type="submit" value="Register">
    </form>
    <p style="color:red;">{{ message }}</p>
    <p>Already have an account? <a href="/">Login here</a></p>
</body>
</html>
"""

# Reset form
reset_form = """
<!doctype html>
<html>
<head>
    <title>Reset Password</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
    <h2>Reset Your Password</h2>
    <form method="POST">
        <label>New Password (min 8 chars):</label><br>
        <input type="password" name="new_password" required><br><br>
        <input type="submit" value="Reset Password">
    </form>
    <p style="color:red;">{{ message }}</p>
</body>
</html>
"""

# Verify form
verify_form = """
<!doctype html>
<html>
<head>
    <title>Verify Code</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
    <h2>Verify Email with Code</h2>
    <form method="POST">
        <label>Email:</label><br>
        <input type="text" name="email" required><br><br>

        <label>Verification Code:</label><br>
        <input type="text" name="code" required><br><br>

        <input type="submit" value="Verify">
    </form>
    <p style="color:red;">{{ message }}</p>
</body>
</html>
"""

# Login route
@app.route("/", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        connection = sqlite3.connect("NEA.db")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            today = datetime.now().date()
            tomorrow = today + timedelta(days=1)
            cursor.execute("SELECT title, due_date FROM tasks WHERE user_id=?", (user[0],))
            rows = cursor.fetchall()
            connection.close()

            due_soon = []
            for title, due_date in rows:
                try:
                    parsed_date = datetime.strptime(due_date, "%Y-%m-%d %H:%M").date()
                except ValueError:
                    parsed_date = datetime.strptime(due_date, "%Y-%m-%dT%H:%M").date()
                if parsed_date in [today, tomorrow]:
                    due_soon.append(title)
            session['due_soon'] = due_soon
            return redirect(url_for("home"))
        else:
            message = "Invalid email or password."
            connection.close()
    return render_template_string(login_form, message=message)

# Register route (updated: confirm password + auto 5-digit code)
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if len(password) < 8:
            message = "Password must be at least 8 characters long."
        elif password != confirm_password:
            message = "Passwords do not match."
        else:
            security_code = str(random.randint(10000, 99999))
            try:
                connection = sqlite3.connect("NEA.db")
                cursor = connection.cursor()
                cursor.execute("INSERT INTO users (email, password, security_code) VALUES (?, ?, ?)",
                               (email, password, security_code))
                connection.commit()
                connection.close()
                message = f"Registration successful! Your security code is {security_code}. Keep it safe."
                return render_template_string(register_form, message=message)
            except sqlite3.IntegrityError:
                message = "Email already exists. Please choose another."
    return render_template_string(register_form, message=message)

# Verify identity
@app.route("/verify", methods=["GET", "POST"])
def verify_code():
    message = ""
    if request.method == "POST":
        email = request.form.get("email")
        code = request.form.get("code")
        connection = sqlite3.connect("NEA.db")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND security_code=?", (email, code))
        user = cursor.fetchone()
        connection.close()
        if user:
            user_email_temp["email"] = email
            return redirect(url_for("reset_password"))
        else:
            message = "Invalid email or security code."
    return render_template_string(verify_form, message=message)

# Reset password
@app.route("/reset", methods=["GET", "POST"])
def reset_password():
    message = ""
    if request.method == "POST":
        new_password = request.form.get("new_password")
        if len(new_password) < 8:
            message = "Password must be at least 8 characters long."
        else:
            email = user_email_temp.get("email")
            connection = sqlite3.connect("NEA.db")
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET password=? WHERE email=?", (new_password, email))
            connection.commit()
            connection.close()
            return redirect(url_for("login"))
    return render_template_string(reset_form, message=message)

# Task template
home_template = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Task Manager</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='home.css') }}">
</head>

<body>

<h2>Welcome, {{ user_email }}</h2>

<!-- ===== NAVBAR ===== -->
<nav class="navbar">
    <div class="nav-left">
        <a href="/home" class="{% if request.path == '/home' %}active{% endif %}">Home</a>
        <a href="/analysis" class="{% if request.path == '/analysis' %}active{% endif %}">Analytics</a>
        <a href="/Scheduling" class="{% if request.path == '/Scheduling' %}active{% endif %}">Scheduling</a>
        <a href="/logout">Log Out</a>
    </div>

    <div class="nav-right">

        <!-- Notifications -->
        <div class="notification">
            <span class="bell" onclick="toggleReminders()">&#128276;</span>
            {% if unread_count > 0 %}
                <span class="badge">{{ unread_count }}</span>
            {% endif %}

            <div id="reminderBox" class="reminder-box">
                <strong>Tasks Due Soon:</strong>
                <ul>
                    {% if due_soon %}
                        {% for task in due_soon %}
                            <li>{{ task }}</li>
                        {% endfor %}
                    {% else %}
                        <li>No upcoming tasks</li>
                    {% endif %}
                </ul>
            </div>
        </div>

        <!-- Settings -->
    <div class="settings">
        <span class="gear" onclick="toggleSettings()">&#9881;</span>

        <div id="settingsBox" class="settings-box">
            <h4>Settings</h4>


            <hr>

            <!-- COLOUR PICKERS -->
            <label>Primary colour:</label>
            <input type="color" onchange="setPrimary(this.value)">

            <label>Secondary colour:</label>
            <input type="color" onchange="setSecondary(this.value)">

            <hr>

            <!-- MANAGE ACCOUNT -->
            <button onclick="openPasswordForm()">Manage Account</button>
        </div>
    </div>
    </nav>
<h1>Task Manager</h1>

<!-- ===== ACTION BUTTONS ===== -->
<button onclick="showForm()">Add Task</button>
<button onclick="toggleFilterForm()">Filter</button>

<!-- ===== OVERLAY ===== -->
<div id="overlay"></div>

<!-- ===== TASK LIST ===== -->
{% for task in tasks %}
    <div class="task">
        <div style="display:flex; justify-content:space-between;">
            <div>
                <strong>{{ task.title }}</strong><br>
                {{ task.description }}<br>
                <em>Due: {{ task.due_date }}</em><br>
                {% if task.label %}
                    <strong>Label:</strong> {{ task.label }}<br>
                {% endif %}
            </div>
            <div>
                <strong>{{ task.progress }}%</strong>
            </div>
        </div>

        <button onclick="openEditForm(
            '{{ task.title }}',
            '{{ task.description }}',
            '{{ task.due_date }}',
            '{{ task.label }}'
        )">Edit</button>

        <form method="POST" action="/delete_task" style="display:inline;">
            <input type="hidden" name="title" value="{{ task.title }}">
            <input type="hidden" name="due_date" value="{{ task.due_date }}">
            <button type="submit">Complete</button>
        </form>
    </div>
{% else %}
    <p>No tasks available.</p>
{% endfor %}

<!-- ===== ADD TASK FORM ===== -->
<div id="taskForm">
    <form method="POST">
        <h3>Add Task</h3>

        <label>Title</label><br>
        <input type="text" name="title" required><br><br>

        <label>Description</label><br>
        <textarea name="description" required></textarea><br><br>

        <label>Due Date</label><br>
        <input type="datetime-local" name="due_date" required><br><br>

        <label>Label</label><br>
        <input type="text" name="label"><br><br>

        <label>Progress</label><br>
        <input type="range" name="progress" min="0" max="100" step="10" value="0"
               oninput="document.getElementById('progressOutput').value = this.value + '%'">
        <output id="progressOutput">0%</output><br><br>

        <button type="submit">Add</button>
        <button type="button" onclick="hideForm()">Cancel</button>
    </form>
</div>

<!-- ===== EDIT TASK FORM ===== -->
<div id="editForm">
    <form method="POST" action="/update_task">
        <h3>Edit Task</h3>

        <input type="hidden" name="original_title" id="editOriginalTitle">
        <input type="hidden" name="original_due_date" id="editOriginalDueDate">

        <label>Title</label><br>
        <input type="text" name="title" id="editTitle" required><br><br>

        <label>Description</label><br>
        <textarea name="description" id="editDescription" required></textarea><br><br>

        <label>Due Date</label><br>
        <input type="datetime-local" name="due_date" id="editDueDate" required><br><br>

        <label>Label</label><br>
        <input type="text" name="label" id="editLabel"><br><br>

        <label>Progress</label><br>
        <input type="range" name="progress" id="editProgress"
       min="0" max="100" step="10" value="0">

        <button type="submit">Update</button>
        <button type="button" onclick="hideEditForm()">Cancel</button>
    </form>
</div>

<!-- ===== FILTER FORM ===== -->
<div id="filterForm">
    <form method="GET" action="/home">
        <h3>Filter Tasks</h3>

        <input type="text" name="query" placeholder="Search">

        <label><input type="checkbox" name="fields" value="title"> Title</label>
        <label><input type="checkbox" name="fields" value="description"> Description</label>
        <label><input type="checkbox" name="fields" value="label"> Label</label><br><br>

        <select name="sort_by">
            <option value="">No sorting</option>
            <option value="due_date">Due date</option>
            <option value="progress">Progress</option>
        </select>

        <select name="order">
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
        </select><br><br>

        <button type="submit">Apply</button>
        <button type="button" onclick="toggleFilterForm()">Cancel</button>
    </form>
</div>


<div id="passwordForm" class="popup-form">
    <h3>Change Password</h3>

    <form method="POST" action="/change_password">
        <label>Current Password</label><br>
        <input type="password" name="current_password" required><br><br>

        <label>New Password</label><br>
        <input type="password" name="new_password" required><br><br>

        <button type="submit">Update</button>
        <button type="button" onclick="closePasswordForm()">Cancel</button>
    </form>
</div>



<!-- ===== JAVASCRIPT ===== -->
<script>
function showForm() {
    document.getElementById("taskForm").style.display = "block";
    document.getElementById("overlay").style.display = "block";
}

function hideForm() {
    document.getElementById("taskForm").style.display = "none";
    document.getElementById("overlay").style.display = "none";
}

function toggleFilterForm() {
    const form = document.getElementById("filterForm");
    const overlay = document.getElementById("overlay");

    if (form.style.display === "block") {
        form.style.display = "none";
        overlay.style.display = "none";
    } else {
        form.style.display = "block";
        overlay.style.display = "block";
    }
}



function openEditForm(title, desc, date, label) {
    document.getElementById("editOriginalTitle").value = title;
    document.getElementById("editOriginalDueDate").value = date;

    document.getElementById("editTitle").value = title;
    document.getElementById("editDescription").value = desc;
    document.getElementById("editDueDate").value = date.replace(" ", "T");
    document.getElementById("editLabel").value = label || "";

    document.getElementById("editForm").style.display = "block";
    document.getElementById("overlay").style.display = "block";
}


function hideEditForm() {
    document.getElementById("editForm").style.display = "none";
    document.getElementById("overlay").style.display = "none";
}

function toggleReminders() {
    const box = document.getElementById("reminderBox");
    box.style.display = box.style.display === "block" ? "none" : "block";
}

document.getElementById("overlay").onclick = function () {
    hideForm();
    hideEditForm();
    document.getElementById("filterForm").style.display = "none";
    document.getElementById("settingsForm").style.display = "none";
    this.style.display = "none";
};


            /* ===== SETTINGS ===== */
    function toggleSettings() {
        const box = document.getElementById("settingsBox");
        box.style.display = box.style.display === "block" ? "none" : "block";
    }




    /* ===== COLOUR PICKER ===== */
    function setPrimary(color) {
        document.documentElement.style.setProperty("--primary", color);
    }

    function setSecondary(color) {
        document.documentElement.style.setProperty("--secondary", color);
        saveThemeSettings();
    }

    function setPrimary(color) {
        document.documentElement.style.setProperty("--primary", color);

        // Calculate brightness
        const r = parseInt(color.substr(1, 2), 16);
        const g = parseInt(color.substr(3, 2), 16);
        const b = parseInt(color.substr(5, 2), 16);
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;

        // Auto text colour
        const textColor = brightness < 140 ? "#ffffff" : "#000000";
        document.documentElement.style.setProperty("--text", textColor);

        saveThemeSettings();
    }

    function saveThemeSettings() {
        const styles = getComputedStyle(document.documentElement);

        localStorage.setItem("primary", styles.getPropertyValue("--primary"));
        localStorage.setItem("secondary", styles.getPropertyValue("--secondary"));
        localStorage.setItem("text", styles.getPropertyValue("--text"));
    }



    /* ===== PASSWORD FORM ===== */
    function openPasswordForm() {
        document.getElementById("passwordForm").style.display = "block";
        document.getElementById("settingsBox").style.display = "none";
    }

    function closePasswordForm() {
        document.getElementById("passwordForm").style.display = "none";
    }

    function openPasswordForm() {
        document.getElementById("passwordForm").style.display = "block";
        document.getElementById("overlay").style.display = "block";
        document.getElementById("settingsBox").style.display = "none";
    }

    function closePasswordForm() {
        document.getElementById("passwordForm").style.display = "none";
        document.getElementById("overlay").style.display = "none";
    }


    window.onload = function () {

        const primary = localStorage.getItem("primary");
        const secondary = localStorage.getItem("secondary");
        const text = localStorage.getItem("text");


        if (primary) document.documentElement.style.setProperty("--primary", primary);
        if (secondary) document.documentElement.style.setProperty("--secondary", secondary);
        if (text) document.documentElement.style.setProperty("--text", text);
    };



</script>

</body>
</html>
"""


@app.route("/change_password", methods=["POST"])
def change_password():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    current = request.form["current_password"]
    new = request.form["new_password"]

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    cursor.execute("SELECT password FROM users WHERE id=?", (user_id,))
    stored = cursor.fetchone()[0]

    if stored != current:
        connection.close()
        return redirect(url_for("home"))

    cursor.execute("UPDATE users SET password=? WHERE id=?", (new, user_id))
    connection.commit()
    connection.close()

    return redirect(url_for("home"))














# Updating Tasks
@app.route("/update_task", methods=["POST"])
def update_task():
    user_id = session.get("user_id")
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    original_title = request.form["original_title"]
    original_due_date = request.form["original_due_date"]
    new_title = request.form["title"]
    new_description = request.form["description"]
    new_due_date = datetime.strptime(request.form["due_date"], '%Y-%m-%dT%H:%M').strftime('%Y-%m-%d %H:%M')
    new_progress = int(request.form.get("progress", 0))
    new_label = request.form["label"]

    if new_progress == 100:
        cursor.execute("""
            INSERT INTO completed_tasks (user_id, title, description, due_date, label, progress, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, new_title, new_description, new_due_date, new_label, 100, datetime.now().strftime('%Y-%m-%d %H:%M')))

        cursor.execute("DELETE FROM tasks WHERE user_id=? AND title=? AND due_date=?", (user_id, original_title, original_due_date))
    else:
        cursor.execute("""
            UPDATE tasks SET title=?, description=?, due_date=?, label=?, progress=?
            WHERE user_id=? AND title=? AND due_date=?
        """, (new_title, new_description, new_due_date, new_label, new_progress, user_id, original_title, original_due_date))

    connection.commit()
    connection.close()
    return redirect(url_for("home"))


@app.route("/delete_task_permanent", methods=["POST"])
def delete_task_permanent():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    original_title = request.form["original_title"]
    original_due_date = request.form["original_due_date"]

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM tasks WHERE user_id=? AND title=? AND due_date=?",
                   (user_id, original_title, original_due_date))
    connection.commit()
    connection.close()

    return redirect(url_for("home"))




# Deleting/completing
@app.route("/delete_task", methods=["POST"])
def delete_task():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    title = request.form["title"]
    due_date = request.form["due_date"]

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT title, description, due_date, label, progress
        FROM tasks
        WHERE user_id=? AND title=? AND due_date=?
    """, (user_id, title, due_date))

    task = cursor.fetchone()

    if task:
        cursor.execute("""
            INSERT INTO completed_tasks
            (user_id, title, description, due_date, label, progress, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            task[0],
            task[1],
            task[2],
            task[3],
            100,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        cursor.execute("""
            DELETE FROM tasks
            WHERE user_id=? AND title=? AND due_date=?
        """, (user_id, title, due_date))

    connection.commit()
    connection.close()

    return redirect(url_for("home"))




# Home route
@app.route("/home", methods=["GET", "POST"])
def home():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    cursor.execute("SELECT email FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    user_email = result[0].split("@")[0].title() if result else "User"

    message = ""

    # ----- ADD TASK -----
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        due_date_str = request.form["due_date"]
        label = request.form.get("label", "")
        progress = int(request.form.get("progress", 0))

        try:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")
            due_date_formatted = due_date.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            connection.close()
            return redirect(url_for("home"))

        cursor.execute("""
            SELECT id FROM tasks
            WHERE user_id=? AND title=? AND due_date=?
        """, (user_id, title, due_date_formatted))

        if cursor.fetchone():
            message = "Duplicate task detected."
        else:
            cursor.execute("""
                INSERT INTO tasks (user_id, title, description, due_date, label, progress)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, title, description, due_date_formatted, label, progress))
            connection.commit()

    # ----- FILTERING -----
    query = request.args.get("query", "").strip()
    fields = request.args.getlist("fields")

    allowed_fields = {"title", "description", "label"}

    if query and fields:
        valid_fields = [f for f in fields if f in allowed_fields]
        if valid_fields:
            conditions = " OR ".join([f"{field} LIKE ?" for field in valid_fields])
            params = [f"%{query}%"] * len(valid_fields)
            cursor.execute(f"""
                SELECT title, description, due_date, label, progress
                FROM tasks
                WHERE user_id=? AND ({conditions})
            """, [user_id] + params)
        else:
            cursor.execute("""
                SELECT title, description, due_date, label, progress
                FROM tasks WHERE user_id=?
            """, (user_id,))
    else:
        cursor.execute("""
            SELECT title, description, due_date, label, progress
            FROM tasks WHERE user_id=?
        """, (user_id,))

    rows = cursor.fetchall()

    # ----- SORTING -----
    sort_by = request.args.get("sort_by")
    order = request.args.get("order", "asc")

    if sort_by == "due_date":
        rows.sort(
            key=lambda r: datetime.strptime(r[2], "%Y-%m-%d %H:%M"),
            reverse=(order == "desc")
        )
    elif sort_by == "progress":
        rows.sort(key=lambda r: r[4], reverse=(order == "desc"))

    connection.close()

    tasks = [
        {
            "title": r[0],
            "description": r[1],
            "due_date": r[2],
            "label": r[3],
            "progress": r[4]
        }
        for r in rows
    ]

    # ----- REMINDERS -----
    due_soon = []
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    for r in rows:
        parsed_date = datetime.strptime(r[2], "%Y-%m-%d %H:%M").date()
        if parsed_date in (today, tomorrow):
            due_soon.append(r[0])

    return render_template_string(
        home_template,
        tasks=tasks,
        user_email=user_email,
        due_soon=due_soon,
        unread_count=len(due_soon),
        message=message
    )



# Scheduling template
scheduling_template = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Scheduling</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='calendar.css') }}">

</head>
<body>
<!-- ===== NAVBAR ===== -->
<nav class="navbar">
    <div class="nav-left">
        <a href="/home" class="{% if request.path == '/home' %}active{% endif %}">Home</a>
        <a href="/analysis" class="{% if request.path == '/analysis' %}active{% endif %}">Analytics</a>
        <a href="/Scheduling" class="{% if request.path == '/Scheduling' %}active{% endif %}">Scheduling</a>
        <a href="/logout">Log Out</a>
    </div>

    <div class="nav-right">

        <!-- Notifications -->
        <div class="notification">
            <span class="bell" onclick="toggleReminders()">&#128276;</span>
            {% if unread_count > 0 %}
                <span class="badge">{{ unread_count }}</span>
            {% endif %}

            <div id="reminderBox" class="reminder-box">
                <strong>Tasks Due Soon:</strong>
                <ul>
                    {% if due_soon %}
                        {% for task in due_soon %}
                            <li>{{ task }}</li>
                        {% endfor %}
                    {% else %}
                        <li>No upcoming tasks</li>
                    {% endif %}
                </ul>
            </div>
        </div>

        <!-- Settings -->
    <div class="settings">
        <span class="gear" onclick="toggleSettings()">&#9881;</span>

        <div id="settingsBox" class="settings-box">
            <h4>Settings</h4>


            <hr>

            <!-- COLOUR PICKERS -->
            <label>Primary colour:</label>
            <input type="color" onchange="setPrimary(this.value)">

            <label>Secondary colour:</label>
            <input type="color" onchange="setSecondary(this.value)">

            <hr>

            <!-- MANAGE ACCOUNT -->
            <button onclick="openPasswordForm()">Manage Account</button>
        </div>
    </div>
    </nav>
    <h1>Calendar View - {{ now.strftime('%B %Y') }}</h1>

    <div style="margin-bottom: 20px;">
        <a href="/Scheduling?month={{ now.month - 1 if now.month > 1 else 12 }}&year={{ now.year if now.month > 1 else now.year - 1 }}">← Previous Month </a>
         |
        <a href="/Scheduling?month={{ now.month + 1 if now.month < 12 else 1 }}&year={{ now.year if now.month < 12 else now.year + 1 }}">Next Month →</a>
    </div>

    <div>
         {{ calendar_html|safe }}
    </div>


    <button onclick="toggleForm('eventForm')">Add Event</button>
    <button onclick="toggleForm('zoomForm')">Zoom into a Day</button>

    <div id="eventForm" style="display:none; margin-top:20px;">
        <form method="POST">
            <label>Title:</label><br>
            <input type="text" name="title" required><br><br>

            <label>Start Time:</label><br>
            <input type="datetime-local" name="start_time" required><br><br>

            <label>End Time:</label><br>
            <input type="datetime-local" name="end_time" required><br><br>

            <label>Description (optional):</label><br>
            <textarea name="description"></textarea><br><br>

            {% if message %}
                <p style="color:red;">{{ message }}</p>
                <label><input type="checkbox" name="confirm" value="yes" required> Confirm overlap and proceed</label><br><br>
            {% endif %}

            <input type="submit" value="Add Event">
        </form>
    </div>

    <div id="zoomForm" style="display:none;">
        <form method="GET" action="/Scheduling/day">
            <label>Select Day:</label><br>
            <input type="date" name="date" required><br><br>
            <input type="submit" value="View Day">
        </form>
    </div>

    <script>
        function toggleForm(id) {
            const el = document.getElementById(id);
            el.style.display = el.style.display === "none" ? "block" : "none";
        }
        {% if message %}
            toggleForm('eventForm');
        {% endif %}



        function toggleReminders() {
            const box = document.getElementById("reminderBox");
            box.style.display = box.style.display === "block" ? "none" : "block";
        }




            /* ===== SETTINGS ===== */
    function toggleSettings() {
        const box = document.getElementById("settingsBox");
        box.style.display = box.style.display === "block" ? "none" : "block";
    }




    /* ===== COLOUR PICKER ===== */
    function setPrimary(color) {
        document.documentElement.style.setProperty("--primary", color);
    }

    function setSecondary(color) {
        document.documentElement.style.setProperty("--secondary", color);
        saveThemeSettings();
    }

    function setPrimary(color) {
        document.documentElement.style.setProperty("--primary", color);

        // Calculate brightness
        const r = parseInt(color.substr(1, 2), 16);
        const g = parseInt(color.substr(3, 2), 16);
        const b = parseInt(color.substr(5, 2), 16);
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;

        // Auto text colour
        const textColor = brightness < 140 ? "#ffffff" : "#000000";
        document.documentElement.style.setProperty("--text", textColor);

        saveThemeSettings();
    }

    function saveThemeSettings() {
        const styles = getComputedStyle(document.documentElement);

        localStorage.setItem("primary", styles.getPropertyValue("--primary"));
        localStorage.setItem("secondary", styles.getPropertyValue("--secondary"));
        localStorage.setItem("text", styles.getPropertyValue("--text"));
    }



    /* ===== PASSWORD FORM ===== */
    function openPasswordForm() {
        document.getElementById("passwordForm").style.display = "block";
        document.getElementById("settingsBox").style.display = "none";
    }

    function closePasswordForm() {
        document.getElementById("passwordForm").style.display = "none";
    }

    function openPasswordForm() {
        document.getElementById("passwordForm").style.display = "block";
        document.getElementById("overlay").style.display = "block";
        document.getElementById("settingsBox").style.display = "none";
    }

    function closePasswordForm() {
        document.getElementById("passwordForm").style.display = "none";
        document.getElementById("overlay").style.display = "none";
    }


    window.onload = function () {

        const primary = localStorage.getItem("primary");
        const secondary = localStorage.getItem("secondary");
        const text = localStorage.getItem("text");


        if (primary) document.documentElement.style.setProperty("--primary", primary);
        if (secondary) document.documentElement.style.setProperty("--secondary", secondary);
        if (text) document.documentElement.style.setProperty("--text", text);
    };

    </script>
</body>
</html>
"""

# Overlap detection
def has_overlap(cursor, user_id, new_start, new_end):
    cursor.execute("""
        SELECT title FROM events
        WHERE user_id=? AND (
            (start_time < ? AND end_time > ?) OR
            (start_time >= ? AND start_time < ?)
        )
    """, (user_id, new_end, new_start, new_start, new_end))
    overlapping_events = cursor.fetchall()

    cursor.execute("""
        SELECT title FROM tasks
        WHERE user_id=? AND (
            due_date BETWEEN ? AND ?
        )
    """, (user_id, new_start, new_end))
    overlapping_tasks = cursor.fetchall()

    return overlapping_events + overlapping_tasks

# Scheduling route
@app.route("/Scheduling", methods=["GET", "POST"])
def scheduling():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # ----- DATE CONTEXT -----
    year = int(request.args.get("year", datetime.now().year))
    month = int(request.args.get("month", datetime.now().month))
    now = datetime(year, month, 1)
    message = ""

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    # ----- USER EMAIL -----
    cursor.execute("SELECT email FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    user_email = result[0].split("@")[0].title() if result else "User"

    # ===== ADD EVENT (POST) =====
    if request.method == "POST":
        title = request.form["title"]
        description = request.form.get("description", "")
        start_time_str = request.form["start_time"]
        end_time_str = request.form["end_time"]
        confirm = request.form.get("confirm")

        start_dt = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M")

        overlaps = has_overlap(
            cursor,
            user_id,
            start_dt.strftime("%Y-%m-%d %H:%M"),
            end_dt.strftime("%Y-%m-%d %H:%M")
        )

        if overlaps and not confirm:
            overlap_titles = ", ".join([o[0] for o in overlaps])
            message = f"Overlaps with: {overlap_titles}. Resubmit to confirm."
        else:
            cursor.execute("""
                INSERT INTO events (user_id, title, description, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                title,
                description,
                start_dt.strftime("%Y-%m-%d %H:%M"),
                end_dt.strftime("%Y-%m-%d %H:%M")
            ))
            connection.commit()

    # ===== EVENTS THIS MONTH =====
    cursor.execute("""
        SELECT title, start_time
        FROM events
        WHERE user_id=?
          AND strftime('%Y', start_time)=?
          AND strftime('%m', start_time)=?
    """, (user_id, str(year), f"{month:02d}"))
    events = cursor.fetchall()

    # ===== TASKS THIS MONTH =====
    cursor.execute("""
        SELECT title, due_date
        FROM tasks
        WHERE user_id=?
          AND strftime('%Y', due_date)=?
          AND strftime('%m', due_date)=?
    """, (user_id, str(year), f"{month:02d}"))
    tasks = cursor.fetchall()

    # ===== BUILD CALENDAR DATA =====
    day_map = {}

    for title, start in events:
        parsed = datetime.strptime(start, "%Y-%m-%d %H:%M")
        day_map.setdefault(parsed.day, []).append(f"Event: {title}")

    for title, due in tasks:
        parsed = datetime.strptime(due, "%Y-%m-%d %H:%M")
        day_map.setdefault(parsed.day, []).append(f"Task: {title}")

    cal = calendar.HTMLCalendar(calendar.MONDAY)
    calendar_html = cal.formatmonth(year, month)

    for day, items in day_map.items():
        calendar_html = calendar_html.replace(
            f">{day}<",
            f">{day}<br><h5>{'<br>'.join(items)}</h5><"
        )

    # ===== REMINDERS (NAVBAR) =====
    due_soon = []
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    cursor.execute("SELECT title, due_date FROM tasks WHERE user_id=?", (user_id,))
    for title, due in cursor.fetchall():
        parsed = datetime.strptime(due, "%Y-%m-%d %H:%M").date()
        if parsed in (today, tomorrow):
            due_soon.append(title)

    connection.close()

    return render_template_string(
        scheduling_template,
        calendar_html=calendar_html,
        user_email=user_email,
        now=now,
        message=message,
        due_soon=due_soon,
        unread_count=len(due_soon)
    )

# Zoom into a day
@app.route("/Scheduling/day", methods=["GET"])
def view_day():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    date_str = request.args.get("date")
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    cursor.execute("SELECT title, description, due_date, label, id FROM tasks WHERE user_id=? AND date(due_date)=?", (user_id, date_str))
    tasks = cursor.fetchall()

    cursor.execute("SELECT title, description, start_time, end_time, id FROM events WHERE user_id=? AND date(start_time)=?", (user_id, date_str))
    events = cursor.fetchall()
    connection.close()

    sch_html = f"""
    <html>
        <body>
            <h2>Schedule for {date_str}</h2>
            <a href="/Scheduling">Back</a><br><br>

            <h3>Tasks</h3>
            {''.join([f"<div><strong>{t[0]}</strong>: {t[1]} ({t[2]})<form method='POST' action='/delete_task_day'><input type='hidden' name='id' value='{t[4]}'><input type='submit' value='Delete'></form></div>" for t in tasks]) or "No tasks"}

            <h3>Events</h3>
            {''.join([f"<div><strong>{e[0]}</strong>: {e[1]} ({e[2].replace('T', ' ')} to {e[3].replace('T', ' ')})<form method='POST' action='/delete_event_day'><input type='hidden' name='id' value='{e[4]}'><input type='submit' value='Delete'></form></div>" for e in events]) or "No events"}
        </body>
    </html>
    """
    return sch_html

@app.route("/delete_task_day", methods=["POST"])
def delete_task_day():
    task_id = request.form["id"]
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    connection.commit()
    connection.close()
    return redirect(request.referrer)

@app.route("/delete_event_day", methods=["POST"])
def delete_event_day():
    event_id = request.form["id"]
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()
    cursor.execute("DELETE FROM events WHERE id=?", (event_id,))
    connection.commit()
    connection.close()
    return redirect(request.referrer)

# Analytics template
analysis_template = """
<!doctype html>
<html>
<head>
    <title>Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* ===== CSS VARIABLES ===== */
        :root {
            --primary: #ffffff;   /* Main background */
            --secondary: #18a300; /* Accents, buttons */
            --text: #222222;      /* Text color */
            --border: #cccccc;    /* Borders */
        }

        /* ===== NAVBAR ===== */
        .navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: var(--primary);
            padding: 10px 20px;
            position: relative;
            z-index: 1002;
        }
        .navbar a {
            color: var(--text);
            text-decoration: none;
            margin-right: 15px;
            font-weight: bold;
        }
        .navbar a:hover,
        .navbar .active {
            color: var(--secondary);
        }

        /* ===== NAV RIGHT ===== */
        .nav-right {
            display: flex;
            align-items: center;
        }

        /* ===== NOTIFICATIONS ===== */
        .notification {
            position: relative;
            margin-right: 20px;
        }
        .bell {
            font-size: 22px;
            color: var(--text);
            cursor: pointer;
        }
        .badge {
            position: absolute;
            top: -6px;
            right: -10px;
            background: red;
            color: white;
            border-radius: 50%;
            padding: 3px 7px;
            font-size: 11px;
        }

        /* Reminder & Settings Dropdowns */
        .reminder-box,
        .settings-box {
            display: none;
            position: absolute;
            top: 30px;
            right: 0;
            background-color: var(--primary);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 12px;
            width: 220px;
            z-index: 1003;
        }
        .reminder-box ul {
            padding-left: 18px;
            margin: 5px 0;
        }
        .settings-box hr {
            margin: 10px 0;
            border-color: var(--border);
        }

        /* ===== SETTINGS ICON ===== */
        .gear {
            font-size: 22px;
            color: var(--text);
            cursor: pointer;
        }

        /* ===== OVERLAY ===== */
        #overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1001;
        }

        /* ===== TASKS ===== */
        .task {
            margin-bottom: 10px;
            padding: 10px;
            color: var(--text);
            border: 1px solid var(--secondary);
            background-color: #ffffff; /* Kept readable background */
        }

        /* ===== BUTTONS ===== */
        button {
            cursor: pointer;
            background-color: var(--secondary);
            color: var(--primary);
            border: none;
            padding: 8px 12px;
        }

        /* ===== FORMS & MODALS ===== */
        #taskForm,
        #editForm,
        #filterForm,
        #settingsForm,
        .popup-form {
            display: none;
            position: fixed;
            background-color: var(--primary);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 20px;
            z-index: 1003;
            width: 320px;
        }
        #taskForm,
        #editForm,
        #filterForm,
        #settingsForm {
            top: 25%;
            left: 50%;
            transform: translateX(-50%);
        }
        .popup-form {
            top: 25%;
            left: 35%;
        }

        /* Inputs */
        input,
        textarea,
        select {
            background-color: var(--primary);
            color: var(--text);
            border: 1px solid var(--border);
            padding: 8px;
            width: 100%;
            margin: 8px 0;
        }

        /* Headings & Labels */
        label,
        h1, h2, h3, h4 {
            color: var(--text);
        }

        * {
            box-sizing: border-box;
        }


        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
            background-color: var(--primary);
            color: var(--text);
            font-family: Arial, sans-serif;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

    </style>
</head>
<body>
    <!-- ===== NAVBAR ===== -->
    <nav class="navbar">
        <div class="nav-left">
            <a href="/home" class="{% if request.path == '/home' %}active{% endif %}">Home</a>
            <a href="/analysis" class="{% if request.path == '/analysis' %}active{% endif %}">Analytics</a>
            <a href="/Scheduling" class="{% if request.path == '/Scheduling' %}active{% endif %}">Scheduling</a>
            <a href="/logout">Log Out</a>
        </div>

        <div class="nav-right">

            <!-- Notifications -->
            <div class="notification">
                <span class="bell" onclick="toggleReminders()">&#128276;</span>
                {% if unread_count > 0 %}
                    <span class="badge">{{ unread_count }}</span>
                {% endif %}

                <div id="reminderBox" class="reminder-box">
                    <strong>Tasks Due Soon:</strong>
                    <ul>
                        {% if due_soon %}
                            {% for task in due_soon %}
                                <li>{{ task }}</li>
                            {% endfor %}
                        {% else %}
                            <li>No upcoming tasks</li>
                        {% endif %}
                    </ul>
                </div>
            </div>

            <!-- Settings -->
        <div class="settings">
            <span class="gear" onclick="toggleSettings()">&#9881;</span>

            <div id="settingsBox" class="settings-box">
                <h4>Settings</h4>


                <hr>

                <!-- COLOUR PICKERS -->
                <label>Primary colour:</label>
                <input type="color" onchange="setPrimary(this.value)">

                <label>Secondary colour:</label>
                <input type="color" onchange="setSecondary(this.value)">

                <hr>

                <!-- MANAGE ACCOUNT -->
                <button onclick="openPasswordForm()">Manage Account</button>
            </div>
        </div>
        </nav>

    <h2>Task Completion Analytics</h2>
    <p>Total tasks this month: {{ total }}</p>
    <p>Completed tasks: {{ completed }}</p>
    <p>Completion percentage: {{ percent|round(2) }}%</p>

    <canvas id="completionChart" width="350" height="350"></canvas>

    <!-- You likely need these if using password form -->
    <div id="overlay" style="display: none;"></div>
    <div id="passwordForm" style="display: none;"> <!-- your form here --> </div>

    <script>
        // Doughnut chart
        const ctx = document.getElementById('completionChart').getContext('2d');
        const completionChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'Incomplete'],
                datasets: [{
                    data: [{{ completed }}, {{ total - completed }}],
                    backgroundColor: ['#4CAF50', '#FF5252']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Tasks Completed This Month'
                    }
                }
            }
        });

function toggleSettings() {
        const box = document.getElementById("settingsBox");
        box.style.display = box.style.display === "block" ? "none" : "block";
    }

    function toggleReminders() {
        const box = document.getElementById("reminderBox");
        box.style.display = box.style.display === "block" ? "none" : "block";
    }

    function setPrimary(color) {
        document.documentElement.style.setProperty("--primary", color);

        const r = parseInt(color.substr(1, 2), 16);
        const g = parseInt(color.substr(3, 2), 16);
        const b = parseInt(color.substr(5, 2), 16);
        const brightness = (r * 299 + g * 587 + b * 114) / 1000;
        const textColor = brightness < 140 ? "#ffffff" : "#000000";
        document.documentElement.style.setProperty("--text", textColor);
        saveThemeSettings();
    }

    function setSecondary(color) {
        document.documentElement.style.setProperty("--secondary", color);
        saveThemeSettings();
    }

    // ... saveThemeSettings, open/closePasswordForm ...

    window.onload = function () {
        const primary = localStorage.getItem("primary");
        const secondary = localStorage.getItem("secondary");
        const text = localStorage.getItem("text");

        if (primary) document.documentElement.style.setProperty("--primary", primary);
        if (secondary) document.documentElement.style.setProperty("--secondary", secondary);
        if (text) document.documentElement.style.setProperty("--text", text);
    };
</script>
</body>
</html>
"""

# Analytics route

@app.route("/analysis")
def analysis():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    # ===== REMINDERS (Due today or tomorrow) =====
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    cursor.execute("""
        SELECT title, due_date FROM tasks
        WHERE user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()

    due_soon = []
    for row in rows:
        title = row[0]
        due_date_str = row[1]
        if due_date_str:
            try:
                # Your due_date is stored as "YYYY-MM-DD HH:MM"
                parsed_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M").date()
                if parsed_date in (today, tomorrow):
                    due_soon.append(title)
            except ValueError:
                continue  # Skip malformed dates

    unread_count = len(due_soon)  # Badge count

    # ===== ANALYTICS: Tasks this month =====
    now = datetime.now()
    year = now.year
    month = now.month
    month_str = f"{month:02d}"

    # Count active (incomplete) tasks due this month
    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE user_id = ?
          AND strftime('%Y', due_date) = ?
          AND strftime('%m', due_date) = ?
    """, (user_id, str(year), month_str))
    active_count = cursor.fetchone()[0]

    # Count completed tasks this month (based on completed_at)
    cursor.execute("""
        SELECT COUNT(*) FROM completed_tasks
        WHERE user_id = ?
          AND strftime('%Y', completed_at) = ?
          AND strftime('%m', completed_at) = ?
    """, (user_id, str(year), month_str))
    completed_count = cursor.fetchone()[0]

    connection.close()

    total = active_count + completed_count
    percent_completed = (completed_count / total * 100) if total > 0 else 0

    # Render the template with ALL required variables
    return render_template_string(
        analysis_template,
        total=total,
        completed=completed_count,
        percent=percent_completed,
        due_soon=due_soon,
        unread_count=unread_count
    )
# Log out route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug = True)











'''
 |
 |
 |   Cycle 2:
 |
 | ->
 | ->
 | ->
 | ->






Add more text to explainations/objective and refceltions
Add comments (in word) to pictures to descibe what each image is
Add good example (about 10 ish (Berry said 5)) to the Evidence doc


'''







