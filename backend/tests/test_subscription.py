#test_subscription.py
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

# Setup test DB
TEST_DB_URL = "sqlite:///./test_subscriptions.db"
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

@pytest.fixture
def user_token():
    email = "subuser@example.com"
    password = "testpass"
    client.post("/register", json={"email": email, "password": password})
    res = client.post("/login", json={"email": email, "password": password})
    return res.json()["access_token"]

# --- Subscription Tests ---

def test_get_all_subscription_plans(user_token):
    res = client.get("/subscription-plans", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    plans = res.json()
    assert isinstance(plans, list)
    assert len(plans) >= 2
    assert all("name" in plan and "price" in plan for plan in plans)

def test_subscribe_to_valid_plan(user_token):
    # Get available plans
    plans = client.get("/subscription-plans", headers={"Authorization": f"Bearer {user_token}"}).json()
    plan_id = plans[1]["id"]  # pick the second plan (e.g., "premium")

    # Subscribe
    res = client.post(f"/subscribe/{plan_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 200
    assert "Successfully subscribed" in res.json()["message"]

def test_subscribe_to_invalid_plan(user_token):
    res = client.post("/subscribe/9999", headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 404
    assert "Subscription plan not found" in res.json()["detail"]

def test_subscription_plan_updated(user_token):
    user = client.get("/me", headers={"Authorization": f"Bearer {user_token}"}).json()
    assert user["subscription_plan"] in ["premium", "unlimited"]

