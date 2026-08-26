"""W.12 public UI download click using Playwright when available."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = "http://13.127.104.99"
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w12_downloads")
RUN = sys.argv[1] if len(sys.argv) > 1 else "20260826_084708_f74912b8"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("PLAYWRIGHT_UNAVAILABLE")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.goto(f"{BASE}/?run={RUN}", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("#view-success:not(.hidden)", timeout=120000)
        workbook = page.locator("#success-workbook").inner_text()
        print("UI_SUCCESS_WORKBOOK", workbook)
        print("UI_SUCCESS_VISIBLE", page.locator("#view-success").is_visible())
        with page.expect_download(timeout=120000) as dlinfo:
            page.locator("#btn-download").click()
        download = dlinfo.value
        dest = OUT / f"ui_{RUN}.xlsx"
        download.save_as(str(dest))
        data = dest.read_bytes()
        print("UI_DOWNLOAD", download.suggested_filename, dest.stat().st_size, data[:2])
        err = page.locator("#download-error")
        hidden = "hidden" in (err.get_attribute("class") or "")
        print("UI_DOWNLOAD_ERROR_HIDDEN", hidden)
        print("UI_STILL_SUCCESS", page.locator("#view-success").is_visible())
        browser.close()
    return 0 if dest.is_file() and dest.stat().st_size > 0 and data[:2] == b"PK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
