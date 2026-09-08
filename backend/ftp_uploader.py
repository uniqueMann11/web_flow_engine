"""
FTP Image Uploader
==================
Uploads images to an FTP server in Passive Mode (vsFTPd 3.0.5 compatible).
Returns the public URL for the uploaded file.

Configuration via environment variables:
  FTP_HOST, FTP_PORT, FTP_USER, FTP_PASS, FTP_FOLDER, FTP_PUBLIC_BASE_URL
"""

import os
import io
import ftplib
import uuid


def _get_ftp_config():
    """Read FTP credentials from environment variables."""
    return {
        "host": os.environ.get("FTP_HOST", ""),
        "port": int(os.environ.get("FTP_PORT", 21)),
        "user": os.environ.get("FTP_USER", ""),
        "password": os.environ.get("FTP_PASS", ""),
        "folder": os.environ.get("FTP_FOLDER", "dynamicpage"),
        "public_base_url": os.environ.get("FTP_PUBLIC_BASE_URL", ""),
    }


def is_ftp_configured():
    """Check whether FTP credentials are present (without exposing secrets)."""
    cfg = _get_ftp_config()
    configured = bool(cfg["host"] and cfg["user"] and cfg["password"])
    return {
        "configured": configured,
        "host": cfg["host"] or "(not set)",
        "port": cfg["port"],
        "folder": cfg["folder"],
        "public_base_url": cfg["public_base_url"] or "(not set)",
    }


def test_ftp_connection():
    """
    Quick connectivity + authentication test.
    Returns (success: bool, message: str).
    """
    cfg = _get_ftp_config()
    if not cfg["host"] or not cfg["user"]:
        return False, "FTP credentials not configured in .env"

    try:
        ftp = ftplib.FTP()
        ftp.connect(cfg["host"], cfg["port"], timeout=15)
        ftp.login(cfg["user"], cfg["password"])
        ftp.set_pasv(True)  # Passive mode
        welcome = ftp.getwelcome()
        ftp.quit()
        return True, f"Connected successfully — {welcome}"
    except Exception as e:
        return False, f"FTP connection failed: {e}"


def upload_image_to_ftp(file_bytes_or_path, original_filename, folder=None, prefix="page-img"):
    """
    Upload an image file to the FTP server.

    Args:
        file_bytes_or_path: Either raw bytes, a BytesIO object, or a local file path (str).
        original_filename:  The original filename (used to derive extension).
        folder:             Remote directory name (defaults to FTP_FOLDER env var).
        prefix:             Filename prefix (default: 'page-img').

    Returns:
        dict with keys:
            - success (bool)
            - public_url (str)   — the permanent HTTPS URL
            - remote_path (str)  — e.g. 'dynamicpage/page-img-uuid.jpg'
            - error (str|None)
    """
    cfg = _get_ftp_config()
    if not cfg["host"] or not cfg["user"]:
        return {
            "success": False,
            "public_url": None,
            "remote_path": None,
            "error": "FTP credentials not configured in .env",
        }

    folder = folder or cfg["folder"]

    # Derive unique filename
    ext = os.path.splitext(original_filename)[1] or ".jpg"
    unique_filename = f"{prefix}-{uuid.uuid4()}{ext}"

    # Prepare the binary stream
    if isinstance(file_bytes_or_path, (bytes, bytearray)):
        stream = io.BytesIO(file_bytes_or_path)
    elif isinstance(file_bytes_or_path, io.IOBase):
        stream = file_bytes_or_path
        stream.seek(0)
    elif isinstance(file_bytes_or_path, str) and os.path.isfile(file_bytes_or_path):
        stream = open(file_bytes_or_path, "rb")
    else:
        return {
            "success": False,
            "public_url": None,
            "remote_path": None,
            "error": f"Invalid input: expected bytes, BytesIO, or file path. Got {type(file_bytes_or_path).__name__}",
        }

    ftp = None
    try:
        ftp = ftplib.FTP()
        ftp.connect(cfg["host"], cfg["port"], timeout=30)
        ftp.login(cfg["user"], cfg["password"])
        ftp.set_pasv(True)  # Passive mode

        # Ensure remote directory exists
        try:
            ftp.cwd(folder)
        except ftplib.error_perm:
            ftp.mkd(folder)
            ftp.cwd(folder)

        # Upload the file
        ftp.storbinary(f"STOR {unique_filename}", stream)

        # Build the public URL
        public_url = f"{cfg['public_base_url'].rstrip('/')}/{folder}/{unique_filename}"
        remote_path = f"{folder}/{unique_filename}"

        ftp.quit()

        return {
            "success": True,
            "public_url": public_url,
            "remote_path": remote_path,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "public_url": None,
            "remote_path": None,
            "error": str(e),
        }
    finally:
        # Close the file handle if we opened it
        if isinstance(file_bytes_or_path, str) and hasattr(stream, "close"):
            stream.close()
        if ftp:
            try:
                ftp.quit()
            except Exception:
                pass
