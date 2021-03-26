import csv
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

projectFolder = os.path.expanduser('~/P2')  # adjust as appropriate
load_dotenv(os.path.join(projectFolder, '.env'))

engine = create_engine(os.getenv("DATABASE_LOCAL"))
db = scoped_session(sessionmaker(bind=engine))


def main():
    f = open("books.csv")
    reader = csv.reader(f)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO book (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                   {"isbn": isbn, "title": title, "author": author, "year": year})
        print(f"Added book {title}")
    db.commit()


if __name__ == "__main__":
    main()
