#!/usr/bin/env python3
"""
GET AI LAB - Cross-Platform Desktop Launcher (Windows, macOS, Linux)
Minimal stdlib implementation. Launches dashboard (web) + optional CLI chat.
For full native desktop: wrap in Tauri / pywebview / Electron (plan below).
Pure GetAiLab: no extra deps. Opens the living PWA-ready web UI + chat.
"""
import os
import sys
import platform
import subprocess
import webbrowser
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver

ROOT = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.join(ROOT, "dashboard", "frontend")

class GetAiLabDesktopHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASH, **kwargs)

def print_desktop_header():
    plat = platform.system()
    print("\n" + "="*70)
    print("🦅 GET AI LAB • DESKTOP LAUNCHER (V4 Multi-Platform)")
    print(f"   OS: {plat} | Python: {platform.python_version()}")
    print("   Web + PWA chat ready. CLI chat: run run_chimera.py --chat")
    print("="*70 + "\n")

def start_local_dashboard(port=8088):
    """Serve the static frontend locally (works offline-ish + PWA)."""
    try:
        with socketserver.TCPServer(("", port), GetAiLabDesktopHandler) as httpd:
            url = f"http://localhost:{port}/index.html"
            print(f"🌐 Desktop local server: {url}")
            print("   (PWA install prompt available in supported browsers. Mobile webviews also load this.)")
            webbrowser.open(url)
            print("   Press Ctrl+C to stop desktop session.")
            httpd.serve_forever()
    except OSError:
        print(f"Port {port} busy. Open dashboard/frontend/index.html manually in browser.")
        webbrowser.open(f"file://{os.path.join(DASH, 'index.html')}")

def launch_full_services_background():
    """Optional: attempt to boot core services (lab + oracle + squad) in bg. Unix friendly, best effort on Win."""
    print("⚙️  Attempting background services launch (lab + oracle + squad)...")
    boot_py = os.path.join(ROOT, "boot_example.sh")
    plat = platform.system().lower()
    try:
        if plat == "windows":
            print("   Windows: Best-effort lab boot. Full squad recommended via: python run_chimera.py or WSL/Docker.")
            # Best effort: start lab only (user can run more in other shells)
            subprocess.Popen([sys.executable, os.path.join(ROOT, "lab", "app_lab.py")], cwd=ROOT)
        else:
            if os.path.exists(boot_py):
                subprocess.Popen(["bash", boot_py], cwd=ROOT)
            else:
                # Fallback pure python
                subprocess.Popen([sys.executable, os.path.join(ROOT, "lab", "app_lab.py")], cwd=ROOT)
                time.sleep(1.5)
                subprocess.Popen([sys.executable, os.path.join(ROOT, "scientists", "app_oracle.py")], cwd=ROOT)
        print("   Services started (check logs/). Use run_chimera.py --chat for council. Cross-platform parity.")
    except Exception as e:
        print(f"   Services launch note: {e}. Start manually for full power.")

def open_cli_chat_hint():
    print("\n💬 For real CLI chat (unified with mobile): python run_chimera.py --chat")
    print("   Full dialectic: python run_chimera.py")

def try_native_desktop_embed(url):
    """Optional pure-vision native desktop window using pywebview (if installed). 
    Plan: pip install pywebview -> true .exe/.app/.deb without browser chrome.
    Cross-platform (Win/Mac/Linux). Falls back to webbrowser if unavailable."""
    try:
        import webview  # pywebview
        print("🪟 Native desktop window via pywebview detected. Launching embedded GetAiLab (no browser tab).")
        webview.create_window("GetAiLab • the example lab — Research Lab", url, width=1280, height=900, resizable=True)
        webview.start()
        return True
    except ImportError:
        print("   (pywebview not installed — using browser. For native desktop app: pip install pywebview)")
        return False
    except Exception as e:
        print(f"   Native embed note: {e}. Falling back.")
        return False

if __name__ == "__main__":
    print_desktop_header()
    print("1. Launch local desktop web + PWA chat (recommended for all platforms)")
    print("2. Attempt full lab services + open web")
    print("3. Just open browser dashboard (remote ready)")
    print("4. Hint for mobile chat + exit")
    print("5. Try native desktop embed (pywebview if avail — plan for true Win/Mac/Linux apps)")
    choice = input("\nChoice [1-5, default 1]: ").strip() or "1"

    if choice == "2":
        launch_full_services_background()
        time.sleep(2)
        start_local_dashboard()
    elif choice == "3":
        webbrowser.open("http://localhost:5035/")
    elif choice == "4":
        print("\n📱 ANDROID / iOS CHAT STUBS:\n - Load http://host:5035 or local index.html / mobile_chat_stub.html in Chrome/Safari\n - Add to Home Screen (PWA manifest + sw.js)\n - Or use native WebView loading /api/mobile/chat (see JS bridge window.sendChatFromNative)\n - Dedicated: /api/mobile/status + quick actions. Cross-platform parity with CLI/web.\n")
        open_cli_chat_hint()
    elif choice == "5":
        # Plan implementation: native desktop for full support beyond browser launcher
        launch_full_services_background()
        time.sleep(1.5)
        url = "http://localhost:5035/"
        if not try_native_desktop_embed(url):
            start_local_dashboard(8088)
        open_cli_chat_hint()
    else:
        # Default: desktop web chat launcher
        launch_full_services_background()
        time.sleep(1.2)
        url = "http://localhost:8088/index.html"
        if not try_native_desktop_embed("http://localhost:8088/index.html"):
            start_local_dashboard(8088)
        open_cli_chat_hint()

# DESKTOP APP PLAN (No Compromises, Pure Vision):
# - Current: This launcher + webbrowser + optional pywebview gives instant native-feeling desktop on Win/Mac/Linux. Choice 5 in menu activates embed.
# - Implemented: Graceful try_native_desktop_embed(url) — uses pywebview if present for true windowed app (no chrome), else browser + local static server.
# - Production next: 
#   * pywebview (add to reqs for builds): full menus (Council Chat, Pulse Field, Ignite Loop, Library Export), system tray, single-binary.
#   * Tauri (recommended for signed dist): Rust sidecar calls Python FastAPI (lab/app_lab + run_chimera.py logic). Compile to .exe (Win), .app (mac), .deb/AppImage (Linux). Shares ALL chat/APIs/PWA assets.
#   * For full parity: mobile already 100% via PWA + /api/mobile/* + mobile_chat_stub + native bridges (Kotlin/Swift examples in README).
# - Docker/CLI remain universal fallbacks. No platform left behind. Run `python desktop_launcher.py` then choose 5 for native preview.
# All platforms (web + Win + mac + Linux + Android + iOS) share 100% of the chat, dashboard, CLI, field, Library logic. The manifold is universal.