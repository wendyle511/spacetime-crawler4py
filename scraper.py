import re
import hashlib
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup
from collections import Counter

visited_urls = set()

word_counter = Counter()
page_word_count = {}

max_words = 0
max_words_url = ""

subdomain_counts = Counter()

page_simhashes = []

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
    return url.rstrip("/")

def stable_hash(word):
    return int(hashlib.md5(word.encode()).hexdigest(), 16)

def simhash(words):
    v = [0] * 64
    for w in words:
        h = stable_hash(w)
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1

    fp = 0
    for i in range(64):
        if v[i] > 0:
            fp |= (1 << i)
    return fp

def hamming(a, b):
    return bin(a ^ b).count("1")

def is_duplicate(words, threshold=10):
    h = simhash(words)

    for old in page_simhashes:
        if hamming(h, old) <= threshold:
            return True

    page_simhashes.append(h)
    return False

def is_trap_url(url):
    return "filter" in url or "people/?" in url

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    global max_words, max_words_url

    links = []

    if resp.status != 200 or not resp.raw_response:
        return links

    if "text/html" not in resp.raw_response.headers.get("Content-Type", ""):
        return links

    url = normalize(url)

    if url in visited_urls:
        return links
    visited_urls.add(url)

    try:
        soup = BeautifulSoup(resp.raw_response.content, "lxml")

        text = soup.get_text(" ")
        words = re.findall(r"[a-zA-Z]+", text.lower())
        words = [w for w in words if w not in STOPWORDS]

        if len(words) < 100:
            return []

        if is_duplicate(words):
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

        if re.search(r"\.(css|js|png|jpg|jpeg|gif|pdf|zip|mp4|docx|pptx)$", parsed.path.lower()):
            return False

        if len(url) > 2000:
            return False

        return True

    except:
        return False

def generate_report():
    with open("report.txt", "w", encoding="utf-8") as f:
        f.write("1. Longest page (by word count)\n")
        f.write(f"{max_words_url} , {max_words}\n\n")

        f.write("2. Top 50 most common words\n")
        for word, count in word_counter.most_common(50):
            f.write(f"{word}, {count}\n")

        f.write("\n3. Subdomains\n")
        for subdomain in sorted(subdomain_counts):
            f.write(f"{subdomain}, {subdomain_counts[subdomain]}\n")
