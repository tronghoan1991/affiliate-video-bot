"""
colab_worker.py — Affiliate Video Bot v4.0 — Colab GPU Worker
=============================================================================
Chạy trên Google Colab (GPU).

Vai trò:
  - Nhận task xử lý video từ Dispatcher (Replit)
  - Chạy toàn bộ pipeline: CLIP → TryOn → Wan2.1 → ESRGAN → Overlay → Music → Drive
  - Gửi video trực tiếp về Telegram
  - Gọi callback về Dispatcher khi xong
=============================================================================

Cách chạy trong Colab (dán vào cell):
  %run colab_worker.py
  # hoặc:
  import asyncio; from colab_worker import start_worker; asyncio.run(start_worker())
"""

import asyncio, base64, gc, json, logging, os, tempfile, traceback, uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import torch
import uvicorn
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse
from PIL import Image
from pyngrok import ngrok

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ColabWorker")

# ─── Config từ env ────────────────────────────────────────────────────────────
DISPATCHER_URL     = os.environ.get("DISPATCHER_URL", "")        # URL Replit dispatcher
TELEGRAM_TOKEN     = os.environ.get("TELEGRAM_BOT_TOKEN", "")
NGROK_AUTH_TOKEN   = os.environ.get("NGROK_AUTH_TOKEN", "")
WORKER_PORT        = int(os.environ.get("WORKER_PORT", 8000))
GDRIVE_CREDENTIALS = os.environ.get("GDRIVE_CREDENTIALS_JSON", "")
GDRIVE_FOLDER_ID   = os.environ.get("GDRIVE_ROOT_FOLDER_ID", "")
REALESRGAN_SCALE   = int(os.environ.get("REALESRGAN_SCALE", "2"))
VIDEO_ENGINE       = os.environ.get("VIDEO_ENGINE", "auto")

# ─── State ───────────────────────────────────────────────────────────────────
worker_app = FastAPI(title="Colab Worker")
is_processing = False
public_url = ""


# ══════════════════════════════════════════════════════════════════════════════
#  FASTAPI ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@worker_app.get("/health")
async def health():
    return {
        "status": "running",
        "is_processing": is_processing,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "vram_free_gb": round((torch.cuda.get_device_properties(0).total_memory
                               - torch.cuda.memory_allocated(0)) / 1e9, 1)
                        if torch.cuda.is_available() else 0,
    }


@worker_app.post("/process")
async def process(request_data: dict, background_tasks: BackgroundTasks):
    """Nhận task từ Dispatcher, chạy pipeline trong background."""
    global is_processing

    if is_processing:
        return JSONResponse(
            {"status": "busy", "error": "Worker đang xử lý task khác. Vui lòng chờ."},
            status_code=503,
        )

    required = ["chat_id", "product_b64", "model_b64"]
    for field in required:
        if not request_data.get(field):
            return JSONResponse({"status": "error", "error": f"Missing: {field}"}, status_code=400)

    is_processing = True
    background_tasks.add_task(run_pipeline_task, request_data)
    return {"status": "queued", "message": "Task đã nhận, đang xử lý..."}


@worker_app.post("/ping")
async def ping_endpoint():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE TASK
# ══════════════════════════════════════════════════════════════════════════════

