# =============================================================================
# 방송 DB 처리 시스템 (레이아웃 비율 및 가독성 버그 수정 버전)
# 기능1: 전화번호 기반 중복 정보 추출 + 엑셀 저장 (단일 시트/테이블 통합)
# 기능2: 상담내역 등록 (추후 구현)
#
# 개발환경: Python 3.13.6 / PySide6 / Windows 전용
# DB: SQL Server 2008 R2 (pyodbc — Windows ODBC 드라이버 직접 사용)
# Excel: xlsxwriter (쓰기 전용, 메모리 효율, 풍부한 포맷 API)
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
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QMessageBox, QFileDialog,
    QSplitter, QGroupBox, QFrame
)


# 프로그램 최상단에 추가해 두면 배포 시 아이콘 누락 오류를 원천 차단합니다.
def resource_path(relative_path):
    """ PyInstaller 임시 폴더 환경 및 개발 환경의 절대 경로를 반환합니다 """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# 예시: 아이콘 세팅 시
    # self.setWindowIcon(QIcon(resource_path("img/ht.ico")))

# =============================================================================
# ★ 수정 필요: Google Drive 공유 링크 및 Config 식별자
# =============================================================================

DB_DIR     = "./DB"
DB_FILE    = "Config_DB.db"
CONFIG_NAME = "HD_MSSQL"   # DBCON 테이블의 Name 값
CONFIG_TXT  = "./config.txt"

def load_config_txt(filepath: str = CONFIG_TXT) -> dict[str, str, str]:
    config: dict[str, str, str] = {'Not_Charge_IDP': '', 'Not_PlaceofDuty': '', 'google_doc_key':''}
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

config_txt = load_config_txt(CONFIG_TXT)
DOC_Key = config_txt.get('google_doc_key', '').strip()
GDRIVE_URL = f"https://drive.google.com/file/d/{DOC_Key}/view?usp=drive_link"

# =============================================================================
# SQL 쿼리 정의 (기존 유지)
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
    return re.sub(r'[^0-9]', '', raw)

def parse_phones(text: str) -> list[str]:
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
    return ', '.join(f"'{item}'" for item in items)



def safe_str(val) -> str:
    if val is None:
        return ''
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%d')
    return str(val)

# =============================================================================
# DB 접속 및 다운로드 관련
# =============================================================================
def download_db() -> tuple[bool, str]:
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
        if "text/html" in resp.headers.get("Content-Type", ""):
            for key, value in resp.cookies.items():
                if key.startswith("download_warning"):
                    download_url = f"https://drive.google.com/uc?export=download&confirm={value}&id={file_id}"
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
    db_path = os.path.join(DB_DIR, DB_FILE)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DB_Type, Host, Port, DB_Name, DB_ID, DB_PW FROM DBCON WHERE Name = ?", (CONFIG_NAME,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise LookupError(f"DBCON 테이블에 Name='{CONFIG_NAME}' 레코드가 없습니다.")
        return {"DB_Type": row[0], "Host": row[1], "Port": row[2], "DB_Name": row[3], "DB_ID": row[4], "DB_PW": row[5]}
    except Exception as e:
        raise Exception(f"DB 설정 로드 실패: {e}")

def get_mssql_connection(cfg: dict) -> pyodbc.Connection:
    conn_str = f"DRIVER={{{cfg['DB_Type']}}};SERVER={cfg['Host']},{cfg['Port']};DATABASE={cfg['DB_Name']};UID={cfg['DB_ID']};PWD={cfg['DB_PW']}"
    return pyodbc.connect(conn_str, timeout=30)

# =============================================================================
# Worker Threads
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

