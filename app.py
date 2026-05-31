import re
import uuid
import threading
import time
import os
from urllib.parse import urlparse
import subprocess

from flask import Flask, render_template, request, Response, jsonify

from scraper import scrape, validate_url
from extractor import extract
from colors import extract_colors
from renderer import render_html

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

TTL_SECONDS = 300

_pages: dict = {}
_pages_lock = threading.Lock()


def _cleanup_loop():
    while True:
        time.sleep(30)
        now = time.time()
        with _pages_lock:
            expired = [k for k, v in _pages.items() if v["expires_at"] < now]
            for k in expired:
                del _pages[k]


threading.Thread(target=_cleanup_loop, daemon=True).start()


def _store_page(html: str) -> str:
    page_id = uuid.uuid4().hex
    with _pages_lock:
        _pages[page_id] = {
            "html": html,
            "expires_at": time.time() + TTL_SECONDS,
        }
    return page_id


def _safe_filename(url: str) -> str:
    parsed = urlparse(url)
    name = parsed.netloc.replace("www.", "").replace(".", "-")
    name = re.sub(r"[^a-zA-Z0-9\-]", "", name)[:40] or "page"
    return f"{name}-retro.html"


@app.route("/")
def index():
    return render_template("form.html", error=None)


@app.route("/transform", methods=["POST"])
def transform():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify(error="URL não informada."), 400

    try:
        validate_url(url)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    driver = None
    try:
        result = scrape(url)
        driver = result["driver"]
        colors = extract_colors(driver)
        content = extract(result["page_source"], result["final_url"])
        html = render_html(content, colors, url)

        page_id = _store_page(html)
        return jsonify(page_id=page_id, url=f"/preview/{page_id}")

    except ValueError as e:
        return jsonify(error=str(e)), 400
    except RuntimeError as e:
        return jsonify(error=str(e)), 422
    except Exception as e:
        app.logger.exception("Unexpected error processing %s", url)
        return jsonify(error=f"Erro interno: {e}"), 500
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


@app.route("/preview/<page_id>")
def preview(page_id: str):
    with _pages_lock:
        entry = _pages.get(page_id)

    if not entry:
        return "Página expirada ou não encontrada. Gere novamente em <a href='/'>home</a>.", 404

    remaining = max(0, int(entry["expires_at"] - time.time()))
    html = entry["html"]

    banner = f"""
<div id="__ttl_banner__" style="
  position:fixed; bottom:0; left:0; right:0; z-index:99999;
  background:#111; color:#ffff00; font-family:monospace;
  font-size:12px; padding:6px 12px; text-align:center;
  border-top:2px solid #ff6600;">
  ⏳ Esta página expira em <span id="__ttl_secs__">{remaining}</span>s &nbsp;|&nbsp;
  <a href="/" style="color:#ff6600;">Gerar nova</a>
</div>
<script>
  (function(){{
    var s = {remaining};
    var el = document.getElementById('__ttl_secs__');
    var iv = setInterval(function(){{
      s--;
      if (s <= 0) {{ clearInterval(iv); el.parentElement.innerHTML = '⌛ Página expirada. <a href="/" style="color:#ff6600;">Gerar nova</a>'; return; }}
      el.textContent = s;
    }}, 1000);
  }})();
</script>"""

    if "</body>" in html:
        html = html.replace("</body>", banner + "</body>", 1)
    else:
        html += banner

    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/debug")
def debug():
    info = {}
    
    # Procura qualquer binário do Firefox
    result = subprocess.run(["find", "/", "-name", "firefox*", "-type", "f"], 
                           capture_output=True, text=True, timeout=10)
    info["find_firefox"] = result.stdout.splitlines()
    
    # Verifica paths comuns
    import shutil, os
    info["which_firefox"] = shutil.which("firefox")
    info["which_firefox_esr"] = shutil.which("firefox-esr")
    info["opt_firefox"] = os.path.exists("/opt/firefox/firefox")
    info["usr_local_firefox"] = os.path.exists("/usr/local/bin/firefox")
    
    # Lista /opt se existir
    if os.path.exists("/opt/firefox"):
        info["opt_firefox_ls"] = os.listdir("/opt/firefox")
    
    # Variáveis de ambiente relevantes
    info["PATH"] = os.environ.get("PATH", "")
    
    return jsonify(info)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)