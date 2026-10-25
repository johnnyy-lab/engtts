"""
一鍵啟動 Gemini TTS 網頁工作台
建立本機 HTTP 伺服器並自動開啟瀏覽器
支援靜態網頁服務與 YouTube 音軌擷取 API (/api/youtube-audio)
"""

import json
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import webbrowser
import http.server
import socketserver
from pathlib import Path

PORT = 8000
DIRECTORY = Path(__file__).parent

# 解決 Windows 終端機 (如 cp950 / Big5) 輸出 UTF-8 中文編碼問題
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def extract_youtube_audio(youtube_url: str) -> tuple[bytes, str, str, float]:
    """
    使用 yt-dlp 擷取 YouTube 影片的最佳音軌 (不需 ffmpeg 轉檔，直接取原生 m4a/webm 音軌供瀏覽器 Web Audio API 解碼)。
    回傳: (audio_bytes, mime_type, video_title, duration_sec)
    """
    with tempfile.TemporaryDirectory(prefix="yt_audio_") as tmpdir:
        tmp_path = Path(tmpdir)
        outtmpl = str(tmp_path / "audio.%(ext)s")
        fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=mp3]/bestaudio"

        # 優先使用當前 Python 環境的 yt_dlp 套件
        try:
            import yt_dlp  # type: ignore

            ydl_opts = {
                "format": fmt,
                "outtmpl": outtmpl,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "js_runtimes": {"node": {}},
                "remote_components": ["ejs:github"],
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                title = info.get("title") or "youtube_audio"
                duration = float(info.get("duration") or 0.0)
        except ImportError:
            # 若使用者以全域 python 啟動而未載入 .venv，自動尋找 .venv 或系統的 yt-dlp 執行檔
            venv_ytdlp = DIRECTORY / ".venv" / "Scripts" / "yt-dlp.exe"
            ytdlp_bin = str(venv_ytdlp) if venv_ytdlp.exists() else shutil.which("yt-dlp")
            if not ytdlp_bin:
                raise RuntimeError("找不到 yt-dlp 模組或執行檔，請確認已安裝 yt-dlp。")

            meta_cmd = [
                ytdlp_bin,
                "--no-playlist",
                "--js-runtimes", "node",
                "--remote-components", "ejs:github",
                "-f", fmt,
                "--print", "%(title)s\n%(duration)s",
                "-o", outtmpl,
                youtube_url,
            ]
            proc = subprocess.run(
                meta_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            if proc.returncode != 0:
                err_msg = (proc.stderr or proc.stdout or "未知錯誤").strip()
                raise RuntimeError(f"YouTube 音軌下載失敗: {err_msg}")

            lines = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
            title = lines[0] if len(lines) >= 1 else "youtube_audio"
            try:
                duration = float(lines[1]) if len(lines) >= 2 else 0.0
            except ValueError:
                duration = 0.0

        files = list(tmp_path.glob("audio.*"))
        if not files:
            raise RuntimeError("未能成功取得 YouTube 音訊檔案。")

        audio_file = files[0]
        ext = audio_file.suffix.lower()
        mime_map = {
            ".m4a": "audio/mp4",
            ".mp4": "audio/mp4",
            ".webm": "audio/webm",
            ".opus": "audio/ogg",
            ".ogg": "audio/ogg",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".aac": "audio/aac",
        }
        mime_type = mime_map.get(ext, "application/octet-stream")
        audio_bytes = audio_file.read_bytes()
        return audio_bytes, mime_type, title, duration


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class TTSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        # 允許跨域存取與 Chrome Private Network Access (支援從 GitHub Pages https://*.github.io 或 file:// 呼叫本機 8000 埠 API)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header(
            "Access-Control-Expose-Headers",
            "X-Video-Title, X-Video-Duration, Content-Disposition",
        )
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/youtube-audio":
            self.handle_youtube_audio(parsed.query)
            return
        super().do_GET()

    def handle_youtube_audio(self, query_string: str):
        params = urllib.parse.parse_qs(query_string)
        youtube_url = (params.get("url") or [""])[0].strip()

        if not youtube_url:
            self.send_json_error(400, "請提供有效的 YouTube 連結參數 (url)。")
            return

        parsed_url = urllib.parse.urlparse(youtube_url)
        host = (parsed_url.netloc or "").lower()
        if not any(domain in host for domain in ("youtube.com", "youtu.be", "music.youtube.com")):
            self.send_json_error(400, "僅支援 YouTube 相關網址 (youtube.com / youtu.be)。")
            return

        try:
            print(f"[*] 正在擷取 YouTube 音軌: {youtube_url}")
            audio_bytes, mime_type, title, duration = extract_youtube_audio(youtube_url)
            print(f"[OK] 擷取成功: {title} ({len(audio_bytes) / 1024:.1f} KB, {duration:.1f}s)")

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(audio_bytes)))
            self.send_header("X-Video-Title", urllib.parse.quote(title))
            self.send_header("X-Video-Duration", str(duration))
            self.end_headers()
            self.wfile.write(audio_bytes)
        except Exception as e:
            print(f"[!] YouTube 音軌擷取失敗: {e}")
            self.send_json_error(500, str(e))

    def send_json_error(self, status_code: int, message: str):
        payload = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    url = f"http://localhost:{PORT}/index.html"
    print("=" * 60)
    print("     Google Gemini TTS 網頁工作台已啟動")
    print(f"     網址: {url}")
    print("     存取防護: 需輸入密碼解鎖使用")
    print("     附加服務: 內建 YouTube 音軌擷取與音樂剪輯支援")
    print("     按 Ctrl+C 可停止伺服器")
    print("=" * 60)

    # 自動開啟預設瀏覽器
    webbrowser.open(url)

    try:
        with ThreadingTCPServer(("", PORT), TTSRequestHandler) as httpd:
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
