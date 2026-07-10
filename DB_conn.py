from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

import pyodbc
import requests


BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "DB"
DB_FILE = "Config_DB.db"
CONFIG_NAME = "HD_MSSQL"
CONFIG_TXT = BASE_DIR / "config.txt"


def load_config_txt(filepath: str | os.PathLike[str] = CONFIG_TXT) -> dict[str, str]:
    """Read config.txt values used by HD projects."""
    config = {
        "Not_Charge_IDP": "",
        "Not_PlaceofDuty": "",
        "google_doc_key": "",
    }
    path = Path(filepath)
    if not path.exists():
        return config

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key in config:
                config[key] = value.strip()
    return config


def get_google_drive_url(config_txt: dict[str, str] | None = None) -> str:
    config = config_txt or load_config_txt()
    doc_key = config.get("google_doc_key", "").strip()
    if not doc_key:
        raise ValueError("config.txt에 google_doc_key 값이 없습니다.")
    return f"https://drive.google.com/file/d/{doc_key}/view?usp=drive_link"


def download_db(
    gdrive_url: str | None = None,
    db_dir: str | os.PathLike[str] = DB_DIR,
    db_file: str = DB_FILE,
) -> tuple[bool, str]:
    """Download Config_DB.db from Google Drive and return (ok, path_or_error)."""
    db_path = Path(db_dir) / db_file
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        url = gdrive_url or get_google_drive_url()
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
        if not match:
            raise ValueError("Google Drive 파일 ID를 추출할 수 없습니다.")

        file_id = match.group(1)
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        session = requests.Session()
        resp = session.get(download_url, stream=True, timeout=60)
        resp.raise_for_status()

        if "text/html" in resp.headers.get("Content-Type", ""):
            for key, value in resp.cookies.items():
                if key.startswith("download_warning"):
                    download_url = (
                        "https://drive.google.com/uc"
                        f"?export=download&confirm={value}&id={file_id}"
                    )
                    resp = session.get(download_url, stream=True, timeout=60)
                    resp.raise_for_status()
                    break

        with db_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True, str(db_path)
    except Exception as exc:
        return False, str(exc)


def ensure_config_db(
    db_dir: str | os.PathLike[str] = DB_DIR,
    db_file: str = DB_FILE,
    force_download: bool = False,
) -> Path:
    """Ensure the SQLite connection-info DB exists locally."""
    db_path = Path(db_dir) / db_file
    if db_path.exists() and not force_download:
        return db_path

    ok, result = download_db(db_dir=db_dir, db_file=db_file)
    if not ok:
        raise RuntimeError(f"설정 DB 다운로드 실패: {result}")
    return Path(result)


def load_db_config(
    config_name: str = CONFIG_NAME,
    db_dir: str | os.PathLike[str] = DB_DIR,
    db_file: str = DB_FILE,
    auto_download: bool = True,
) -> dict[str, Any]:
    """Load MSSQL connection settings from DBCON inside Config_DB.db."""
    db_path = Path(db_dir) / db_file
    if auto_download:
        db_path = ensure_config_db(db_dir=db_dir, db_file=db_file)

    if not db_path.exists():
        raise FileNotFoundError(f"설정 DB 파일이 없습니다: {db_path}")

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT DB_Type, Host, Port, DB_Name, DB_ID, DB_PW
                FROM DBCON
                WHERE Name = ?
                """,
                (config_name,),
            )
            row = cursor.fetchone()
    except Exception as exc:
        raise RuntimeError(f"DB 설정 로드 실패: {exc}") from exc

    if not row:
        raise LookupError(f"DBCON 테이블에 Name='{config_name}' 레코드가 없습니다.")

    return {
        "DB_Type": row[0],
        "Host": row[1],
        "Port": row[2],
        "DB_Name": row[3],
        "DB_ID": row[4],
        "DB_PW": row[5],
    }


def build_mssql_connection_string(cfg: dict[str, Any]) -> str:
    return (
        f"DRIVER={{{cfg['DB_Type']}}};"
        f"SERVER={cfg['Host']},{cfg['Port']};"
        f"DATABASE={cfg['DB_Name']};"
        f"UID={cfg['DB_ID']};"
        f"PWD={cfg['DB_PW']}"
    )


def get_mssql_connection(cfg: dict[str, Any], timeout: int = 30) -> pyodbc.Connection:
    return pyodbc.connect(build_mssql_connection_string(cfg), timeout=timeout)


def connect(
    config_name: str = CONFIG_NAME,
    timeout: int = 30,
    auto_download: bool = True,
) -> pyodbc.Connection:
    """Load config from Google Drive backed Config_DB.db and open MSSQL."""
    cfg = load_db_config(config_name=config_name, auto_download=auto_download)
    return get_mssql_connection(cfg, timeout=timeout)


__all__ = [
    "DB_DIR",
    "DB_FILE",
    "CONFIG_NAME",
    "CONFIG_TXT",
    "load_config_txt",
    "get_google_drive_url",
    "download_db",
    "ensure_config_db",
    "load_db_config",
    "build_mssql_connection_string",
    "get_mssql_connection",
    "connect",
]
