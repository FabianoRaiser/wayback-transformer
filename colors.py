import re


FALLBACK = {
    "bg": "#003366",
    "text": "#ffffff",
    "accent": "#ff6600",
    "nav_bg": "#002244",
    "link": "#ffcc00",
}


def _rgb_to_hex(rgb_str: str) -> str:
    """Convert 'rgb(r, g, b)' or 'rgba(r,g,b,a)' to #rrggbb."""
    nums = re.findall(r"\d+", rgb_str)
    if len(nums) >= 3:
        r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
        if r == 0 and g == 0 and b == 0:
            return ""  # transparent / unset
        return f"#{r:02x}{g:02x}{b:02x}"
    return ""


def _get_computed(driver, selector: str, prop: str) -> str:
    try:
        script = f"""
        var el = document.querySelector({repr(selector)});
        if (!el) return '';
        return window.getComputedStyle(el).getPropertyValue({repr(prop)});
        """
        val = driver.execute_script(script)
        return _rgb_to_hex(val) if val else ""
    except Exception:
        return ""


def darken(hex_color: str, amount: int = 30) -> str:
    """Darken a hex color by reducing each channel."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return hex_color
    r = max(0, int(hex_color[0:2], 16) - amount)
    g = max(0, int(hex_color[2:4], 16) - amount)
    b = max(0, int(hex_color[4:6], 16) - amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def lighten(hex_color: str, amount: int = 40) -> str:
    """Lighten a hex color."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return hex_color
    r = min(255, int(hex_color[0:2], 16) + amount)
    g = min(255, int(hex_color[2:4], 16) + amount)
    b = min(255, int(hex_color[4:6], 16) + amount)
    return f"#{r:02x}{g:02x}{b:02x}"


def extract_colors(driver) -> dict:
    """
    Extract brand colors from the loaded page via computed styles.
    Returns dict with bg, text, accent, nav_bg, link, table_bg, header_bg.
    """
    colors = {}

    # Background
    colors["bg"] = (
        _get_computed(driver, "body", "background-color")
        or _get_computed(driver, "main", "background-color")
        or FALLBACK["bg"]
    )

    # Text color
    colors["text"] = (
        _get_computed(driver, "body", "color")
        or _get_computed(driver, "p", "color")
        or FALLBACK["text"]
    )

    # Accent / primary — try buttons and links first
    for sel in ["button", ".btn", "[class*='btn']", "[class*='button']", "a"]:
        c = _get_computed(driver, sel, "background-color")
        if c and c not in (colors["bg"], "#ffffff", "#000000"):
            colors["accent"] = c
            break
    if "accent" not in colors:
        for sel in ["a", "h1", "h2"]:
            c = _get_computed(driver, sel, "color")
            if c and c not in (colors["text"], "#000000"):
                colors["accent"] = c
                break
    colors.setdefault("accent", FALLBACK["accent"])

    # Nav background
    colors["nav_bg"] = (
        _get_computed(driver, "header", "background-color")
        or _get_computed(driver, "nav", "background-color")
        or darken(colors["bg"], 20)
        or FALLBACK["nav_bg"]
    )

    # Link color
    colors["link"] = (
        _get_computed(driver, "a", "color")
        or lighten(colors["accent"], 30)
        or FALLBACK["link"]
    )

    # Derived colors
    colors["table_bg"] = darken(colors["bg"], 15) or FALLBACK["nav_bg"]
    colors["header_bg"] = colors["nav_bg"]
    colors["accent_dark"] = darken(colors["accent"], 25)
    colors["bg_light"] = lighten(colors["bg"], 25)

    return colors