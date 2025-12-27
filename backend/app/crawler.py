import asyncio
import httpx
import ipaddress
from typing import List, Optional
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
from playwright.async_api import async_playwright, Playwright, Browser
from .config import settings
from fastapi import HTTPException

def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Valida URL para prevenir SSRF (Server-Side Request Forgery)

    Args:
        url: URL a ser validada

    Returns:
        Tupla (is_valid, error_message)
    """
    try:
        parsed = urlparse(url)

        # 1. Apenas http/https
        if parsed.scheme not in ('http', 'https'):
            return False, f"Esquema '{parsed.scheme}' não permitido. Use http ou https."

        # 2. Hostname deve existir
        if not parsed.hostname:
            return False, "URL inválida: hostname ausente."

        # 3. Bloquear localhost explícito
        if parsed.hostname in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
            return False, "Acesso a localhost não permitido."

        # 4. Bloquear IPs privados/internos
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, f"Acesso a IP privado/interno não permitido: {parsed.hostname}"
        except ValueError:
            # Não é um IP, é um domínio - OK
            pass

        # 5. Bloquear ranges conhecidos de cloud metadata (AWS, GCP, Azure)
        # AWS: 169.254.169.254, GCP: metadata.google.internal
        if parsed.hostname in ('169.254.169.254', 'metadata.google.internal', 'metadata.azure.com'):
            return False, "Acesso a metadata de cloud não permitido."

        # 6. Bloquear portas sensíveis (opcional, mas recomendado)
        if parsed.port:
            blocked_ports = {
                22,    # SSH
                23,    # Telnet
                25,    # SMTP
                3306,  # MySQL
                5432,  # PostgreSQL
                6379,  # Redis
                27017, # MongoDB
            }
            if parsed.port in blocked_ports:
                return False, f"Porta {parsed.port} não permitida por razões de segurança."

        return True, ""

    except Exception as e:
        return False, f"Erro ao validar URL: {str(e)}"

class BrowserPool:
    """
    Singleton browser pool for reusing Playwright browser instances.

    Reduces memory usage and startup time by keeping browser alive
    across multiple requests.
    """
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_browser(cls) -> Browser:
        """
        Get or create browser instance (thread-safe).

        Returns:
            Playwright Browser instance
        """
        async with cls._lock:
            if cls._browser is None or not cls._browser.is_connected():
                if cls._playwright is None:
                    cls._playwright = await async_playwright().start()
                cls._browser = await cls._playwright.chromium.launch(
                    headless=settings.HEADLESS
                )
        return cls._browser

    @classmethod
    async def close(cls):
        """
        Close browser and playwright (call on app shutdown).
        """
        async with cls._lock:
            if cls._browser:
                try:
                    await cls._browser.close()
                except Exception:
                    pass
                cls._browser = None
            if cls._playwright:
                try:
                    await cls._playwright.stop()
                except Exception:
                    pass
                cls._playwright = None


class ClickExpandEvaluator:
    async def evaluate_async(self, page):
        try:
            await page.set_extra_http_headers({"User-Agent": settings.USER_AGENT})
            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.evaluate("() => { document.querySelectorAll('details').forEach(d => d.open = true); }")
        except Exception:
            pass
        try:
            return await page.evaluate("() => document.body.innerText || ''")
        except Exception:
            return ""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def _get(client: httpx.AsyncClient, url: str) -> str:
    r = await client.get(url, follow_redirects=True, headers={"User-Agent": settings.USER_AGENT})
    r.raise_for_status()
    return r.text


async def render_urls(urls: List[str]) -> List[dict]:
    """
    Render URLs with Playwright and return list of dicts with page_content and metadata.

    Uses browser pool to reuse browser instances across requests.

    Raises:
        HTTPException: If any URL is considered unsafe (SSRF protection)
    """
    # Validate all URLs BEFORE getting browser
    for url in urls:
        is_valid, error_msg = is_safe_url(url)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"URL blocked: {error_msg}")

    results = []
    evaluator = ClickExpandEvaluator()

    # Get browser from pool (reused across requests)
    browser = await BrowserPool.get_browser()

    # Create new context for isolation (cookies, storage, etc.)
    context = await browser.new_context(user_agent=settings.USER_AGENT)

    try:
        for url in urls:
            try:
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                content = await evaluator.evaluate_async(page)
                await page.close()

                results.append({
                    "page_content": content,
                    "metadata": {"source": url}
                })
            except Exception as e:
                print(f"Error rendering {url}: {e}")
                results.append({
                    "page_content": "",
                    "metadata": {"source": url}
                })
    finally:
        # Close context but keep browser alive for next request
        await context.close()

    return results
