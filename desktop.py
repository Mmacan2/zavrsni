import threading
import webview
import time
import requests
from app import app

def start_flask():
    print("[INFO] Starting Flask server...")
    app.run(port=5000, debug=False, use_reloader=False)

def wait_for_server(url, timeout=10):
    print(f"[INFO] Waiting for server at {url}...")
    for _ in range(timeout * 10):
        try:
            r = requests.get(url)
            if r.status_code == 200:
                print("[INFO] Server is up!")
                return True
        except:
            pass
        time.sleep(0.1)
    print("[ERROR] Server not responding.")
    return False

if __name__ == '__main__':
    threading.Thread(target=start_flask, daemon=True).start()

    if wait_for_server("http://localhost:5000"):
        window = webview.create_window("Logic Gate Classifier", "http://localhost:5000", width=1200, height=800)
        webview.start(gui='edgechromium')
    else:
        print("[ERROR] Flask app failed to start.")
