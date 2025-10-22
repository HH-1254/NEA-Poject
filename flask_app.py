import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for, session
from datetime import datetime
import calendar


 # Replace with a secure key


app = Flask(__name__)
app.secret_key = "your_secret_key_here"


#List for tasks
tasks = []
#List for emails if a reset is needed
user_email_temp = {"email": "", "code": ""}


#Initalise Database
connection = sqlite3.connect("NEA.db")
cursor = connection.cursor()


#Table for login system
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        security_code TEXT NOT NULL
    )
""")


#Table for Task management
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        due_date TEXT NOT NULL,
        label TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")


connection.commit()
connection.close()




# Create login form in html
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
    </div>
</body>
</body>
</html>
"""

# Create register form in html
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

        <label>Security Code (numbers only):</label><br>
        <input type="text" name="security_code" pattern="\d+" required><br><br>

        <input type="submit" value="Register">
    </form>
    <p style="color:red;">{{ message }}</p>
    <p>Already have an account? <a href="/">Login here</a></p>
</body>
</html>
"""
# Create forgot form in html
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

# Create verify form in html
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





# Login
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
        connection.close()

        if user:
            session['user_id'] = user[0]
            return redirect(url_for("home"))
        else:
            message = "Invalid email or password."

    # This handles GET requests and also POST failures
    return render_template_string(login_form, message=message)



#Register account
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        security_code = request.form.get("security_code")

        if len(password) < 8:
            message = "Password must be at least 8 characters long."
        elif not security_code.isdigit():
            message = "Security code must be numeric."
        else:
            try:
                connection = sqlite3.connect("NEA.db")
                cursor = connection.cursor()
                cursor.execute("INSERT INTO users (email, password, security_code) VALUES (?, ?, ?)",
                               (email, password, security_code))
                connection.commit()
                connection.close()
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                message = "Email already exists. Please choose another."

    return render_template_string(register_form, message=message)


#Verify identity
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


#Reset password
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
            message = "Password reset successful."
            return redirect(url_for("login"))
    return render_template_string(reset_form, message=message)







#Task template
home_template = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Task Manager</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='home.css') }}">
    <style>
        body {
            font-family: Arial, sans-serif;
            padding: 20px;
        }
        .task {
            margin-bottom: 10px;
            padding: 10px;
            border: 1px solid #ccc;
        }
        #taskForm, #editForm {
            display: none;
            position: fixed;
            top: 20%;
            left: 35%;
            background: #fff;
            padding: 20px;
            border: 2px solid #333;
            z-index: 1001;
        }
        #overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
        }
    </style>
</head>
<body>
    <h2>Welcome, {{ user_email }}</h2>

    <header class="site-header">
        <nav class="navbar">
            <a href="/home">Home</a>
            <a href="/analysis">Analytics</a>
            <a href="/logout">Log Out</a>
            <a href="/Scheduling">Scheduling</a>
        </nav>
    </header>

    <h1>Task Manager</h1>
    <button onclick="showForm()">Add Task</button>

    <div id="overlay" onclick="hideForm(); hideEditForm();"></div>
    <!-- Add Task Form -->
    <div id="taskForm">
        <form method="POST">
            <label>Title:</label><br>
            <input type="text" name="title" required><br><br>
            <label>Description:</label><br>
            <textarea name="description" required></textarea><br><br>
            <label>Due Date:</label><br>
            <input type="datetime-local" name="due_date" required><br><br>
            <label>Label:</label><br>
            <input type="text" name="label"><br><br>
            <button type="submit">Add Task</button>
            <button type="button" onclick="hideForm()">Cancel</button>
        </form>
    </div>

    <!-- Edit Task Form -->
    <div id="editForm">
        <form method="POST" action="/update_task">
            <input type="hidden" name="original_title" id="editOriginalTitle">
            <input type="hidden" name="original_due_date" id="editOriginalDueDate">
            <label>New Title:</label><br>
            <input type="text" name="title" required><br><br>
            <label>New Description:</label><br>
            <textarea name="description" required></textarea><br><br>
            <label>New Due Date:</label><br>
            <input type="datetime-local" name="due_date" required><br><br>
            <label>New Label:</label><br>
            <input type="text" name="label"><br><br>
            <button type="submit">Update Task</button>
            <button type="button" onclick="hideEditForm()">Cancel</button>
        </form>
    </div>

    <!-- Task Display -->
    {% for task in tasks %}
        <div class="task">
            <strong>{{ task.title }}</strong><br>
            {{ task.description }}<br>
            <em>Due: {{ task.due_date }}</em><br>
            {% if task.label %}
                <strong>Label:</strong> {{ task.label }}<br>
            {% endif %}
            <button onclick="openEditForm('{{ task.title }}', '{{ task.description }}', '{{ task.due_date }}', '{{ task.label }}')">Edit</button>
            <form method="POST" action="/delete_task" style="display:inline;">
                <input type="hidden" name="title" value="{{ task.title }}">
                <input type="hidden" name="due_date" value="{{ task.due_date }}">
                <button type="submit">Complete</button>
            </form>
        </div>
    {% endfor %}
    </body>
    <script>

    function showForm() {
    document.getElementById('taskForm').style.display = 'block';
    document.getElementById('overlay').style.display = 'block';
    }

    function hideForm() {
        document.getElementById('taskForm').style.display = 'none';
        document.getElementById('overlay').style.display = 'none';
    }

    function hideEditForm() {
        document.getElementById('editForm').style.display = 'none';
        document.getElementById('overlay').style.display = 'none';
    }

    function openEditForm(title, description, dueDate, label) {
        document.getElementById('editOriginalTitle').value = title;
        document.getElementById('editOriginalDueDate').value = dueDate;
        const editForm = document.getElementById('editForm');
        editForm.querySelector('input[name="title"]').value = title;
        editForm.querySelector('textarea[name="description"]').value = description;
        editForm.querySelector('input[name="due_date"]').value = dueDate.replace(' ', 'T');
        editForm.querySelector('input[name="label"]').value = label || "";
        editForm.style.display = 'block';
        document.getElementById('overlay').style.display = 'block';
    }
    </script>
"""





