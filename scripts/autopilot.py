"""Autopilot: make and auto-post N videos in a row (run from the Colab notebook)."""
import json, os, random, re, subprocess, sys, uuid
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root); os.chdir(root)
from app.models.schema import VideoParams, VideoAspect
from app.services import task as tm, llm
from app.services import youtube_upload as yt

NICHE = ["famous true crime cases from around the world", "Maldives true crime and court cases reported in the news",
         "real-life survival stories", "unsolved historical mysteries", "strange true stories",
         "amazing archaeological discoveries", "real ghost-story legends with documented history"]


def pick_topics(n, used):
    try:
        txt = yt.gemini(
            f"Give {n} different YouTube Shorts topics, one per line, no numbering. Pick randomly across: "
            + "; ".join(NICHE) + ". Each must be a well-documented, publicly reported case or event "
            "(famous cases, court-decided cases, historical events). No private individuals, no minors, "
            "no unproven accusations. Avoid these: " + "; ".join(used[-30:]))
        topics = [re.sub(r"^[\s\-\*\d\.]+", "", t).strip() for t in txt.splitlines() if t.strip()]
        if topics:
            return topics[:n]
    except Exception as ex:
        print("Gemini topic pick failed:", ex)
    return [random.choice(["The Mary Celeste mystery", "The Dyatlov Pass incident", "The Tamam Shud case",
                           "The discovery of Tutankhamun's tomb", "Juliane Koepcke's survival story"]) for _ in range(n)]


def add_watermark(video, text="@Mnijeongggguk", image=""):
    """Stamp Malaak's watermark (her logo image if given, else her channel handle) bottom-right."""
    out = video[:-4] + "_wm.mp4"
    if image and os.path.isfile(image):
        vf = ["-i", image, "-filter_complex",
              "[1:v][0:v]scale2ref=w=iw*0.22:h=ow/mdar[wm][v];[wm]format=rgba,colorchannelmixer=aa=0.8[w];[v][w]overlay=W-w-30:H-h-200"]
    elif text:
        font = os.path.join(root, "resource", "fonts", "BeVietnamPro-Bold.ttf")
        t = text.replace(":", "\\:").replace("'", "")
        vf = ["-vf", f"drawtext=fontfile='{font}':text='{t}':fontcolor=white@0.85:fontsize=h/32:"
                     "borderw=3:bordercolor=black@0.6:x=w-tw-30:y=h-th-200"]
    else:
        return video
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video] + vf +
                       ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "copy", out])
    return out if r.returncode == 0 and os.path.isfile(out) else video


def run(n=3, topics=None, voice="en-US-GuyNeural-Male", privacy="public", watermark="@Mnijeongggguk", watermark_image=""):
    topics = [t.strip() for t in (topics or []) if t.strip()]
    used = []
    if len(topics) < n:
        topics += pick_topics(n - len(topics), used)
    for i, topic in enumerate(topics[:n], 1):
        print(f"\n🎬 [{i}/{n}] {topic}")
        try:
            script = llm.generate_script(video_subject=topic, paragraph_number=1,
                                         video_script_prompt=yt.SAFETY_RULES)
            terms = llm.generate_terms(topic, script, amount=5)
            p = VideoParams(video_subject=topic, video_script=script, video_terms=terms,
                            video_aspect=VideoAspect.portrait, voice_name=voice, video_count=1)
            res = tm.start(str(uuid.uuid4()), p) or {}
            vids = [v for v in (res.get("videos") or []) if os.path.isfile(v)]
            if not vids:
                print("  ❌ video failed:", res.get("error", "no video")); continue
            vids[0] = add_watermark(vids[0], watermark, watermark_image)
            print("  ✅ made", vids[0])
            if yt.enabled():
                print("  📤 posted:", yt.upload(vids[0], topic, script, privacy))
            else:
                print("  (YouTube not signed in, not posted)")
        except Exception as ex:
            print("  ❌ error:", ex)
        used.append(topic)
