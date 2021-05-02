import json
import os
import tempfile
import requests

from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, session, render_template, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


app = Flask(__name__)


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# Configure session to use filesystem
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@   app.route("/", methods=["POST", "GET"])
def index():
    if request.method == "GET":
        return render_template("index.html")

    else:
        q = request.form.get("q") + "%"
        books = db.execute(
            "Select * from book WHERE isbn LIKE :q or title LIKE :q or author like :q", {"q": q}).fetchall()

    return render_template("books.html", q=q, books=books)


@   app.route("/books/<string:book_isbn>")
def book(book_isbn):
    book = db.execute("SELECT * from book WHERE isbn = :isbn", {
        "isbn": book_isbn}).fetchone()

    if book is None:
        return jsonify({"error": "Invalid book isbn"}), 422

    reviews = db.execute(
        "SELECT * from reviews where id_book = :id_book", {"id_book": book["id_book"]})

    alreadyComented = False

    for review in reviews:
        if review["id_user"] == session["user_id"]:
            alreadyComented = True

    response = requests.get(
        "https://www.googleapis.com/books/v1/volumes?q=isbn:"+book_isbn)
    data = response.json()
    book_Google = data["items"][0]["volumeInfo"]
    img = book_Google["imageLinks"]["thumbnail"]

    return render_template("book.html", alreadyComented=alreadyComented, reviews=book_Google["ratingsCount"], promedio=book_Google["averageRating"], img=img, book=book, description=book_Google["description"])


@   app.route("/api/books/<string:book_isbn>")
def api(book_isbn):
    book = db.execute("SELECT title, author, year from book WHERE isbn = :isbn", {
        "isbn": book_isbn}).fetchone()
    if book is None:
        return jsonify({"error": "Invalid book isbn"})

    data = requests.get(
        "https://www.googleapis.com/books/v1/volumes?q=isbn:"+book_isbn).json()
    if data is None:
        return jsonify({"error": "Invalid book isbn"})
    book_Google = data["items"][0]["volumeInfo"]
    return jsonify({
        "title": book["title"],
        "author": book["author"],
        "year": book["year"],
        "review_count": book_Google["ratingsCount"],
        "average_score": book_Google["averageRating"]
    })


@   app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    if request.method == "POST":
        if request.form.get("password") != request.form.get("confirmation"):
            return "passwords doesn´t match!"

        user = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username": request.form.get("username")}).fetchone()
        if user is not None:
            return "User is taken, please go back"

        db.execute("INSERT INTO users(username, password) VALUES(:username, :password)",
                   {"username": request.form.get("username"),
                    "password": generate_password_hash(request.form.get("password"))})
        db.commit()

        novoid = db.execute("Select * from users where username = :username",
                            {"username": request.form.get("username")}).fetchone()

        session["user_id"] = novoid["id_user"]
        return redirect('/')

    else:
        return render_template("/register.html")


@   app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")


@ app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return "Must provide username"

        # Ensure password was submitted
        elif not request.form.get("password"):
            return "Must provide password"

        # Query database for username
        user = db.execute("SELECT * FROM users WHERE username = :username", {
            "username": request.form.get("username")}).fetchone()

        # Ensure username exists and password is correct
        if not user:
            return "invalid username"

        if not check_password_hash(user["password"], request.form.get("password")):
            return "invalid password"

            # Remember which user has logged in
        session["user_id"] = user["id_user"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
