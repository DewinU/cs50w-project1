import json
import os
import tempfile
import requests

from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
from flask import Flask, session, render_template, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from helpers import apology, login_required

projectFolder = os.path.expanduser('~/cs50w-project1')  # adjust as appropriate
load_dotenv(os.path.join(projectFolder, '.env'))

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_LOCAL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_LOCAL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    else:
        q = request.form.get("q") + "%"
        books = db.execute(
            "Select * from book WHERE isbn LIKE :q or title LIKE :q or author like :q", {"q": q}).fetchall()
        return render_template("books.html", books=books, q=q)


@app.route("/books/<string:book_isbn>")
def book(book_isbn):
    response = requests.get(
        "https://www.googleapis.com/books/v1/volumes?q=isbn:"+book_isbn).json()
    return response


@app.route("/api/books/<string:book_isbn>")
def api(book_isbn):
    book = db.execute("SELECT title, author, year from book WHERE isbn = :isbn", {
                      "isbn": book_isbn}).fetchone()
    if book is None:
        return jsonify({"error": "Invalid book isbn"}), 422

    external = requests.get(
        "https://www.googleapis.com/books/v1/volumes?q=isbn:"+book_isbn)
    data = external.json()
    if data is None:
        return jsonify({"error": "Invalid book isbn"}), 422
    book_Google = data["items"][0]["volumeInfo"]
    return jsonify({
        "title": book["title"],
        "author": book["author"],
        "year": book["year"],
        "review_count": book_Google["ratingsCount"],
        "average_score": book_Google["averageRating"]
    })


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    if request.method == "POST":
        if not request.form.get("username") or not request.form.get("password") or not request.form.get("confirmation"):
            return apology("must fill all the blanks!", 400)

        if request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords doesn´t match!", 400)

        if db.execute("SELECT username FROM users WHERE username = :username",
                      username=request.form.get("username")):
            return apology("user is already taken!", 400)

        novoid = db.execute("INSERT INTO users('username', 'hash') VALUES(:username, :password)",
                            {"username"=request.form.get("username"),
                             "password"=generate_password_hash(request.form.get("password"))})
        session["user_id"] = novoid
        flash("Registered")
        return redirect("/")

    else:
        return render_template("/register.html")


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM user WHERE username = :username", {
            "username": request.form.get("username")})

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
