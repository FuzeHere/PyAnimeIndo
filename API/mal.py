"""MyAnimeList adapter to enrich anime details and score from myanimelist.net."""

import re
import time
from typing import Dict, Any, Optional
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Cache for MAL queries: { cleaned_title: { "timestamp": float, "data": dict } }
_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 86400  # 24 hours


def clean_title(title: str) -> str:
    """Clean anime title by stripping Indonesian subtitles, tags, episode counters, etc."""
    if not title:
        return ""
    t = str(title)
    # Remove bracketed content like (End), (TV), [Batch], etc.
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"\[.*?\]", "", t)
    # Remove subtitle tags and status keywords
    t = re.sub(r"(?i)\b(sub\s*indo|subtitle\s*indonesia|sub\s*ind|batch|lengkap|end|tamat|bd|bluray)\b", "", t)
    # Remove episode markers like "Episode 12", "Eps 01"
    t = re.sub(r"(?i)\bepisode\s*\d+.*", "", t)
    t = re.sub(r"(?i)\beps\.?\s*\d+.*", "", t)
    # Normalize whitespaces and dashes
    t = re.sub(r"\s+", " ", t).strip(" -:—_")
    return t


def get_mal_info(title: str, fetch_full: bool = True) -> Dict[str, Any]:
    """Search myanimelist.net for an anime title and return score and detailed information."""
    cleaned = clean_title(title)
    if not cleaned:
        return {"found": False, "query": title}

    cache_key = cleaned.lower()
    now = time.time()
    if cache_key in _CACHE:
        cached = _CACHE[cache_key]
        if now - cached.get("timestamp", 0) < CACHE_TTL:
            return cached["data"]

    result: Dict[str, Any] = {
        "found": False,
        "query": title,
        "cleaned_query": cleaned,
        "title": "",
        "english_title": "",
        "japanese_title": "",
        "score": None,
        "scored_by": None,
        "ranked": None,
        "popularity": None,
        "members": None,
        "type": "",
        "status": "",
        "episodes": None,
        "aired": "",
        "studios": [],
        "source": "",
        "duration": "",
        "rating": "",
        "genres": [],
        "synopsis": "",
        "mal_url": "",
        "image": "",
    }

    try:
        # Step 1: Use MAL prefix JSON API (fast & returns top candidates)
        resp = requests.get(
            "https://myanimelist.net/search/prefix.json",
            params={"type": "anime", "keyword": cleaned},
            headers=HEADERS,
            timeout=8,
        )

        mal_item = None
        if resp.status_code == 200:
            payload = resp.json()
            for cat in payload.get("categories", []):
                if cat.get("type") == "anime":
                    items = cat.get("items", [])
                    if items:
                        mal_item = items[0]
                        break

        # Fallback to HTML search page if prefix API found nothing
        if not mal_item:
            search_resp = requests.get(
                "https://myanimelist.net/anime.php",
                params={"q": cleaned},
                headers=HEADERS,
                timeout=8,
            )
            if search_resp.status_code == 200:
                soup = BeautifulSoup(search_resp.text, "html.parser")
                for tr in soup.select("table tr"):
                    tds = tr.find_all("td")
                    if len(tds) >= 5:
                        a_elem = tr.find("a", href=re.compile(r"^https://myanimelist\.net/anime/\d+/"))
                        if a_elem and not a_elem["href"].endswith(("/pics", "/reviews", "/userrecs", "/stats")):
                            raw_score = tds[4].get_text(strip=True)
                            mal_item = {
                                "name": a_elem.get_text(strip=True),
                                "url": a_elem["href"],
                                "image_url": "",
                                "payload": {
                                    "media_type": tds[2].get_text(strip=True),
                                    "score": raw_score if raw_score not in ("N/A", "-") else None,
                                },
                            }
                            break

        if not mal_item:
            _CACHE[cache_key] = {"timestamp": now, "data": result}
            return result

        # Basic metadata from search result
        result["found"] = True
        result["title"] = mal_item.get("name", "")
        result["mal_url"] = mal_item.get("url", "")
        result["image"] = mal_item.get("image_url", "")
        p = mal_item.get("payload", {})
        result["type"] = p.get("media_type", "")
        result["status"] = p.get("status", "")
        result["aired"] = p.get("aired", "")
        raw_sc = str(p.get("score", "")).strip()
        if raw_sc and raw_sc not in ("N/A", "-"):
            try:
                result["score"] = float(raw_sc)
            except ValueError:
                result["score"] = raw_sc

        # Step 2: Fetch detail page on myanimelist.net for complete metadata
        if fetch_full and result["mal_url"]:
            try:
                detail_resp = requests.get(result["mal_url"], headers=HEADERS, timeout=8)
                if detail_resp.status_code == 200:
                    d_soup = BeautifulSoup(detail_resp.text, "html.parser")

                    # Score
                    score_el = d_soup.select_one(".score-label")
                    if score_el and score_el.text.strip() not in ("N/A", ""):
                        try:
                            result["score"] = float(score_el.text.strip())
                        except ValueError:
                            pass

                    # Ranked, Popularity, Members
                    ranked_el = d_soup.select_one(".ranked strong")
                    if ranked_el:
                        result["ranked"] = ranked_el.get_text(strip=True)
                    pop_el = d_soup.select_one(".popularity strong")
                    if pop_el:
                        result["popularity"] = pop_el.get_text(strip=True)
                    members_el = d_soup.select_one(".members strong")
                    if members_el:
                        result["members"] = members_el.get_text(strip=True)

                    # Genres
                    genres = [g.get_text(strip=True) for g in d_soup.find_all("span", itemprop="genre")]
                    if genres:
                        result["genres"] = genres

                    # Synopsis
                    syn_el = d_soup.find("p", itemprop="description")
                    if syn_el:
                        result["synopsis"] = syn_el.get_text(" ", strip=True)

                    # Cover image
                    cover_el = d_soup.select_one("img[itemprop='image']") or d_soup.select_one(".leftside img")
                    if cover_el and cover_el.get("data-src"):
                        result["image"] = cover_el.get("data-src")
                    elif cover_el and cover_el.get("src"):
                        result["image"] = cover_el.get("src")

                    # Sidebar key-value pairs
                    leftside = d_soup.find("div", class_="leftside")
                    if leftside:
                        for pad in leftside.find_all("div", class_="spaceit_pad"):
                            text = pad.get_text(" ", strip=True)
                            if ":" in text:
                                k, v = text.split(":", 1)
                                k = k.strip().lower()
                                v = v.strip()
                                if k == "japanese":
                                    result["japanese_title"] = v
                                elif k == "english":
                                    result["english_title"] = v
                                elif k == "episodes":
                                    result["episodes"] = v
                                elif k == "status" and not result["status"]:
                                    result["status"] = v
                                elif k == "aired" and not result["aired"]:
                                    result["aired"] = v
                                elif k == "studios":
                                    studios = [a.get_text(strip=True) for a in pad.find_all("a")]
                                    result["studios"] = studios or ([v] if v and v != "None found, add some" else [])
                                elif k == "source":
                                    result["source"] = v
                                elif k == "duration":
                                    result["duration"] = v
                                elif k == "rating":
                                    result["rating"] = v
            except Exception as e:
                # Do not fail if detail scraping times out, prefix data is already preserved
                pass

        _CACHE[cache_key] = {"timestamp": now, "data": result}
        return result

    except Exception:
        return result

