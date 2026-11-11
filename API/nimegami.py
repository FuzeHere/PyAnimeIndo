"""Nimegami catalog and player adapter for the PyAnimeIndo web API."""

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

host = "https://nimegami.id/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/json",
}


def _site_url(url):
    resolved = urljoin(host, str(url or ""))
    parsed = urlsplit(resolved)
    if parsed.scheme != "https" or parsed.hostname != "nimegami.id" or parsed.port not in (None, 443):
        raise ValueError("URL harus berasal dari https://nimegami.id/")
    return resolved


def _soup(url):
    url = _site_url(url)
    response = requests.get(url, headers=headers, timeout=12)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _image(card):
    image = card.select_one("img.poster-image, img")
    if not image:
        return ""
    src = image.get("src") or image.get("data-src") or ""
    if not src and image.get("srcset"):
        src = image["srcset"].split(",")[0].strip().split(" ")[0]
    return urljoin(host, src)


def _cards(soup):
    result = []
    seen = set()
    for card in soup.select("article.anime-card"):
        link = card.select_one("a.poster-link[href]") or card.select_one("a[href]")
        if not link:
            continue
        anime_url = urljoin(host, link["href"])
        if anime_url in seen:
            continue
        seen.add(anime_url)
        title = (link.get("aria-label", "").replace("Lihat ", "").strip()
                 or (card.select_one(".card-title") or link).get_text(" ", strip=True)
                 or (card.select_one("img") or {}).get("alt", ""))
        episode = card.select_one(".card-last-episode strong")
        result.append({
            "title": title,
            "eps": f"Episode {episode.get_text(strip=True)}" if episode and episode.get_text(strip=True) != "—" else "",
            "img": _image(card),
            "hari": "",
            "url": anime_url,
        })
    return result


def _stream_routes(soup):
    # Episode and quality URLs are included in Next.js server data as playUrl values.
    raw = str(soup).replace(r'\"', '"')
    routes = []
    for match in re.finditer(r'"playUrl":"([^"]*/streaming/(\d+)/(360|480|720|1080)p/[^"\\]+)', raw):
        routes.append((match.group(2), f"{match.group(3)}p", urljoin(host, match.group(1))))
    # Also accept regular anchors used for the currently selected player.
    for link in soup.select("a[href]"):
        match = re.search(r"/streaming/(\d+)/(360|480|720|1080)p/[^/?#]+", link.get("href", ""))
        if match:
            routes.append((match.group(1), f"{match.group(2)}p", urljoin(host, link["href"])))
    return routes


def getOngoing(next_page=1):
    page = max(1, int(next_page or 1))
    url = urljoin(host, "anime/")
    if page > 1:
        url = f"{url}?page={page}"
    return _cards(_soup(url))


def getGenreList():
    soup = _soup(urljoin(host, "genre/"))
    genres = {}
    for link in soup.select('a.genre-tile[href], a[href*="/category/"]'):
        heading = link.select_one("h2")
        name = (heading or link).get_text(" ", strip=True).lstrip("#").strip()
        href = urljoin(host, link.get("href", ""))
        if name and "/category/" in href:
            genres.setdefault(name, href)
    return genres


def getGenreAnime(genre_path):
    url = _site_url(genre_path)
    return _cards(_soup(url))


def searchAnime(title):
    response = requests.get(
        urljoin(host, "api/anime-search/"),
        params={"q": title.strip()}, headers=headers, timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    results = []
    for item in payload.get("suggestions", []):
        slug = item.get("slug")
        if not slug:
            continue
        results.append({
            "title": item.get("title", ""),
            "img": urljoin(host, item.get("poster", "")),
            "url": urljoin(host, slug.strip("/") + "/"),
            "eps": item.get("format", ""),
            "hari": str(item.get("year", "")),
        })
    return results


def getEpisodes(url):
    soup = _soup(url)
    heading = soup.select_one("h1")
    title = heading.get_text(" ", strip=True) if heading else ""
    for row in soup.select(".anime-info-summary > div"):
        key, value = row.select_one("dt"), row.select_one("dd")
        if key and value and key.get_text(" ", strip=True).lower() == "judul":
            title = value.get_text(" ", strip=True)
            break
    poster = soup.select_one('meta[property="og:image"]')
    cover = urljoin(host, poster.get("content", "")) if poster else _image(soup)
    description = soup.select_one('meta[name="description"]')
    synopsis = description.get("content", "") if description else ""

    info = []
    for row in soup.select(".anime-info-summary > div, .anime-info-more dl div"):
        key, value = row.select_one("dt"), row.select_one("dd")
        if key and value:
            info.append(f"{key.get_text(' ', strip=True)}: {value.get_text(' ', strip=True)}")

    episode_numbers = {int(ep) for ep, _, _ in _stream_routes(soup)}
    for stage in soup.select('.player-stage[id^="episode_"]'):
        match = re.search(r"episode_(\d+)", stage.get("id", ""))
        if match:
            episode_numbers.add(int(match.group(1)))
    episodes = []
    parsed_url = urlsplit(_site_url(url).split("#", 1)[0])
    base_path = parsed_url.path.rstrip("/") + "/"
    episode_base_url = urlunsplit(parsed_url._replace(path=base_path))
    for number in sorted(episode_numbers):
        episodes.append({
            "title": f"Episode {number}",
            "url": f"{episode_base_url}#episode_{number}",
            "date": "",
        })
    if not episodes:
        for link in soup.select("#stream-episode-list a[href^='#episode_']"):
            match = re.search(r"episode_(\d+)", link.get("href", ""))
            if match:
                number = match.group(1)
                episodes.append({"title": f"Episode {number}", "url": f"{episode_base_url}#episode_{number}", "date": ""})

    recommendations = []
    for card in soup.select("article.anime-card"):
        item = _cards(BeautifulSoup(str(card), "html.parser"))
        if item:
            recommendations.append({"title": item[0]["title"], "url": item[0]["url"], "cover": item[0]["img"]})

    return {
        "title": title,
        "cover": cover,
        "sinopsis": synopsis,
        "info": "\n".join(info),
        "episodes": episodes,
        "recommend": recommendations,
    }


def getDownload(url):
    page_url = url.split("#", 1)[0]
    episode_match = re.search(r"episode_(\d+)", url)
    episode_num = episode_match.group(1) if episode_match else "1"
    soup = _soup(page_url)
    stage = soup.find(id=f"episode_{episode_num}")

    streams = {}
    quality_links = stage.select("[data-quality-url]") if stage else []
    for link in quality_links:
        quality = link.get("data-quality", "")
        if not quality:
            quality_match = re.search(r"(1080|720|480|360)p", link.get_text(" ", strip=True), re.I)
            quality = f"{quality_match.group(1)}p" if quality_match else ""
        stream_url = link.get("data-quality-url")
        if quality and stream_url:
            streams[quality.lower()] = urljoin(host, stream_url)

    # Anime detail pages expose a streaming page link for each episode and resolution.
    for number, quality, stream_url in _stream_routes(soup):
        if number == episode_num:
            streams[quality] = stream_url

    # On Nimegami the player URL itself serves the selected quality.
    if streams:
        streams["embed"] = streams.get("720p") or next(iter(streams.values()))
    return streams
