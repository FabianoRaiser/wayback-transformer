from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


NOISE_SELECTORS = [
    "[class*='cookie']", "[id*='cookie']",
    "[class*='modal']", "[id*='modal']",
    "[class*='popup']", "[id*='popup']",
    "[class*='banner']", "[id*='banner']",
    "script", "style", "noscript", "iframe",
    "form", "input", "textarea", "select",
]

MAX_PARAGRAPHS = 20
MAX_IMAGES = 10
MAX_LINKS = 15


def _absolute(url: str, base: str) -> str:
    if not url or url.startswith("data:"):
        return ""
    return urljoin(base, url)


def extract(page_source: str, base_url: str) -> dict:
    """
    Extract structured content from landing page HTML.
    Returns a dict with title, meta_description, headings, paragraphs,
    images, links, og_image, logo_url.
    """
    soup = BeautifulSoup(page_source, "lxml")

    # Remove noise elements
    for selector in NOISE_SELECTORS:
        try:
            for el in soup.select(selector):
                el.decompose()
        except Exception:
            pass

    # --- Meta ---
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc = ""
    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or "").lower()
        if name in ("description", "og:description"):
            meta_desc = tag.get("content", "").strip()
            if meta_desc:
                break

    # OG image
    og_image = ""
    og_tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if og_tag:
        og_image = _absolute(og_tag.get("content", ""), base_url)

    # --- Headings ---
    headings = []
    for tag in soup.find_all(["h1", "h2", "h3"])[:12]:
        text = tag.get_text(separator=" ", strip=True)
        if text and len(text) > 2:
            headings.append({"level": tag.name, "text": text})

    # --- Paragraphs ---
    paragraphs = []
    for p in soup.find_all("p"):
        text = p.get_text(separator=" ", strip=True)
        if text and len(text) > 30:
            paragraphs.append(text)
        if len(paragraphs) >= MAX_PARAGRAPHS:
            break

    # Also grab list items if few paragraphs
    if len(paragraphs) < 5:
        for li in soup.find_all("li")[:20]:
            text = li.get_text(separator=" ", strip=True)
            if text and len(text) > 15:
                paragraphs.append("• " + text)

    # --- Images ---
    logo_url = ""
    images = []

    header = soup.find("header")
    if header:
        for img in header.find_all("img"):
            src = _absolute(img.get("src", ""), base_url)
            alt = img.get("alt", "").lower()
            if src and not logo_url:
                logo_url = src
                if "logo" in alt:
                    break

    for img in soup.find_all("img"):
        src = _absolute(img.get("src", ""), base_url)
        alt = img.get("alt", "")
        if not src:
            continue
        if "logo" in alt.lower() and not logo_url:
            logo_url = src
        images.append({"src": src, "alt": alt})
        if len(images) >= MAX_IMAGES:
            break

    # Prefer og:image as hero
    hero_image = og_image or (images[0]["src"] if images else "")

    # --- Links ---
    links = []
    for a in soup.find_all("a", href=True):
        href = _absolute(a["href"], base_url)
        text = a.get_text(strip=True)
        if href and text and href.startswith("http") and len(text) > 1:
            parsed = urlparse(href)
            base_parsed = urlparse(base_url)
            # Only same-domain links (nav/footer)
            if parsed.netloc == base_parsed.netloc:
                links.append({"href": href, "text": text[:60]})
        if len(links) >= MAX_LINKS:
            break

    return {
        "title": title,
        "meta_description": meta_desc,
        "headings": headings,
        "paragraphs": paragraphs,
        "images": images,
        "hero_image": hero_image,
        "logo_url": logo_url,
        "og_image": og_image,
        "links": links,
        "has_content": bool(headings or paragraphs),
    }