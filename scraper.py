"""
scraper.py - Handles web scraping using requests and BeautifulSoup.
Extracts the page title and main text content from a given URL.
"""

import re
import requests
from bs4 import BeautifulSoup

# Request timeout in seconds (don't wait forever)
REQUEST_TIMEOUT = 10

# Full browser-like headers that prevent bot-detection disconnects
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
}

# Tags to remove completely (they don't have useful readable text)
TAGS_TO_REMOVE = [
    "script", "style", "nav", "header", "footer",
    "aside", "form", "button", "iframe", "noscript",
    "svg", "img", "input", "select", "textarea"
]


def clean_text(raw_text):
    """
    Clean up extracted text:
    - Remove extra whitespace and blank lines
    - Strip leading/trailing spaces
    Returns a clean, readable string.
    """
    # Replace multiple spaces/tabs with a single space
    text = re.sub(r"[ \t]+", " ", raw_text)
    # Replace multiple newlines with a single newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip overall whitespace
    return text.strip()


def scrape_url(url):
    """
    Scrape a single URL and return its title and text content.

    Returns a tuple: (title, content)
    - title: string, the page's <title> tag text
    - content: string, cleaned main text content

    Returns (None, None) if scraping fails.
    """
    # ── Basic URL validation ──────────────────────────────────────
    if not url.startswith(("http://", "https://")):
        print(f"  [ERROR] Invalid URL (must start with http/https): {url}")
        return None, None

    # ── Fetch the page ────────────────────────────────────────────
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()  # Raises an error for 4xx / 5xx responses
    except requests.exceptions.MissingSchema:
        print(f"  [ERROR] Malformed URL: {url}")
        return None, None
    except requests.exceptions.ConnectionError as e:
        # Some sites (e.g. 1001fonts) silently drop connections on plain bots.
        # Try Jina AI reader as a fallback before giving up.
        print(f"  [INFO] Connection dropped — trying Jina bypass for: {url}")
        try:
            proxy_url = f"https://r.jina.ai/{url}"
            r = requests.get(proxy_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            r.raise_for_status()
            text = r.text
            title = "Scraped via Proxy"
            for line in text.splitlines():
                if line.startswith("Title: "):
                    title = line.replace("Title: ", "").strip()
                    break
            return title, text
        except Exception:
            print(f"  [ERROR] Could not connect to: {url}")
            return None, None
    except requests.exceptions.Timeout:
        print(f"  [ERROR] Request timed out: {url}")
        return None, None
    except requests.exceptions.HTTPError as e:
        if getattr(e.response, "status_code", None) in [403, 401, 406, 429]:
            try:
                print(f"  [INFO] Trying fallback bypass proxy for: {url}")
                proxy_url = f"https://r.jina.ai/{url}"
                # Use a simplified User-Agent because Jina blocks the Chrome scraper footprint
                r = requests.get(proxy_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                r.raise_for_status()
                text = r.text
                
                title = "Scraped via Proxy"
                for line in text.splitlines():
                    if line.startswith("Title: "):
                        title = line.replace("Title: ", "").strip()
                        break
                        
                return title, text
            except Exception as proxy_e:
                print(f"  [ERROR] Fallback proxy also failed: {proxy_e}")
        
        print(f"  [ERROR] HTTP error {e.response.status_code} for: {url}")
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Failed to fetch {url}: {e}")
        return None, None

    # ── Parse the HTML ────────────────────────────────────────────
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract the page title — try multiple strategies
    title = None
    # 1. og:title (most reliable for modern sites)
    og = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "og:title"})
    if og and og.get("content", "").strip():
        title = og["content"].strip()
    # 2. Standard <title> tag
    if not title:
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
    # 3. First <h1> on the page
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    # 4. Fall back to URL slug
    if not title:
        slug = url.rstrip("/").split("/")[-1].replace("-", " ").replace("_", " ")
        title = slug.title() if slug else "Saved Page"

    # Remove noisy tags before extracting text
    for tag in soup(TAGS_TO_REMOVE):
        tag.decompose()  # Removes the tag and its children from the tree

    # Try to find the main content area first
    # Many sites use <main>, <article>, or a div with id="content"
    main_content = (
        soup.find("main") or
        soup.find("article") or
        soup.find(id="content") or
        soup.find(id="main-content") or
        soup.find(class_="post-content") or
        soup.find(class_="entry-content") or
        soup.body  # Fall back to entire body
    )

    if main_content:
        raw_text = main_content.get_text(separator="\n")
    else:
        raw_text = soup.get_text(separator="\n")

    content = clean_text(raw_text)

    # Warn if almost nothing was extracted
    if len(content) < 50:
        print(f"  [WARN] Very little content extracted from: {url}")

    return title, content


def scrape_multiple(urls):
    """
    Scrape a list of URLs one by one.
    Returns a list of dicts: [{url, title, content}, ...]
    Only includes successfully scraped pages.
    """
    results = []

    for i, url in enumerate(urls, start=1):
        url = url.strip()
        if not url:
            continue  # Skip blank lines

        print(f"\n[{i}/{len(urls)}] Scraping: {url}")
        title, content = scrape_url(url)

        if title is not None and content is not None:
            results.append({
                "url": url,
                "title": title,
                "content": content
            })

    return results


def load_urls_from_file(filepath):
    """
    Read URLs from a text file (one URL per line).
    Ignores blank lines and lines starting with '#' (comments).
    Returns a list of URL strings.
    """
    urls = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
        print(f"[FILE] Loaded {len(urls)} URLs from '{filepath}'")
    except FileNotFoundError:
        print(f"[ERROR] File not found: {filepath}")
    return urls


def generate_tags(content):
    """
    Generate simple topic tags based on keywords in content.
    Returns a comma-separated string of tags.
    """
    if not content:
        return ""
        
    tags = []
    content_lower = content.lower()
    
    # Simple rule-based mapping
    rules = {
        "python": "Python",
        "robot": "Robotics",
        "ai ": "AI",
        "artificial intelligence": "AI",
        "math": "Math",
        "tutorial": "Tutorial",
        "guide": "Guide",
        "programming": "Programming",
        "machine learning": "Machine Learning",
        "history": "History",
        "science": "Science",
        "technology": "Technology"
    }

    for keyword, tag in rules.items():
        if keyword in content_lower and tag not in tags:
            tags.append(tag)
            
    return ", ".join(tags)