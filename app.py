"""
Virtual Painter — Browser Edition
Run:  python app.py
Then: http://localhost:5000
"""
import os, threading, webbrowser
from flask import Flask, send_from_directory

BASE = os.path.dirname(__file__)
app  = Flask(__name__)

@app.route("/")
def index():
    return send_from_directory(os.path.join(BASE, "static"), "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(os.path.join(BASE, "static"), path)

if __name__ == "__main__":
    port = 8080
    url  = f"http://localhost:{port}"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f"""
  ╔══════════════════════════════════════════╗
  ║   Virtual Painter  —  Browser Edition   ║
  ║   {url:<40} ║
  ║   Allow camera access when prompted     ║
  ╚══════════════════════════════════════════╝
""")
    app.run(host="localhost", port=port, debug=False)
