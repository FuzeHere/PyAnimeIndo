import os
import sys
import webbrowser
import urllib.parse
import requests
import uvicorn
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Query, HTTPException, Body, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware


# Ensure workspace root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import API.otakudesu as otakudesu_api
import API.samehadaku as samehadaku_api
from API.extractor.krakenfiles import getStream
from utils.database import (
    loadSettings, saveSettings, loadData, saveData,
    saveDataAnime, getSavedAnime, deleteDataAnime,
    saveHistoryAnime, getHistoryAnime, getHistoryAnimeList
)

app = FastAPI(title="PyAnimeIndo Web API", version="1.2.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROVIDERS = {
    "samehadaku": {
        "id": "samehadaku",
        "name": "Samehadaku",
        "module": samehadaku_api,
        "host": "https://v2.samehadaku.how/"
    },
    "otakudesu": {
        "id": "otakudesu",
        "name": "Otakudesu",
        "module": otakudesu_api,
        "host": "https://otakudesu.blog/"
    }
}

def get_module(provider_id: Optional[str] = None):
    p = (provider_id or "samehadaku").lower()
    return PROVIDERS.get(p, PROVIDERS["samehadaku"])["module"]

def get_module_by_url(url: str):
    if not url:
        return get_module()
    u = url.lower()
    if "samehadaku" in u:
        return samehadaku_api
    elif "otakudesu" in u:
        return otakudesu_api
    return get_module()


@app.get("/api/providers")
def list_providers():
    return [
        {"id": k, "name": v["name"], "host": v["host"]}
        for k, v in PROVIDERS.items()
    ]


