import asyncio
import httpx
import ipaddress
import re
import socket
from typing import List, Optional
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential
from playwright.async_api import async_playwright, Playwright, Browser
from .config import settings
from fastapi import HTTPException


# Hostnames explicitly blocked (cloud metadata + loopback aliases).
_DENY_HOSTS = {
    "localhost", "ip6-localhost", "ip6-loopback",
    "metadata.google.internal", "metadata", "metadata.azure.com",
    "metadata.azure.internal", "instance-data",
}

# Strict IPv4 dotted-quad regex (rejects octal/hex/integer encodings).
_DOTTED_QUAD = re.compile(r"^(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$")

# Extra blocked v4 networks beyond what ipaddress flags as private/reserved.
_EXTRA_V4_NETS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),       # CGNAT
    ipaddress.ip_network("169.254.0.0/16"),      # link-local + AWS metadata
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),        # TEST-NET-1
    ipaddress.ip_network("198.18.0.0/15"),       # benchmark
    ipaddress.ip_network("198.51.100.0/24"),     # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),      # TEST-NET-3
    ipaddress.ip_network("240.0.0.0/4"),         # reserved
    ipaddress.ip_network("255.255.255.255/32"),  # broadcast
]

# Extra blocked v6 networks (e.g. AWS IPv6 metadata).
_EXTRA_V6_NETS = [
    ipaddress.ip_network("fd00:ec2::/32"),       # AWS IPv6 metadata range
]

_BLOCKED_PORTS = {22, 23, 25, 3306, 5432, 6379, 27017}


def _check_ip(ip_obj: ipaddress._BaseAddress) -> tuple[bool, str]:
    """Return (ok, err) for a resolved IP. Rejects private/loopback/etc."""
    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local \
            or ip_obj.is_reserved or ip_obj.is_multicast or ip_obj.is_unspecified:
        return False, f"IP privado/interno bloqueado: {ip_obj}"

    if isinstance(ip_obj, ipaddress.IPv4Address):
        for net in _EXTRA_V4_NETS:
            if ip_obj in net:
                return False, f"IP em rango bloqueado ({net}): {ip_obj}"
    else:  # IPv6
        # Reject mapped/translated IPv4 by validating the embedded v4
        embedded = None
        if ip_obj.ipv4_mapped is not None:
            embedded = ip_obj.ipv4_mapped
        elif ip_obj.sixtofour is not None:
            embedded = ip_obj.sixtofour
        elif ip_obj.teredo is not None:
            # teredo returns (server, client) — check the client v4
            embedded = ip_obj.teredo[1]
        if embedded is not None:
            ok, err = _check_ip(embedded)
            if not ok:
                return False, f"IPv6 com v4 embutido bloqueado: {err}"
        for net in _EXTRA_V6_NETS:
            if ip_obj in net:
                return False, f"IP em rango bloqueado ({net}): {ip_obj}"

    return True, ""


def _normalize_host(hostname: str) -> tuple[Optional[str], str]:
    """Return (host, err). Strips trailing dot, rejects userinfo, idna-decodes."""
    if not hostname:
        return None, "URL inválida: hostname ausente."
    if "@" in hostname:
        return None, "Hostname inválido: contém '@'."
    host = hostname.rstrip(".")
    # IDNA / punycode normalization (best-effort)
    try:
        host = host.encode("idna").decode("ascii").lower()
    except Exception:
        host = host.lower()
    return host, ""


def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Valida URL para prevenir SSRF (Server-Side Request Forgery).

    Algoritmo:
      1. Esquema http/https
      2. Normaliza hostname (strip dot, rejeita '@', punycode)
      3. Deny-list explícita (localhost, metadata)
      4. Se hostname é literal IP — exige formato dotted-quad estrito (v4)
      5. Resolve via getaddrinfo e valida TODOS os IPs retornados
      6. Aplica deny-list de redes (v4 + v6, incluindo metadata cloud)
    """
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False, f"Esquema '{parsed.scheme}' não permitido. Use http ou https."

        host, err = _normalize_host(parsed.hostname or "")
        if err:
            return False, err

        # Deny-list por nome
        if host in _DENY_HOSTS:
            return False, f"Hostname bloqueado: {host}"

        # Portas sensíveis
        try:
            port = parsed.port
        except ValueError:
            return False, "Porta inválida."
        if port and port in _BLOCKED_PORTS:
            return False, f"Porta {port} não permitida."

        # Detecta literal IP
        ip_literal: Optional[ipaddress._BaseAddress] = None
        if host.startswith("[") and host.endswith("]"):
            # IPv6 literal (urllib já strip-a, mas por segurança)
            try:
                ip_literal = ipaddress.IPv6Address(host[1:-1])
            except ValueError:
                return False, "IPv6 literal inválido."
        else:
            # Tenta IPv4 estrito (rejeita 0177.0.0.1, hex, integer)
            if "." in host and all(c.isdigit() or c == "." for c in host):
                if not _DOTTED_QUAD.match(host):
                    return False, f"IPv4 mal-formado/encoding ofuscado bloqueado: {host}"
                try:
                    ip_literal = ipaddress.IPv4Address(host)
                except ValueError:
                    return False, f"IPv4 inválido: {host}"
            else:
                # Pode ainda ser IPv6 sem brackets (raro em URL, mas trata)
                try:
                    ip_literal = ipaddress.IPv6Address(host)
                except ValueError:
                    pass

        if ip_literal is not None:
            ok, err = _check_ip(ip_literal)
            if not ok:
                return False, err
            return True, ""

        # Hostname → resolve TODOS os IPs (A + AAAA)
        try:
            infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        except socket.gaierror as e:
            return False, f"Falha ao resolver DNS para {host}: {e}"

        if not infos:
            return False, f"Sem registros DNS para {host}."

        seen = set()
        for info in infos:
            sockaddr = info[4]
            ip_str = sockaddr[0]
            # IPv6 link-local pode vir com %scope — strip
            if "%" in ip_str:
                ip_str = ip_str.split("%", 1)[0]
            if ip_str in seen:
                continue
            seen.add(ip_str)
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                return False, f"DNS retornou IP inválido: {ip_str}"
            ok, err = _check_ip(ip_obj)
            if not ok:
                return False, err

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
    """
    GET com proteção SSRF em redirects.

    Não seguimos redirects automaticamente — re-validamos `Location`
    contra `is_safe_url` antes de prosseguir, para evitar bypass
    via 30x apontando para IP interno.
    """
    current = url
    for _ in range(5):  # máx 5 hops
        ok, err = is_safe_url(current)
        if not ok:
            raise HTTPException(status_code=400, detail=f"URL blocked (redirect): {err}")
        r = await client.get(
            current,
            follow_redirects=False,
            headers={"User-Agent": settings.USER_AGENT},
        )
        if r.is_redirect:
            loc = r.headers.get("Location")
            if not loc:
                r.raise_for_status()
                return r.text
            # Resolve relativos
            current = str(httpx.URL(current).join(loc))
            continue
        r.raise_for_status()
        return r.text
    raise HTTPException(status_code=400, detail="Too many redirects")


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

    # SSRF guard at network layer: every request (incl. subresources & redirects)
    # is re-validated against is_safe_url. Aborted if it hits a private/blocked target.
    async def _ssrf_guard(route, request):
        try:
            ok, _err = is_safe_url(request.url)
        except Exception:
            ok = False
        if not ok:
            try:
                await route.abort("blockedbyclient")
            except Exception:
                pass
            return
        try:
            await route.continue_()
        except Exception:
            pass

    await context.route("**/*", _ssrf_guard)

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
