"""
scripts/keep_alive.py
Render free plan ngủ sau 15 phút không có request.
Script này chạy từ máy tính hoặc GitHub Actions để ping định kỳ.

Cách dùng:
  python keep_alive.py --render https://affiliate-video-bot.onrender.com
  
Hoặc dùng cron job / GitHub Actions (xem .github/workflows/keep_alive.yml)
"""
import argparse, time, requests, logging
from datetime import datetime

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("KeepAlive")

def ping_service(url: str, name: str) -> bool:
    try:
        r = requests.get(f"{url}/ping", timeout=15)
        ok = r.status_code == 200
        data = r.json() if ok else {}
        logger.info(f"{'✅' if ok else '❌'} {name}: {r.status_code} | {data}")
        return ok
    except Exception as e:
        logger.error(f"❌ {name}: {e}")
        return False

def run(render_url: str, colab_url: str = "", interval_min: int = 10):
    logger.info(f"🔄 Keep-alive started | interval={interval_min}m")
    logger.info(f"   Render : {render_url}")
    if colab_url:
        logger.info(f"   Colab  : {colab_url}")

    while True:
        now = datetime.now().strftime("%H:%M:%S")
        logger.info(f"\n── Ping {now} ─────────────────")
        ping_service(render_url, "Render")
        if colab_url:
            ping_service(colab_url, "Colab ")
        time.sleep(interval_min * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--render",   required=True,  help="Render URL")
    parser.add_argument("--colab",    default="",     help="Colab ngrok URL")
    parser.add_argument("--interval", type=int, default=10, help="Minutes between pings")
    args = parser.parse_args()
    run(args.render, args.colab, args.interval)
