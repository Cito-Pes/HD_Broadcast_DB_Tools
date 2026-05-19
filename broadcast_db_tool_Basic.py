# =============================================================================
# 방송 DB 처리 시스템
# 기능1: 전화번호 기반 중복 정보 추출 + 엑셀 저장
# 기능2: 상담내역 등록 (추후 구현)
#
# 개발환경: Python 3.13.6 / PySide6 / Windows 전용
# DB: SQL Server 2008 R2 (pyodbc — Windows ODBC 드라이버 직접 사용)
# Excel: xlsxwriter (쓰기 전용, 메모리 효율, 풍부한 포맷 API)
# Config: Google Drive Config_DB.db 패턴 (Google_Drive_ConfigDB_Guide.md 준수)
# =============================================================================

import os
import re
import sys
import sqlite3
import requests
import pyodbc
import xlsxwriter
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox, QFileDialog,
    QSplitter, QGroupBox, QFrame
)

# =============================================================================
# ★ 수정 필요: Google Drive 공유 링크 및 Config 식별자
# =============================================================================
GDRIVE_URL = "https://drive.google.com/file/d/1oncya1uYDnbVS2KwuBAKw4x4o9oQDct0/view?usp=drive_link"
DB_DIR     = "./DB"
DB_FILE    = "Config_DB.db"
CONFIG_NAME = "HD_MSSQL"   # DBCON 테이블의 Name 값
CONFIG_TXT  = "./config.txt"

# =============================================================================
# SQL 쿼리 정의
# 플레이스홀더: {phones}, {channel}, {exc_consultant}, {exc_org}
# config.txt의 Not_Charge_IDP, Not_PlaceofDuty 값은
# 이미 'val1', 'val2' 형태로 저장되어 있으므로 그대로 삽입
# =============================================================================

QUERY_CHANNEL_COMBO = (
    "SELECT Code_Name FROM Code "
    "WHERE code = '채널경로' ORDER BY Num;"
)

QUERY_ALL_DUP = """\
SELECT x.mobile, COUNT(*) AS all_cnt
FROM (
    SELECT REPLACE(mm.Mobile, '-', '') AS mobile
    FROM Member mm WITH(NOLOCK)
    INNER JOIN (
        SELECT id, MA_etc_str5 FROM Member_Add WITH(NOLOCK)
    ) ma ON mm.ID = ma.ID
    WHERE mm.Mobile <> ''
      AND REPLACE(mm.Mobile, '-', '') IN ({phones})
    GROUP BY REPLACE(mm.Mobile, '-', ''), mm.MemberNo
    UNION ALL
    SELECT REPLACE(mm.Mobile, '-', '') AS mobile
    FROM TM_MEMBER mm WITH(NOLOCK)
    WHERE LEN(mm.AssignDate) = 10
      AND mm.Mobile <> ''
      AND REPLACE(mm.Mobile, '-', '') IN ({phones})
    GROUP BY mm.Mobile, mm.OrderNo
) x
GROUP BY x.mobile
"""

QUERY_ALL_60_DUP = """\
SELECT x.mobile, COUNT(*) AS all_60_cnt
FROM (
    SELECT REPLACE(mm.Mobile, '-', '') AS mobile
    FROM Member mm WITH(NOLOCK)
    INNER JOIN (
        SELECT id, MA_etc_str5 FROM Member_Add WITH(NOLOCK)
    ) ma ON mm.ID = ma.ID
    WHERE mm.Reg_Date > CONVERT(VARCHAR(10), DATEADD(DAY, -60, GETDATE()), 120)
      AND mm.Mobile <> ''
      AND REPLACE(mm.Mobile, '-', '') IN ({phones})
    GROUP BY REPLACE(mm.Mobile, '-', ''), mm.MemberNo
    UNION ALL
    SELECT REPLACE(mm.Mobile, '-', '') AS mobile
    FROM TM_MEMBER mm WITH(NOLOCK)
    WHERE mm.Reg_Date > CONVERT(VARCHAR(10), DATEADD(DAY, -60, GETDATE()), 120)
      AND LEN(mm.AssignDate) = 10
      AND mm.Mobile <> ''
      AND REPLACE(mm.Mobile, '-', '') IN ({phones})
    GROUP BY mm.Mobile, mm.OrderNo
) x
GROUP BY x.mobile
"""

QUERY_60_CHANNEL_DUP = """\
SELECT x.mobile, COUNT(*) AS ch_60_cnt
FROM (
    SELECT REPLACE(mm.Mobile, '-', '') AS mobile
    FROM Member mm WITH(NOLOCK)
    INNER JOIN (
        SELECT id, MA_etc_str5
        FROM Member_Add WITH(NOLOCK)
        WHERE MA_etc_str5 IN ({channel})
    ) ma ON mm.ID = ma.ID
    WHERE mm.Reg_Date > CONVERT(VARCHAR(10), DATEADD(DAY, -60, GETDATE()), 120)
      AND mm.Mobile <> ''
      AND REPLACE(mm.Mobile, '-', '') IN ({phones})
    GROUP BY REPLACE(mm.Mobile, '-', ''), mm.MemberNo
    UNION ALL
    SELECT REPLACE(mm.Mobile, '-', '') AS mobile
    FROM TM_MEMBER mm WITH(NOLOCK)
    WHERE HS_Name IN ({channel})
      AND mm.Reg_Date > CONVERT(VARCHAR(10), DATEADD(DAY, -60, GETDATE()), 120)
      AND LEN(mm.AssignDate) = 10
      AND mm.Mobile <> ''
      AND REPLACE(mm.Mobile, '-', '') IN ({phones})
    GROUP BY mm.Mobile, mm.OrderNo
) x
GROUP BY x.mobile
"""

