import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

from API import nimegami


class FakeResponse:
    def __init__(self, text, payload=None):
        self.text = text
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class NimegamiParserTests(unittest.TestCase):
    def test_search_uses_public_api_and_normalizes_relative_image_and_slug(self):
        response = FakeResponse("", {"suggestions": [{
            "slug": "demo-sub-indo", "title": "Demo", "poster": "/poster.jpg",
            "format": "TV", "year": 2026,
        }]})
        with patch.object(nimegami.requests, "get", return_value=response) as get:
            result = nimegami.searchAnime(" Demo ")

        self.assertEqual(get.call_args.kwargs["params"], {"q": "Demo"})
        self.assertEqual(result[0]["url"], "https://nimegami.id/demo-sub-indo/")
        self.assertEqual(result[0]["img"], "https://nimegami.id/poster.jpg")

    def test_episode_parser_finds_routes_in_next_server_data(self):
        soup = BeautifulSoup(
            '<h1>Demo</h1><script>self.x="playUrl":"/demo/streaming/2/720p/token/";</script>'
            '<script>self.y="playUrl":"/demo/streaming/1/480p/token2/";</script>',
            "html.parser",
        )
        with patch.object(nimegami, "_soup", return_value=soup):
            result = nimegami.getEpisodes("https://nimegami.id/demo/")

        self.assertEqual([ep["title"] for ep in result["episodes"]], ["Episode 1", "Episode 2"])

    def test_episode_title_uses_clean_catalog_title_and_keeps_trailing_slash(self):
        soup = BeautifulSoup(
            '<h1>Nonton Demo Series Episode 1-12 (End) Subtitle Indonesia</h1>'
            '<dl class="anime-info-summary"><div><dt>Judul</dt><dd>Demo Series</dd></div></dl>'
            '<script>self.x="playUrl":"/demo/streaming/1/720p/token/";</script>',
            "html.parser",
        )
        with patch.object(nimegami, "_soup", return_value=soup) as fetch:
            result = nimegami.getEpisodes("https://nimegami.id/demo/")

        self.assertEqual(result["title"], "Demo Series")
        self.assertEqual(result["episodes"][0]["url"], "https://nimegami.id/demo/#episode_1")
        fetch.assert_called_once_with("https://nimegami.id/demo/")

    def test_download_resolves_only_requested_episode_to_direct_media_url(self):
        soup = BeautifulSoup(
            '<div class="player-stage" id="episode_1"></div>'
            '<script>self.x="playUrl":"/demo/streaming/1/720p/one/";'
            'self.y="playUrl":"/demo/streaming/2/480p/two/";</script>',
            "html.parser",
        )
        player = BeautifulSoup(
            '<main id="player" data-src="https://stream-stor.berkasdrive.com/v/token"></main>',
            "html.parser",
        )
        with patch.object(nimegami, "_soup", side_effect=[soup, player]):
            result = nimegami.getDownload("https://nimegami.id/demo/#episode_2")

        self.assertEqual(result, {
            "480p": "https://stream-stor.berkasdrive.com/v/token",
        })

    def test_download_rejects_media_urls_outside_berkasdrive(self):
        detail = BeautifulSoup(
            '<script>self.x="playUrl":"/demo/streaming/1/720p/one/";</script>',
            "html.parser",
        )
        player = BeautifulSoup(
            '<main id="player" data-src="https://attacker.example/video.mp4"></main>',
            "html.parser",
        )
        with patch.object(nimegami, "_soup", side_effect=[detail, player]):
            result = nimegami.getDownload("https://nimegami.id/demo/#episode_1")

        self.assertEqual(result, {})

    def test_unknown_episode_does_not_fall_back_to_another_episode_player(self):
        soup = BeautifulSoup(
            '<div class="player-stage" id="episode_1"><a data-quality="720p" data-quality-url="/stream/1/720"></a></div>'
            '<script>self.x="playUrl":"/demo/streaming/1/720p/one/";</script>',
            "html.parser",
        )
        with patch.object(nimegami, "_soup", return_value=soup):
            result = nimegami.getDownload("https://nimegami.id/demo/#episode_99")

        self.assertEqual(result, {})

    def test_scrapers_reject_urls_outside_nimegami(self):
        with patch.object(nimegami.requests, "get") as get:
            with self.assertRaises(ValueError):
                nimegami.getEpisodes("https://example.org/collect")
            with self.assertRaises(ValueError):
                nimegami.getGenreAnime("https://example.org/collect")
            get.assert_not_called()

    def test_extractor_recognizes_berkasdrive_direct_stream(self):
        from API.extractor.krakenfiles import getStream
        media_url = "https://stream-stor.berkasdrive.com/v/v1.abc123token"
        with patch("API.extractor.krakenfiles.requests.get") as get:
            stream_result = getStream(media_url)
            self.assertEqual(stream_result, media_url)
            get.assert_not_called()

    def test_desktop_provider_routes_nimegami_urls(self):
        import pyanimeindo
        self.assertIn("nimegami", pyanimeindo.AVAILABLE_PROVIDERS)
        self.assertIs(pyanimeindo.get_provider_by_url("https://nimegami.id/demo-series/"), nimegami)


if __name__ == "__main__":
    unittest.main()
