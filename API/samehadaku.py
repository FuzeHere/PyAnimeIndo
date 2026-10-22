import requests
import time
from bs4 import BeautifulSoup

host = "https://v2.samehadaku.how/"
headers = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

_schedule_cache = {
	"time": 0,
	"map": {}
}

def getScheduleMap():
	global _schedule_cache
	now = time.time()
	if _schedule_cache["map"] and (now - _schedule_cache["time"] < 600):
		return _schedule_cache["map"]

	try:
		r = requests.get(f"{host}jadwal-rilis/", headers=headers, timeout=8)
		soup = BeautifulSoup(r.text, "html.parser")
		day_map = {
			'monday': 'Senin',
			'tuesday': 'Selasa',
			'wednesday': 'Rabu',
			'thursday': 'Kamis',
			'friday': 'Jumat',
			'saturday': 'Sabtu',
			'sunday': 'Minggu'
		}
		sched = {}
		for en_day, id_day in day_map.items():
			container = soup.find('div', attrs={'x-show': lambda v: v and en_day in str(v)})
			if container:
				for card in container.find_all('div', class_='animepost'):
					a = card.find('a', href=True)
					title = a.get('title') or (card.find(class_='title').text if card.find(class_='title') else '')
					if a:
						sched[a['href'].strip('/')] = id_day
						if title:
							sched[title.strip().lower()] = id_day
		_schedule_cache["map"] = sched
		_schedule_cache["time"] = now
		return sched
	except Exception as e:
		print("getScheduleMap error:", e)
		return _schedule_cache.get("map", {})


def getOngoing(next_page=1):
	sched_map = getScheduleMap()
	url = f"{host}anime-terbaru/page/{next_page}/" if next_page > 1 else f"{host}anime-terbaru/"
	ret = []

	try:
		r = requests.get(url, headers=headers, timeout=10)
		soup = BeautifulSoup(r.text, "html.parser")
		for li in soup.select(".post-show ul li"):
			thumb_a = li.find("div", class_="thumb")
			img_tag = thumb_a.find("img") if thumb_a else None
			img = img_tag.get("src", "") if img_tag else ""
			
			h2 = li.find("h2", class_="entry-title")
			if not h2 or not h2.find("a"):
				continue
			title = h2.find("a").text.strip()
			anime_url = h2.find("a")["href"]
			
			eps = ""
			for span in li.find_all("span"):
				if "episode" in span.text.lower():
					eps = span.text.replace("Episode", "Eps").strip()
					break
			
			hari = sched_map.get(anime_url.strip("/"), "")
			if not hari:
				hari = sched_map.get(title.lower(), "")
			
			ret.append({"title": title, "eps": eps, "img": img, "hari": hari, "url": anime_url})
		
		if ret:
			return ret
	except Exception as e:
		print("getOngoing HTML error:", e)

	# Fallback to REST API: /wp-json/apk/latest?page={next_page}
	try:
		r = requests.get(f"{host}wp-json/apk/latest?page={next_page}", headers=headers, timeout=10)
		if r.status_code == 200:
			items = r.json()
			if isinstance(items, list):
				for item in items:
					title = item.get("series_title") or item.get("title", "")
					eps = f"Eps {item.get('episode', '')}".strip()
					img = item.get("thumb", "")
					url = item.get("url", "")
					hari = sched_map.get(title.lower(), "")
					ret.append({"title": title, "eps": eps, "img": img, "hari": hari, "url": url})
	except Exception as e:
		print("getOngoing REST fallback error:", e)

	return ret


def getGenreList():
	genres = {}
	try:
		r = requests.get(f"{host}daftar-anime-2/", headers=headers, timeout=10)
		soup = BeautifulSoup(r.text, "html.parser")
		for a in soup.find_all("a", href=True):
			if "/genre/" in a["href"]:
				name = a.text.strip()
				if name and name not in genres:
					genres[name] = a["href"]
		if genres:
			return genres
	except Exception as e:
		print("getGenreList error:", e)

	# Fallback to /wp-json/wp/v2/genre
	try:
		r = requests.get(f"{host}wp-json/wp/v2/genre?per_page=100", headers=headers, timeout=10)
		if r.status_code == 200:
			for g in r.json():
				name = g.get("name", "")
				link = g.get("link", "")
				if name and link:
					genres[name] = link
	except Exception as e:
		print("getGenreList fallback error:", e)

	return genres