QUERY_ALL_60_CONSULTANT = """\
SELECT REPLACE(x.Mobile, '-', '') AS phone_number,
       sf.saname,
       x.AssignDate,
       x.MemberNo,
       x.Charge_IDP
FROM (
    SELECT mm.MemberNo, mm.Mobile, mm.Reg_Date AS AssignDate, mm.Charge_IDP
    FROM Member mm WITH(NOLOCK)
    INNER JOIN (
        SELECT id, MA_etc_str5 FROM Member_Add
    ) ma ON mm.ID = ma.ID
    LEFT JOIN dbo.staff s1 WITH(NOLOCK) ON s1.SaBun = mm.Charge_IDP
    WHERE mm.Reg_Date > CONVERT(VARCHAR(10), DATEADD(DAY, -60, GETDATE()), 120)
      AND mm.Mobile <> ''
      AND mm.Charge_IDP NOT IN ({exc_consultant})
      AND s1.PlaceofDuty NOT IN ({exc_org})
    GROUP BY mm.MemberNo, mm.Mobile, mm.Reg_Date, mm.Charge_IDP
    UNION ALL
    SELECT mm.OrderNo AS MemberNo, mm.Mobile, mm.AssignDate,
           mm.AssignCharge_ID AS Charge_IDP
    FROM TM_MEMBER mm WITH(NOLOCK)
    LEFT JOIN dbo.staff s1 WITH(NOLOCK) ON mm.AssignCharge_ID = s1.SaBun
    WHERE mm.AssignDate > CONVERT(VARCHAR(10), DATEADD(DAY, -60, GETDATE()), 120)
      AND mm.AssignCharge_ID NOT IN ({exc_consultant})
      AND s1.PlaceofDuty NOT IN ({exc_org})
      AND LEN(mm.AssignDate) = 10
      AND mm.Mobile <> ''
    GROUP BY mm.OrderNo, mm.Mobile, mm.AssignDate, mm.AssignCharge_ID
) x
INNER JOIN staff sf ON x.Charge_IDP = sf.sabun
WHERE REPLACE(x.Mobile, '-', '') IN ({phones})
GROUP BY x.MemberNo, REPLACE(x.Mobile, '-', ''), x.Charge_IDP, sf.saname, x.AssignDate
ORDER BY x.AssignDate DESC, x.MemberNo,
         REPLACE(x.Mobile, '-', ''), x.Charge_IDP, sf.saname
"""

QUERY_CHANNEL_60_CONSULTANT = """\
SELECT REPLACE(x.Mobile, '-', '') AS phone_number,
       sf.saname,
       x.AssignDate,
       x.MemberNo,
       x.Charge_IDP
FROM (
    SELECT mm.MemberNo, mm.Mobile, mm.Reg_Date AS AssignDate, mm.Charge_IDP
    FROM Member mm WITH(NOLOCK)
    INNER JOIN (
        SELECT id, MA_etc_str5
        FROM Member_Add
        WHERE MA_etc_str5 IN ({channel})
    ) ma ON mm.ID = ma.ID
    LEFT JOIN dbo.staff s1 WITH(NOLOCK) ON s1.SaBun = mm.Charge_IDP
    WHERE mm.Reg_Date > CONVERT(VARCHAR(10), DATEADD(DAY, -60, GETDATE()), 120)
      AND mm.Mobile <> ''
      AND mm.Charge_IDP NOT IN ({exc_consultant})
      AND s1.PlaceofDuty NOT IN ({exc_org})
    GROUP BY mm.MemberNo, mm.Mobile, mm.Reg_Date, mm.Charge_IDP
    UNION ALL
    SELECT mm.OrderNo AS MemberNo, mm.Mobile, mm.AssignDate,
           mm.AssignCharge_ID AS Charge_IDP
    FROM TM_MEMBER mm WITH(NOLOCK)
    LEFT JOIN dbo.staff s1 WITH(NOLOCK) ON mm.AssignCharge_ID = s1.SaBun
    WHERE HS_Name IN ({channel})
      AND mm.AssignDate > CONVERT(VARCHAR(10), DATEADD(DAY, -60, GETDATE()), 120)
      AND mm.AssignCharge_ID NOT IN ({exc_consultant})
      AND s1.PlaceofDuty NOT IN ({exc_org})
      AND LEN(mm.AssignDate) = 10
      AND mm.Mobile <> ''
    GROUP BY mm.OrderNo, mm.Mobile, mm.AssignDate, mm.AssignCharge_ID
) x
INNER JOIN staff sf ON x.Charge_IDP = sf.sabun
WHERE REPLACE(x.Mobile, '-', '') IN ({phones})
GROUP BY x.MemberNo, REPLACE(x.Mobile, '-', ''), x.Charge_IDP, sf.saname, x.AssignDate
ORDER BY x.AssignDate DESC, x.MemberNo,
         REPLACE(x.Mobile, '-', ''), x.Charge_IDP, sf.saname
"""


# =============================================================================
# 헬퍼 함수
# =============================================================================

def clean_phone(raw: str) -> str:
    """전화번호에서 숫자만 추출 (공백·탭·하이픈·특수문자 모두 제거)"""
    return re.sub(r'[^0-9]', '', raw)


def parse_phones(text: str) -> list[str]:
    """
    붙여넣기 텍스트에서 전화번호 목록 추출
    - 줄바꿈·탭·쉼표를 구분자로 분리
    - 숫자만 남기고 빈값·중복 제거
    - 원본 입력 순서 유지
    """
    parts = re.split(r'[\n\r\t,]+', text)
    seen: set[str] = set()
    phones: list[str] = []
    for part in parts:
        phone = clean_phone(part.strip())
        if phone and phone not in seen:
            phones.append(phone)
            seen.add(phone)
    return phones


