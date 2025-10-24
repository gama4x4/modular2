import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
}

def scrape_stock_from_html(html_text):
    try:
        match = re.search(r'"available_quantity"\s*:\s*(\d+)', html_text)
        return int(match.group(1)) if match else None
    except (ValueError, TypeError, IndexError):
        return None

def scrape_competitor_info(product_url):
    data = {"title": None, "price": None, "stock": None, "error": None}
    try:
        resp = requests.get(product_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')

        title = soup.find('h1', class_='ui-pdp-title') or soup.find('h1')
        if title:
            data['title'] = title.get_text(strip=True)

        meta_price = soup.find('meta', itemprop='price')
        if meta_price and meta_price.get('content'):
            data['price'] = float(meta_price['content'])
        else:
            match = re.search(r'"price"\s*:\s*([0-9]+(?:\.[0-9]+)?)', resp.text)
            if match:
                data['price'] = float(match.group(1))

        data['stock'] = scrape_stock_from_html(resp.text)

        if not data['title']:
            data['error'] = "Título não encontrado."
        elif data['price'] is None:
            data['error'] = "Preço não encontrado."

    except requests.RequestException as e:
        data['error'] = f"Erro de rede: {e}"
    except Exception as e:
        data['error'] = f"Erro inesperado: {e}"

    return data
