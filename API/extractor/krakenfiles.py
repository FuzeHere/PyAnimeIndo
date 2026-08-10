import requests
from bs4 import BeautifulSoup

host = "https://krakenfiles.com"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def getId(url):
	if "view/" in url:
		return url.split("view/")[1].split("/file")[0]
	return url

def getStream(url):
	if not url:
		return ""
	try:
		r = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
		final_url = r.url

		if "pixeldrain.com" in final_url or "pdrain" in final_url:
			file_id = final_url.split('/')[-1]
			return f"https://pixeldrain.com/api/file/{file_id}"
		elif "krakenfiles.com" in final_url:
			file_id = getId(final_url)
			r_k = requests.get(f"{host}/embed-video/{file_id}", headers=headers, timeout=10)
			soup_k = BeautifulSoup(r_k.content, "html.parser")
			source = soup_k.find("source")
			if source and source.get("src"):
				src = source.get("src")
				return "https:" + src if src.startswith("//") else src
		elif "vikingfile" in final_url or "vik1ngfile" in final_url:
			soup = BeautifulSoup(r.text, 'html.parser')
			source = soup.find('source')
			if source and source.get('src'):
				return source.get('src')
		return final_url
	except Exception as e:
		print("getStream error:", e)
		return url