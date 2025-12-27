import asyncio
import httpx
import ipaddress
from typing import List
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
from playwright.async_api import async_playwright
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
    Renderiza URLs com Playwright e retorna lista de dicts com page_content e metadata.

    Raises:
        HTTPException: Se alguma URL for considerada insegura (SSRF protection)
    """
    # Validar todas as URLs ANTES de abrir o browser
    for url in urls:
        is_valid, error_msg = is_safe_url(url)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"URL bloqueada por segurança: {error_msg}")

    results = []
    evaluator = ClickExpandEvaluator()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=settings.HEADLESS)
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
            # Garantir que browser sempre fecha, mesmo com erro
            await browser.close()

    return results
