"""
Automated Pytest Test Suite for NxtWave WhatsApp Referral Engine
================================================================
Verifies phone normalization, code collision resistance, webhook parsing,
referral attribution incrementation, and growth analytics endpoints.
"""

import pytest
import xml.etree.ElementTree as ET
from fastapi.testclient import TestClient
from main import app, crm, generate_unique_referral_code, GoogleSheetsCRM

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_database():
    """Reset the in-memory mock database before each test run."""
    crm._mock_db.clear()
    crm._cached_rows.clear()
    crm._sheet = None  # Force in-memory mode for pure deterministic unit testing

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["campaign"]["target_referrals"] == 3

def test_phone_normalization():
    assert GoogleSheetsCRM.normalize_phone("whatsapp:+919876543210") == "+919876543210"
    assert GoogleSheetsCRM.normalize_phone("+919876543210") == "+919876543210"
    assert GoogleSheetsCRM.normalize_phone("  whatsapp:+14155238886  ") == "+14155238886"

def test_referral_code_uniqueness():
    existing = {"NXT-A1B2C", "NXT-K8M9P"}
    new_code = generate_unique_referral_code(existing, prefix="NXT-", length=5)
    assert new_code.startswith("NXT-")
    assert len(new_code) == 9  # NXT- + 5 chars
    assert new_code not in existing

def test_incomplete_registration_prompt():
    """If a student only sends a greeting, the bot should guide them with onboarding format."""
    response = client.post(
        "/whatsapp",
        data={"From": "whatsapp:+919876543210", "Body": "Hi there!", "ProfileName": "Aarav"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    root = ET.fromstring(response.text)
    msg = root.find("Message").text
    assert "Welcome to the *AI Workshop Registration*" in msg
    assert "Full Name" in msg

def test_new_student_registration_flow():
    """Tests full first-time registration and referral code assignment."""
    response = client.post(
        "/whatsapp",
        data={
            "From": "whatsapp:+919876543210",
            "Body": "Aarav Sharma\nIIT Bombay",
            "ProfileName": "Aarav Sharma"
        }
    )
    assert response.status_code == 200
    root = ET.fromstring(response.text)
    msg = root.find("Message").text
    assert "Registration successful, Aarav Sharma! 🎉" in msg
    assert "NXT-" in msg

    # Verify user was saved in CRM
    user = crm.find_user_by_phone("+919876543210")
    assert user is not None
    assert user["name"] == "Aarav Sharma"
    assert user["college"] == "Iit Bombay"
    assert user["total_referrals"] == 0

def test_viral_referral_attribution_loop():
    """Tests that Student B using Student A's code increments Student A's total referrals."""
    # 1. Register Student A
    client.post(
        "/whatsapp",
        data={
            "From": "whatsapp:+919876543210",
            "Body": "Aarav Sharma\nIIT Bombay",
            "ProfileName": "Aarav"
        }
    )
    aarav_data = crm.find_user_by_phone("+919876543210")
    aarav_code = aarav_data["my_code"]

    # 2. Register Student B using Aarav's code
    client.post(
        "/whatsapp",
        data={
            "From": "whatsapp:+919876543211",
            "Body": f"Sneha Patel\nBITS Pilani\n{aarav_code}",
            "ProfileName": "Sneha"
        }
    )

    # 3. Verify Aarav's referral count is incremented to 1
    updated_aarav = crm.find_user_by_phone("+919876543210")
    assert updated_aarav["total_referrals"] == 1

def test_growth_analytics_api():
    """Tests that /api/stats computes K-factor, counts, and blended CAC properly."""
    # Add 1 seed user and 1 referred user
    crm.create_registration("+919876543210", "Aarav", "IIT Bombay", "NXT-AAA11", None)
    crm.create_registration("+919876543211", "Sneha", "BITS Pilani", "NXT-BBB22", "NXT-AAA11")

    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_registered"] == 2
    assert data["seed_count"] == 1
    assert data["viral_count"] == 1
    assert data["k_factor"] == 1.0
    assert data["blended_cac_inr"] == 1000.0  # ₹2000 / 2

def test_dashboard_and_ambassador_html():
    """Ensures dashboard endpoints return valid HTML/JSON responses."""
    resp1 = client.get("/dashboard")
    assert resp1.status_code == 200
    assert "AI Workshop Referral Command Center" in resp1.text

    resp2 = client.get("/ambassadors")
    assert resp2.status_code == 200
    assert "ambassadors" in resp2.json()

    resp3 = client.get("/reward/download")
    assert resp3.status_code == 200
