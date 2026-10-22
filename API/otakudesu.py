import requests
from bs4 import BeautifulSoup
from API.extractor.desudrive import desudrive

host = "https://otakudesu.blog/"
headers = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def getOngoing(next_page=1):
	data = BeautifulSoup(requests.get(host + f"ongoing-anime/page/{next_page}/", headers=headers).text, features="html.parser")
	ret = []

	animelists = data.find('div', {'class': 'venz'})
	if not animelists:
		return ret
	for anime in animelists.findAll("li"):
		title = anime.find('h2', {"class": "jdlflm"}).text
		eps = anime.find('div', {"class": "epz"}).text
		img = anime.find('img')['src']
		hari = anime.find('div', {"class": "epztipe"}).text.strip()
		url = anime.find('a')['href']
		ret.append({"title": title, "eps": eps, "img": img, "hari": hari, "url": url})

	return ret


def getGenreList():
	r = BeautifulSoup(requests.get(host + "genre-list/", headers=headers).content, features="html.parser")
	genres = {}
	genres_ul = r.find('ul', {"class": "genres"})
	if not genres_ul:
		return genres
	for data in genres_ul.li.findAll("a"):
		genres[data.text] = data['href']
	return genres


def getGenreAnime(genre_path):
	url = genre_path if genre_path.startswith("http") else host + genre_path
	r = BeautifulSoup(requests.get(url, headers=headers).content, features="html.parser")
	data = []
	for anime in r.findAll('div', {"class": "col-anime"}):
		title = anime.find('div', {"class": "col-anime-title"}).text
		url = anime.find('div', {"class": "col-anime-title"}).a['href']
		eps = anime.find('div', {"class": "col-anime-eps"}).text
		img = anime.find('div', {"class": "col-anime-cover"}).img['src']
		data.append({"title": title, "eps": eps, "img": img, "hari": "", "url": url})
	return data


def getEpisodes(url):
	data = BeautifulSoup(requests.get(url, headers=headers).text, features="html.parser")
	jdlrx = data.find('div', {"class": "jdlrx"})
	title = jdlrx.text if jdlrx else ""
	cover_img = data.find('img', {'class': 'attachment-post-thumbnail'})
	cover = cover_img['src'] if cover_img else ""
	sinopc = data.find('div', {'class': 'sinopc'})
	sinopsis = "\n\n".join([x.text for x in sinopc.findAll('p')]) if sinopc else ""
	infozingle = data.find("div", {"class": "infozingle"})
	info = "\n".join([x.text for x in infozingle.findAll('p')]) if infozingle else ""
	
	ret = {'title': title, 'cover': cover, 'sinopsis': sinopsis, "info": info, "episodes": []}

	epslists = data.findAll('div', {'class': 'episodelist'})
	for chlists in epslists:
		for eps in chlists.findAll("li"):
			a_tag = eps.find('a')
			if not a_tag:
				continue
			title = a_tag.text
			url = a_tag['href']
			zeebr = eps.find('span', {"class": "zeebr"})
			date = zeebr.text if zeebr else ""
			ret['episodes'].append({"title": title, "url": url, "date": date})

	ret['recommend'] = []
	rec_div = data.find("div", {"class": "isi-recommend-anime-series"})
	if rec_div:
		recommendationData = rec_div.findAll("div", {"class": "isi-konten"})
		for reclist in recommendationData:
			title = reclist.span.text if reclist.span else ""
			url = reclist.a['href'] if reclist.a else ""
			cover = reclist.img['src'] if reclist.img else ""
			ret['recommend'].append({"title": title, "url": url, "cover": cover})

	return ret


def getDownload(url):
	data = BeautifulSoup(requests.get(url, headers=headers).text, features="html.parser")
	ret = {}
	mp4_ret = {}
	mkv_ret = {}

	download = data.find('div', {'class': 'download'})
	if download:
		for dlurl in download.findAll("li"):
			filetype = dlurl.strong.text if dlurl.strong else ""
			fileurl = ""
			for urlname in dlurl.findAll("a"):
				text = urlname.text.lower()
				if "pdrain" in text or "pixeldrain" in text:
					fileurl = urlname['href']
					break
				elif "kfiles" in text or "kraken" in text:
					fileurl = urlname['href']
			if not fileurl and dlurl.a:
				fileurl = dlurl.a['href']
			if "desudrive" in fileurl:
				fileurl = desudrive(fileurl)

			if fileurl:
				ft_lower = filetype.lower()
				is_mp4 = "mp4" in ft_lower
				q_norm = ""
				if "1080" in ft_lower:
					q_norm = "1080p"
				elif "720" in ft_lower:
					q_norm = "720p"
				elif "480" in ft_lower:
					q_norm = "480p"
				elif "360" in ft_lower:
					q_norm = "360p"

				if is_mp4:
					if q_norm:
						mp4_ret[q_norm] = fileurl
					mp4_ret[filetype] = fileurl
				else:
					if q_norm:
						mkv_ret[q_norm] = fileurl
					mkv_ret[filetype] = fileurl
	elif batchlink := data.find('div', {'class': 'batchlink'}):
		for dlurl in batchlink.findAll("li"):
			filetype = dlurl.strong.text if dlurl.strong else ""
			fileurl = ""
			for urlname in dlurl.findAll("a"):
				text = urlname.text.lower()
				if "pdrain" in text or "pixeldrain" in text:
					fileurl = urlname['href']
					break
				elif "kfiles" in text or "kraken" in text:
					fileurl = urlname['href']
			if not fileurl and dlurl.a:
				fileurl = dlurl.a['href']
			if "desudrive" in fileurl:
				fileurl = desudrive(fileurl)
			if fileurl:
				ret[filetype] = fileurl

	# Merge: MP4 overrides MKV
	ret = {**mkv_ret, **mp4_ret, **ret}

	# Extract embed iframe
	embed = (data.find('div', {'class': 'responsive-embed-stream'}) or
			 data.find('div', {'class': 'player-embed'}))
	if embed and embed.find('iframe'):
		ifr_src = embed.find('iframe').get('src', '')
		if ifr_src:
			ret['embed'] = ifr_src

	return ret



def searchAnime(title):
	a = BeautifulSoup(requests.get(host + "/?s={}&post_type=anime".format(title), headers=headers).content, features="html.parser")
	chivsrc = a.find("ul", {"class": "chivsrc"})
	data = []
	if not chivsrc:
		return data
	s = chivsrc.findAll("li")
	for x in s:
		img_src = x.img['src'] if x.img else ""
		title_text = x.h2.text if x.h2 else ""
		url_href = x.h2.a['href'] if (x.h2 and x.h2.a) else ""
		data.append({"title": title_text, "img": img_src, "url": url_href})
	
	return data