def build_in_clause(items: list[str]) -> str:
    """
    리스트 → SQL IN절 문자열
    예: ['010...', '011...'] → "'010...', '011...'"
    """
    return ', '.join(f"'{item}'" for item in items)


def load_config_txt(filepath: str = CONFIG_TXT) -> dict[str, str]:
    """
    config.txt에서 Not_Charge_IDP, Not_PlaceofDuty 읽기
    값은 이미 'val1', 'val2' 형태로 저장되어 있다고 가정
    파일이 없거나 키가 없으면 빈 문자열 반환
    """
    config: dict[str, str] = {
        'Not_Charge_IDP': '',
        'Not_PlaceofDuty': ''
    }
    if not os.path.exists(filepath):
        return config
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip()
                    if key in config:
                        config[key] = value
    except Exception as e:
        print(f"[WARN] config.txt 읽기 실패: {e}")
    return config


def safe_str(val) -> str:
    """None 및 다양한 타입을 안전하게 문자열로 변환"""
    if val is None:
        return ''
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%d')
    return str(val)


# =============================================================================
# Google Drive DB 다운로드 (Google_Drive_ConfigDB_Guide.md 표준 구현)
# =============================================================================

def download_db() -> tuple[bool, str]:
    """Google Drive에서 Config_DB.db 다운로드"""
    db_path = os.path.join(DB_DIR, DB_FILE)
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)
    try:
        match = re.search(r"/d/([a-zA-Z0-9_-]+)", GDRIVE_URL)
        if not match:
            raise ValueError("Google Drive 파일 ID를 추출할 수 없습니다.")
        file_id = match.group(1)
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        session = requests.Session()
        resp = session.get(download_url, stream=True)
        resp.raise_for_status()
        # 대용량 파일 confirm 토큰 처리
        if "text/html" in resp.headers.get("Content-Type", ""):
            for key, value in resp.cookies.items():
                if key.startswith("download_warning"):
                    download_url = (
                        f"https://drive.google.com/uc"
                        f"?export=download&confirm={value}&id={file_id}"
                    )
                    resp = session.get(download_url, stream=True)
                    resp.raise_for_status()
                    break
        with open(db_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True, db_path
    except Exception as e:
        return False, str(e)


def load_db_config() -> dict:
    """Config_DB.db에서 SQL Server 접속 정보 읽기"""
    db_path = os.path.join(DB_DIR, DB_FILE)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DB_Type, Host, Port, DB_Name, DB_ID, DB_PW "
            "FROM DBCON WHERE Name = ?",
            (CONFIG_NAME,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise LookupError(
                f"DBCON 테이블에 Name='{CONFIG_NAME}' 레코드가 없습니다."
            )
        return {
            "DB_Type": row[0],
            "Host":    row[1],
            "Port":    row[2],
            "DB_Name": row[3],
            "DB_ID":   row[4],
            "DB_PW":   row[5],
        }
    except Exception as e:
        raise Exception(f"DB 설정 로드 실패: {e}")


def get_mssql_connection(cfg: dict) -> pyodbc.Connection:
    """SQL Server 2008 R2 pyodbc 연결 반환"""
    conn_str = (
        f"DRIVER={{{cfg['DB_Type']}}};"
        f"SERVER={cfg['Host']},{cfg['Port']};"
        f"DATABASE={cfg['DB_Name']};"
        f"UID={cfg['DB_ID']};"
        f"PWD={cfg['DB_PW']}"
    )
    return pyodbc.connect(conn_str, timeout=30)


# =============================================================================
# Worker Thread — 방송사 콤보 로드
# =============================================================================

class ChannelLoadWorker(QThread):
    finished = Signal(list)
    error    = Signal(str)

    def __init__(self, db_config: dict):
        super().__init__()
        self.db_config = db_config

    def run(self):
        try:
            conn = get_mssql_connection(self.db_config)
            cursor = conn.cursor()
            cursor.execute(QUERY_CHANNEL_COMBO)
            rows = cursor.fetchall()
            conn.close()
            self.finished.emit([row[0] for row in rows])
        except Exception as e:
            self.error.emit(str(e))


# =============================================================================
# Worker Thread — 5개 쿼리 순차 실행
# =============================================================================

class QueryWorker(QThread):
    progress = Signal(str)          # 상태 메시지
    finished = Signal(dict)         # 전체 결과
    error    = Signal(str)          # 오류 메시지

    def __init__(
        self,
        db_config:       dict,
        phones:          list[str],
        channel:         str,
        exc_consultant:  str,
        exc_org:         str
    ):
        super().__init__()
        self.db_config      = db_config
        self.phones         = phones
        self.channel        = channel
        self.exc_consultant = exc_consultant
        self.exc_org        = exc_org

    def run(self):
        try:
            # ── 변수 준비 ──────────────────────────────────────────────
            phones_in = build_in_clause(self.phones)
            # 방송사: 콤보에서 선택된 단일 값 → 'K쇼핑' 형태
            channel_in = f"'{self.channel}'"
            # exc_consultant, exc_org 는 config.txt 에서
            # 이미 'val1', 'val2' 형태로 읽혀 왔으므로 그대로 사용

            self.progress.emit("SQL Server 연결 중...")
            conn   = get_mssql_connection(self.db_config)
            cursor = conn.cursor()

            results: dict = {}

            # ── 쿼리 1: 전체 방송 중복 ──────────────────────────────────
            self.progress.emit("[1/5] 전체 방송 중복 조회 중...")
            cursor.execute(QUERY_ALL_DUP.format(phones=phones_in))
            results['all_dup'] = {
                row[0]: row[1] for row in cursor.fetchall()
            }

            # ── 쿼리 2: 전체방송 최근 60일 중복 ────────────────────────
            self.progress.emit("[2/5] 전체방송 최근 60일 중복 조회 중...")
            cursor.execute(QUERY_ALL_60_DUP.format(phones=phones_in))
            results['all_60_dup'] = {
                row[0]: row[1] for row in cursor.fetchall()
            }

            # ── 쿼리 3: 최근 60일 방송사 중복 ──────────────────────────
            self.progress.emit("[3/5] 최근 60일 방송사 중복 조회 중...")
            cursor.execute(
                QUERY_60_CHANNEL_DUP.format(
                    phones=phones_in,
                    channel=channel_in
                )
            )
            results['ch_60_dup'] = {
                row[0]: row[1] for row in cursor.fetchall()
            }

            # ── 쿼리 4: 전체 60일 상담사 ────────────────────────────────
            self.progress.emit("[4/5] 전체 60일 상담사 조회 중...")
            cursor.execute(
                QUERY_ALL_60_CONSULTANT.format(
                    phones=phones_in,
                    exc_consultant=self.exc_consultant,
                    exc_org=self.exc_org
                )
            )
            results['all_60_consultant'] = [
                {
                    'phone':      safe_str(row[0]),
                    'saname':     safe_str(row[1]),
                    'assign_date': safe_str(row[2]),
                    'member_no':  safe_str(row[3]),
                    'charge_idp': safe_str(row[4]),
                }
                for row in cursor.fetchall()
            ]

            # ── 쿼리 5: 방송사 60일 상담사 ──────────────────────────────
            self.progress.emit("[5/5] 방송사 60일 상담사 조회 중...")
            cursor.execute(
                QUERY_CHANNEL_60_CONSULTANT.format(
                    phones=phones_in,
                    channel=channel_in,
                    exc_consultant=self.exc_consultant,
                    exc_org=self.exc_org
                )
            )
            results['ch_60_consultant'] = [
                {
                    'phone':      safe_str(row[0]),
                    'saname':     safe_str(row[1]),
                    'assign_date': safe_str(row[2]),
                    'member_no':  safe_str(row[3]),
                    'charge_idp': safe_str(row[4]),
                }
                for row in cursor.fetchall()
            ]

            conn.close()

            # 메타 정보 포함
            results['phones']  = self.phones
            results['channel'] = self.channel

            self.progress.emit("조회 완료!")
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


# =============================================================================
# Excel 내보내기
# 시트명: 중복데이터
# 구성: [섹션1] 중복 카운트 요약 | [섹션2] 전체 60일 상담사 | [섹션3] 방송사 60일 상담사
# =============================================================================

def export_to_excel(results: dict, filepath: str, channel_name: str) -> None:
    """
    xlsxwriter 기반 Excel 내보내기 (쓰기 전용 / 메모리 효율)
    시트명: 중복데이터
    구성 : [섹션1] 중복 카운트 요약
           [섹션2] 전체 60일 상담사
           [섹션3] 방송사 60일 상담사
    """
    wb = xlsxwriter.Workbook(filepath)
    ws = wb.add_worksheet("중복데이터")   # ← 요구사항 정확히 반영

    # ── 포맷 정의 (xlsxwriter는 포맷 객체를 미리 생성해서 재사용) ──
    # 색상 상수
    C_HDR_BLUE   = "#2F5496"
    C_HDR_GREEN  = "#375623"
    C_HDR_ORANGE = "#C55A11"
    C_TTL_BG     = "#D9E2F3"
    C_TTL_FG     = "#1F3864"
    C_EVEN_BG    = "#EEF3FA"
    C_RED        = "#C00000"
    C_BORDER     = "#141414"

    def _base(extra: dict) -> dict:
        """공통 border 포함한 포맷 딕셔너리 생성"""
        base = {
            'border': 1,
            'border_color': C_BORDER,
            'valign': 'vcenter',
        }
        base.update(extra)
        return base

    # 섹션 제목 포맷
    fmt_title = wb.add_format(_base({
        'bold': True, 'font_size': 11,
        'font_color': C_TTL_FG, 'bg_color': C_TTL_BG,
        'border': 0,   # 제목행은 테두리 없이 깔끔하게
    }))

    # 헤더 포맷 3종 (섹션별 색상만 다름)
    def _hdr_fmt(bg: str):
        return wb.add_format(_base({
            'bold': True, 'font_color': '#FFFFFF',
            'bg_color': bg, 'align': 'center',
            'text_wrap': True, 'font_size': 10,
        }))
    fmt_hdr_blue   = _hdr_fmt(C_HDR_BLUE)
    fmt_hdr_green  = _hdr_fmt(C_HDR_GREEN)
    fmt_hdr_orange = _hdr_fmt(C_HDR_ORANGE)

    # 데이터 포맷 — 홀/짝 × 좌/중앙 × 일반/빨간굵게
    def _data_fmt(align: str, even: bool, red_bold: bool = False):
        d = _base({'align': align})
        if even:
            d['bg_color'] = C_EVEN_BG
        if red_bold:
            d['bold'] = True
            d['font_color'] = C_RED
        return wb.add_format(d)

    # 포맷 캐시 (조합이 많지 않아 미리 생성)
    FMT = {
        # (align, even, red_bold)
        ('left',   False, False): _data_fmt('left',   False, False),
        ('left',   True,  False): _data_fmt('left',   True,  False),
        ('center', False, False): _data_fmt('center', False, False),
        ('center', True,  False): _data_fmt('center', True,  False),
        ('center', False, True):  _data_fmt('center', False, True),
        ('center', True,  True):  _data_fmt('center', True,  True),
    }

    # 결과 없음 포맷
    fmt_nodata = wb.add_format({
        'italic': True, 'font_color': '#888888', 'align': 'left',
    })

    # ── 열 너비 설정 ────────────────────────────────────────────────
    ws.set_column(0, 0, 16)   # A: 전화번호
    ws.set_column(1, 1, 14)   # B: 카운트/상담사명
    ws.set_column(2, 2, 14)   # C: 카운트/배정일자
    ws.set_column(3, 3, 16)   # D: 카운트/MemberNo
    ws.set_column(4, 4, 14)   # E: 상담사ID

    # ── 데이터 준비 ─────────────────────────────────────────────────
    phones      = results.get('phones', [])
    all_dup     = results.get('all_dup', {})
    all_60_dup  = results.get('all_60_dup', {})
    ch_60_dup   = results.get('ch_60_dup', {})
    all_60_cons = results.get('all_60_consultant', [])
    ch_60_cons  = results.get('ch_60_consultant', [])

    r = 0   # xlsxwriter는 0-indexed

    # ──────────────────────────────────────────────────────────────
    # [섹션1] 중복 카운트 요약
    # ──────────────────────────────────────────────────────────────
    ws.merge_range(r, 0, r, 4, "■ 중복 카운트 요약", fmt_title)
    ws.set_row(r, 20)
    r += 1

    hdrs_count = [
        '전화번호', '전체방송중복', '전체방송\n60일중복', f'{channel_name}\n60일중복'
    ]
    ws.set_row(r, 30)
    for c, h in enumerate(hdrs_count):
        ws.write(r, c, h, fmt_hdr_blue)
    r += 1

    for i, phone in enumerate(phones):
        even     = (i % 2 == 0)
        all_cnt  = all_dup.get(phone, 0)
        a60_cnt  = all_60_dup.get(phone, 0)
        ch60_cnt = ch_60_dup.get(phone, 0)

        ws.write(r, 0, phone,    FMT[('left',   even, False)])
        ws.write(r, 1, all_cnt,  FMT[('center', even, all_cnt  > 0)])
        ws.write(r, 2, a60_cnt,  FMT[('center', even, a60_cnt  > 0)])
        ws.write(r, 3, ch60_cnt, FMT[('center', even, ch60_cnt > 0)])
        r += 1

    if not phones:
        ws.write(r, 0, "(조회 결과 없음)", fmt_nodata)
        r += 1

    r += 1  # 빈 줄

    # ──────────────────────────────────────────────────────────────
    # [섹션2] 전체 60일 상담사
    # ──────────────────────────────────────────────────────────────
    ws.merge_range(r, 0, r, 4, "■ 전체 60일 상담사", fmt_title)
    ws.set_row(r, 20)
    r += 1

    hdrs_cons = ['전화번호', '상담사명', '배정일자', 'MemberNo', '상담사ID']
    ws.set_row(r, 22)
    for c, h in enumerate(hdrs_cons):
        ws.write(r, c, h, fmt_hdr_green)
    r += 1

    for i, d in enumerate(all_60_cons):
        even = (i % 2 == 0)
        ws.write(r, 0, d['phone'],       FMT[('left',   even, False)])
        ws.write(r, 1, d['saname'],      FMT[('center', even, False)])
        ws.write(r, 2, d['assign_date'], FMT[('center', even, False)])
        ws.write(r, 3, d['member_no'],   FMT[('center', even, False)])
        ws.write(r, 4, d['charge_idp'],  FMT[('center', even, False)])
        r += 1

    if not all_60_cons:
        ws.write(r, 0, "(조회 결과 없음)", fmt_nodata)
        r += 1

    r += 1  # 빈 줄

    # ──────────────────────────────────────────────────────────────
    # [섹션3] 방송사 60일 상담사
    # ──────────────────────────────────────────────────────────────
    ws.merge_range(r, 0, r, 4, f"■ {channel_name} 60일 상담사", fmt_title)
    ws.set_row(r, 20)
    r += 1

    ws.set_row(r, 22)
    for c, h in enumerate(hdrs_cons):
        ws.write(r, c, h, fmt_hdr_orange)
    r += 1

    for i, d in enumerate(ch_60_cons):
        even = (i % 2 == 0)
        ws.write(r, 0, d['phone'],       FMT[('left',   even, False)])
        ws.write(r, 1, d['saname'],      FMT[('center', even, False)])
        ws.write(r, 2, d['assign_date'], FMT[('center', even, False)])
        ws.write(r, 3, d['member_no'],   FMT[('center', even, False)])
        ws.write(r, 4, d['charge_idp'],  FMT[('center', even, False)])
        r += 1

    if not ch_60_cons:
        ws.write(r, 0, "(조회 결과 없음)", fmt_nodata)
        r += 1

    # ── 틀 고정 (1행) ────────────────────────────────────────────────
    ws.freeze_panes(1, 0)

    wb.close()


# =============================================================================
# UI — 결과 테이블 채우기 공통 함수
# =============================================================================

def _fill_consultant_table(table: QTableWidget, rows: list[dict]) -> None:
    """전체/방송사 상담사 QTableWidget 채우기"""
    table.setRowCount(len(rows))
    for r_idx, row in enumerate(rows):
        vals = [
            row['phone'], row['saname'], row['assign_date'],
            row['member_no'], row['charge_idp']
        ]
        for c_idx, val in enumerate(vals):
            item = QTableWidgetItem(val)
            if c_idx > 0:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(r_idx, c_idx, item)


# =============================================================================
# 메인 윈도우
# =============================================================================

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.db_config:     dict | None  = None
        self.query_results: dict | None  = None
        self.worker:        QueryWorker | None       = None
        self.ch_worker:     ChannelLoadWorker | None = None
        self.config_txt:    dict = {}

        self.setWindowTitle("방송 DB 처리 시스템 v1.0")
        self.setMinimumSize(1150, 760)

        self._build_ui()
        self._apply_styles()
        self.load_config()

    # ─────────────────────────────────────────────────────────────────
    # UI 구성
    # ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 4)
        root_layout.setSpacing(4)

        # 탭 위젯
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root_layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_tab_duplicate(),     "📋  중복 정보 추출")
        self.tabs.addTab(self._build_tab_consultation(),  "📝  상담내역 등록")

        # 상태바
        self.statusBar().showMessage("초기화 중...")

    # ── 탭1: 중복 정보 추출 ──────────────────────────────────────────

    def _build_tab_duplicate(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        # ── 상단 컨트롤 그룹 ──
        ctrl_box = QGroupBox("조회 설정")
        ctrl_lay = QHBoxLayout(ctrl_box)
        ctrl_lay.setSpacing(10)

        ctrl_lay.addWidget(QLabel("방송사:"))
        self.cmb_channel = QComboBox()
        self.cmb_channel.setMinimumWidth(160)
        self.cmb_channel.setToolTip("채널경로 코드 목록 (DB 자동 로드)")
        ctrl_lay.addWidget(self.cmb_channel)

        self.btn_refresh_ch = QPushButton("🔄")
        self.btn_refresh_ch.setToolTip("방송사 목록 새로고침")
        self.btn_refresh_ch.setFixedSize(32, 28)
        self.btn_refresh_ch.clicked.connect(self.load_channels)
        ctrl_lay.addWidget(self.btn_refresh_ch)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        ctrl_lay.addWidget(sep)

        self.lbl_config_info = QLabel("설정 로딩 중...")
        self.lbl_config_info.setStyleSheet("color:#555; font-size:10px;")
        ctrl_lay.addWidget(self.lbl_config_info)

        ctrl_lay.addStretch()

        self.btn_query = QPushButton("🔍  조회 실행")
        self.btn_query.setMinimumSize(120, 32)
        self.btn_query.setEnabled(False)
        self.btn_query.clicked.connect(self.run_query)
        ctrl_lay.addWidget(self.btn_query)

        self.btn_export = QPushButton("📥  엑셀 저장")
        self.btn_export.setMinimumSize(120, 32)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_excel)
        ctrl_lay.addWidget(self.btn_export)

        lay.addWidget(ctrl_box)

        # ── 진행 표시줄 ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)     # indeterminate
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setVisible(False)
        lay.addWidget(self.progress_bar)

        # ── 메인 스플리터 (입력 | 결과) ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── 왼쪽: 전화번호 입력 패널 ──
        left = QWidget()
        left.setMaximumWidth(270)
        left.setMinimumWidth(200)
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(0, 0, 6, 0)
        l_lay.setSpacing(4)

        lbl_ph = QLabel("전화번호 입력")
        lbl_ph.setStyleSheet("font-weight:bold; font-size:12px;")
        l_lay.addWidget(lbl_ph)

        lbl_hint = QLabel("엑셀 열 복사 후 붙여넣기 (Ctrl+V)\n공백·하이픈 자동 제거")
        lbl_hint.setStyleSheet("color:#888; font-size:10px;")
        lbl_hint.setWordWrap(True)
        l_lay.addWidget(lbl_hint)

        self.txt_phones = QPlainTextEdit()
        self.txt_phones.setPlaceholderText(
            "예시:\n01012345678\n010-9876-5432\n010 1111 2222"
        )
        self.txt_phones.setFont(QFont("Consolas", 10))
        self.txt_phones.textChanged.connect(self._update_phone_count)
        l_lay.addWidget(self.txt_phones)

        self.lbl_phone_count = QLabel("0개 입력됨")
        self.lbl_phone_count.setStyleSheet("color:#555; font-size:10px;")
        l_lay.addWidget(self.lbl_phone_count)

        btn_clear = QPushButton("지우기")
        btn_clear.setObjectName("btnSecondary")
        btn_clear.setMaximumWidth(70)
        btn_clear.clicked.connect(self.txt_phones.clear)
        l_lay.addWidget(btn_clear)

        splitter.addWidget(left)

        # ── 오른쪽: 결과 패널 ──
        right = QWidget()
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(4)

        lbl_result = QLabel("조회 결과")
        lbl_result.setStyleSheet("font-weight:bold; font-size:12px;")
        r_lay.addWidget(lbl_result)

        # 결과 3분할 수직 스플리터
        res_split = QSplitter(Qt.Orientation.Vertical)

        # 결과1: 중복 카운트 요약
        self.grp_count = QGroupBox("중복 카운트 요약")
        gc_lay = QVBoxLayout(self.grp_count)
        gc_lay.setContentsMargins(4, 4, 4, 4)
        self.tbl_count = self._make_table(
            ['전화번호', '전체방송중복', '전체방송 60일중복', '방송사 60일중복']
        )
        gc_lay.addWidget(self.tbl_count)
        res_split.addWidget(self.grp_count)

        # 결과2: 전체 60일 상담사
        self.grp_all_cons = QGroupBox("전체 60일 상담사")
        ga_lay = QVBoxLayout(self.grp_all_cons)
        ga_lay.setContentsMargins(4, 4, 4, 4)
        self.tbl_all_cons = self._make_table(
            ['전화번호', '상담사명', '배정일자', 'MemberNo', '상담사ID']
        )
        ga_lay.addWidget(self.tbl_all_cons)
        res_split.addWidget(self.grp_all_cons)

        # 결과3: 방송사 60일 상담사
        self.grp_ch_cons = QGroupBox("방송사 60일 상담사")
        gch_lay = QVBoxLayout(self.grp_ch_cons)
        gch_lay.setContentsMargins(4, 4, 4, 4)
        self.tbl_ch_cons = self._make_table(
            ['전화번호', '상담사명', '배정일자', 'MemberNo', '상담사ID']
        )
        gch_lay.addWidget(self.tbl_ch_cons)
        res_split.addWidget(self.grp_ch_cons)

        res_split.setSizes([180, 250, 250])
        r_lay.addWidget(res_split)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        lay.addWidget(splitter)

        return w

    def _make_table(self, headers: list[str]) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setDefaultSectionSize(22)
        tbl.verticalHeader().setVisible(False)
        return tbl

    # ── 탭2: 상담내역 등록 (placeholder) ────────────────────────────

    def _build_tab_consultation(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl1 = QLabel("📝  상담내역 등록")
        lbl1.setStyleSheet("font-size:26px; color:#8899AA;")
        lbl1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl1)

        lbl2 = QLabel("이 기능은 추후 구현 예정입니다.")
        lbl2.setStyleSheet("font-size:13px; color:#AABBC0;")
        lbl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl2)

        return w

    # ─────────────────────────────────────────────────────────────────
    # 스타일시트
    # ─────────────────────────────────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #F0F4F8;
                font-family: '맑은 고딕', 'Malgun Gothic', sans-serif;
                font-size: 11px;
            }
            QTabWidget::pane {
                border: 1px solid #141414;
                background: #F8FAFD;
                border-radius: 0 4px 4px 4px;
            }
            QTabBar::tab {
                background: #DDE5F0;
                border: 1px solid #C0C8D8;
                border-bottom: none;
                padding: 6px 18px;
                font-size: 12px;
                margin-right: 2px;
                border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:selected {
                background: #2F5496;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #C8D8EE;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                border: 1px solid #141414;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 6px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #2F5496;
            }
            QPushButton {
                background-color: #2F5496;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover   { background-color: #3A67B5; }
            QPushButton:pressed { background-color: #1E3D7A; }
            QPushButton:disabled { background-color: #A8B4C4; }
            QPushButton#btnSecondary {
                background-color: #6C757D;
                font-weight: normal;
            }
            QPushButton#btnSecondary:hover { background-color: #5A6471; }
            QTableWidget {
                gridline-color: #DEE2E6;
                font-size: 11px;
                border: 1px solid #141414;
            }
            QTableWidget::item:selected {
                background-color: #BDD7EE;
                color: black;
            }
            QHeaderView::section {
                background-color: #2F5496;
                color: white;
                font-weight: bold;
                font-size: 11px;
                padding: 5px 4px;
                border: none;
                border-right: 1px solid #4A6FAA;
                border-bottom: 1px solid #1E3D7A;
            }
            QPlainTextEdit {
                border: 1px solid #141414;
                border-radius: 4px;
                background: #FAFBFC;
                font-size: 11px;
            }
            QComboBox {
                border: 1px solid #141414;
                border-radius: 4px;
                padding: 3px 8px;
                background: white;
                min-height: 26px;
            }
            QComboBox:focus { border-color: #2F5496; }
            QProgressBar {
                border: 1px solid #141414;
                border-radius: 3px;
                text-align: center;
                font-size: 10px;
                background: #F0F4F8;
            }
            QProgressBar::chunk { background-color: #2F5496; }
            QStatusBar {
                background: #2F5496;
                color: white;
                font-size: 11px;
            }
        """)

    # ─────────────────────────────────────────────────────────────────
    # 초기화 로직
    # ─────────────────────────────────────────────────────────────────

    def log(self, msg: str):
        self.statusBar().showMessage(msg)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def load_config(self):
        """앱 시작 시 config.txt + Config_DB.db 로드"""
        self.log("설정 파일 확인 중...")

        # config.txt 로드
        self.config_txt = load_config_txt(CONFIG_TXT)
        exc_idp = self.config_txt.get('Not_Charge_IDP', '').strip()
        exc_org = self.config_txt.get('Not_PlaceofDuty', '').strip()

        if exc_idp or exc_org:
            preview = f"제외상담사 설정 {len(exc_idp.split(','))}개 | 제외조직 설정 {len(exc_org.split(','))}개"
            self.lbl_config_info.setText(preview)
            self.lbl_config_info.setToolTip(
                f"Not_Charge_IDP: {exc_idp}\nNot_PlaceofDuty: {exc_org}"
            )
        else:
            self.lbl_config_info.setText("⚠ config.txt 없음 또는 설정 누락")
            self.lbl_config_info.setStyleSheet("color:#C00000; font-size:10px;")

        # Config_DB.db 확인 및 다운로드
        db_path = os.path.join(DB_DIR, DB_FILE)
        if not os.path.exists(db_path):
            self.log("Config_DB.db 없음 → Google Drive 다운로드 중...")
            ok, result = download_db()
            if not ok:
                QMessageBox.critical(
                    self, "설정 로드 실패",
                    f"Config_DB.db를 다운로드할 수 없습니다.\n\n오류: {result}"
                )
                return
            self.log(f"다운로드 완료: {result}")

        try:
            self.db_config = load_db_config()
            self.log(
                f"DB 준비 완료 → "
                f"{self.db_config['Host']}:{self.db_config['Port']} "
                f"/ {self.db_config['DB_Name']}"
            )
            self.btn_query.setEnabled(True)
            self.load_channels()
        except Exception as e:
            QMessageBox.critical(self, "DB 설정 오류", str(e))
            self.log(f"DB 설정 오류: {e}")

    def load_channels(self):
        """방송사 콤보박스 데이터 로드 (DB → 채널경로 코드)"""
        if not self.db_config:
            return
        self.btn_refresh_ch.setEnabled(False)
        self.log("방송사 목록 로딩 중...")
        self.ch_worker = ChannelLoadWorker(self.db_config)
        self.ch_worker.finished.connect(self._on_channels_loaded)
        self.ch_worker.error.connect(self._on_channel_error)
        self.ch_worker.start()

    def _on_channels_loaded(self, channels: list[str]):
        self.cmb_channel.clear()
        for ch in channels:
            self.cmb_channel.addItem(ch)
        self.btn_refresh_ch.setEnabled(True)
        self.log(f"방송사 {len(channels)}개 로드 완료")

    def _on_channel_error(self, msg: str):
        self.btn_refresh_ch.setEnabled(True)
        self.log(f"방송사 로드 오류: {msg}")
        QMessageBox.warning(self, "방송사 로드 오류", msg)

    def _update_phone_count(self):
        phones = parse_phones(self.txt_phones.toPlainText())
        self.lbl_phone_count.setText(f"{len(phones)}개 입력됨 (정제 후)")

    # ─────────────────────────────────────────────────────────────────
    # 쿼리 실행
    # ─────────────────────────────────────────────────────────────────

    def run_query(self):
        # ── 입력 검증 ──
        phones = parse_phones(self.txt_phones.toPlainText())
        if not phones:
            QMessageBox.warning(self, "입력 오류", "전화번호를 입력해 주세요.")
            return

        channel = self.cmb_channel.currentText().strip()
        if not channel:
            QMessageBox.warning(self, "입력 오류", "방송사를 선택해 주세요.")
            return

        exc_consultant = self.config_txt.get('Not_Charge_IDP', '').strip()
        exc_org        = self.config_txt.get('Not_PlaceofDuty', '').strip()

        if not exc_consultant or not exc_org:
            ans = QMessageBox.question(
                self, "설정 확인",
                "config.txt에서 제외 상담사 또는 제외 조직 정보를 읽지 못했습니다.\n"
                "상담사 쿼리 결과가 부정확할 수 있습니다.\n계속 진행하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        # ── UI 잠금 ──
        self.btn_query.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(True)
        self._clear_tables()

        # ── Worker 시작 ──
        self.worker = QueryWorker(
            self.db_config, phones, channel,
            exc_consultant, exc_org
        )
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self._on_query_finished)
        self.worker.error.connect(self._on_query_error)
        self.worker.start()

    def _on_query_finished(self, results: dict):
        self.query_results = results
        self._populate_results(results)
        self.progress_bar.setVisible(False)
        self.btn_query.setEnabled(True)
        self.btn_export.setEnabled(True)

        phones  = results.get('phones', [])
        all_dup = results.get('all_dup', {})
        all_60  = results.get('all_60_dup', {})
        ch_60   = results.get('ch_60_dup', {})
        self.log(
            f"조회 완료 | 전화번호 {len(phones)}개 | "
            f"전체중복 {sum(all_dup.values())}건 | "
            f"60일중복 {sum(all_60.values())}건 | "
            f"방송사60일 {sum(ch_60.values())}건"
        )

    def _on_query_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.btn_query.setEnabled(True)
        self.log(f"쿼리 오류: {msg}")
        QMessageBox.critical(
            self, "쿼리 오류",
            f"조회 중 오류가 발생했습니다.\n\n{msg}"
        )

    def _clear_tables(self):
        self.tbl_count.setRowCount(0)
        self.tbl_all_cons.setRowCount(0)
        self.tbl_ch_cons.setRowCount(0)

    def _populate_results(self, results: dict):
        phones     = results.get('phones', [])
        all_dup    = results.get('all_dup', {})
        all_60_dup = results.get('all_60_dup', {})
        ch_60_dup  = results.get('ch_60_dup', {})
        channel    = results.get('channel', '방송사')

        # 방송사명을 헤더·그룹박스 제목에 반영
        self.tbl_count.setHorizontalHeaderLabels([
            '전화번호', '전체방송중복',
            '전체방송 60일중복', f'{channel} 60일중복'
        ])
        self.grp_ch_cons.setTitle(f"{channel} 60일 상담사")

        # ── 중복 카운트 테이블 ──
        self.tbl_count.setRowCount(len(phones))
        for r_idx, phone in enumerate(phones):
            self.tbl_count.setItem(r_idx, 0, QTableWidgetItem(phone))

            for c_idx, cnt in enumerate([
                all_dup.get(phone, 0),
                all_60_dup.get(phone, 0),
                ch_60_dup.get(phone, 0)
            ], start=1):
                item = QTableWidgetItem(str(cnt))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if cnt > 0:
                    item.setForeground(QColor("#C00000"))
                    item.setFont(QFont("", -1, QFont.Weight.Bold))
                self.tbl_count.setItem(r_idx, c_idx, item)

        # ── 상담사 테이블 ──
        _fill_consultant_table(
            self.tbl_all_cons, results.get('all_60_consultant', [])
        )
        _fill_consultant_table(
            self.tbl_ch_cons, results.get('ch_60_consultant', [])
        )

    # ─────────────────────────────────────────────────────────────────
    # 엑셀 저장
    # ─────────────────────────────────────────────────────────────────

    def export_excel(self):
        if not self.query_results:
            QMessageBox.warning(self, "내보내기 오류", "먼저 조회를 실행해 주세요.")
            return

        channel = self.query_results.get('channel', '방송사')
        default_name = (
            f"중복추출_{channel}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

        filepath, _ = QFileDialog.getSaveFileName(
            self, "엑셀 파일 저장", default_name,
            "Excel 파일 (*.xlsx)"
        )
        if not filepath:
            return

        try:
            export_to_excel(self.query_results, filepath, channel)
            self.log(f"엑셀 저장 완료: {filepath}")
            QMessageBox.information(
                self, "저장 완료",
                f"파일이 저장되었습니다.\n\n{filepath}"
            )
        except Exception as e:
            self.log(f"엑셀 저장 오류: {e}")
            QMessageBox.critical(
                self, "저장 오류",
                f"엑셀 저장 중 오류가 발생했습니다.\n\n{e}"
            )


# =============================================================================
# 진입점
# =============================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
