"""Build config.toml at container start from Space secrets (never committed)."""
import os, toml
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = toml.load(f"{root}/config.example.toml")
app, ui = cfg.setdefault("app", {}), cfg.setdefault("ui", {})
e = lambda k: (os.environ.get(k) or "").strip()
if e("PEXELS_API_KEY"):
    app["pexels_api_keys"] = [e("PEXELS_API_KEY")]; app["video_source"] = "pexels"
elif e("PIXABAY_API_KEY"):
    app["pixabay_api_keys"] = [e("PIXABAY_API_KEY")]; app["video_source"] = "pixabay"
else:
    app["video_source"] = "local"  # keyless: upload your own images/clips
llm = None
for env, prov, key in [("GEMINI_API_KEY","gemini","gemini_api_key"),("OPENAI_API_KEY","openai","openai_api_key"),
                       ("DEEPSEEK_API_KEY","deepseek","deepseek_api_key"),("POLLINATIONS_API_KEY","pollinations","pollinations_api_key")]:
    if e(env):
        app[key] = e(env); llm = llm or prov
if e("OPENAI_BASE_URL"): app["openai_base_url"] = e("OPENAI_BASE_URL")
if e("OPENAI_MODEL_NAME"): app["openai_model_name"] = e("OPENAI_MODEL_NAME")
app["llm_provider"] = e("LLM_PROVIDER") or llm or "pollinations"
app["subtitle_provider"] = "edge"
ui.update({"language": "en", "video_language": "en-US", "tts_server": "azure-tts-v1",
           "voice_name": "en-US-GuyNeural-Male", "voice_mode": "tts", "bgm_type": "random",
           "subtitle_enabled": True, "open_task_folder_on_completion": False, "video_count": 1,
           "font_name": "MicrosoftYaHeiBold.ttc"})
for src in ["pexels","pixabay","local","coverr"]:
    ui[f"video_aspect_{src}"] = "9:16"
with open(f"{root}/config.toml", "w") as f: toml.dump(cfg, f)
print("config ready: video_source=%s llm=%s" % (app["video_source"], app["llm_provider"]))
