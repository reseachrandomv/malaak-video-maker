"""Autopilot: make and auto-post N videos in a row (run from the Colab notebook)."""
import json, os, random, re, sys, uuid
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


def run(n=3, topics=None, voice="en-US-GuyNeural-Male", privacy="public"):
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
            print("  ✅ made", vids[0])
            if yt.enabled():
                print("  📤 posted:", yt.upload(vids[0], topic, script, privacy))
            else:
                print("  (YouTube not signed in, not posted)")
        except Exception as ex:
            print("  ❌ error:", ex)
        used.append(topic)
