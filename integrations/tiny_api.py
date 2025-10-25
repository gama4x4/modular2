import requests
import xml.etree.ElementTree as ET

TINY_BASE_URL = "https://api.tiny.com.br/api2"

def build_url(endpoint, token, params=None):
    base = f"{TINY_BASE_URL}/{endpoint}.php"
    query = {"token": token, "formato": "json"}
    if params:
        query.update(params)
    return base, query

def send_tiny_request(endpoint, token, params=None):
    url, query = build_url(endpoint, token, params)
    try:
        resp = requests.get(url, params=query, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def create_product(token, product_data):
    return send_tiny_request("produto.incluir", token, product_data)

def update_product(token, product_data):
    return send_tiny_request("produto.alterar", token, product_data)

def get_product(token, sku):
    return send_tiny_request("produto.consultar", token, {"sku": sku})

def list_products(token, page=1):
    return send_tiny_request("produtos.listar", token, {"pagina": page})
