#!/usr/bin/env python3
"""W.13 public UI download click using Playwright. No secrets."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = "http://13.127.104.99"
OUT = Path(r"C:\Users\nishanth.h\AppData\Local\Temp\w13_downloads")
RUN = sys.argv[1] if len(sys.argv) > 1 else "20260826_141507_88aff694"


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
        html = page.content()
        print("CACHE_BUST", "app.js?v=W.13" in html)
        print("DOWNLOAD_IS_ANCHOR", 'id="btn-download"' in html and "<a " in html)
        page.wait_for_selector("#view-success:not(.hidden)", timeout=120000)
        print("UI_SUCCESS_WORKBOOK", page.locator("#success-workbook").inner_text())
        print("UI_SUCCESS_VISIBLE", page.locator("#view-success").is_visible())
        href = page.locator("#btn-download").get_attribute("href")
        print("NATIVE_HREF", href)
        with page.expect_download(timeout=120000) as dlinfo:
            page.locator("#btn-download").click()
        download = dlinfo.value
        dest = OUT / f"ui_{RUN}_1.xlsx"
        download.save_as(str(dest))
        data = dest.read_bytes()
        print("UI_CLICK_1", download.suggested_filename, dest.stat().st_size, data[:2])
        with page.expect_download(timeout=120000) as dlinfo2:
            page.locator("#btn-download").click()
        download2 = dlinfo2.value
        dest2 = OUT / f"ui_{RUN}_2.xlsx"
        download2.save_as(str(dest2))
        print("UI_CLICK_2", dest2.stat().st_size, dest2.read_bytes()[:2])
        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector("#view-success:not(.hidden)", timeout=120000)
        with page.expect_download(timeout=120000) as dlinfo3:
            page.locator("#btn-download").click()
        download3 = dlinfo3.value
        dest3 = OUT / f"ui_{RUN}_refresh.xlsx"
        download3.save_as(str(dest3))
        print("UI_CLICK_REFRESH", dest3.stat().st_size, dest3.read_bytes()[:2])
        err = page.locator("#download-error")
        hidden = "hidden" in (err.get_attribute("class") or "")
        print("UI_DOWNLOAD_ERROR_HIDDEN", hidden)
        print("UI_STILL_SUCCESS", page.locator("#view-success").is_visible())
        browser.close()
    ok = dest.is_file() and dest.stat().st_size > 0 and data[:2] == b"PK"
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