class QueryWorker(QThread):
    progress = Signal(str)
    finished = Signal(dict)
    error    = Signal(str)

    def __init__(self, db_config: dict, phones: list[str], channel: str, exc_consultant: str, exc_org: str):
        super().__init__()
        self.db_config      = db_config
        self.phones         = phones
        self.channel        = channel
        self.exc_consultant = exc_consultant
        self.exc_org        = exc_org

    def run(self):
        try:
            phones_in = build_in_clause(self.phones)
            channel_in = f"'{self.channel}'"

            self.progress.emit("SQL Server 연결 중...")
            conn   = get_mssql_connection(self.db_config)
            cursor = conn.cursor()
            results: dict = {}

            self.progress.emit("[1/5] 전체 방송 중복 조회 중...")
            cursor.execute(QUERY_ALL_DUP.format(phones=phones_in))
            results['all_dup'] = {row[0]: row[1] for row in cursor.fetchall()}

            self.progress.emit("[2/5] 전체방송 최근 60일 중복 조회 중...")
            cursor.execute(QUERY_ALL_60_DUP.format(phones=phones_in))
            results['all_60_dup'] = {row[0]: row[1] for row in cursor.fetchall()}

            self.progress.emit("[3/5] 최근 60일 방송사 중복 조회 중...")
            cursor.execute(QUERY_60_CHANNEL_DUP.format(phones=phones_in, channel=channel_in))
            results['ch_60_dup'] = {row[0]: row[1] for row in cursor.fetchall()}

            self.progress.emit("[4/5] 전체 60일 상담사 조회 중...")
            cursor.execute(QUERY_ALL_60_CONSULTANT.format(phones=phones_in, exc_consultant=self.exc_consultant, exc_org=self.exc_org))
            results['all_60_consultant'] = [
                {'phone': safe_str(row[0]), 'saname': safe_str(row[1])} for row in cursor.fetchall()
            ]

            self.progress.emit("[5/5] 방송사 60일 상담사 조회 중...")
            cursor.execute(QUERY_CHANNEL_60_CONSULTANT.format(phones=phones_in, channel=channel_in, exc_consultant=self.exc_consultant, exc_org=self.exc_org))
            results['ch_60_consultant'] = [
                {'phone': safe_str(row[0]), 'saname': safe_str(row[1])} for row in cursor.fetchall()
            ]

            conn.close()
            results['phones']  = self.phones
            results['channel'] = self.channel

            self.progress.emit("조회 완료!")
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

# =============================================================================
# 데이터 병합 가공 함수
# =============================================================================
def build_integrated_data(results: dict) -> list[dict]:
    phones      = results.get('phones', [])
    all_dup     = results.get('all_dup', {})
    all_60_dup  = results.get('all_60_dup', {})
    ch_60_dup   = results.get('ch_60_dup', {})
    all_60_cons = results.get('all_60_consultant', [])
    ch_60_cons  = results.get('ch_60_consultant', [])

    all_cons_map = {}
    for item in all_60_cons:
        ph = item['phone']
        name = item['saname'].strip()
        if name:
            all_cons_map.setdefault(ph, set()).add(name)

    ch_cons_map = {}
    for item in ch_60_cons:
        ph = item['phone']
        name = item['saname'].strip()
        if name:
            ch_cons_map.setdefault(ph, set()).add(name)

    integrated = []
    for phone in phones:
        val_all_dup = all_dup.get(phone, 0) + 1
        val_all_60  = all_60_dup.get(phone, 0) + 1
        val_ch_60   = ch_60_dup.get(phone, 0) + 1

        str_all_cons = ", ".join(sorted(list(all_cons_map.get(phone, []))))
        str_ch_cons  = ", ".join(sorted(list(ch_cons_map.get(phone, []))))

        integrated.append({
            'phone': phone,
            'all_dup': val_all_dup,
            'all_60_dup': val_all_60,
            'ch_60_dup': val_ch_60,
            'all_consultant': str_all_cons,
            'ch_consultant': str_ch_cons
        })
    return integrated

# =============================================================================
# Excel 내보내기
# =============================================================================
def export_to_excel(results: dict, filepath: str, channel_name: str) -> None:
    wb = xlsxwriter.Workbook(filepath)
    ws = wb.add_worksheet("중복데이터")

    ws.hide_gridlines(0) 
    ws.set_column(0, 0, 18)
    ws.set_column(1, 3, 16)
    ws.set_column(4, 5, 26)

    C_HDR_BG   = "#2F5496"
    C_EVEN_BG  = "#F2F5F9"
    C_BORDER   = "#A6B9D0"
    C_RED_TEXT = "#C00000"

    fmt_hdr = wb.add_format({
        'bold': True, 'font_color': '#FFFFFF', 'bg_color': C_HDR_BG,
        'align': 'center', 'valign': 'vcenter', 'border': 1, 'border_color': C_BORDER, 'font_size': 10
    })

    def _get_data_format(align: str, is_even: bool, is_red: bool = False):
        opt = {'align': align, 'valign': 'vcenter', 'border': 1, 'border_color': C_BORDER, 'font_size': 10}
        if is_even:
            opt['bg_color'] = C_EVEN_BG
        if is_red:
            opt['bold'] = True
            opt['font_color'] = C_RED_TEXT
        return wb.add_format(opt)

    headers = ['전화번호', '전체방송중복', '전체방송 60일중복', f'{channel_name} 60일중복', '전체 60일 상담사명', f'{channel_name} 60일 상담사명']
    ws.set_row(0, 26)
    for c_idx, text in enumerate(headers):
        ws.write(0, c_idx, text, fmt_hdr)

    data_list = build_integrated_data(results)
    for r_idx, row in enumerate(data_list, start=1):
        ws.set_row(r_idx, 22)
        even = (r_idx % 2 == 0)

        ws.write(r_idx, 0, row['phone'],          _get_data_format('left', even))
        ws.write(r_idx, 1, row['all_dup'],        _get_data_format('center', even, row['all_dup'] > 1))
        ws.write(r_idx, 2, row['all_60_dup'],     _get_data_format('center', even, row['all_60_dup'] > 1))
        ws.write(r_idx, 3, row['ch_60_dup'],      _get_data_format('center', even, row['ch_60_dup'] > 1))
        ws.write(r_idx, 4, row['all_consultant'], _get_data_format('left', even))
        ws.write(r_idx, 5, row['ch_consultant'],  _get_data_format('left', even))

    ws.freeze_panes(1, 0)
    wb.close()

