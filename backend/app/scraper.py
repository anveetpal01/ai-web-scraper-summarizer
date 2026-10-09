"""Downloads a web page and extracts its main readable text."""

import asyncio
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup, Tag

from app.errors import AppError
from app.url_safety import ensure_public_url

REQUEST_TIMEOUT = httpx.Timeout(15.0)
TOTAL_FETCH_TIMEOUT_SECONDS = 25
MAX_REDIRECTS = 5
MAX_BODY_BYTES = 3 * 1024 * 1024
MAX_TEXT_CHARS = 24_000
MIN_TEXT_CHARS = 50
MIN_CONTENT_ROOT_CHARS = 500

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; WebSummarizer/1.0; +https://github.com/anveetpal01/ai-web-scraper-summarizer)",
    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
    "Accept-Language": "en-US,en;q=0.9",
}
READABLE_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")

# Elements that never contain readable content.
NON_CONTENT_TAGS = ["script", "style", "noscript", "template", "svg", "canvas", "iframe", "object", "embed", "link", "meta"]

# Page chrome that usually sits around the actual content.
PAGE_CHROME_SELECTOR = ", ".join([
    "nav",
    "aside",
    "footer",
    "form",
    "button",
    "dialog",
    "[role='navigation']",
    "[role='complementary']",
    "[role='contentinfo']",
    "[role='search']",
    "[aria-hidden='true']",
    "[hidden]",
])

# Block-level elements that should start on a new line in the extracted text.
BLOCK_TAGS = [
    "address", "article", "blockquote", "dd", "div", "dl", "dt", "figcaption",
    "figure", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main",
    "ol", "p", "pre", "section", "table", "tr", "ul",
]

# Placeholder for block boundaries, so line breaks that only exist in the HTML
# source can be collapsed without gluing paragraphs together.
BLOCK_BREAK = "\ue000"


@dataclass
class ScrapedPage:
    url: str
    title: str
    description: str
    text: str
    word_count: int
    truncated: bool


async def scrape_page(url: str) -> ScrapedPage:
    try:
        body, content_type, final_url = await asyncio.wait_for(fetch_page(url), TOTAL_FETCH_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        raise AppError("The page took too long to download.", 504) from None

    charset = _charset_from(content_type)
    if "text/plain" in content_type:
        title, description = "", ""
        text = clean_lines(_decode(body, charset))
    else:
        title, description, text = extract_content(body, charset)

    if len(text) < MIN_TEXT_CHARS:
        raise AppError(
            "Couldn't find enough readable text on that page. "
            "It may be empty, behind a login, or built entirely with JavaScript.",
            422,
        )

    truncated = len(text) > MAX_TEXT_CHARS
    return ScrapedPage(
        url=final_url,
        title=title or urlsplit(final_url).hostname or final_url,
        description=description,
        text=text[:MAX_TEXT_CHARS],
        word_count=len(text.split()),
        truncated=truncated,
    )


async def fetch_page(url: str) -> tuple[bytes, str, str]:
    """
    Downloads the page and returns (body, content type, final URL).

    Redirects are followed by hand so that every hop is checked against
    private network addresses before it is requested.
    """
    current = url
    async with httpx.AsyncClient(headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await ensure_public_url(current)
            try:
                async with client.stream("GET", current) as response:
                    if response.is_redirect:
                        current = urljoin(current, response.headers["location"])
                        continue

                    content_type = _check_response(response)
                    body = await _read_limited(response, MAX_BODY_BYTES)
                    return body, content_type, str(response.url)
            except httpx.TimeoutException:
                raise AppError("The page took too long to respond.", 504) from None
            except httpx.HTTPError:
                raise AppError("Couldn't connect to that website. Check the URL and try again.", 502) from None

    raise AppError("The page redirected too many times.", 502)


def extract_content(html: bytes | str, charset: str | None = None) -> tuple[str, str, str]:
    """Returns (title, description, main text) for an HTML document."""
    options = {"from_encoding": charset} if isinstance(html, bytes) and charset else {}
    soup = BeautifulSoup(html, "lxml", **options)

    title = _read_title(soup)
    description = _meta_content(soup, name="description") or _meta_content(soup, property="og:description")

    for tag in soup.find_all(NON_CONTENT_TAGS):
        if not tag.decomposed:
            tag.decompose()

    root = _pick_content_root(soup)
    for tag in root.select(PAGE_CHROME_SELECTOR):
        if not tag.decomposed:
            tag.decompose()
    # Site-wide headers go, but keep headers that belong to an article (title, byline).
    for header in root.find_all("header"):
        if not header.decomposed and header.find_parent("article") is None:
            header.decompose()

    for line_break in root.find_all("br"):
        line_break.replace_with(BLOCK_BREAK)
    for block in root.find_all(BLOCK_TAGS):
        block.insert(0, BLOCK_BREAK)
        block.append(BLOCK_BREAK)
    for cell in root.find_all(["td", "th"]):
        cell.append(" ")

    text = re.sub(r"\s+", " ", root.get_text()).replace(BLOCK_BREAK, "\n")
    return title, description, clean_lines(text)


def clean_lines(text: str) -> str:
    """Collapses whitespace, drops empty lines and consecutive duplicates."""
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = _collapse(raw_line)
        if line and (not lines or line != lines[-1]):
            lines.append(line)
    return "\n".join(lines)


def _check_response(response: httpx.Response) -> str:
    """Raises if the response isn't a readable page. Returns its content type."""
    if not response.is_success:
        hint = " The site may be blocking automated requests." if response.status_code in (401, 403, 429) else ""
        raise AppError(f"The website responded with HTTP {response.status_code}.{hint}", 502)

    content_type = response.headers.get("content-type", "").lower()
    if content_type and not any(kind in content_type for kind in READABLE_CONTENT_TYPES):
        kind = content_type.split(";")[0].strip()
        raise AppError(f'That URL points to a "{kind}" file, not a web page.', 415)
    return content_type


async def _read_limited(response: httpx.Response, limit: int) -> bytes:
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body.extend(chunk)
        if len(body) >= limit:
            break
    return bytes(body[:limit])


def _pick_content_root(soup: BeautifulSoup) -> Tag | BeautifulSoup:
    """
    Prefers the largest <article>/<main> element when it holds a reasonable
    amount of text, otherwise falls back to the whole <body>.
    """
    best, best_length = None, 0
    for candidate in soup.select("article, main, [role='main']"):
        length = len(_collapse(candidate.get_text(" ")))
        if length > best_length:
            best, best_length = candidate, length

    if best is not None and best_length >= MIN_CONTENT_ROOT_CHARS:
        return best
    return soup.body or soup


def _read_title(soup: BeautifulSoup) -> str:
    candidates = [
        _meta_content(soup, property="og:title"),
        soup.title.get_text() if soup.title else "",
        h1.get_text() if (h1 := soup.find("h1")) else "",
    ]
    return next((_collapse(value) for value in candidates if _collapse(value)), "")


def _meta_content(soup: BeautifulSoup, **attrs: str) -> str:
    tag = soup.find("meta", attrs=attrs)
    content = tag.get("content") if isinstance(tag, Tag) else None
    return _collapse(content) if isinstance(content, str) else ""


def _charset_from(content_type: str) -> str | None:
    match = re.search(r"charset=[\"']?([\w-]+)", content_type, re.IGNORECASE)
    return match.group(1) if match else None


def _decode(body: bytes, charset: str | None) -> str:
    try:
        return body.decode(charset or "utf-8", errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def _collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
