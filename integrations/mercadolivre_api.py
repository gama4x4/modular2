import requests
import urllib.parse

ML_CLIENT_ID = '3574022221088825'
ML_CLIENT_SECRET = 'msLQzMKsrF0is2hyoBgaa4dqE47E1SXE'
ML_REDIRECT_URI = 'https://api.meliunlocker.cc/callback'
ML_SITE_ID = "MLB"
ML_API_BASE_URL = "https://api.mercadolibre.com"
APP_USER_AGENT = "MLAdCreatorMultiAccount/3.0.0"

def get_auth_url():
    return (
        f"https://auth.mercadolivre.com.br/authorization"
        f"?response_type=code&client_id={ML_CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(ML_REDIRECT_URI)}"
    )

def get_access_token(auth_code):
    url = f"{ML_API_BASE_URL}/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "code": auth_code,
        "redirect_uri": ML_REDIRECT_URI
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(url, data=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

def get_user_info(access_token):
    url = f"{ML_API_BASE_URL}/users/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def make_ml_api_request(url, access_token, params=None, user_agent=None):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": user_agent or APP_USER_AGENT
    }
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

def get_site_categories(site_id, access_token):
    return make_ml_api_request(
        f"{ML_API_BASE_URL}/sites/{site_id}/categories", access_token
    )

def get_category_details(cat_id, access_token):
    return make_ml_api_request(
        f"{ML_API_BASE_URL}/categories/{cat_id}", access_token
    )

def get_category_dump(site_id, access_token):
    return make_ml_api_request(
        f"{ML_API_BASE_URL}/sites/{site_id}/categories/all", access_token
    )