# =============================================================================
# 메인 UI 클래스
# =============================================================================
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.db_config:     dict | None  = None
        self.query_results: dict | None  = None
        self.worker:        QueryWorker | None       = None
        self.ch_worker:     ChannelLoadWorker | None = None
        self.config_txt:    dict = {}

        self.setWindowTitle("방송 DB 처리 시스템 v1.1")
        self.setMinimumSize(1150, 760)

        self._build_ui()
        self._apply_styles()
        self.load_config()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 4)
        root_layout.setSpacing(4)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root_layout.addWidget(self.tabs)

        self.tabs.addTab(self._build_tab_duplicate(),     "📋  중복 정보 추출")
        self.tabs.addTab(self._build_tab_consultation(),  "📝  상담내역 등록")

        self.statusBar().showMessage("초기화 중...")
        
        

    def _build_tab_duplicate(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        # [수정] 조회 설정 영역 고정 높이 처리 및 레이아웃 슬림화
        ctrl_box = QGroupBox("조회 설정")
        ctrl_box.setMaximumHeight(65) 
        ctrl_lay = QHBoxLayout(ctrl_box)
        ctrl_lay.setContentsMargins(12, 4, 12, 8)
        ctrl_lay.setSpacing(10)

        ctrl_lay.addWidget(QLabel("방송사:"))
        self.cmb_channel = QComboBox()
        self.cmb_channel.setMinimumWidth(160)
        ctrl_lay.addWidget(self.cmb_channel)

        self.btn_refresh_ch = QPushButton("🔄")
        self.btn_refresh_ch.setFixedSize(32, 28)
        self.btn_refresh_ch.clicked.connect(self.load_channels)
        ctrl_lay.addWidget(self.btn_refresh_ch)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        ctrl_lay.addWidget(sep)

        self.lbl_config_info = QLabel("설정 로딩 중...")
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

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setMaximumHeight(14)
        self.progress_bar.setVisible(False)
        lay.addWidget(self.progress_bar)

        # 메인 가로 분할 스플리터
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 좌측 입력 창
        left = QWidget()
        left.setMaximumWidth(270)
        left.setMinimumWidth(220)
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(0, 4, 6, 0)
        l_lay.setSpacing(4)

        lbl_ph = QLabel("전화번호 입력")
        lbl_ph.setStyleSheet("font-weight:bold; font-size:12px; color: #1F3864;")
        l_lay.addWidget(lbl_ph)

        lbl_hint = QLabel("엑셀 열 복사 후 붙여넣기 (Ctrl+V)\n공백·하이픈 자동 제거")
        lbl_hint.setStyleSheet("color:#666; font-size:10px;")
        l_lay.addWidget(lbl_hint)

        self.txt_phones = QPlainTextEdit()
        self.txt_phones.setPlaceholderText("예시:\n01012345678\n010-9876-5432")
        self.txt_phones.setFont(QFont("Consolas", 10))
        self.txt_phones.textChanged.connect(self._update_phone_count)
        l_lay.addWidget(self.txt_phones)

        self.lbl_phone_count = QLabel("0개 입력됨")
        l_lay.addWidget(self.lbl_phone_count)

        btn_clear = QPushButton("지우기")
        btn_clear.setObjectName("btnSecondary")
        btn_clear.setMaximumWidth(70)
        btn_clear.clicked.connect(self.txt_phones.clear)
        l_lay.addWidget(btn_clear)

        splitter.addWidget(left)

        # 우측 결과 테이블 창
        right = QWidget()
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(4, 4, 0, 0)
        r_lay.setSpacing(4)

        lbl_result = QLabel("조회 결과 통합 리스트")
        lbl_result.setStyleSheet("font-weight:bold; font-size:12px; color: #1F3864;")
        r_lay.addWidget(lbl_result)

        self.grp_main_result = QGroupBox("통합 데이터 분석 결과")
        g_lay = QVBoxLayout(self.grp_main_result)
        g_lay.setContentsMargins(8, 12, 8, 8)

        # 단일 테이블 위젯 선언
        self.tbl_integrated = QTableWidget()
        self.tbl_integrated.setColumnCount(6)
        self.tbl_integrated.setHorizontalHeaderLabels(['전화번호', '전체방송중복', '전체방송 60일중복', '방송사 60일중복', '전체 60일 상담사명', '방송사 60일 상담사명'])
        self.tbl_integrated.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.tbl_integrated.horizontalHeader().setStretchLastSection(True)
        self.tbl_integrated.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_integrated.setAlternatingRowColors(True)
        self.tbl_integrated.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tbl_integrated.verticalHeader().setDefaultSectionSize(28)
        self.tbl_integrated.verticalHeader().setVisible(False)
        
        # 기본 컬럼 너비 밸런스 조정
        self.tbl_integrated.setColumnWidth(0, 130)
        self.tbl_integrated.setColumnWidth(1, 100)
        self.tbl_integrated.setColumnWidth(2, 120)
        self.tbl_integrated.setColumnWidth(3, 120)
        self.tbl_integrated.setColumnWidth(4, 180)
        self.tbl_integrated.setColumnWidth(5, 180)

        g_lay.addWidget(self.tbl_integrated)
        r_lay.addWidget(self.grp_main_result)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        lay.addWidget(splitter)

        return w

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

    def _apply_styles(self):
        # [수정] 가독성 향상 및 텍스트 묻힘 증상 제거 (테마 색상 명도 대조 최적화)
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #F4F7FA;
                font-family: '맑은 고딕', 'Malgun Gothic', sans-serif;
                font-size: 12px;
                color: #111111;
            }
            QTabWidget::pane {
                border: 1px solid #A6B9D0;
                background: #FFFFFF;
            }
            QTabBar::tab {
                background: #E2EBF5;
                border: 1px solid #A6B9D0;
                border-bottom: none;
                padding: 6px 20px;
                font-size: 12px;
                color: #444444;
                border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:selected {
                background: #2F5496;
                color: #FFFFFF;
                font-weight: bold;
                border-color: #2F5496;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #B0C4DE;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 4px;
                background: #FFFFFF;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: #1F3864;
            }
            QPushButton {
                background-color: #2F5496;
                color: #FFFFFF;
                border: 1px solid #1F3864;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover   { background-color: #3A67B5; }
            QPushButton:pressed { background-color: #1E3D7A; }
            QPushButton:disabled { background-color: #D3D3D3; color: #777777; border-color: #CCCCCC; }
            QPushButton#btnSecondary {
                background-color: #7F8C8D;
                border-color: #616A6B;
            }
            
            /* [버그 수정] 가독성이 차단되던 테이블 위젯 배경색 포맷 교정 */
            QTableWidget {
                gridline-color: #D6E4F0;
                background-color: #FFFFFF;
                color: #111111;
                border: 1px solid #A6B9D0;
                font-size: 11px;
            }
            /* 홀수 행 배경색 흰색 고정 */
            QTableWidget::item {
                background-color: #FFFFFF;
                color: #111111;
            }
            /* 짝수 행(Alternating) 배경색을 아주 밝은 회색으로 변경해 텍스트 가시성 보장 */
            QTableWidget::alternate-background-color {
                background-color: #F8FAFC;
            }
            /* 마우스 선택 행 배경 포맷 수정 */
            QTableWidget::item:selected {
                background-color: #E2EFDA;
                color: #000000;
            }
            
            QHeaderView::section {
                background-color: #2F5496;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 11px;
                padding: 6px 2px;
                border: 1px solid #1F3864;
            }
            QPlainTextEdit, QComboBox {
                border: 1px solid #A6B9D0;
                border-radius: 4px;
                background: #FFFFFF;
                color: #000000;
                padding: 2px;
            }
        """)

    def log(self, msg: str):
        self.statusBar().showMessage(msg)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def load_config(self):
        self.log("설정 파일 확인 중...")
        self.config_txt = load_config_txt(CONFIG_TXT)
        exc_idp = self.config_txt.get('Not_Charge_IDP', '').strip()
        exc_org = self.config_txt.get('Not_PlaceofDuty', '').strip()
        DOC_Key = self.config_txt.get('google_doc_key', '').strip()

        if exc_idp or exc_org:
            preview = f"제외상담사 설정 {len(exc_idp.split(','))}개 | 제외조직 설정 {len(exc_org.split(','))}개"
            self.lbl_config_info.setText(preview)
        else:
            self.lbl_config_info.setText("⚠ config.txt 없음 또는 설정 누락")
            self.lbl_config_info.setStyleSheet("color:#C00000; font-weight:bold;")

        db_path = os.path.join(DB_DIR, DB_FILE)
        if not os.path.exists(db_path):
            self.log("Config_DB.db 없음 → Google Drive 다운로드 중...")
            ok, result = download_db()
            if not ok:
                QMessageBox.critical(self, "설정 로드 실패", f"Config_DB.db 다운로드 불가.\n오류: {result}")
                return

        try:
            self.db_config = load_db_config()
            self.log(f"DB 준비 완료 → {self.db_config['Host']} / {self.db_config['DB_Name']}")
            self.btn_query.setEnabled(True)
            self.load_channels()
        except Exception as e:
            QMessageBox.critical(self, "DB 설정 오류", str(e))

    def load_channels(self):
        if not self.db_config:
            return
        self.btn_refresh_ch.setEnabled(False)
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
        QMessageBox.warning(self, "방송사 로드 오류", msg)

    def _update_phone_count(self):
        phones = parse_phones(self.txt_phones.toPlainText())
        self.lbl_phone_count.setText(f"{len(phones)}개 입력됨 (정제 후)")

    def run_query(self):
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

        self.btn_query.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.tbl_integrated.setRowCount(0)

        self.worker = QueryWorker(self.db_config, phones, channel, exc_consultant, exc_org)
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
        self.log("통합 테이블 조회 완료")

    def _on_query_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.btn_query.setEnabled(True)
        QMessageBox.critical(self, "쿼리 오류", f"조회 중 오류가 발생했습니다.\n\n{msg}")

    def _populate_results(self, results: dict):
        channel = results.get('channel', '방송사')
        
        self.tbl_integrated.setHorizontalHeaderLabels([
            '전화번호', '전체방송중복', '전체방송 60일중복', f'{channel} 60일중복', '전체 60일 상담사명', f'{channel} 60일 상담사명'
        ])
        self.grp_main_result.setTitle(f"통합 분석 결과 ({channel} 기준)")

        data_list = build_integrated_data(results)
        self.tbl_integrated.setRowCount(len(data_list))

        for r_idx, row in enumerate(data_list):
            # 전화번호
            ph_item = QTableWidgetItem(row['phone'])
            self.tbl_integrated.setItem(r_idx, 0, ph_item)

            # 카운트 정보 셀 (+1 보정 반영)
            counts = [row['all_dup'], row['all_60_dup'], row['ch_60_dup']]
            for i, cnt in enumerate(counts, start=1):
                cnt_item = QTableWidgetItem(str(cnt))
                cnt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # 중복이 실질적으로 감지된 항목만 진한 버건디레드로 굵게 강조
                if cnt > 1:
                    cnt_item.setForeground(QColor("#B30000"))
                    font = cnt_item.font()
                    font.setBold(True)
                    cnt_item.setFont(font)
                self.tbl_integrated.setItem(r_idx, i, cnt_item)

            # 전체 60일 상담사
            all_cons_item = QTableWidgetItem(row['all_consultant'])
            if row['all_consultant']:
                all_cons_item.setForeground(QColor("#1F3864"))
            self.tbl_integrated.setItem(r_idx, 4, all_cons_item)

            # 방송사 60일 상담사
            ch_cons_item = QTableWidgetItem(row['ch_consultant'])
            if row['ch_consultant']:
                ch_cons_item.setForeground(QColor("#2F5496"))
            self.tbl_integrated.setItem(r_idx, 5, ch_cons_item)

    def export_excel(self):
        if not self.query_results:
            QMessageBox.warning(self, "내보내기 오류", "먼저 조회를 실행해 주세요.")
            return

        channel = self.query_results.get('channel', '방송사')
        default_name = f"중복추출통합_{channel}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        filepath, _ = QFileDialog.getSaveFileName(self, "엑셀 파일 저장", default_name, "Excel 파일 (*.xlsx)")
        if not filepath:
            return

        try:
            export_to_excel(self.query_results, filepath, channel)
            self.log(f"엑셀 저장 완료: {filepath}")
            QMessageBox.information(self, "저장 완료", f"통합 엑셀 파일이 저장되었습니다.\n\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"엑셀 저장 중 오류 발생:\n{e}")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()