async def run_pipeline_task(data: dict):
    """Chạy toàn bộ pipeline và gửi kết quả về."""
    global is_processing
    uid     = str(uuid.uuid4())[:8]
    tmp     = Path(tempfile.mkdtemp(prefix=f"colab_{uid}_"))
    chat_id = data["chat_id"]
    device  = "cuda" if torch.cuda.is_available() else "cpu"

    async def tg_send(text: str):
        """Gửi status message về Telegram trực tiếp."""
        if not TELEGRAM_TOKEN: return
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                await c.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                )
        except Exception:
            pass

    try:
        # ── Giải mã ảnh ───────────────────────────────────────────────────
        product = tmp / "product.jpg"
        model   = tmp / "model.jpg"
        product.write_bytes(base64.b64decode(data["product_b64"]))
        model.write_bytes(base64.b64decode(data["model_b64"]))

        name        = data.get("name", "")
        price       = data.get("price", "")
        platform    = data.get("platform", "tiktok")
        style       = data.get("style", "tiktok")
        orientation = data.get("orientation", "portrait")

        # Cần import các module pipeline
        # Đảm bảo repo đã được clone vào /content/
        import sys
        repo_path = Path("/content/affiliate-video-bot")
        if repo_path.exists() and str(repo_path) not in sys.path:
            sys.path.insert(0, str(repo_path))

        from pipeline.background import get_background_prompt
        from pipeline.caption_gen import generate_caption
        from pipeline.classifier import classify_garment
        from pipeline.gdrive import GDriveUploader
        from pipeline.music_engine import attach_trending_music
        from pipeline.text_overlay import add_text_overlay
        from pipeline.tryon import run_virtual_tryon
        from pipeline.upscale import run_realesrgan_video
        from pipeline.video_engine import run_video_pipeline

        # ── 1. Phân loại trang phục ───────────────────────────────────────
        await tg_send("🔍 *[1/6] Đang phân tích trang phục (CLIP)...*")
        garment = classify_garment(product, device="cpu")
        bg      = get_background_prompt(garment)
        logger.info(f"[{uid}] garment={garment}")

        # ── 2. Virtual Try-On ─────────────────────────────────────────────
        await tg_send(f"👗 *[2/6] Đang ghép trang phục lên mẫu...*\n_({garment})_")
        tryon = tmp / f"tryon_{uid}.png"
        run_virtual_tryon(product, model, tryon, device, bg)
        _free()

        # ── 3. Video Generation ───────────────────────────────────────────
        await tg_send(
            "🎬 *[3/6] Đang tạo video (Wan2.1 I2V)...*\n"
            "_(5-15 phút — bước này lâu nhất)_"
        )
        raw_video = tmp / f"raw_{uid}.mp4"
        engine_used = await run_video_pipeline(
            image_path=tryon,
            output_path=raw_video,
            bg_prompt=bg,
            garment_class=garment,
            orientation=orientation,
            device=device,
        )
        _free()

        # ── 4. Real-ESRGAN Upscale ────────────────────────────────────────
        await tg_send(f"✨ *[4/6] Upscale {REALESRGAN_SCALE}× (Real-ESRGAN)...*")
        upscaled = tmp / f"up_{uid}.mp4"
        try:
            run_realesrgan_video(raw_video, upscaled, REALESRGAN_SCALE, device)
            working = upscaled
        except Exception as e:
            logger.warning(f"[{uid}] ESRGAN skip: {e}")
            working = raw_video
        _free()

        # ── 5. Text Overlay & Music ───────────────────────────────────────
        await tg_send("✍️ *[5/6] Thêm text overlay và nhạc...*")
        if style:
            txt_vid = tmp / f"txt_{uid}.mp4"
            add_text_overlay(working, txt_vid, name, price, garment, platform, style)
            working = txt_vid

        final = tmp / f"final_{uid}.mp4"
        attach_trending_music(working, final, garment, platform)
        _free()

        # ── 6. Upload Google Drive ────────────────────────────────────────
        await tg_send("☁️ *[6/6] Đang lưu lên Google Drive...*")
        ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"{(name or garment).replace(' ','_')[:40]}_{ts}.mp4"
        drive_url = ""
        try:
            uploader  = GDriveUploader()
            drive_url = uploader.upload_video(final, filename, platform)
        except Exception as e:
            logger.warning(f"[{uid}] Drive upload skip: {e}")

        # ── Gửi video về Telegram ─────────────────────────────────────────
        caption    = generate_caption(name, price, garment, platform)
        drive_line = f"\n\n📂 [Xem trên Drive]({drive_url})" if drive_url else ""
        fsize_mb   = final.stat().st_size / 1e6

        if fsize_mb <= 50 and TELEGRAM_TOKEN:
            await tg_send("📤 *Đang gửi video về Telegram...*")
            async with httpx.AsyncClient(timeout=120) as c:
                with open(final, "rb") as vf:
                    await c.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVideo",
                        data={
                            "chat_id": chat_id,
                            "caption": caption + drive_line,
                            "parse_mode": "Markdown",
                            "supports_streaming": True,
                        },
                        files={"video": (filename, vf, "video/mp4")},
                    )

        # ── Callback về Dispatcher ────────────────────────────────────────
        await _callback(chat_id, "success", drive_url, caption, engine_used)
        logger.info(f"[{uid}] ✅ Pipeline done | engine={engine_used}")

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[{uid}] Pipeline error:\n{tb}")
        await tg_send(f"❌ *Lỗi xử lý video:*\n`{str(e)[:300]}`")
        await _callback(chat_id, "error", error_msg=str(e)[:500])

    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
        _free()
        is_processing = False


