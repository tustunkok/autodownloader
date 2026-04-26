# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-04-26

### Added
- Initial release of AutoDownloader.
- Async video download and processing pipeline using FastAPI, yt-dlp, and FFmpeg.
- Web UI for submitting URLs and configuring FFmpeg parameters (resolution, FPS, codec, CRF, preset, audio).
- Persistent job tracking via SQLite with aiosqlite.
- Browser-refresh-safe progress monitoring via job ID URLs.
- Automatic file cleanup after a configurable retention period (`RETENTION_SECONDS`).
- Extensive Python logging with rotating file handler and console output.

### Fixed
- Fixed `TypeError: can't subtract offset-naive and offset-aware datetimes` in startup cleanup sweep.
- Fixed duplicate log entries by setting `propagate = False` on uvicorn loggers.
- Fixed process hang on CTRL-C by replacing raw task cancellation with `asyncio.Event`-based graceful shutdown.

### Changed
- Made file retention age configurable via `RETENTION_SECONDS` environment variable (default: 86400).
