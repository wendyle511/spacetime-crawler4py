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

page_simhashes = set()

STOPWORDS = set("""
a an and are as at be by for from has he in is it its of on that the to was were will with
""".split())

ALLOWED_DOMAINS = (
    "ics.uci.edu",
    "cs.uci.edu",
    "informatics.uci.edu",
    "stat.uci.edu"
)

def normalize(url):
    try:
        url, _ = urldefrag(url)
        parsed = urlparse(url)
        return parsed._replace(fragment="").geturl().rstrip("/")
    except:
        return url

def stable_hash(word):
    return int(hashlib.md5(word.encode()).hexdigest(), 16)

def simhash(words):
    v = [0] * 64
    for w in words:
        h = stable_hash(w)
        for i in range(64):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)
    return fingerprint

def hamming(a, b):
    return bin(a ^ b).count("1")

def is_duplicate(words, threshold=3):
    h = simhash(words)
    for old in page_simhashes:
        if hamming(h, old) <= threshold:
            return True
    page_simhashes.add(h)
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
        content = resp.raw_response.content
        soup = BeautifulSoup(content, "lxml")

        text = soup.get_text(" ")
        words = re.findall(r"[a-zA-Z]+", text.lower())
        words = [w for w in words if w not in STOPWORDS]

        if len(words) < 50:
            return []

        if is_duplicate(words):
            return []

        word_counter.update(words)
        page_word_count[url] = len(words)

        if len(words) > max_words:
            max_words = len(words)
            max_words_url = url

        subdomain = urlparse(url).netloc
        subdomain_counts[subdomain] += 1

        for a in soup.find_all("a", href=True):
            href = a.get("href")
            abs_url = normalize(urljoin(url, href))
            links.append(abs_url)

    except Exception:
        return []

    return links

def is_valid(url):
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        if not any(parsed.netloc.endswith(d) for d in ALLOWED_DOMAINS):
            return False

        if url.count("=") > 2:
            return False

        if url.count("/") > 10:
            return False

        if re.search(r"(calendar|event|year|month)", url, re.IGNORECASE):
            return False

        if len(url) > 200:
            return False

        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$",
            parsed.path.lower()
        ):
            return False

        return True

    except:
        return False