def getGenreAnime(genre_path):
	url = genre_path if genre_path.startswith("http") else host + genre_path.lstrip("/")
	data = []
	try:
		r = requests.get(url, headers=headers, timeout=10)
		soup = BeautifulSoup(r.text, "html.parser")
		for a in soup.find_all("a", class_="series"):
			anime_url = a.get("href")
			title = a.get("title") or (a.find(class_="judul").text if a.find(class_="judul") else "")
			img_el = a.find("img")
			img = img_el.get("src", "") if img_el else ""
			rating_el = a.find("span", class_="rating")
			score = rating_el.text.strip().replace("★", "").strip() if rating_el else ""
			eps = f"★ {score}" if score else ""
			if anime_url and title:
				data.append({"title": title, "eps": eps, "img": img, "hari": "", "url": anime_url})
	except Exception as e:
		print("getGenreAnime error:", e)
	return data


def getEpisodes(url):
	try:
		r = requests.get(url, headers=headers, timeout=10)
		soup = BeautifulSoup(r.text, "html.parser")

		# If an episode URL is passed, resolve to the anime series URL
		if "/anime/" not in url:
			all_eps = soup.find("a", class_="all-eps-btn") or soup.select_one(".nvs.nvsc a")
			if not all_eps:
				for a in soup.find_all("a", href=True):
					if "/anime/" in a["href"] and any(k in a.text.lower() for k in ["all episode", "semua episode", "lainnya"]):
						all_eps = a
						break
			if all_eps and all_eps.get("href") and "/anime/" in all_eps["href"]:
				url = all_eps["href"]
				r = requests.get(url, headers=headers, timeout=10)
				soup = BeautifulSoup(r.text, "html.parser")

		# Title
		h1 = soup.find("h1", class_="page-title") or soup.find("h1")
		title = h1.text.strip().replace("Sub Indo", "").strip() if h1 else ""

		# Cover
		cover = ""
		for img_sel in [".content-thumb img", ".thumb img", "img.anmsa"]:
			img_el = soup.select_one(img_sel)
			if img_el and img_el.get("src"):
				cover = img_el["src"]
				break

		# Synopsis
		sinop = soup.find("div", class_="entry-content-single") or soup.find("div", class_="desc") or soup.find("div", class_="entry-content")
		sinopsis = "\n\n".join([p.text.strip() for p in sinop.find_all("p") if p.text.strip()]) if sinop else ""
		if not sinopsis and sinop:
			sinopsis = sinop.text.strip()

		# Info metadata
		info_map = {}
		for div in soup.find_all("div", class_=lambda c: c and "flex" in c and "justify-between" in c):
			spans = div.find_all("span")
			if len(spans) >= 2:
				k = spans[0].text.strip().lower()
				v = spans[1].text.strip()
				info_map[k] = v

		genres = [a.text.strip() for a in soup.find_all("a", href=lambda h: h and "/genre/" in h)]
		unique_genres = list(dict.fromkeys(genres))

		score = ""
		rating_el = soup.find(class_="rating") or soup.find(class_="score")
		if rating_el:
			score = rating_el.text.strip().replace("★", "").strip()

		studio = info_map.get("studio", "")
		status = info_map.get("status", "")
		durasi = info_map.get("duration", info_map.get("durasi", ""))
		genre_str = ", ".join(unique_genres[:5])

		info_lines = [
			f"Studio : {studio}",
			f"Genre : {genre_str}",
			f"Status : {status}",
			f"Durasi : {durasi}",
			f"Skor : {score}"
		]
		info = "\n".join(info_lines)

		# Episodes
		episodes = []
		seen = {}
		for a in soup.find_all("a", href=True):
			u = a["href"]
			if "episode" in u and u.startswith(host):
				txt = a.text.strip()
				if not txt:
					continue
				p = a.parent
				date_el = p.find_next_sibling("span") or (p.parent.find("span") if p.parent else None)
				date = date_el.text.strip() if date_el else ""
				if u not in seen:
					item = {"title": txt, "url": u, "date": date}
					seen[u] = item
					episodes.append(item)
				else:
					if len(txt) > len(seen[u]["title"]):
						seen[u]["title"] = txt

		# Recommendations
		recommend = []
		rec_seen = set()
		for art in soup.select(".recom-section article.animepost, .widgets li"):
			a = art.find("a", href=True)
			img = art.find("img")
			if a and a.get("href") and a["href"] not in rec_seen:
				rec_title = a.get("title") or (art.find(class_="title").text if art.find(class_="title") else "")
				rec_cover = img.get("src", "") if img else ""
				if rec_title:
					recommend.append({"title": rec_title, "url": a["href"], "cover": rec_cover})
					rec_seen.add(a["href"])

		return {
			"title": title,
			"cover": cover,
			"sinopsis": sinopsis,
			"info": info,
			"episodes": episodes,
			"recommend": recommend
		}
	except Exception as e:
		print("getEpisodes error:", e)
		return {"title": "", "cover": "", "sinopsis": "", "info": "", "episodes": [], "recommend": []}


