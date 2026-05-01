import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
from collections import Counter

visited_urls = set()
word_counter = Counter()
page_word_count = {}

max_words = 0
max_words_url = ""

subdomain_counts = Counter()

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

def normalize(url):
    url, _ = urldefrag(url)
    parsed = urlparse(url)
    return parsed.scheme + "://" + parsed.netloc + parsed.path.rstrip("/")

def is_trap_url(url):
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.lower()
    query = parsed.query.lower()

    if "calendar" in url or "login" in url or "signup" in url:
        return True

    if "/events/" in path or path.endswith("/events"):
        return True

    if "ical" in path or "ical" in query:
        return True

    if "tribe" in path or "tribe" in query:
        return True

    if "doku.php" in path:
        return True

    if domain == "ics.uci.edu" and path.startswith("/~eppstein/pix"):
        return True

    if domain == "fano.ics.uci.edu" and path.startswith("/ca/rules"):
        return True

    if domain == "gitlab.ics.uci.edu":
        return True

    if domain == "grape.ics.uci.edu":
        return True

    if domain == "isg.ics.uci.edu" and path.startswith("/events"):
        return True

    return False

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

    url = normalize(url)

    if url in visited_urls:
        return links
    visited_urls.add(url)

    try:
        soup = BeautifulSoup(resp.raw_response.content, "lxml")

        for tag in soup(["script", "style"]):
            tag.extract()

        text = soup.get_text(" ")
        words = re.findall(r"[a-zA-Z]+", text.lower())
        words = [w for w in words if w not in STOPWORDS and len(w) > 2]

        if len(words) < 20:
            return []

        if len(words) > 80000:
            return []

        word_counter.update(words)
        page_word_count[url] = len(words)

        if len(words) > max_words:
            max_words = len(words)
            max_words_url = url

        host = urlparse(url).netloc.lower().replace("www.", "")
        subdomain_counts[host] += 1

        for a in soup.find_all("a", href=True):
            abs_url = normalize(urljoin(url, a["href"]))
            if is_trap_url(abs_url):
                continue
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

        if not any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS):
            return False

        if re.search(r"\.(css|js|png|jpg|jpeg|gif|pdf|zip|mp4|docx|pptx|xlsx|exe)$", parsed.path.lower()):
            return False

        if len(url) > 3000:
            return False

        return True

    except:
        return False

def generate_report():
    with open("report.txt", "w", encoding="utf-8") as f:
        f.write("0. Number of unique pages\n")
        f.write(f"{len(visited_urls)}\n\n")

        f.write("1. Longest page (by word count)\n")
        f.write(f"{max_words_url} , {max_words}\n\n")

        f.write("2. Top 50 most common words\n")
        for word, count in word_counter.most_common(50):
            f.write(f"{word}, {count}\n")

        f.write("\n3. Subdomains\n")
        for subdomain in sorted(subdomain_counts):
            f.write(f"{subdomain}, {subdomain_counts[subdomain]}\n")
