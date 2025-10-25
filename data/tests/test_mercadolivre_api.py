import unittest
from unittest.mock import patch
from integrations import mercadolivre_api as ml

class MercadoLivreApiTestCase(unittest.TestCase):

    @patch("integrations.mercadolivre_api.requests.post")
    def test_get_access_token(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"access_token": "abc123"}

        result = ml.get_access_token("fake_code")
        self.assertIn("access_token", result)
        self.assertEqual(result["access_token"], "abc123")

    @patch("integrations.mercadolivre_api.requests.get")
    def test_get_user_info(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"id": 98765, "nickname": "teste_ml"}

        result = ml.get_user_info("fake_token")
        self.assertEqual(result["nickname"], "teste_ml")

    @patch("integrations.mercadolivre_api.requests.get")
    def test_make_ml_api_request(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"price": 100, "stock": 5}

        result = ml.make_ml_api_request("https://fake.api/test", "fake_token")
        self.assertEqual(result["price"], 100)

if __name__ == '__main__':
    unittest.main()