def _free():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


async def _callback(chat_id: int, status: str,
                    drive_url: str = "", caption: str = "",
                    engine: str = "", error_msg: str = ""):
    """Gửi callback về Dispatcher."""
    if not DISPATCHER_URL: return
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            await c.post(f"{DISPATCHER_URL}/callback", json={
                "chat_id":   chat_id,
                "status":    status,
                "drive_url": drive_url,
                "caption":   caption,
                "engine":    engine,
                "error_msg": error_msg,
            })
    except Exception as e:
        logger.warning(f"Callback failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  STARTUP — ngrok + đăng ký với Dispatcher
# ══════════════════════════════════════════════════════════════════════════════

async def _register_with_dispatcher(url: str):
    """Đăng ký URL ngrok với Replit Dispatcher."""
    if not DISPATCHER_URL:
        logger.warning("DISPATCHER_URL chưa set — bỏ qua đăng ký")
        return
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(f"{DISPATCHER_URL}/register", json={"colab_url": url})
        logger.info(f"✅ Đã đăng ký với Dispatcher: {r.status_code}")
    except Exception as e:
        logger.error(f"Đăng ký Dispatcher thất bại: {e}")


async def _keepalive_loop():
    """Ping Dispatcher mỗi 4 phút để giữ kết nối."""
    if not DISPATCHER_URL: return
    while True:
        await asyncio.sleep(240)
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                await c.post(f"{DISPATCHER_URL}/ping")
        except Exception:
            pass


async def start_worker():
    """Hàm chính — gọi từ Colab notebook."""
    global public_url

    if not TELEGRAM_TOKEN:
        raise ValueError("Chưa set TELEGRAM_BOT_TOKEN!")

    # ── Setup ngrok ───────────────────────────────────────────────────────
    if NGROK_AUTH_TOKEN:
        ngrok.set_auth_token(NGROK_AUTH_TOKEN)

    # Đóng tunnel cũ nếu có
    ngrok.kill()
    await asyncio.sleep(1)

    tunnel     = ngrok.connect(WORKER_PORT, "http", bind_tls=True)
    public_url = tunnel.public_url
    logger.info(f"🌐 ngrok URL: {public_url}")

    # In ra màn hình Colab để dễ copy
    print("\n" + "="*60)
    print(f"✅ COLAB WORKER SẴN SÀNG")
    print(f"🌐 Public URL: {public_url}")
    print(f"📡 Dispatcher URL: {DISPATCHER_URL}")
    print("="*60 + "\n")

    # ── Đăng ký với Dispatcher ────────────────────────────────────────────
    await _register_with_dispatcher(public_url)

    # ── Chạy keepalive ────────────────────────────────────────────────────
    asyncio.create_task(_keepalive_loop())

    # ── Chạy FastAPI server ───────────────────────────────────────────────
    config = uvicorn.Config(
        worker_app, host="0.0.0.0", port=WORKER_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    logger.info(f"✅ Colab Worker đang chạy trên cổng {WORKER_PORT}")
    await server.serve()


if __name__ == "__main__":
    asyncio.run(start_worker())