@app.get("/api/ongoing")
def get_ongoing(page: int = 1, provider: str = "samehadaku"):
    mod = get_module(provider)
    try:
        data = mod.getOngoing(page)
        return {"success": True, "page": page, "provider": provider, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@app.get("/api/schedule")
def get_schedule(provider: str = "samehadaku"):
    # Group schedules by day
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    schedule_data = {day: [] for day in days}

    try:
        if provider == "samehadaku":
            # Extract from samehadaku jadwal-rilis
            sched_map = samehadaku_api.getScheduleMap()
            ongoing = samehadaku_api.getOngoing(1)
            for item in ongoing:
                day = item.get("hari")
                if day in schedule_data and item not in schedule_data[day]:
                    schedule_data[day].append(item)
        else:
            ongoing = otakudesu_api.getOngoing(1)
            for item in ongoing:
                day = item.get("hari")
                if day in schedule_data:
                    schedule_data[day].append(item)

        return {"success": True, "provider": provider, "data": schedule_data}
    except Exception as e:
        return {"success": False, "error": str(e), "data": schedule_data}


@app.get("/api/genres")
def get_genres(provider: str = "samehadaku"):
    mod = get_module(provider)
    try:
        genres = mod.getGenreList()
        formatted = [{"name": k, "path": v} for k, v in genres.items()]
        return {"success": True, "provider": provider, "data": formatted}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@app.get("/api/genre-anime")
def get_genre_anime(path: str, provider: str = "samehadaku"):
    mod = get_module_by_url(path) if path.startswith("http") else get_module(provider)
    try:
        items = mod.getGenreAnime(path)
        return {"success": True, "path": path, "data": items}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@app.get("/api/search")
def search(q: str, provider: str = "samehadaku"):
    if not q or not q.strip():
        return {"success": True, "query": "", "data": []}
    mod = get_module(provider)
    try:
        results = mod.searchAnime(q.strip())
        return {"success": True, "query": q, "provider": provider, "data": results}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@app.get("/api/episodes")
def episodes(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")
    mod = get_module_by_url(url)
    try:
        data = mod.getEpisodes(url)
        return {"success": True, "url": url, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/download")
def download(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")
    mod = get_module_by_url(url)
    try:
        data = mod.getDownload(url)
        return {"success": True, "url": url, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/stream")
def stream(url: str = "", ep_url: str = "", quality: str = "720p"):
    if not url and not ep_url:
        raise HTTPException(status_code=400, detail="Missing url or ep_url")
    try:
        direct = getStream(url, ep_url=ep_url, quality=quality)
        return {
            "success": bool(direct),
            "stream_url": direct,
            "quality": quality,
            "is_direct": direct.endswith(".mp4") or "pixeldrain.com/api/file" in direct or direct.endswith(".mkv")
        }
    except Exception as e:
        return {"success": False, "error": str(e), "stream_url": ""}


@app.get("/api/video-proxy")
@app.head("/api/video-proxy")
def video_proxy(request: Request, url: str = Query(...)):
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }
    range_header = request.headers.get("range")
    if range_header:
        headers["Range"] = range_header

    try:
        upstream = requests.get(url, headers=headers, stream=True, timeout=12)
        resp_headers = {
            "Content-Type": upstream.headers.get("Content-Type", "video/mp4"),
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type",
        }
        for h in ["Content-Length", "Content-Range", "Last-Modified", "ETag"]:
            if h in upstream.headers:
                resp_headers[h] = upstream.headers[h]

        if request.method == "HEAD":
            return StreamingResponse(iter([]), status_code=upstream.status_code, headers=resp_headers)

        def iter_stream():
            try:
                for chunk in upstream.iter_content(chunk_size=128 * 1024):
                    if chunk:
                        yield chunk
            except Exception:
                pass

        return StreamingResponse(
            iter_stream(),
            status_code=upstream.status_code,
            headers=resp_headers
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")


@app.get("/api/stream-candidates")
def stream_candidates(ep_url: str = Query(...), quality: str = Query("720p")):
    if not ep_url:
        raise HTTPException(status_code=400, detail="Missing ep_url parameter")

    mod = get_module_by_url(ep_url)
    try:
        dl = mod.getDownload(ep_url)
    except Exception as e:
        return {"success": False, "error": str(e), "candidates": []}

    candidates = []
    seen_urls = set()
    std_qualities = ["1080p", "720p", "480p", "360p"]

    # Normalize requested quality
    q_target = quality.lower().replace("mp4", "").replace("mkv", "").strip()
    if not any(k in q_target for k in ["1080", "720", "480", "360"]):
        q_target = "720p"

    # Find matching key in dl
    target_dl = None
    for k in [q_target, f"Mp4 {q_target}", f"MP4 {q_target}", "720p", "480p", "360p", "1080p"]:
        if k in dl and dl[k]:
            target_dl = dl[k]
            break

    # 1. Primary Direct Stream for requested quality
    if target_dl:
        try:
            direct = getStream(target_dl, ep_url=ep_url, quality=q_target)
            if direct and direct.startswith("http"):
                enc_url = urllib.parse.quote(direct, safe="")
                proxy_url = f"/api/video-proxy?url={enc_url}"
                candidates.append({
                    "id": f"proxy_{q_target}",
                    "name": f"Server 1 (Stream Proxy {q_target.upper()})",
                    "type": "video",
                    "url": proxy_url,
                    "quality": q_target
                })
                candidates.append({
                    "id": f"direct_{q_target}",
                    "name": f"Server 2 (Direct MP4 {q_target.upper()})",
                    "type": "video",
                    "url": direct,
                    "quality": q_target
                })
                seen_urls.add(direct)
        except Exception as e:
            print("Direct stream candidate error:", e)

    # 2. Embed Player iframe (official CDN / Blogger / Desustream)
    embed = dl.get("embed")
    if not embed:
        # Fallback check directly from page
        try:
            from API.extractor.krakenfiles import extract_stream_from_ep
            embed_cand = extract_stream_from_ep(ep_url, q_target)
            if embed_cand and ("blogger" in embed_cand or "desustream" in embed_cand or "embed" in embed_cand):
                embed = embed_cand
        except Exception:
            pass

    if embed:
        candidates.append({
            "id": "embed_official",
            "name": "Server 3 (Embed Player Resmi / Multi-Quality)",
            "type": "iframe",
            "url": embed,
            "quality": q_target
        })

    # 3. Fallback alternative resolutions
    for alt_q in ["720p", "480p", "1080p", "360p"]:
        if alt_q != q_target and alt_q in dl:
            try:
                alt_dl = dl[alt_q]
                alt_direct = getStream(alt_dl, ep_url=ep_url, quality=alt_q)
                if alt_direct and alt_direct not in seen_urls and alt_direct.startswith("http"):
                    enc_url = urllib.parse.quote(alt_direct, safe="")
                    proxy_url = f"/api/video-proxy?url={enc_url}"
                    candidates.append({
                        "id": f"proxy_{alt_q}",
                        "name": f"Server Cadangan (Stream Proxy {alt_q})",
                        "type": "video",
                        "url": proxy_url,
                        "quality": alt_q
                    })
                    seen_urls.add(alt_direct)
            except Exception:
                pass

    # Extract all available resolution pills from dl
    available_qualities = []
    for q in std_qualities:
        if any(q in k.lower() for k in dl.keys()):
            available_qualities.append(q)
    if not available_qualities:
        available_qualities = ["720p", "480p", "360p"]

    return {
        "success": True,
        "requested_quality": q_target,
        "candidates": candidates,
        "available_qualities": available_qualities,
        "downloads": dl
    }



@app.get("/api/saved")
def get_saved():
    try:
        saved_dict = getSavedAnime()
        items = list(saved_dict.values())
        return {"success": True, "data": items}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@app.post("/api/saved")
def save_anime(item: Dict[str, Any] = Body(...)):
    url = item.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url in anime payload")
    try:
        saveDataAnime(url, str(item))
        return {"success": True, "message": "Saved successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/saved")
def delete_saved(url: str):
    try:
        deleteDataAnime(url)
        return {"success": True, "message": "Deleted successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/history")
def get_history():
    try:
        items = getHistoryAnimeList()
        return {"success": True, "data": items}
    except Exception as e:
        return {"success": False, "error": str(e), "data": []}


@app.post("/api/history")
def save_history(payload: Dict[str, Any] = Body(...)):
    anime_url = payload.get("url")
    ep_url = payload.get("ep_url", "")
    if not anime_url:
        raise HTTPException(status_code=400, detail="Missing url")
    try:
        history = getHistoryAnime(anime_url)
        if ep_url and ep_url not in history:
            history.append(ep_url)
        payload["history"] = history
        saveHistoryAnime(anime_url, str(payload))
        return {"success": True, "history": history}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Mount static web directory
WEB_DIR = os.path.join(BASE_DIR, "web")
if not os.path.exists(WEB_DIR):
    os.makedirs(WEB_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
def serve_home():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "PyAnimeIndo Web API running. Frontend index.html not yet built."}

@app.get("/{full_path:path}")
def serve_static(full_path: str):
    file_path = os.path.join(WEB_DIR, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Not Found")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting PyAnimeIndo Web Server on http://localhost:{port}")
    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception:
        pass
    uvicorn.run("web_server:app", host="0.0.0.0", port=port, reload=False)
