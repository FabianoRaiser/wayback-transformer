import ipaddress
import os
import socket
import shutil
import time
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager


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
    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Apenas URLs http:// ou https:// são permitidas.")

    host = parsed.hostname
    if not host:
        raise ValueError("URL inválida: hostname não encontrado.")

    if host.lower() in BLOCKED_HOSTS:
        raise ValueError(f"Host bloqueado por segurança: {host}")

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


def build_driver() -> webdriver.Firefox:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--width=1280")
    options.add_argument("--height=900")

    # Busca o Firefox em todos os paths possíveis do Nix/Linux
    firefox_path = None
    candidates = [
        shutil.which("firefox"),
        shutil.which("firefox-esr"),
        "/usr/bin/firefox",
        "/usr/bin/firefox-esr",
        "/run/current-system/sw/bin/firefox",
    ]

    # Busca dinâmica nos paths do Nix
    import glob
    candidates += glob.glob("/nix/store/*/bin/firefox")
    candidates += glob.glob("/nix/var/nix/profiles/*/bin/firefox")

    for path in candidates:
        if path and os.path.exists(path):
            firefox_path = path
            break

    print(f"[scraper] Firefox encontrado em: {firefox_path}", flush=True)

    if not firefox_path:
        raise RuntimeError("Firefox não encontrado no sistema.")

    options.binary_location = firefox_path

    service = Service(GeckoDriverManager().install())
    return webdriver.Firefox(service=service, options=options)


def scrape(url: str) -> dict:
    url = validate_url(url)
    driver = None
    try:
        driver = build_driver()
        driver.set_page_load_timeout(20)
        driver.get(url)

        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        driver.execute_script("window.scrollTo(0, 600);")
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
            "driver": driver,
        }
    except ValueError:
        if driver:
            driver.quit()
        raise
    except Exception as e:
        if driver:
            driver.quit()
        raise RuntimeError(f"Falha ao carregar a página: {e}") from e