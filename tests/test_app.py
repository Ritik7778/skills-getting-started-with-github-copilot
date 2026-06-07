import sys
import os
import pathlib
import copy
import urllib.parse

import pytest
from fastapi.testclient import TestClient

# Add the src directory to sys.path so we can import src/app.py as module `app`
HERE = pathlib.Path(__file__).parent.resolve()
sys.path.insert(0, str(HERE.parent / "src"))

import app as app_module  # noqa: E402


@pytest.fixture(autouse=True)
def restore_activities():
    """Save and restore the in-memory `activities` between tests for isolation."""
    original = copy.deepcopy(app_module.activities)
    try:
        yield
    finally:
        app_module.activities.clear()
        app_module.activities.update(copy.deepcopy(original))


@pytest.fixture(scope="module")
def client():
    return TestClient(app_module.app)


def _quote(s: str) -> str:
    return urllib.parse.quote(s, safe='')


def test_root_redirect(client):
    # Arrange
    url = "/"

    # Act
    resp = client.get(url, allow_redirects=False)

    # Assert
    assert resp.status_code == 307
    assert resp.headers.get("location") == "/static/index.html"


def test_get_activities(client):
    # Arrange
    url = "/activities"

    # Act
    resp = client.get(url)

    # Assert
    assert resp.status_code == 200
    assert resp.json() == app_module.activities


def test_signup_success(client):
    # Arrange
    activity = "Chess Club"
    email = "test.user@example.com"
    assert email not in app_module.activities[activity]["participants"]
    url = f"/activities/{_quote(activity)}/signup"

    # Act
    resp = client.post(url, params={"email": email})

    # Assert
    assert resp.status_code == 200
    assert email in app_module.activities[activity]["participants"]
    assert "Signed up" in resp.json().get("message", "")


def test_signup_nonexistent_activity(client):
    # Arrange
    activity = "Nonexistent Activity"
    email = "someone@example.com"
    url = f"/activities/{_quote(activity)}/signup"

    # Act
    resp = client.post(url, params={"email": email})

    # Assert
    assert resp.status_code == 404
    assert resp.json().get("detail") == "Activity not found"


def test_duplicate_signup(client):
    # Arrange
    activity = "Programming Class"
    email = "duplicate@example.com"
    url = f"/activities/{_quote(activity)}/signup"

    # Act - first signup
    resp1 = client.post(url, params={"email": email})

    # Assert first signup succeeded
    assert resp1.status_code == 200

    # Act - duplicate signup
    resp2 = client.post(url, params={"email": email})

    # Assert duplicate signup fails
    assert resp2.status_code == 400
    assert resp2.json().get("detail") == "Student already signed up for this activity"


def test_remove_participant_success(client):
    # Arrange
    activity = "Chess Club"
    email = "michael@mergington.edu"
    assert email in app_module.activities[activity]["participants"]
    url = f"/activities/{_quote(activity)}/participants/{_quote(email)}"

    # Act
    resp = client.delete(url)

    # Assert
    assert resp.status_code == 200
    assert email not in app_module.activities[activity]["participants"]
    assert "Removed" in resp.json().get("message", "")


def test_remove_nonexistent_participant(client):
    # Arrange
    activity = "Chess Club"
    email = "notfound@example.com"
    assert email not in app_module.activities[activity]["participants"]
    url = f"/activities/{_quote(activity)}/participants/{_quote(email)}"

    # Act
    resp = client.delete(url)

    # Assert
    assert resp.status_code == 404
    assert resp.json().get("detail") == "Participant not found"


def test_remove_from_nonexistent_activity(client):
    # Arrange
    activity = "No Such Activity"
    email = "someone@example.com"
    url = f"/activities/{_quote(activity)}/participants/{_quote(email)}"

    # Act
    resp = client.delete(url)

    # Assert
    assert resp.status_code == 404
    assert resp.json().get("detail") == "Activity not found"
