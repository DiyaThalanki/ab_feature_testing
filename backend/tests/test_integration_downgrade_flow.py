# test_integration(downgrade_flow).py
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
TEST_DB_URL = "sqlite:///./test_integration_plan.db"
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

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    if not database_exists(test_engine.url):
        create_database(test_engine.url)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    client.post("/seed-data")

def test_plan_downgrade_access_control():
    email = "downgradeuser@example.com"
    password = "downgradetest"

    # Register + Login
    client.post("/register", json={"email": email, "password": password})
    r = client.post("/login", json={"email": email, "password": password})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Subscribe to premium
    plans = client.get("/subscription-plans", headers=headers).json()
    premium_plan = next(p for p in plans if p["name"] == "premium")
    free_plan = next(p for p in plans if p["name"] == "free")
    client.post(f"/subscribe/{premium_plan['id']}", headers=headers)

    # Add a premium book
    books = client.get("/books", headers=headers).json()
    premium_books = [b for b in books if b["is_premium"]]
    first_premium = premium_books[0]
    second_premium = premium_books[1]

    r = client.post(f"/books/{first_premium['id']}/add-to-library", headers=headers)
    assert r.status_code == 200

    # Downgrade to free plan
    r = client.post(f"/subscribe/{free_plan['id']}", headers=headers)
    assert r.status_code == 200

    # Try adding another premium book (should fail)
    r = client.post(f"/books/{second_premium['id']}/add-to-library", headers=headers)
    assert r.status_code == 403
    assert "Premium subscription required" in r.json()["detail"]

    # Check library still has old premium book
    r = client.get("/my-books", headers=headers)
    book_ids = [b["id"] for b in r.json()]
    assert first_premium["id"] in book_ids

