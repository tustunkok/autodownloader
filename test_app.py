import io
from fastapi.testclient import TestClient
from autodownloader.main import app

client = TestClient(app)

def test_index():
    r = client.get("/")
    assert r.status_code == 200
    assert "Video Downloader" in r.text
    print("[PASS] GET / OK")

def test_submit_url():
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
    print(f"[PASS] POST /submit (URL) OK -> job_id={job_id}")

    r2 = client.get(f"/status/{job_id}")
    assert r2.status_code == 200
    status = r2.json()
    assert status["status"] in ("queued", "downloading", "processing", "ready", "error")
    print(f"[PASS] GET /status/{job_id} OK -> status={status['status']}")

def test_submit_url_no_ffmpeg():
    r = client.post("/submit", data={
        "url": "https://example.com/video",
        "apply_ffmpeg": "false",
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
    print(f"[PASS] POST /submit (URL, no ffmpeg) OK -> job_id={payload['job_id']}")

def test_submit_upload():
    fake_video = io.BytesIO(b"fake video content")
    r = client.post(
        "/submit",
        data={
            "resolution": "1920x1080",
            "fps": "30",
            "codec": "libx265",
            "crf": "28",
            "preset": "medium",
            "audio": "copy",
        },
        files={"video_file": ("test.mp4", fake_video, "video/mp4")},
    )
    assert r.status_code == 200
    payload = r.json()
    assert "job_id" in payload
    job_id = payload["job_id"]
    print(f"[PASS] POST /submit (upload) OK -> job_id={job_id}")

    r2 = client.get(f"/status/{job_id}")
    assert r2.status_code == 200
    status = r2.json()
    assert status["status"] in ("queued", "downloading", "processing", "ready", "error")
    assert status["original_filename"] == "test.mp4"
    print(f"[PASS] GET /status/{job_id} OK -> original_filename={status['original_filename']}")

def test_submit_both():
    fake_video = io.BytesIO(b"fake video content")
    r = client.post(
        "/submit",
        data={
            "url": "https://example.com/video",
            "resolution": "1920x1080",
            "fps": "30",
            "codec": "libx265",
            "crf": "28",
            "preset": "medium",
            "audio": "copy",
        },
        files={"video_file": ("test.mp4", fake_video, "video/mp4")},
    )
    assert r.status_code == 400
    assert "not both" in r.json()["detail"]
    print("[PASS] POST /submit (both) rejected with 400")

def test_submit_neither():
    r = client.post("/submit", data={
        "resolution": "1920x1080",
        "fps": "30",
        "codec": "libx265",
        "crf": "28",
        "preset": "medium",
        "audio": "copy",
    })
    assert r.status_code == 400
    assert "either a URL or a file" in r.json()["detail"]
    print("[PASS] POST /submit (neither) rejected with 400")

if __name__ == "__main__":
    test_index()
    test_submit_url()
    test_submit_url_no_ffmpeg()
    test_submit_upload()
    test_submit_both()
    test_submit_neither()
    print("\nAll basic tests passed.")
