from playwright.async_api import async_playwright
import json
import os
import asyncio
from datetime import datetime


class ScraperService:
    def __init__(self):
        self.base_dir = "screenshots"
        os.makedirs(f"{self.base_dir}/baselines", exist_ok=True)
        os.makedirs(f"{self.base_dir}/currents", exist_ok=True)
        self.max_retries = 3
        self.retry_backoff_base = 2  # exponential backoff: 2, 4, 8 seconds

    async def _retry_with_backoff(self, coro, retry_count=0):
        """Execute coroutine with exponential backoff retry logic."""
        try:
            return await coro
        except Exception as e:
            if retry_count < self.max_retries:
                wait_time = self.retry_backoff_base ** (retry_count + 1)
                print(f"INFO: Retry attempt {retry_count + 1}/{self.max_retries}, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self._retry_with_backoff(coro, retry_count + 1)
            else:
                raise

    async def run_check(self, url: str, site_id: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # ── Capture console logs & network errors ────────
            console_logs = []
            network_errors = []

            def handle_console(msg):
                try:
                    message_text = msg.text if hasattr(msg, 'text') else str(msg)
                    console_logs.append({
                        "level": getattr(msg, 'type', 'log'),
                        "message": message_text,
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    console_logs.append({
                        "level": "error",
                        "message": f"Failed to capture log: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })

            def handle_request_failed(req):
                try:
                    error_msg = ""
                    if hasattr(req, 'failure') and req.failure:
                        error_msg = getattr(req.failure, 'error_text', 'Unknown error')
                    network_errors.append({
                        "message": f"{req.method} {req.url} - {error_msg or 'Connection failed'}",
                        "url": req.url,
                        "status": error_msg
                    })
                except Exception as e:
                    network_errors.append({
                        "message": f"Network error: {str(e)}",
                        "url": "unknown"
                    })

            page.on("console", handle_console)
            page.on("requestfailed", handle_request_failed)

            try:
                # Retry logic for page navigation
                response = None
                for attempt in range(self.max_retries):
                    try:
                        response = await page.goto(url, wait_until="load", timeout=60000)
                        break
                    except Exception as e:
                        if attempt < self.max_retries - 1:
                            wait_time = self.retry_backoff_base ** (attempt + 1)
                            print(f"INFO: Navigation failed, retry {attempt + 1}/{self.max_retries} in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                        else:
                            raise
                
                status_code = response.status if response else 0

                # ── 1. Capture Screenshot ────────────────────
                baseline_path = f"{self.base_dir}/baselines/{site_id}.png"
                current_time = int(datetime.now().timestamp())
                current_path = f"{self.base_dir}/currents/{site_id}_{current_time}.png"

                is_new_baseline = not os.path.exists(baseline_path)
                save_path = baseline_path if is_new_baseline else current_path

                await page.screenshot(path=save_path, full_page=True)

                # ── 2. Distill DOM (L0 + L1) ─────────────────
                await page.evaluate("""() => {
                    const scrap = ['script', 'style', 'svg', 'noscript', 'iframe'];
                    scrap.forEach(tag => {
                        const elements = document.getElementsByTagName(tag);
                        while (elements.length > 0) elements[0].parentNode.removeChild(elements[0]);
                    });
                }""")

                elements = await page.evaluate("""() => {
                    const rect = (el) => el.getBoundingClientRect();
                    const isVisible = (el) => {
                        const r = rect(el);
                        return r.width > 0 && r.height > 0 && window.getComputedStyle(el).visibility !== 'hidden';
                    };

                    const interactive = Array.from(document.querySelectorAll('button, a, input, select, textarea, [role="button"]'));
                    return interactive.filter(isVisible).map(el => ({
                        tag: el.tagName.toLowerCase(),
                        id: el.id,
                        text: el.innerText.trim() || el.placeholder || el.value,
                        role: el.getAttribute('role') || 'none'
                    }));
                }""")

                # ── 3. Capture page title & meta ─────────────
                title = await page.title()

                return {
                    "dom": json.dumps(elements),
                    "screenshot": save_path,
                    "baseline": baseline_path if not is_new_baseline else None,
                    "is_new_baseline": is_new_baseline,
                    "status_code": status_code,
                    "console_logs": console_logs,
                    "network_errors": network_errors,
                    "title": title,
                    "url": url
                }

            except Exception as e:
                return {
                    "error": str(e),
                    "status_code": 0,
                    "console_logs": console_logs,
                    "network_errors": network_errors
                }
            finally:
                await browser.close()


scraper_service = ScraperService()
