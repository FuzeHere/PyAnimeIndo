import unittest
from unittest.mock import patch

import web_server
from API import nimegami, otakudesu, samehadaku


class ProviderRoutingTests(unittest.TestCase):
    def test_urls_are_matched_by_hostname_not_substring(self):
        self.assertIs(web_server.get_module_by_url("https://otakudesu.blog/anime/"), otakudesu)
        self.assertIs(web_server.get_module_by_url("https://v2.samehadaku.how/anime/"), samehadaku)
        self.assertIs(web_server.get_module_by_url("https://nimegami.id/demo/"), nimegami)
        self.assertIsNone(web_server.get_module_by_url("https://nimegami.id.attacker.example/demo/"))
        self.assertIsNone(web_server.get_module_by_url("https://otakudesu.blog.attacker.example/"))
        self.assertIsNone(web_server.get_module_by_url("https://samehadaku.attacker.example/"))

    def test_unknown_provider_url_is_rejected_before_scraping(self):
        from fastapi import HTTPException
        from unittest.mock import patch

        with patch.object(samehadaku, "getEpisodes") as scrape:
            with self.assertRaises(HTTPException) as raised:
                web_server.episodes("https://attacker.example/collect")

        self.assertEqual(raised.exception.status_code, 400)
        scrape.assert_not_called()

    def test_nimegami_stream_candidates_are_iframes_for_requested_quality(self):
        streams = {
            "360p": "https://nimegami.id/demo/streaming/1/360p/a/",
            "720p": "https://nimegami.id/demo/streaming/1/720p/b/",
            "embed": "https://nimegami.id/demo/streaming/1/720p/b/",
        }
        with patch.object(nimegami, "getDownload", return_value=streams), patch.object(
            web_server, "getStream", side_effect=AssertionError("should not extract player pages as video files")
        ):
            result = web_server.stream_candidates(
                "https://nimegami.id/demo/#episode_1", "360p"
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["candidates"][0]["quality"], "360p")
        self.assertEqual(result["candidates"][0]["type"], "iframe")
        self.assertEqual(result["candidates"][0]["url"], streams["360p"])


if __name__ == "__main__":
    unittest.main()
