"""
pipeline/devops.py
Chạy trên Colab — GitHub push, Render deploy, Drive management
"""
import os, subprocess, logging, time
from pathlib import Path

logger = logging.getLogger("DevOps")

REPO_DIR = Path("/content/affiliate-studio-v8")


def github_push(commit_msg: str = "Auto-update", branch: str = "main") -> dict:
    """
    Tự động add + commit + push lên GitHub.
    Yêu cầu: GITHUB_TOKEN trong env, repo đã clone với token auth.
    """
    if not REPO_DIR.exists():
        return {"error": f"Repo dir không tồn tại: {REPO_DIR}"}

    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return {"error": "GITHUB_TOKEN chưa set trong Cell 0"}

    results = {}
    try:
        # Config git identity (one-time)
        _run(["git", "config", "user.email", "affiliatebot@auto.com"], REPO_DIR)
        _run(["git", "config", "user.name",  "AffiliateStudio Bot"],   REPO_DIR)

        # Cập nhật remote URL với token
        remote = _run(["git", "remote", "get-url", "origin"], REPO_DIR).strip()
        if "github.com" in remote and "@" not in remote:
            new_remote = remote.replace("https://", f"https://{token}@")
            _run(["git", "remote", "set-url", "origin", new_remote], REPO_DIR)

        # Stage all changes
        _run(["git", "add", "-A"], REPO_DIR)

        # Check if there's anything to commit
        status = _run(["git", "status", "--porcelain"], REPO_DIR)
        if not status.strip():
            results["commit"] = "nothing-to-commit"
            results["status"] = "up-to-date"
            return results

        # Commit
        ts      = time.strftime("%Y-%m-%d %H:%M")
        msg     = f"[{ts}] {commit_msg}"
        _run(["git", "commit", "-m", msg], REPO_DIR)
        results["commit"] = msg

        # Push
        push_out = _run(["git", "push", "origin", branch], REPO_DIR)
        results["push"]    = "OK"
        results["output"]  = push_out[:200]

        # Get repo URL (without token)
        clean_remote = remote.split("@")[-1] if "@" in remote else remote
        results["repo_url"] = clean_remote.replace(".git", "")

        logger.info(f"✅ GitHub push: {msg}")
        return results

    except Exception as e:
        logger.error(f"GitHub push fail: {e}")
        return {"error": str(e)}


def render_trigger_deploy(deploy_hook_url: str) -> dict:
    """Trigger Render redeploy via deploy hook URL."""
    import requests
    try:
        r = requests.post(deploy_hook_url, timeout=15)
        if r.status_code in (200, 201):
            return {"success": True, "status": r.status_code}
        return {"error": f"Render status {r.status_code}: {r.text[:100]}"}
    except Exception as e:
        return {"error": str(e)}


def sync_pipeline_to_repo(repo_dir: Path = REPO_DIR):
    """
    Copy pipeline changes từ /content vào repo dir trước khi push.
    Dùng khi edit pipeline trực tiếp trên Colab.
    """
    import shutil
    src = Path("/content/affiliate-studio-v8/pipeline")
    dst = repo_dir / "pipeline"
    if src.exists() and src != dst:
        shutil.copytree(src, dst, dirs_exist_ok=True)
        logger.info(f"✅ Synced pipeline: {src} → {dst}")


def setup_git_repo(github_repo: str, github_token: str,
                   repo_dir: Path = REPO_DIR) -> bool:
    """Clone hoặc pull repo từ GitHub."""
    if repo_dir.exists():
        try:
            _run(["git", "-C", str(repo_dir), "pull"], repo_dir)
            logger.info("✅ Git pull OK")
            return True
        except Exception as e:
            logger.warning(f"Git pull fail: {e}, re-cloning...")

    # Clone với token auth
    auth_url = github_repo.replace(
        "https://", f"https://{github_token}@"
    ) if github_token and "https://" in github_repo else github_repo

    try:
        subprocess.run(
            ["git", "clone", auth_url, str(repo_dir)],
            check=True, capture_output=True, text=True
        )
        logger.info(f"✅ Git clone OK: {repo_dir}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git clone fail: {e.stderr}")
        return False


def _run(cmd: list, cwd: Path) -> str:
    result = subprocess.run(
        cmd, cwd=str(cwd),
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0 and result.stderr:
        raise RuntimeError(result.stderr.strip())
    return result.stdout + result.stderr
