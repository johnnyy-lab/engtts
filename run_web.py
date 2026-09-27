"""
一鍵啟動 Gemini TTS 網頁工作台
建立本機 HTTP 伺服器並自動開啟瀏覽器
"""

import sys
import webbrowser
import http.server
import socketserver
from pathlib import Path

PORT = 8000
DIRECTORY = Path(__file__).parent


class TTSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)


def main():
    url = f"http://localhost:{PORT}/index.html"
    print("=" * 60)
    print("     Google Gemini TTS 網頁工作台已啟動")
    print(f"     網址: {url}")
    print("     存取防護: 需輸入密碼解鎖使用")
    print("     按 Ctrl+C 可停止伺服器")
    print("=" * 60)

    # 自動開啟預設瀏覽器
    webbrowser.open(url)

    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), TTSRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[OK] 網頁伺服器已停止。")
    except OSError as e:
        if "address already in use" in str(e).lower() or getattr(e, "errno", None) == 10048:
            print(f"[!] 通訊埠 {PORT} 已被占用，請直接在瀏覽器打開: {url}")
        else:
            raise e


if __name__ == "__main__":
    main()
