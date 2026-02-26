# Error Handling & Logging Redesign

## Problem
- Errors display as a single truncated line ("Une erreur s'est produite [0...") — not copiable, no details
- Log file only created with `--debug`/`--verbose` — no trace in normal usage
- Users can't easily share error context for debugging

## Design

### 1. Permanent logging with rotation (`videodl_logger.py`)
- Always add a `RotatingFileHandler` to `~/.videodl/logs/videodl.log`
- Max 5 MB per file, 2 backup files
- File handler level: INFO normally, DEBUG with `--debug`/`--verbose`
- Stdout handler unchanged (ERROR by default)
- Expose `LOG_DIR` constant for UI access
- Create `~/.videodl/logs/` at startup if missing

### 2. Error report module (`core/error_report.py`)
Pure functions, no Flet dependency.

**`ErrorReport` dataclass:**
- `short_message: str` — one-liner for the banner
- `detail: str` — full traceback
- `color: str` — "red" or "yellow"
- `should_break: bool` — True = stop queue, False = continue to next URL
- `has_detail: bool` — True if detail dialog should be available

**`build_error_report(exception) -> ErrorReport`:**

| Exception | color | should_break | has_detail |
|-----------|-------|-------------|------------|
| `DownloadCancelled` | yellow | True | False |
| `PlaylistNotFound` | yellow | False | False |
| `FFmpegNoValidEncoderFound` | red | False | False |
| Generic `Exception` | red | False | True |

For generic exceptions: strip `ERROR:` prefix, keep full message (no `;` split), traceback in `detail`.

### 3. UI: clickable error banner + detail dialog (`gui/app.py`)

**Error banner:**
- Replace `download_status_text` Text with a clickable `Container(Row([icon, text]))`
- `has_detail=True` → click opens detail dialog; cursor indicates clickability
- `has_detail=False` → plain text, same as today

**Detail dialog (AlertDialog):**
- Title: short error message
- Content: `TextField(read_only=True, multiline=True)` with full traceback — natively copiable
- Actions: "Copy" (clipboard), "Open log" (file explorer), "Close"

**Refactored `_run_download_async`:**
```python
except Exception as e:
    report = build_error_report(e)
    logger.error(report.detail)
    self._show_error(report)
    error_occurred = True
    if report.should_break:
        break
```

### 4. i18n additions
New `GuiField` entries: `error_copy`, `error_open_log`, `error_close`, `error_details_title`.

### 5. Tests (`tests/test_error_report.py`)
- `build_error_report` for each exception type
- Verify `short_message`, `color`, `should_break`, `has_detail`
- Generic exception: verify traceback in `detail`, `ERROR:` prefix stripped

## Files
- **Modified:** `videodl_logger.py`, `gui/app.py`, `i18n/lang.py`
- **New:** `core/error_report.py`, `tests/test_error_report.py`
