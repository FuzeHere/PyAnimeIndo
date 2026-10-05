import requests
import re
import json
import base64
from bs4 import BeautifulSoup

host = "https://krakenfiles.com"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def getId(url):
	if "view/" in url:
		return url.split("view/")[1].split("/file")[0]
	return url

def extract_direct_from_iframe(iframe_url):
	try:
		r = requests.get(iframe_url, headers=headers, timeout=8)
		if "desustream" in iframe_url:
			m = re.search(r'const\s+videoURL\s*=\s*["\']([^"\']+)["\']', r.text)
			if m:
				return m.group(1)
			m = re.search(r'file:\s*["\']([^"\']+\.mp4)["\']', r.text)
			if m:
				return m.group(1)
			m = re.findall(r'https?://[^\s"\'<>]+\.mp4', r.text)
			if m:
				return m[0]
	except Exception as e:
		print("extract_direct_from_iframe error:", e)
	return ""

def extract_stream_from_ep(ep_url, quality="720p"):
	if not ep_url:
		return ""
	try:
		r = requests.get(ep_url, headers=headers, timeout=10)
		soup = BeautifulSoup(r.text, "html.parser")

		# 1. Try mirrorstream via admin-ajax.php
		mirror = soup.find("div", class_="mirrorstream")
		if mirror:
			action_stream = None
			action_nonce = None
			for s in soup.find_all("script"):
				if "admin-ajax.php" in s.text:
					actions = re.findall(r'action:\s*["\']([a-f0-9]{32})["\']', s.text)
					if len(actions) >= 2:
						action_stream = actions[0]
						action_nonce = actions[1]
					elif len(actions) == 1:
						action_nonce = actions[0]

			if action_nonce and action_stream:
				try:
					r_n = requests.post("https://otakudesu.blog/wp-admin/admin-ajax.php",
										data={"action": action_nonce},
										headers={**headers, "Referer": ep_url, "X-Requested-With": "XMLHttpRequest"},
										timeout=5)
					nonce = r_n.json().get("data")
					if nonce:
						q_clean = quality.lower().replace("mp4", "").replace("mkv", "").strip() if quality else "720p"
						if "1080" in q_clean or "720" in q_clean:
							pref_order = ["720p", "480p", "360p"]
						elif "480" in q_clean:
							pref_order = ["480p", "720p", "360p"]
						elif "360" in q_clean:
							pref_order = ["360p", "480p", "720p"]
						else:
							pref_order = ["720p", "480p", "360p"]

						for pref in pref_order:
							ul = mirror.find("ul", class_=lambda c: c and f"m{pref}" in "".join(c).lower())
							if not ul:
								continue
							for a in ul.find_all("a"):
								s_name = a.text.strip().lower()
								if "odcdn" in s_name or "odstream" in s_name or "desu" in s_name:
									raw_c = a.get("data-content")
									if raw_c:
										e = json.loads(base64.b64decode(raw_c).decode())
										post_data = {**e, "nonce": nonce, "action": action_stream}
										r_s = requests.post("https://otakudesu.blog/wp-admin/admin-ajax.php",
															data=post_data,
															headers={**headers, "Referer": ep_url, "X-Requested-With": "XMLHttpRequest"},
															timeout=5)
										b64_html = r_s.json().get("data")
										if b64_html:
											embed_html = base64.b64decode(b64_html).decode()
											ifr_m = re.search(r'src=["\']([^"\']+)["\']', embed_html)
											if ifr_m:
												direct = extract_direct_from_iframe(ifr_m.group(1))
												if direct:
													return direct
				except Exception as ajax_err:
					print("Mirror AJAX error:", ajax_err)

		# 2. Fallback to default responsive-embed-stream iframe
		embed = soup.find("div", class_="responsive-embed-stream")
		if embed and embed.find("iframe"):
			direct = extract_direct_from_iframe(embed.find("iframe")["src"])
			if direct:
				return direct
	except Exception as e:
		print("extract_stream_from_ep error:", e)
	return ""

def getStream(url, ep_url="", quality=""):
	if not url and not ep_url:
		return ""
	try:
		if url and url.startswith("http"):
			r = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
			final_url = r.url

			if "pixeldrain.com" in final_url or "pdrain" in final_url:
				file_id = final_url.split('/')[-1]
				p_url = f"https://pixeldrain.com/api/file/{file_id}"
				try:
					chk = requests.head(p_url, headers=headers, timeout=4)
					if chk.status_code in (200, 206):
						return p_url
					else:
						print(f"Pixeldrain link unavailable ({chk.status_code}), falling back...")
				except Exception:
					pass
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
			elif final_url.endswith(".mp4") or final_url.endswith(".mkv"):
				return final_url

		# Fallback to episode stream if url resolution failed or was dead
		if ep_url:
			print("Falling back to episode stream extraction:", ep_url)
			stream_ep = extract_stream_from_ep(ep_url, quality)
			if stream_ep:
				return stream_ep

		return url
	except Exception as e:
		print("getStream error:", e)
		if ep_url:
			return extract_stream_from_ep(ep_url, quality)
		return url