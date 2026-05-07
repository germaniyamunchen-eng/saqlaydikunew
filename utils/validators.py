from __future__ import annotations

import re
from urllib.parse import urlparse

SUPPORTED_DOMAINS = {
    "tiktok.com": "TikTok",
    "vm.tiktok.com": "TikTok",
    "instagram.com": "Instagram",
    "threads.net": "Threads",
    "youtu.be": "YouTube",
    "youtube.com": "YouTube",
    "m.youtube.com": "YouTube",
    "facebook.com": "Facebook",
    "fb.watch": "Facebook",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "snapchat.com": "Snapchat",
    "likee.video": "Likee",
    "likee.com": "Likee",
    "pinterest.com": "Pinterest",
    "pin.it": "Pinterest",
    "vk.com": "VK",
    "vkvideo.ru": "VK",
}

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def extract_url(text: str | None) -> str | None:
    if not text:
        return None
    match = URL_RE.search(text.strip())
    if not match:
        return None
    return match.group(0).rstrip(".,)")


def get_supported_platform(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    for domain, platform in SUPPORTED_DOMAINS.items():
        if host == domain or host.endswith(f".{domain}"):
            return platform
    return None


def is_supported_url(url: str) -> bool:
    return get_supported_platform(url) is not None


def looks_like_playlist(url: str) -> bool:
    parsed = urlparse(url)
    query = parsed.query.lower()
    path = parsed.path.lower()
    return "list=" in query or "/playlist" in path
