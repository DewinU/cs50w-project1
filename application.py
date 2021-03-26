import os
import tempfile
import requests

from dotenv import load_dotenv
from flask import Flask, session, render_template, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

projectFolder = os.path.expanduser('~/P2')  # adjust as appropriate
load_dotenv(os.path.join(projectFolder, '.env'))

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_LOCAL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
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
