"""Auto-post finished videos to YouTube (Malaak Video Maker).

Token lives only in the Colab session (YT_TOKEN_FILE, default /content/yt_token.json)
or in her Google Drive if she opted in. Nothing secret is stored in the repo.
"""
import json, os, re, time
import requests

TOKEN_FILE = os.environ.get("YT_TOKEN_FILE", "/content/yt_token.json")
LOG_FILE = os.environ.get("YT_UPLOAD_LOG", "/tmp/yt_uploaded.json")
SCOPE = "https://www.googleapis.com/auth/youtube"  # allowed for device-code flow, covers uploads
SAFETY_RULES = (
    "Only use well-documented, publicly reported facts from reputable news or official sources. "
    "Do not name private individuals or minors; never make unproven accusations; say 'reportedly' "
    "or 'according to reports' for anything not legally established. Be respectful to victims. "
    "No gore. End with the main source name."
)


def enabled() -> bool:
    return os.path.isfile(TOKEN_FILE)


def _load():
    with open(TOKEN_FILE) as f:
        return json.load(f)


def access_token() -> str:
    t = _load()
    if t.get("expires_at", 0) - 60 > time.time():
        return t["access_token"]
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": t["client_id"], "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    d = r.json()
    t["access_token"] = d["access_token"]
    t["expires_at"] = time.time() + int(d.get("expires_in", 3600))
    with open(TOKEN_FILE, "w") as f:
        json.dump(t, f)
    os.chmod(TOKEN_FILE, 0o600)
    return t["access_token"]


def device_login(client_id: str, client_secret: str, show=print) -> dict:
    """Google device-code flow: she opens google.com/device on her phone and types a code."""
    r = requests.post("https://oauth2.googleapis.com/device/code",
                      data={"client_id": client_id, "scope": SCOPE}, timeout=30)
    r.raise_for_status()
    d = r.json()
    show(d["verification_url"], d["user_code"])
    interval = int(d.get("interval", 5))
    deadline = time.time() + int(d.get("expires_in", 1800))
    while time.time() < deadline:
        time.sleep(interval)
        p = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id, "client_secret": client_secret, "device_code": d["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}, timeout=30).json()
        if "access_token" in p:
            tok = {"client_id": client_id, "client_secret": client_secret,
                   "refresh_token": p["refresh_token"], "access_token": p["access_token"],
                   "expires_at": time.time() + int(p.get("expires_in", 3600))}
            os.makedirs(os.path.dirname(TOKEN_FILE) or ".", exist_ok=True)
            with open(TOKEN_FILE, "w") as f:
                json.dump(tok, f)
            os.chmod(TOKEN_FILE, 0o600)
            return tok
        err = p.get("error")
        if err == "slow_down":
            interval += 5
        elif err != "authorization_pending":
            raise RuntimeError(f"YouTube sign-in failed: {err} {p.get('error_description', '')}")
    raise RuntimeError("YouTube sign-in timed out. Run the cell again.")


def gemini(prompt: str) -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return ""
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                      params={"key": key}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=90)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def build_metadata(subject: str, script: str) -> dict:
    subject = (subject or "").strip() or (script or "").strip()[:80] or "Short video"
    meta = {}
    try:
        txt = gemini(
            "Write YouTube Shorts metadata as JSON with keys title (max 90 chars, no clickbait lies), "
            "description (2-3 sentences, use 'reportedly' for unproven claims, then a line 'Source: <main "
            "public source>'), tags (list of 8 short tags). " + SAFETY_RULES +
            f"\nTopic: {subject}\nScript: {script[:3000]}\nReturn only JSON.")
        m = re.search(r"\{.*\}", txt or "", re.S)
        if m:
            meta = json.loads(m.group(0))
    except Exception:
        meta = {}
    title = str(meta.get("title") or subject)[:90]
    desc = str(meta.get("description") or (script or subject)[:600])
    tags = [str(t)[:30] for t in (meta.get("tags") or re.findall(r"[A-Za-z]{4,}", subject)[:8])]
    if "#Shorts" not in title:
        title = (title[:90] + " #Shorts")[:100]
    desc = (desc + "\n\n#Shorts\nMade by Fathimath Malaak Jaufar")[:4900]
    return {"title": title, "description": desc, "tags": (tags + ["Shorts"])[:15]}


def _log():
    try:
        with open(LOG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def already_uploaded(path: str):
    return _log().get(os.path.abspath(path))


def upload(path: str, subject: str = "", script: str = "", privacy: str = "public") -> str:
    """Upload once per file; returns the YouTube link."""
    done = already_uploaded(path)
    if done:
        return done
    meta = build_metadata(subject, script)
    body = {"snippet": {"title": meta["title"], "description": meta["description"],
                        "tags": meta["tags"], "categoryId": "24"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    size = os.path.getsize(path)
    h = {"Authorization": "Bearer " + access_token()}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos",
                      params={"uploadType": "resumable", "part": "snippet,status"},
                      headers={**h, "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                      json=body, timeout=60)
    r.raise_for_status()
    with open(path, "rb") as f:
        u = requests.put(r.headers["Location"], data=f,
                         headers={**h, "Content-Type": "video/mp4"}, timeout=1800)
    u.raise_for_status()
    vid = u.json()["id"]
    url = f"https://youtube.com/shorts/{vid}"
    log = _log(); log[os.path.abspath(path)] = url
    with open(LOG_FILE, "w") as f:
        json.dump(log, f)
    return url
