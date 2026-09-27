"""
Google AI Studio (Gemini) Text-to-Speech (TTS) 語音合成程式
使用 Google GenAI 官方 SDK，調用 Gemini TTS 模型將文字轉換為標準 WAV 音訊檔。
"""

import os
import sys
import wave
import logging
import argparse
import warnings
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 抑制非必要警告與 SDK 內部提示訊息
warnings.filterwarnings("ignore")
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

# 載入當前目錄的 .env 檔案
load_dotenv()

# 若同時設定了 GOOGLE_API_KEY 與 GEMINI_API_KEY，避免 SDK 輸出重複通知
if os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    del os.environ["GEMINI_API_KEY"]

from google import genai
from google.genai import types

# 解決 Windows 終端機 (如 cp950 / Big5) 編碼問題
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 常用與推薦的語音選項列表 (Gemini 支援 30 種預建聲音，此處標註男女聲與特色)
POPULAR_VOICES = {
    # 女性聲音 (Female)
    "Kore": "👩 女性 ｜ 沉穩、堅定 (Firm) - 預設推薦",
    "Zephyr": "👩 女性 ｜ 明亮、清晰 (Bright)",
    "Aoede": "👩 女性 ｜ 輕鬆、微風感 (Breezy)",
    "Leda": "👩 女性 ｜ 年輕、活力 (Youthful)",
    "Despina": "👩 女性 ｜ 柔和、流暢 (Smooth)",
    # 男性聲音 (Male)
    "Puck": "👨 男性 ｜ 輕快、活潑 (Upbeat)",
    "Charon": "👨 男性 ｜ 知性、解說型 (Informative)",
    "Fenrir": "👨 男性 ｜ 熱情、興奮 (Excitable)",
    "Orus": "👨 男性 ｜ 沉穩、剛毅 (Firm)",
    "Sulafat": "👨 男性 ｜ 溫暖、親和 (Warm)",
}

DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
DEFAULT_VOICE = "Kore"


def get_client() -> genai.Client:
    """初始化並回傳 Google GenAI Client"""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[!] 錯誤：找不到 API 金鑰！請確認 .env 檔案中已設定 GEMINI_API_KEY 或 GOOGLE_API_KEY。")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def save_pcm_to_wav(
    pcm_data: bytes,
    output_path: str | Path,
    channels: int = 1,
    sample_rate: int = 24000,
    sample_width: int = 2,
) -> Path:
    """將模型回傳的原始 PCM 資料 (24kHz, 16-bit, Mono) 封裝儲存為標準 WAV 格式音訊檔"""
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(out_file), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)

    return out_file


def text_to_speech(
    text: str,
    output_path: str = "output.wav",
    voice_name: str = DEFAULT_VOICE,
    model_name: str = DEFAULT_MODEL,
    client: genai.Client | None = None,
) -> Path:
    """
    調用 Gemini TTS 模型將文字轉換為語音並儲存為 WAV 檔。
    
    支援情感與語氣標籤（如 [excitedly], [whispers], [slowly] 等）。
    """
    text = text.strip()
    if not text:
        raise ValueError("輸入的文字不可為空。")

    if client is None:
        client = get_client()

    print(f"[*] 正在調用模型 [{model_name}] (語音: {voice_name}) 進行語音合成...")

    # 加上明確指示前綴，避免短語被模型誤判為對話問題
    prompt = f"TTS the following text:\n{text}"

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            ),
        ),
    )

    # 擷取音訊 raw PCM bytes
    try:
        candidate = response.candidates[0]
        part = candidate.content.parts[0]
        audio_data = part.inline_data.data
        if not audio_data:
            raise ValueError("回傳的音訊數據為空。")
    except (IndexError, AttributeError) as e:
        raise RuntimeError(f"未能從模型回傳中解析出音訊資料: {e}")

    out_file = save_pcm_to_wav(audio_data, output_path)

    # 計算時長 (16-bit mono: 2 bytes/sample, 24000 samples/sec -> 48000 bytes/sec)
    duration_sec = len(audio_data) / (24000 * 2)
    print(f"[OK] 語音生成成功！")
    print(f"     - 檔案路徑: {out_file}")
    print(f"     - 音訊時長: 約 {duration_sec:.2f} 秒")
    print(f"     - 檔案大小: {len(audio_data) / 1024:.1f} KB")

    return out_file


def interactive_mode(client: genai.Client):
    """互動式命令列介面"""
    print("=" * 60)
    print("      Google AI Studio (Gemini) TTS 語音生成工具")
    print("=" * 60)
    print("提示：支援中文、英文等多國語言，可於文字前加入情緒標籤（如 [cheerful], [whispers] 等）。")
    print("輸入 'exit' 或 'q' 結束程式。\n")

    while True:
        try:
            text = input("\n請輸入要轉換為語音的文字：\n> ").strip()
            if not text:
                continue
            if text.lower() in ["exit", "q", "quit"]:
                print("已結束程式。")
                break

            # 產生預設檔名包含時間戳記
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"tts_{timestamp}.wav"

            filename_input = input(f"輸出檔名 (直接按 Enter 預設為 '{default_filename}'): ").strip()
            output_file = filename_input if filename_input else default_filename
            if not output_file.lower().endswith(".wav"):
                output_file += ".wav"

            print(f"\n可選常用聲音 (直接按 Enter 預設為 '{DEFAULT_VOICE}'):")
            for v_name, v_desc in POPULAR_VOICES.items():
                marker = "*" if v_name == DEFAULT_VOICE else " "
                print(f"  [{marker}] {v_name:<10} : {v_desc}")
            voice_choice = input(f"請輸入聲音名稱 (預設: {DEFAULT_VOICE}): ").strip()
            selected_voice = voice_choice if voice_choice in POPULAR_VOICES else DEFAULT_VOICE

            text_to_speech(
                text=text,
                output_path=output_file,
                voice_name=selected_voice,
                client=client,
            )

        except KeyboardInterrupt:
            print("\n已中斷程式。")
            break
        except Exception as e:
            print(f"[!] 執行失敗: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Google AI Studio (Gemini) 文字轉語音 (TTS) 工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="?", help="要轉換的文字內容（若未提供則進入互動式介面）")
    parser.add_argument("-f", "--file", help="從指定純文字檔案讀取文字內容")
    parser.add_argument("-o", "--output", default="output.wav", help="輸出 WAV 檔案路徑 (預設: output.wav)")
    parser.add_argument("-v", "--voice", default=DEFAULT_VOICE, help=f"語音名稱 (預設: {DEFAULT_VOICE})")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"模型名稱 (預設: {DEFAULT_MODEL})")
    parser.add_argument("--list-voices", action="store_true", help="列出推薦語音清單")

    args = parser.parse_args()

    if args.list_voices:
        print("推薦的 Gemini TTS 語音選項：")
        for v_name, v_desc in POPULAR_VOICES.items():
            print(f"  - {v_name:<12}: {v_desc}")
        return

    client = get_client()

    input_text = None
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"[!] 錯誤：找不到檔案: {file_path}")
            sys.exit(1)
        input_text = file_path.read_text(encoding="utf-8")
    elif args.text:
        input_text = args.text

    if input_text:
        try:
            text_to_speech(
                text=input_text,
                output_path=args.output,
                voice_name=args.voice,
                model_name=args.model,
                client=client,
            )
        except Exception as e:
            print(f"[!] 錯誤：生成失敗: {e}")
            sys.exit(1)
    else:
        interactive_mode(client)


if __name__ == "__main__":
    main()