# Editing Tasks
@app.route("/edit_task", methods=["POST"])
def edit_task():
    return render_template_string(home_template, tasks=get_tasks(), user_email=get_user_email(), show_edit_form=True, original_title=request.form["original_title"], original_due_date=request.form["original_due_date"])


# Updating (Live updating) Tasks
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

    cursor.execute("""
        UPDATE tasks SET title=?, description=?, due_date=?
        WHERE user_id=? AND title=? AND due_date=?
    """, (new_title, new_description, new_due_date, user_id, original_title, original_due_date))
    connection.commit()
    connection.close()
    return redirect(url_for("home"))



#Deleting/completeing
@app.route("/delete_task", methods=["POST"])
def delete_task():
    user_id = session.get("user_id")
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    title = request.form["title"]
    due_date = request.form["due_date"]

    cursor.execute("DELETE FROM tasks WHERE user_id=? AND title=? AND due_date=?", (user_id, title, due_date))
    connection.commit()
    connection.close()
    return redirect(url_for("home"))




#Route to homepage
@app.route("/home", methods=["GET", "POST"])
def home():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()

    # Fetch user's email
    cursor.execute("SELECT email FROM users WHERE id=?", (user_id,))
    user_email = cursor.fetchone()[0].split("@")
    user_email = user_email[0].title()

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        due_date_str = request.form["due_date"]
        label = request.form.get("label", "")

        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            due_date_formatted = due_date.strftime('%Y-%m-%d %H:%M')
        except ValueError:
            due_date_formatted = "Invalid date"

        cursor.execute("""
            SELECT * FROM tasks WHERE user_id=? AND title=? AND due_date=?
        """, (user_id, title, due_date_formatted))
        existing_task = cursor.fetchone()

        if not existing_task:
            cursor.execute("""
                INSERT INTO tasks (user_id, title, description, due_date, label)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, title, description, due_date_formatted, label))
            connection.commit()

    cursor.execute("SELECT title, description, due_date, label FROM tasks WHERE user_id=?", (user_id,))
    tasks = [{'title': row[0], 'description': row[1], 'due_date': row[2], 'label': row[3]} for row in cursor.fetchall()]

    return render_template_string(home_template, tasks=tasks, user_email=user_email)




#Scheduling
scheduling_template = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Scheduling</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='calendar.css') }}">
    <style>

    </style>
</head>
<body>
    <h2>Welcome, {{ user_email }}</h2>

    <header class="site-header">
        <nav class="navbar">
            <a href="/home">Home</a>
            <a href="/analysis">Analytics</a>
            <a href="/logout">Log Out</a>
            <a href="/Scheduling">Scheduling</a>
        </nav>
    </header>

    <h1>Calendar View - {{ now.strftime('%B %Y') }}</h1>
    <div>
        {{ calendar_html|safe }}
    </div>
</body>
</html>
"""







#Scheduling route

@app.route("/Scheduling")
def scheduling():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # Get current month and year
    now = datetime.now()
    year = now.year
    month = now.month

    # Generate calendar HTML
    cal = calendar.HTMLCalendar(calendar.MONDAY)
    calendar_html = cal.formatmonth(year, month)

    # Fetch user's email
    connection = sqlite3.connect("NEA.db")
    cursor = connection.cursor()
    cursor.execute("SELECT email FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()
    connection.close()

    if result:
        user_email = result[0].split("@")[0].title()
    else:
        user_email = "Unknown"

    # Render calendar template
    return render_template_string(scheduling_template,calendar_html=calendar_html,user_email=user_email,now=now)













@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
