# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-05-02

First non-alpha release, stabilizing features from 0.1.0-alpha.1 through 0.1.0-alpha.5.

## [0.1.0-alpha.5] - 2026-05-02

### Added
- Upload progress bar in the web UI for file upload submissions.

## [0.1.0-alpha.4] - 2026-04-26

### Fixed
- Fixed `latest` Docker tag only being pushed on semver tags instead of every push.

## [0.1.0-alpha.3] - 2026-04-26

### Added
- Video file upload support (alternative to URL submission).
- Optional FFmpeg processing toggle (skip transcoding and serve the original file).
- Descriptive output filenames based on the original video title.

## [0.1.0-alpha.2] - 2026-04-26

### Fixed
- Fixed FFmpeg `readline()` crash when output lines exceeded the buffer size.

## [0.1.0-alpha.1] - 2026-04-26

### Added
- Initial pre-alpha release.
- Async video download and processing pipeline using FastAPI, yt-dlp (native Python API), and FFmpeg.
- Web UI for submitting URLs and configuring FFmpeg parameters (resolution, FPS, codec, CRF, preset, audio).
- Persistent job tracking via SQLite with aiosqlite.
- Browser-refresh-safe progress monitoring via job ID URLs.
- Automatic file cleanup after a configurable retention period (`RETENTION_SECONDS`).
- Rotating file + console logging.
- Dockerfile and docker-compose.yaml for containerized deployment.
- GitHub Actions CI workflow for Docker builds and releases on version tags.

### Fixed
- Fixed `TypeError: can't subtract offset-naive and offset-aware datetimes` in startup cleanup sweep.
- Fixed duplicate log entries by setting `propagate = False` on uvicorn loggers.
- Fixed process hang on CTRL-C by replacing raw task cancellation with `asyncio.Event`-based graceful shutdown.
- Fixed yt-dlp download return type: treated as integer instead of list.

### Changed
- Replaced yt-dlp subprocess call with native Python API via `asyncio.to_thread`.
