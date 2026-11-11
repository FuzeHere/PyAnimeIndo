import unittest
from unittest.mock import patch, MagicMock

import API.mal as mal
from fastapi.testclient import TestClient
from web_server import app


class MyAnimeListIntegrationTests(unittest.TestCase):
    def test_clean_title(self):
        self.assertEqual(mal.clean_title("Sousou no Frieren Episode 28 Sub Indo"), "Sousou no Frieren")
        self.assertEqual(mal.clean_title("One Piece (TV) Subtitle Indonesia"), "One Piece")
        self.assertEqual(mal.clean_title("[Batch] Bleach: Sennen Kessen-hen (End)"), "Bleach: Sennen Kessen-hen")
        self.assertEqual(mal.clean_title("Kikansha no Mahou wa Tokubetsu desu"), "Kikansha no Mahou wa Tokubetsu desu")
        self.assertEqual(mal.clean_title(""), "")

    def test_get_mal_info_from_prefix_json(self):
        fake_prefix_response = {
            "categories": [{
                "type": "anime",
                "items": [{
                    "id": 52991,
                    "name": "Sousou no Frieren",
                    "url": "https://myanimelist.net/anime/52991/Sousou_no_Frieren",
                    "image_url": "https://cdn.myanimelist.net/image.jpg",
                    "payload": {
                        "media_type": "TV",
                        "score": "9.24",
                        "status": "Finished Airing",
                        "aired": "Sep 2023 to Mar 2024"
                    }
                }]
            }]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_prefix_response

        with patch("API.mal.requests.get", return_value=mock_resp):
            # Clear cache for testing
            mal._CACHE.clear()
            info = mal.get_mal_info("Sousou no Frieren Sub Indo", fetch_full=False)

        self.assertTrue(info["found"])
        self.assertEqual(info["title"], "Sousou no Frieren")
        self.assertEqual(info["score"], 9.24)
        self.assertEqual(info["status"], "Finished Airing")
        self.assertEqual(info["mal_url"], "https://myanimelist.net/anime/52991/Sousou_no_Frieren")

    def test_web_mal_api_endpoint(self):
        client = TestClient(app)
        mock_data = {
            "found": True,
            "title": "Sousou no Frieren",
            "score": 9.24,
            "ranked": "#1",
            "popularity": "#95",
            "members": "1,500,000",
            "studios": ["Madhouse"],
            "genres": ["Adventure", "Fantasy"],
            "mal_url": "https://myanimelist.net/anime/52991/Sousou_no_Frieren"
        }
        with patch("API.mal.get_mal_info", return_value=mock_data):
            res = client.get("/api/mal?title=Frieren")

        self.assertEqual(res.status_code, 200)
        json_data = res.json()
        self.assertTrue(json_data["success"])
        self.assertEqual(json_data["data"]["score"], 9.24)
        self.assertEqual(json_data["data"]["ranked"], "#1")


if __name__ == "__main__":
    unittest.main()
