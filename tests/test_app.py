import copy

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


@pytest.fixture(autouse=True)
def reset_activities_state():
    snapshot = copy.deepcopy(app_module.activities)
    yield
    app_module.activities.clear()
    app_module.activities.update(snapshot)


@pytest.fixture
def client():
    return TestClient(app_module.app)


def test_root_redirects_to_static_index(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (307, 302)
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_data(client):
    response = client.get("/activities")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert "Chess Club" in payload
    assert "participants" in payload["Chess Club"]


def test_signup_success_adds_participant(client):
    activity_name = "Chess Club"
    new_email = "new.student@mergington.edu"

    response = client.post(f"/activities/{activity_name}/signup", params={"email": new_email})

    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {new_email} for {activity_name}"
    assert new_email in app_module.activities[activity_name]["participants"]


def test_signup_rejects_duplicate_participant(client):
    activity_name = "Chess Club"
    existing_email = app_module.activities[activity_name]["participants"][0]

    response = client.post(f"/activities/{activity_name}/signup", params={"email": existing_email})

    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


def test_signup_rejects_unknown_activity(client):
    response = client.post("/activities/Unknown%20Activity/signup", params={"email": "student@mergington.edu"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_requires_email_query_param(client):
    response = client.post("/activities/Chess%20Club/signup")

    assert response.status_code == 422


def test_signup_rejects_when_activity_is_full(client):
    activity_name = "Chess Club"
    app_module.activities[activity_name]["participants"] = [
        f"student{i}@mergington.edu"
        for i in range(app_module.activities[activity_name]["max_participants"])
    ]

    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "overflow.student@mergington.edu"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Activity is full"


def test_unregister_success_removes_participant(client):
    activity_name = "Chess Club"
    email = app_module.activities[activity_name]["participants"][0]

    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json()["message"] == f"Unregistered {email} from {activity_name}"
    assert email not in app_module.activities[activity_name]["participants"]


def test_unregister_rejects_unknown_activity(client):
    response = client.delete(
        "/activities/Unknown%20Activity/participants",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_rejects_missing_participant(client):
    response = client.delete(
        "/activities/Chess%20Club/participants",
        params={"email": "not.in.club@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Participant not found in this activity"


def test_unregister_requires_email_query_param(client):
    response = client.delete("/activities/Chess%20Club/participants")

    assert response.status_code == 422