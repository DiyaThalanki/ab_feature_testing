# test_books.py
import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app, get_db, Base, engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
pytestmark = pytest.mark.unit

# Use a separate test DB
TEST_DB_URL = "sqlite:///./test_books.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Override FastAPI dependency
def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# --- Setup ---
@pytest.fixture(scope="module", autouse=True)
def setup_database():
    if not database_exists(test_engine.url):
        create_database(test_engine.url)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    client.post("/seed-data")

@pytest.fixture
def user_token():
    email = "booktest@example.com"
    password = "pass123"
    client.post("/register", json={"email": email, "password": password})
    res = client.post("/login", json={"email": email, "password": password})
    return res.json()["access_token"]

# --- BOOK TESTS ---

def test_get_all_books(user_token):
    res = client.get("/books", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    books = res.json()
    assert isinstance(books, list)
    assert len(books) > 0
    assert "title" in books[0]

def test_get_single_book(user_token):
    res = client.get("/books/1", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    book = res.json()
    assert book["id"] == 1
    assert "title" in book

def test_add_book_to_library(user_token):
    res = client.post("/books/1/add-to-library", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    assert "Book added to library" in res.json()["message"]

def test_add_same_book_twice(user_token):
    res = client.post("/books/1/add-to-library", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 400
    assert "already in library" in res.json()["detail"]

def test_mark_book_as_read(user_token):
    res = client.post("/books/1/mark-read", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    assert "marked as read" in res.json()["message"]

def test_get_my_books(user_token):
    res = client.get("/my-books", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    books = res.json()
    assert isinstance(books, list)
    assert len(books) >= 1

