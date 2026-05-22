"""
pipeline/gdrive.py
Upload & quản lý video trên Google Drive Workspace.
Dùng Service Account — không cần đăng nhập OAuth trên browser.

Cấu trúc thư mục tự động:
  AffiliateVideos/            ← GDRIVE_FOLDER_ID
  └── 2025-01/
      ├── tiktok/
      │   └── Váy_hoa_nhí_20250115_143022.mp4
      └── shopee/
          └── Áo_sơ_mi_20250115_150000.mp4
"""
import base64, json, logging, os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("GDrive")
SCOPES = ["https://www.googleapis.com/auth/drive"]


def _load_credentials():
    """Load Service Account credentials từ JSON string, base64, hoặc file path."""
    from google.oauth2 import service_account
    from config import Config

    raw = Config.GDRIVE_CREDENTIALS
    if not raw:
        raise ValueError(
            "GDRIVE_CREDENTIALS_JSON chưa được set!\n"
            "Xem hướng dẫn tạo Service Account trong DEPLOY_GUIDE.md"
        )

    if raw.strip().startswith("{"):
        info = json.loads(raw)
    elif os.path.isfile(raw):
        with open(raw) as f:
            info = json.load(f)
    else:
        try:
            info = json.loads(base64.b64decode(raw).decode())
        except Exception:
            raise ValueError(
                "GDRIVE_CREDENTIALS_JSON không hợp lệ.\n"
                "Phải là: JSON string, path đến file, hoặc base64 encoded JSON."
            )

    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


class GDriveUploader:
    """Upload và quản lý video trên Google Drive."""

    def __init__(self):
        self._svc         = None
        self._folder_cache: dict = {}

    def _service(self):
        if not self._svc:
            from googleapiclient.discovery import build
            creds = _load_credentials()
            self._svc = build("drive", "v3", credentials=creds)
            logger.info("✅ Google Drive service initialized")
        return self._svc

    def _ensure_folder(self, name: str, parent_id: str) -> str:
        key = f"{parent_id}/{name}"
        if key in self._folder_cache:
            return self._folder_cache[key]

        svc = self._service()
        q = (
            f"name='{name}' and '{parent_id}' in parents and "
            "mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        found = svc.files().list(q=q, fields="files(id)").execute().get("files", [])

        if found:
            fid = found[0]["id"]
        else:
            body = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            }
            fid = svc.files().create(body=body, fields="id").execute()["id"]
            logger.info(f"Drive: tạo thư mục '{name}' ({fid})")

        self._folder_cache[key] = fid
        return fid

    def _target_folder(self, platform: str) -> str:
        from config import Config
        root = Config.GDRIVE_FOLDER_ID
        if not root:
            raise ValueError("GDRIVE_ROOT_FOLDER_ID chưa được set!")

        if not Config.GDRIVE_AUTO_FOLDER:
            return root

        month_id      = self._ensure_folder(datetime.now().strftime("%Y-%m"), root)
        platform_name = "tiktok-shopee" if platform == "both" else platform
        return self._ensure_folder(platform_name, month_id)

    def upload_video(
        self,
        video_path: Path,
        filename: str,
        platform: str = "tiktok",
    ) -> str:
        from googleapiclient.http import MediaFileUpload

        folder_id = self._target_folder(platform)
        svc = self._service()

        file_meta = {"name": filename, "parents": [folder_id]}
        media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)

        logger.info(f"Uploading '{filename}' → Drive/{platform}...")
        uploaded = (
            svc.files()
            .create(body=file_meta, media_body=media, fields="id,webViewLink")
            .execute()
        )
        fid  = uploaded["id"]
        link = uploaded.get("webViewLink", f"https://drive.google.com/file/d/{fid}/view")

        try:
            svc.permissions().create(
                fileId=fid,
                body={"type": "anyone", "role": "reader"},
            ).execute()
        except Exception as e:
            logger.warning(f"Không set share permission: {e}")

        logger.info(f"✅ Uploaded: {link}")
        return link

    def list_recent(self, limit: int = 10) -> list:
        from config import Config
        root = Config.GDRIVE_FOLDER_ID
        if not root:
            return []

        svc = self._service()
        res = svc.files().list(
            q="mimeType='video/mp4' and trashed=false",
            orderBy="createdTime desc",
            pageSize=limit,
            fields="files(id,name,webViewLink,createdTime,size)",
        ).execute()
        return res.get("files", [])
