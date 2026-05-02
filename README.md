# AutoDownloader

An async Python web application for downloading videos via [yt-dlp](https://github.com/yt-dlp/yt-dlp), processing them with [FFmpeg](https://ffmpeg.org/), and serving the results through a simple web UI.

## Features

- **Async Processing**: Submit a video URL or upload a file and get a job ID immediately. Long-running downloads and transcodes happen in the background without blocking the web server.
- **Persistent State**: Job status is stored in SQLite, so you can close your browser and resume monitoring later by reopening the job URL.
- **Configurable FFmpeg Options**: Choose resolution, frame rate, video codec (H.264/HEVC), CRF, preset, and audio handling directly from the web form.
- **Automatic Cleanup**: Processed files are deleted after a configurable retention period (default: 24 hours). A periodic background task and startup sweep ensure nothing is left behind.
- **Extensive Logging**: Dual logging to rotating files (`logs/app.log`) and stdout with full debug-level capture.

## Requirements

- Python >= 3.13
- [uv](https://docs.astral.sh/uv/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/)

## Quick Start

```bash
# Install dependencies
uv sync

# Run the application
uv run uvicorn autodownloader.main:app --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000 in your browser.

### Docker

```bash
docker compose up -d
```

## Configuration

Set the `RETENTION_SECONDS` environment variable to change how long files are kept before automatic deletion:

```powershell
$env:RETENTION_SECONDS="300"
uv run uvicorn autodownloader.main:app --host 0.0.0.0 --port 8000
```

Default is `86400` (24 hours).

## How It Works

1. **Submit**: Enter a video URL and choose processing options.
2. **Track**: The UI polls the server for status updates (`queued` -> `downloading` -> `processing` -> `ready`).
3. **Download**: Once ready, click the download button to get your processed MP4.
4. **Expire**: The file is automatically deleted after the retention period, and the job status becomes `expired`.

## Project Structure

```
autodownloader/
├── src/autodownloader/
│   ├── main.py        # FastAPI app, endpoints, lifespan
│   ├── database.py    # SQLite persistence with aiosqlite
│   ├── processor.py   # yt-dlp + ffmpeg async workers
│   ├── logger.py      # Rotating file + console logging setup
│   └── templates/
│       └── index.html # Web UI
├── data/              # SQLite database
├── downloads/         # Temporary video storage
├── logs/              # Application logs
├── pyproject.toml
└── README.md
```

## Testing

```bash
uv run python test_app.py
```

## License

MIT
