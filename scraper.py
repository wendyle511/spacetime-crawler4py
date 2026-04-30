import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup

# Allowed domains
ALLOWED_DOMAINS = (
    "ics.uci.edu",
    "cs.uci.edu",
    "informatics.uci.edu",
    "stat.uci.edu"
)

def scraper(url, resp):
    """
    Main entry point called by crawler.
    Returns filtered list of URLs.
    """
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]


def extract_next_links(url, resp):
    """
    Extracts and normalizes all hyperlinks from a page.
    """
    extracted_links = []

    try:
        # Ensure response is valid
        if not resp or not resp.raw_response or not resp.raw_response.content:
            return extracted_links

        # Parse HTML
        soup = BeautifulSoup(resp.raw_response.content, "html.parser")

        # Find all anchor tags
        for tag in soup.find_all("a", href=True):
            href = tag.get("href")

            if not href:
                continue

            # Convert relative URL → absolute URL
            absolute_url = urljoin(resp.url, href)

            # Remove fragment (#section)
            clean_url, _ = urldefrag(absolute_url)

            extracted_links.append(clean_url)

    except Exception as e:
        print(f"[extract_next_links error] {e}")

    return extracted_links


def is_valid(url):
    """
    Filters URLs to ensure crawler stays inside allowed domains
    and avoids unwanted file types.
    """
    try:
        parsed = urlparse(url)

        # Only http/https
        if parsed.scheme not in {"http", "https"}:
            return False

        host = parsed.netloc.lower()

        # Remove port if present (e.g., example.com:80)
        host = host.split(":")[0]

        # Must belong to allowed domains (including subdomains)
        if not any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS):
            return False

        # Must have valid host
        if not host:
            return False

        # Reject unwanted file extensions
        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            r"|png|tiff?|mid|mp2|mp3|mp4"
            r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx"
            r"|data|dat|exe|bz2|tar|msi|bin|7z|dmg|iso"
            r"|epub|dll|tgz|war|zip|rar|gz)$",
            parsed.path.lower()
        ):
            return False

        # Optional safety: avoid extremely long URLs (trap prevention)
        if len(url) > 2000:
            return False

        return True

    except TypeError:
        return False
    except Exception:
        return False