def getDownload(url):
	try:
		r = requests.get(url, headers=headers, timeout=10)
		soup = BeautifulSoup(r.text, "html.parser")
		mp4_ret = {}
		mkv_ret = {}

		download_sections = soup.find_all("div", class_="download-eps")
		for sec in download_sections:
			fmt = sec.find("b")
			fmt_text = (fmt.text.strip().upper() if fmt else "")
			is_mp4 = "MP4" in fmt_text

			for li in sec.find_all("li"):
				quality_el = li.find("strong")
				quality = quality_el.text.strip() if quality_el else ""

				# Normalize resolution
				q_norm = ""
				q_lower = quality.lower()
				if "mp4hd" in q_lower or "720" in q_lower:
					q_norm = "720p"
				elif "fullhd" in q_lower or "1080" in q_lower:
					q_norm = "1080p"
				elif "480" in q_lower:
					q_norm = "480p"
				elif "360" in q_lower:
					q_norm = "360p"

				links = {}
				for a in li.find_all("a"):
					srv = a.text.strip()
					if a.get("href"):
						links[srv] = a["href"]

				chosen = ""
				for srv in ["Pixeldrain", "Krakenfiles", "Gofile", "Acefile", "Mediafire", "Filedon"]:
					for s_name, s_url in links.items():
						if srv.lower() in s_name.lower():
							chosen = s_url
							break
					if chosen:
						break
				if not chosen and links:
					chosen = list(links.values())[0]

				if chosen:
					label = f"{fmt_text} {quality}".strip()
					if is_mp4:
						if q_norm:
							mp4_ret[q_norm] = chosen
						mp4_ret[label] = chosen
					else:
						if q_norm:
							mkv_ret[q_norm] = chosen
						mkv_ret[label] = chosen

		# Merge: MP4 overrides MKV for web browser compatibility
		ret = {**mkv_ret, **mp4_ret}

		# Extract embed iframe (e.g. Blogger video or direct embed)
		embed = (soup.find("div", id="player-frame-wrapper") or
				 soup.find("div", class_="player-embed") or
				 soup.find("div", id="pembed") or
				 soup.find("div", class_="responsive-embed-stream"))
		if embed and embed.find("iframe"):
			iframe_src = embed.find("iframe").get("src", "")
			if iframe_src:
				ret["embed"] = iframe_src

		return ret
	except Exception as e:
		print("getDownload error:", e)
		return {}


def searchAnime(title):
	# 1. Try REST API with embed: /wp-json/wp/v2/anime?search={title}&_embed=1
	try:
		r = requests.get(f"{host}wp-json/wp/v2/anime?search={requests.utils.quote(title)}&_embed=1", headers=headers, timeout=8)
		if r.status_code == 200:
			data = r.json()
			if data and isinstance(data, list):
				ret = []
				for item in data:
					t = item.get("title", {}).get("rendered", "")
					u = item.get("link", "")
					img = ""
					embedded = item.get("_embedded", {})
					if "wp:featuredmedia" in embedded and embedded["wp:featuredmedia"]:
						img = embedded["wp:featuredmedia"][0].get("source_url", "")
					ret.append({"title": t, "img": img, "url": u})
				if ret:
					return ret
	except Exception as e:
		print("searchAnime REST error:", e)

	# 2. Fallback to HTML search: /?s={title}
	try:
		r = requests.get(f"{host}?s={requests.utils.quote(title)}", headers=headers, timeout=8)
		soup = BeautifulSoup(r.text, "html.parser")
		ret = []
		seen = set()
		for art in soup.find_all("article"):
			a = art.find("a", href=True)
			if not a:
				continue
			u = a["href"]
			if u in seen:
				continue
			img_el = art.find("img")
			img = img_el.get("src", "") if img_el else ""
			title_el = art.find(["h2", "h3"]) or a
			t = title_el.text.strip()
			ret.append({"title": t, "img": img, "url": u})
			seen.add(u)
		return ret
	except Exception as e:
		print("searchAnime HTML error:", e)
		return []
