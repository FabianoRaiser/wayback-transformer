import hashlib
import random
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
import os


def _fake_hit_counter(url: str) -> str:
    """Generate a deterministic fake hit counter based on URL hash."""
    h = int(hashlib.md5(url.encode()).hexdigest(), 16)
    base = (h % 900_000) + 100_000
    return f"{base:,}".replace(",", ".")


def _fake_guestbook() -> list:
    entries = [
        {"name": "Visitante_SP", "msg": "Site muiiito massa!! Favoritei ja!! :D :D"},
        {"name": "webmaster_br", "msg": "Parabens pelo site!! Continue assim!! Grande abraco!"},
        {"name": "navegador2002", "msg": "Otimo site!! Me add no MSN tá? hehe"},
        {"name": "InternetExplora", "msg": "Carregou rapido aqui no meu IE6!! 5 estrelas!!"},
        {"name": "Marquinha_RS", "msg": "Amei o layout!! Quando atualiza de novo??"},
        {"name": "T3chn0_G33k", "msg": "Esse site e foda! Botei nos favoritos!!"},
    ]
    random.shuffle(entries)
    return entries[:3]


def _tagline_for_marquee(content: dict) -> str:
    if content.get("meta_description"):
        return content["meta_description"]
    headings = content.get("headings", [])
    if headings:
        return " *** ".join(h["text"] for h in headings[:3])
    return f"Bem-vindo ao {content.get('title', 'nosso site')}! *** O melhor da internet! *** Visite sempre!"


def render_html(content: dict, colors: dict, source_url: str) -> str:
    """Render the final retro Geocities HTML."""
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("retro_page.html")

    context = {
        "content": content,
        "colors": colors,
        "source_url": source_url,
        "hit_counter": _fake_hit_counter(source_url),
        "guestbook": _fake_guestbook(),
        "marquee_text": _tagline_for_marquee(content),
        "last_updated": datetime.now().strftime("%d/%m/%Y"),
        "year": datetime.now().year,
    }

    return template.render(**context)