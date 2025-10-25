import re
import html
from bs4 import BeautifulSoup

def strip_html_tags(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "lxml")
    return soup.get_text()

def html_to_text(html_content):
    try:
        text = strip_html_tags(html_content)
        text = html.unescape(text)
        return text
    except Exception:
        return html_content

def normalize_plain_text_ml(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = text.replace("\n", " ").replace("\r", "")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def simulate_free_shipping(price: float, shipping: float):
    if shipping == 0:
        return price
    return round(price + shipping, 2)

def find_forbidden_indices(text: str, forbidden_keywords: list):
    found = []
    for word in forbidden_keywords:
        index = text.lower().find(word.lower())
        if index != -1:
            found.append((word, index))
    return found

def debug_plaintext_refs(text):
    print("--- DEBUG PLAINTEXT TEXT ---")
    print(text)
    print("----------------------------")
