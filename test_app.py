from fastapi.testclient import TestClient
from autodownloader.main import app

client = TestClient(app)

def test_index():
    r = client.get("/")
    assert r.status_code == 200
    assert "Video Downloader" in r.text
    print("[PASS] GET / OK")

def test_submit_and_status():
    r = client.post("/submit", data={
        "url": "https://example.com/video",
        "resolution": "1280x720",
        "fps": "30",
        "codec": "libx264",
        "crf": "23",
        "preset": "fast",
        "audio": "aac",
    })
    assert r.status_code == 200
    payload = r.json()
    assert "job_id" in payload
    job_id = payload["job_id"]
    print(f"[PASS] POST /submit OK -> job_id={job_id}")

    r2 = client.get(f"/status/{job_id}")
    assert r2.status_code == 200
    status = r2.json()
    assert status["status"] in ("queued", "downloading", "processing", "ready", "error")
    print(f"[PASS] GET /status/{job_id} OK -> status={status['status']}")

if __name__ == "__main__":
    test_index()
    test_submit_and_status()
    print("\nAll basic tests passed.")
