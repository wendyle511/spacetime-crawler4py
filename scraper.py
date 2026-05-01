import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
from collections import Counter

visited_urls = set()
word_counter = Counter()
page_word_count = {}

max_words = 0
max_words_url = ""

subdomain_pages = {}

STOPWORDS = set("""
a an and are as at be by for from has he in is it its of on that the to was were will with
this that these those
""".split())

ALLOWED_DOMAINS = (
    "ics.uci.edu",
    "cs.uci.edu",
    "informatics.uci.edu",
    "stat.uci.edu"
)

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    global max_words, max_words_url

    links = []

    if resp.status != 200 or not resp.raw_response:
        return links

    content_type = resp.raw_response.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return links

    url, _ = urldefrag(url)
    parsed = urlparse(url)
    clean_url = parsed.scheme + "://" + parsed.netloc + parsed.path.rstrip("/")

    if clean_url in visited_urls:
        return links
    visited_urls.add(clean_url)

    try:
        soup = BeautifulSoup(resp.raw_response.content, "lxml")

        for tag in soup(["script", "style"]):
            tag.extract()

        text = soup.get_text(" ")
        words = re.findall(r"[a-zA-Z]+", text.lower())
        words = [w for w in words if w not in STOPWORDS and len(w) > 2]

        if len(words) < 20 or len(words) > 80000:
            return []

        word_counter.update(words)
        page_word_count[clean_url] = len(words)

        if len(words) > max_words:
            max_words = len(words)
            max_words_url = clean_url

        host = parsed.netloc.lower().replace("www.", "")

        if "uci.edu" in host:
            if host not in subdomain_pages:
                subdomain_pages[host] = set()
            subdomain_pages[host].add(clean_url)

        for a in soup.find_all("a", href=True):
            abs_url = urljoin(clean_url, a["href"])
            abs_url, _ = urldefrag(abs_url)
            links.append(abs_url)

    except:
        return []

    return links

def is_valid(url):
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        host = parsed.netloc.lower().replace("www.", "")
        path = parsed.path.lower()
        query = parsed.query.lower()

        if not any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS):
            return False

        if re.search(r"\.(css|js|png|jpg|jpeg|gif|ico|pdf|zip|mp4|docx|pptx|xlsx|exe)$", path):
            return False

        if len(url) > 3000:
            return False

        # ---------------- TRAPS ----------------

        if "/events/" in path or path.endswith("/events"):
            return False

        if "ical" in path or "ical" in query:
            return False

        if "tribe" in path or "tribe" in query:
            return False

        if "doku.php" in path:
            return False

        if host == "ics.uci.edu" and path.startswith("/~eppstein/pix"):
            return False

        if host == "fano.ics.uci.edu" and path.startswith("/ca/rules"):
            return False

        if "gitlab.ics.uci.edu" in host:
            return False

        if "grape.ics.uci.edu" in host:
            return False

        if host == "isg.ics.uci.edu" and path.startswith("/events"):
            return False

        return True

    except:
        return False

def generate_report():
    with open("report.txt", "w", encoding="utf-8") as f:
        f.write("1. Number of unique pages\n")
        f.write(f"{len(visited_urls)}\n\n")

        f.write("2. Longest page (by word count)\n")
        f.write(f"{max_words_url} , {max_words}\n\n")

        f.write("3. Top 50 most common words\n")
        for word, count in word_counter.most_common(50):
            f.write(f"{word}, {count}\n")

        f.write("\n4. Subdomains\n")
        for subdomain in sorted(subdomain_pages):
            f.write(f"{subdomain}, {len(subdomain_pages[subdomain])}\n")
