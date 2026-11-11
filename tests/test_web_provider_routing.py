import unittest
from urllib.parse import quote
from unittest.mock import patch

import web_server
from API import nimegami, otakudesu, samehadaku
from fastapi import HTTPException
from starlette.requests import Request


def make_request(method="GET", headers=None):
    raw_headers = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    scope = {
        "type": "http", "http_version": "1.1", "method": method,
        "scheme": "http", "path": "/api/nimegami-video-proxy",
        "raw_path": b"/api/nimegami-video-proxy", "query_string": b"",
        "headers": raw_headers, "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }
    return Request(scope)


class ProviderRoutingTests(unittest.TestCase):
    def test_urls_are_matched_by_hostname_not_substring(self):
        self.assertIs(web_server.get_module_by_url("https://otakudesu.blog/anime/"), otakudesu)
        self.assertIs(web_server.get_module_by_url("https://v2.samehadaku.how/anime/"), samehadaku)
        self.assertIs(web_server.get_module_by_url("https://nimegami.id/demo/"), nimegami)
        self.assertIsNone(web_server.get_module_by_url("https://nimegami.id.attacker.example/demo/"))
        self.assertIsNone(web_server.get_module_by_url("https://otakudesu.blog.attacker.example/"))
        self.assertIsNone(web_server.get_module_by_url("https://samehadaku.attacker.example/"))

    def test_unknown_provider_url_is_rejected_before_scraping(self):
        with patch.object(samehadaku, "getEpisodes") as scrape:
            with self.assertRaises(HTTPException) as raised:
                web_server.episodes("https://attacker.example/collect")

        self.assertEqual(raised.exception.status_code, 400)
        scrape.assert_not_called()

    def test_nimegami_stream_candidates_proxy_the_requested_mp4_quality(self):
        streams = {
            "360p": "https://stream-stor.berkasdrive.com/v/a",
            "720p": "https://stream-stor.berkasdrive.com/v/b",
        }
        with patch.object(nimegami, "getDownload", return_value=streams), patch.object(
            web_server, "getStream", side_effect=AssertionError("should not extract player pages as video files")
        ):
            result = web_server.stream_candidates(
                "https://nimegami.id/demo/#episode_1", "360p"
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["candidates"][0]["quality"], "360p")
        self.assertEqual(result["candidates"][0]["type"], "video")
        self.assertEqual(
            result["candidates"][0]["url"],
            f"/api/nimegami-video-proxy?url={quote(streams['360p'], safe='')}",
        )

    def test_nimegami_video_proxy_forwards_range_and_partial_response(self):
        class Upstream:
            status_code = 206
            headers = {
                "Content-Type": "video/mp4", "Content-Length": "1024",
                "Content-Range": "bytes 0-1023/5000", "Accept-Ranges": "bytes",
            }

            def close(self):
                self.closed = True

        upstream = Upstream()
        media_url = "https://stream-stor.berkasdrive.com/v/opaque-token"
        with patch.object(web_server.requests, "get", return_value=upstream) as get:
            response = web_server.nimegami_video_proxy(
                make_request(headers={"Range": "bytes=0-1023"}), media_url
            )

        self.assertEqual(get.call_args.kwargs["headers"]["Range"], "bytes=0-1023")
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.headers["content-range"], "bytes 0-1023/5000")
        self.assertEqual(response.headers["content-type"], "video/mp4")

    def test_nimegami_video_proxy_rejects_non_provider_hosts(self):
        with patch.object(web_server.requests, "get") as get:
            with self.assertRaises(HTTPException) as raised:
                web_server.nimegami_video_proxy(
                    make_request(), "https://attacker.example/private"
                )

        self.assertEqual(raised.exception.status_code, 400)
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
