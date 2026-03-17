import json
import os
import signal
import threading
import time
import webbrowser

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import scraper

app = FastAPI(title="PJINT - Pages Jaunes Scraper")


# ── Scraping SSE ───────────────────────────────────────────────────────────────

async def scrape_generator(ville: str, keyword: str, start_page: int = 1):
    async for event in scraper.scrape(ville, keyword, start_page):
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


# ── Endpoint de diagnostic ─────────────────────────────────────────────────────

@app.get("/api/debug")
async def debug(
    ville:   str = Query(default="Lyon"),
    keyword: str = Query(default="restaurant"),
):
    from playwright.async_api import async_playwright
    from bs4 import BeautifulSoup

    result: dict = {}
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                      "--disable-blink-features=AutomationControlled", "--lang=fr-FR"],
            )
            ctx = await scraper.make_context(browser)
            tab = await ctx.new_page()
            await scraper.goto_and_wait(tab, scraper.HOME_URL, delay=2.0)
            url  = f"{scraper.BASE_URL}?quoiqui={keyword}&ou={ville}&page=1"
            html = await scraper.goto_and_wait(tab, url, delay=2.5)
            await browser.close()

        parsed = scraper.parse_page(html)
        result = {
            "url":                  url,
            "html_length":          len(html),
            "is_blocked":           scraper.is_blocked(html),
            "nb_results_parsed":    len(parsed),
            "total_pages_detected": scraper.get_total_pages(html)[0],
            "sample":               parsed[:3],
        }
    except Exception as e:
        result = {"erreur": str(e)}

    return HTMLResponse(
        "<pre style='font:12px monospace;white-space:pre-wrap'>"
        + json.dumps(result, ensure_ascii=False, indent=2)
        + "</pre>"
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/api/scrape")
async def scrape_endpoint(
    ville:      str = Query(..., min_length=1),
    keyword:    str = Query(default=""),
    start_page: int = Query(default=1, ge=1),
):
    return StreamingResponse(
        scrape_generator(ville.strip(), keyword.strip(), start_page),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "Connection":        "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/rubriques")
async def get_rubriques(ville: str = Query(default="Paris")):
    rubriques = await scraper.fetch_rubriques_pj(ville.strip())
    return {"ville": ville, "count": len(rubriques), "rubriques": rubriques}


@app.get("/api/quit")
async def quit_server():
    threading.Thread(
        target=lambda: (time.sleep(0.3), os.killpg(os.getpgid(0), signal.SIGINT)),
        daemon=True,
    ).start()
    return {"status": "bye"}


@app.get("/")
async def root():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn

    def _open_browser():
        time.sleep(1.2)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
