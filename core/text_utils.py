import re
import html
import unicodedata
from bs4 import BeautifulSoup

_RE_ZERO_WIDTH = re.compile(r'[\u200B-\u200D\u2060\uFEFF]')
_RE_NBSP = re.compile(r'[\u00A0\u202F]')
_RE_SOFT_HYPH = re.compile(r'\u00AD')

def normalize_plain_text_ml(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = _RE_ZERO_WIDTH.sub('', s)
    s = _RE_SOFT_HYPH.sub('', s)
    s = _RE_NBSP.sub(' ', s)

    trans = {
        0x2010: ord('-'), 0x2011: ord('-'), 0x2012: ord('-'),
        0x2013: ord('-'), 0x2014: ord('-'), 0x2212: ord('-'),
        0x00D7: ord('x'), 0x2026: ord('.'), 0x2022: ord('-'),
        0x2018: ord("'"), 0x2019: ord("'"), 0x201C: ord('"'),
        0x201D: ord('"'), 0x00B0: None,
    }

    s = s.translate(trans)
    s = re.sub(r'[ \t]+', ' ', s).strip()
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s

def strip_html_tags(html_text: str) -> str:
    if not html_text:
        return ""

    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup.find_all(['p','div','h1','h2','h3','li']):
        tag.insert_before('\n\n')
        tag.insert_after('\n\n')
    for br in soup.find_all('br'):
        br.replace_with('\n')

    text = soup.get_text()
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()

def html_to_text(html_content: str) -> str:
    raw = strip_html_tags(html_content)
    return normalize_plain_text_ml(raw)
