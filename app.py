import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for



app = Flask(__name__)
#List for tasks
tasks = []
#List for emails if a reset is needed
user_email_temp = {"email": "", "code": ""}

# Initialize database
connection = sqlite3.connect("accounts.db")
cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        security_code TEXT NOT NULL
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




#Login
@app.route("/", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        connection = sqlite3.connect("accounts.db")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        connection.close()

        if user:
            return redirect(url_for("home"))
        else:
            message = "Invalid email or password."

    return render_template_string(login_form, message=message)

#Create an account
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
                connection = sqlite3.connect("accounts.db")
                cursor = connection.cursor()
                cursor.execute("INSERT INTO users (email, password, security_code) VALUES (?, ?, ?)",
                               (email, password, security_code))
                connection.commit()
                connection.close()
                return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                message = "Email already exists. Please choose another."

    return render_template_string(register_form, message=message)


#Forgotten password
@app.route("/reset", methods=["GET", "POST"])
def reset_password():
    message = ""
    if request.method == "POST":
        new_password = request.form.get("new_password")

        if len(new_password) < 8:
            message = "Password must be at least 8 characters long."
        else:
            email = user_email_temp.get("email")
            connection = sqlite3.connect("accounts.db")
            cursor = connection.cursor()
            cursor.execute("UPDATE users SET password=? WHERE email=?", (new_password, email))
            connection.commit()
            connection.close()
            message = "Password reset successful."
            return redirect(url_for("login"))

    return render_template_string(reset_form, message=message)

#Verifying email
@app.route("/verify", methods=["GET", "POST"])
def verify_code():
    message = ""
    if request.method == "POST":
        email = request.form.get("email")
        code = request.form.get("code")
        connection = sqlite3.connect("accounts.db")
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






@app.route('/home', methods=['GET', 'POST'])
def home():
    return "Hello"



'''
Task Algorithm
 |
 |   Cycle 1:
 |-> Add tasks (exclusive to the user) ID:13
 |-> Remove/Complete Task ID:14
 |-> Create, remove and edit a label IDs: 8,9,10 (respectivley)
 |-> Edit Task ID: 15

 |
 |   Cycle 2:
 |-> Smart Schdueling (Time tabling) enter free hours/days, add events and create time table ID: 11
 |->
 |->
 |->



'''




















































