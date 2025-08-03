# test_users.py

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

# Create a new test database
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test_books.db"
test_engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Override the get_db dependency to use test DB
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Run once before all tests
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    if not database_exists(test_engine.url):
        create_database(test_engine.url)
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

@pytest.fixture
def test_user():
    return {
        "email": "test@example.com",
        "password": "testpassword"
    }

def test_register_user(test_user):
    response = client.post("/register", json=test_user)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert "id" in data

def test_duplicate_registration(test_user):
    # Register again with same user
    response = client.post("/register", json=test_user)
    assert response.status_code == 400
    assert "Email already registered" in response.text

def test_login_user(test_user):
    response = client.post("/login", json=test_user)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_password(test_user):
    bad_user = {**test_user, "password": "wrongpass"}
    response = client.post("/login", json=bad_user)
    assert response.status_code == 401

def test_login_invalid_user():
    response = client.post("/login", json={"email": "not@exist.com", "password": "any"})
    assert response.status_code == 401

