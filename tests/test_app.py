import json
import io


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert "status" in data
    assert "vector_store" in data


def test_web_routes(client):
    assert client.get("/").status_code == 200
    assert client.get("/submit").status_code == 200
    assert client.get("/history").status_code == 200
    assert client.get("/knowledge-base").status_code == 200


def test_api_submit_bug_and_get(client):
    payload = {
        "title": "RecursionError in tree traversal",
        "description": "Recursive tree traversal exceeded stack depth",
        "stack_trace": "RecursionError: maximum recursion depth exceeded",
        "language": "Python",
        "severity": "High"
    }

    res = client.post(
        "/api/bugs",
        data=json.dumps(payload),
        content_type="application/json"
    )
    assert res.status_code == 201
    data = res.get_json()
    bug_id = data["bug"]["bug_id"]

    # Retrieve bug
    get_res = client.get(f"/api/bugs/{bug_id}")
    assert get_res.status_code == 200
    assert get_res.get_json()["title"] == payload["title"]

    # Trigger analysis
    analyze_res = client.post(f"/api/bugs/{bug_id}/analyze")
    assert analyze_res.status_code == 200
    report = analyze_res.get_json()["report"]
    assert report["root_cause"] is not None

    # Get results
    results_res = client.get(f"/api/bugs/{bug_id}/results")
    assert results_res.status_code == 200
    assert results_res.get_json()["status"] == "COMPLETED"

    # Submit feedback
    feedback_payload = {
        "is_accurate": True,
        "rating": 5,
        "feedback": "Confirmed accurate fix"
    }
    fb_res = client.post(
        f"/api/bugs/{bug_id}/feedback",
        data=json.dumps(feedback_payload),
        content_type="application/json"
    )
    assert fb_res.status_code == 201


def test_api_upload_file(client):
    data = {
        "file": (io.BytesIO(b"Traceback (most recent call last):\n  File 'test.py', line 1\nZeroDivisionError: division by zero"), "error.log"),
        "title": "Uploaded division bug"
    }
    res = client.post("/api/bugs/upload", data=data, content_type="multipart/form-data")
    assert res.status_code == 201
    assert "Uploaded division bug" in res.get_json()["bug"]["title"]
