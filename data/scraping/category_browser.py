import requests

def make_ml_api_request_for_category_browser(url, access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_site_categories_for_browser(site_id, access_token):
    url = f"https://api.mercadolibre.com/sites/{site_id}/categories"
    return make_ml_api_request_for_category_browser(url, access_token)

def get_category_details_for_browser(category_id, access_token):
    url = f"https://api.mercadolibre.com/categories/{category_id}"
    return make_ml_api_request_for_category_browser(url, access_token)
