"""Colab launcher: writes config, starts Streamlit, opens a public link."""
import os, re, subprocess, sys, time, urllib.request
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)
subprocess.run([sys.executable, "scripts/make_config.py"], check=True)
log = open("/tmp/streamlit.log", "w")
subprocess.Popen([sys.executable, "-m", "streamlit", "run", "webui/Main.py", "--server.port", "8501",
                  "--server.headless", "true", "--server.address", "0.0.0.0",
                  "--server.enableCORS", "false", "--server.enableXsrfProtection", "false",
                  "--browser.gatherUsageStats", "false", "--server.maxUploadSize", "500"],
                 stdout=log, stderr=subprocess.STDOUT)
for _ in range(120):
    try: urllib.request.urlopen("http://127.0.0.1:8501/_stcore/health", timeout=2); break
    except Exception: time.sleep(1)
else:
    print(open("/tmp/streamlit.log").read()[-3000:]); sys.exit("App did not start")
url = None
try:
    cf = "/usr/local/bin/cloudflared"
    if not os.path.exists(cf):
        subprocess.run(["wget", "-q", "-O", cf, "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"], check=True)
        os.chmod(cf, 0o755)
    p = subprocess.Popen([cf, "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:8501"],
                         stdout=open("/tmp/cf.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(60):
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", open("/tmp/cf.log").read())
        if m: url = m.group(0); break
        time.sleep(1)
except Exception as ex:
    print("cloudflared failed:", ex)
if not url:
    try:
        from google.colab.output import eval_js
        url = eval_js("google.colab.kernel.proxyPort(8501)")
    except Exception as ex:
        print("Colab proxy failed:", ex)
try:
    from IPython.display import HTML, display
    display(HTML(f'<h1 style="font-size:2.2em">🎬 <a href="{url}" target="_blank">TAP HERE: Open Malaak Video Maker</a></h1><p>{url}</p>'
                 '<p>Keep this tab open. Download every video before you close it.</p>'))
except Exception:
    pass
print("\n\n🎬 OPEN THIS LINK:", url, "\n")
