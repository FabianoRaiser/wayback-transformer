import ipaddress
import socket
from urllib.parse import urlparse
import shutil


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


BLOCKED_HOSTS = {"localhost", "0.0.0.0"}
BLOCKED_PREFIXES = ("169.254.", "::1", "fe80:")
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def validate_url(url: str) -> str:
    """Validate and sanitize URL. Raises ValueError on invalid/unsafe URLs."""
    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Apenas URLs http:// ou https:// são permitidas.")

    host = parsed.hostname
    if not host:
        raise ValueError("URL inválida: hostname não encontrado.")

    if host.lower() in BLOCKED_HOSTS:
        raise ValueError(f"Host bloqueado por segurança: {host}")

    # Resolve hostname to IP and check for private ranges
    try:
        ip_str = socket.gethostbyname(host)
        ip = ipaddress.ip_address(ip_str)
        for net in BLOCKED_NETWORKS:
            if ip in net:
                raise ValueError(f"Endereço IP privado/local bloqueado: {ip_str}")
        for prefix in BLOCKED_PREFIXES:
            if ip_str.startswith(prefix):
                raise ValueError(f"Endereço IP bloqueado: {ip_str}")
    except socket.gaierror:
        raise ValueError(f"Não foi possível resolver o hostname: {host}")

    return url


def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--single-process")       # importante no Railway
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1280,900")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Usa o Chromium do sistema se disponível (Railway/Linux)
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    if chrome_path:
        options.binary_location = chrome_path

    return webdriver.Chrome(options=options)


def scrape(url: str) -> dict:
    """
    Scrape a single landing page.
    Returns dict with keys: page_source, title, final_url
    Raises ValueError for bad URLs, RuntimeError for scraping failures.
    """
    url = validate_url(url)
    driver = None
    try:
        driver = build_driver()
        driver.set_page_load_timeout(20)
        driver.get(url)

        # Wait for page to be ready
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # Scroll a bit to trigger lazy loading
        driver.execute_script("window.scrollTo(0, 600);")
        import time
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")

        page_source = driver.page_source
        title = driver.title
        final_url = driver.current_url

        if not page_source or len(page_source) < 200:
            raise RuntimeError("Página retornou conteúdo vazio ou muito pequeno.")

        return {
            "page_source": page_source,
            "title": title,
            "final_url": final_url,
            "driver": driver,  # keep alive for colors extraction
        }
    except ValueError:
        if driver:
            driver.quit()
        raise
    except Exception as e:
        if driver:
            driver.quit()
        raise RuntimeError(f"Falha ao carregar a página: {e}") from e