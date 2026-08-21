from fastapi.testclient import TestClient

from app.limits import MAX_TOPIC_LENGTH, MAX_TRANSCRIPT_LENGTH
from app.main import app

client = TestClient(app)

TRANSCRIPT = "This is a short rehearsal about public speaking."


def test_missing_topic_returns_400():
    response = client.post("/feedback", json={"topic": "", "transcript": TRANSCRIPT})
    assert response.status_code == 400
    assert "error" in response.json()


def test_topic_over_max_length_returns_400():
    response = client.post(
        "/feedback",
        json={"topic": "x" * (MAX_TOPIC_LENGTH + 1), "transcript": TRANSCRIPT},
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_missing_transcript_returns_400():
    response = client.post("/feedback", json={"topic": "public speaking", "transcript": ""})
    assert response.status_code == 400
    assert "error" in response.json()


def test_transcript_over_max_length_returns_400():
    response = client.post(
        "/feedback",
        json={
            "topic": "public speaking",
            "transcript": "x" * (MAX_TRANSCRIPT_LENGTH + 1),
        },
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_happy_path_returns_grounded_feedback_only(mocker):
    mocker.patch(
        "app.main.get_feedback",
        return_value=[
            {
                "category": "clarity",
                "quote": "a short rehearsal about public speaking",
                "issue": "too brief",
                "suggestion": "add more detail",
            },
            {
                "category": "pacing",
                "quote": "this sentence was never said",
                "issue": "fabricated",
                "suggestion": "n/a",
            },
        ],
    )

    response = client.post(
        "/feedback", json={"topic": "public speaking", "transcript": TRANSCRIPT}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["feedback"]) == 1
    assert body["feedback"][0]["quote"] == "a short rehearsal about public speaking"
