#test_integration(user_flow).py
import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from main import app, get_db, Base, engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

pytestmark = pytest.mark.integration

# Setup test DB
TEST_DB_URL = "sqlite:///./test_integration.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

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

# --- Integration Test ---

def test_user_flow_integration():
    email = "integration@example.com"
    password = "secure123"

    # 1. Register
    r = client.post("/register", json={"email": email, "password": password})
    assert r.status_code == 200

    # 2. Login
    r = client.post("/login", json={"email": email, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Browse books
    r = client.get("/books", headers=headers)
    assert r.status_code == 200
    books = r.json()
    assert len(books) > 0

    # 4. Try adding premium book (should fail on free plan)
    premium_book = next(book for book in books if book["is_premium"])
    r = client.post(f"/books/{premium_book['id']}/add-to-library", headers=headers)
    assert r.status_code == 403
    assert "Premium subscription required" in r.json()["detail"]

    # 5. Subscribe to premium
    r = client.get("/subscription-plans", headers=headers)
    plans = r.json()
    premium_plan = next(plan for plan in plans if plan["name"] == "premium")
    r = client.post(f"/subscribe/{premium_plan['id']}", headers=headers)
    assert r.status_code == 200
    assert "Successfully subscribed" in r.json()["message"]

    # 6. Add premium book again (should succeed)
    r = client.post(f"/books/{premium_book['id']}/add-to-library", headers=headers)
    assert r.status_code == 200
    assert "Book added to library" in r.json()["message"]

    # 7. View my library
    r = client.get("/my-books", headers=headers)
    my_books = r.json()
    assert any(book["id"] == premium_book["id"] for book in my_books)

    # 8. Mark book as read
    r = client.post(f"/books/{premium_book['id']}/mark-read", headers=headers)
    assert r.status_code == 200
    assert "marked as read" in r.json()["message"]

