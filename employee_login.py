from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from DB_conn import get_mssql_connection


QUERY_LOGIN = """\
SELECT A.sabun, A.saname
FROM   staff     AS A
INNER JOIN user_count AS B ON A.sabun = B.usrID
WHERE  A.sabun  = ?
  AND  B.pw     = ?
  AND  A.OutDate = ''
"""


@dataclass(frozen=True)
class LoginUser:
    sabun: str
    saname: str


def authenticate_employee(
    db_config: dict[str, Any],
    sabun: str,
    password: str,
) -> LoginUser | None:
    """Return LoginUser when employee credentials are valid, otherwise None."""
    sabun = sabun.strip()
    password = password.strip()
    if not sabun or not password:
        return None

    conn = get_mssql_connection(db_config)
    try:
        cursor = conn.cursor()
        cursor.execute(QUERY_LOGIN, (sabun, password))
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return None
    return LoginUser(sabun=str(row[0]).strip(), saname=str(row[1]).strip())


class LoginDialog(QDialog):
    """Reusable employee login dialog for HD PySide6 tools."""

    MAX_FAILS = 3

    def __init__(
        self,
        db_config: dict[str, Any],
        *,
        title: str = "사원 로그인",
        window_title: str = "로그인",
        parent=None,
    ):
        super().__init__(parent)
        self.db_config = db_config
        self.fail_count = 0
        self.user: LoginUser | None = None

        self.setWindowTitle(window_title)
        self.setFixedSize(360, 220)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        self._build_ui(title)
        self._apply_style()

    def _build_ui(self, title: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(30, 24, 30, 20)
        root.setSpacing(12)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            "font-size:16px; font-weight:bold; color:#1F3864;"
        )
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(lbl_title)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_sabun = QLineEdit()
        self.txt_sabun.setPlaceholderText("사번을 입력하세요")
        self.txt_sabun.setMinimumHeight(30)
        form.addRow("사  번 :", self.txt_sabun)

        self.txt_pw = QLineEdit()
        self.txt_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pw.setPlaceholderText("비밀번호를 입력하세요")
        self.txt_pw.setMinimumHeight(30)
        form.addRow("비밀번호 :", self.txt_pw)

        root.addLayout(form)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color:#C00000; font-size:11px;")
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.lbl_error)

        self.btn_login = QPushButton("로그인")
        self.btn_login.setMinimumHeight(34)
        self.btn_login.clicked.connect(self._try_login)
        root.addWidget(self.btn_login)

        self.txt_sabun.returnPressed.connect(self.txt_pw.setFocus)
        self.txt_pw.returnPressed.connect(self._try_login)

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #F4F7FA;
                font-family: '맑은 고딕', 'Malgun Gothic', sans-serif;
            }
            QLabel { font-size: 12px; color: #222222; }
            QLineEdit {
                border: 1px solid #A6B9D0;
                border-radius: 4px;
                padding: 4px 8px;
                background: #FFFFFF;
                font-size: 12px;
                color: #000000;
            }
            QLineEdit:focus { border-color: #2F5496; }
            QPushButton {
                background-color: #2F5496;
                color: #FFFFFF;
                border: 1px solid #1F3864;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover   { background-color: #3A67B5; }
            QPushButton:pressed { background-color: #1E3D7A; }
        """)

    def _try_login(self) -> None:
        sabun = self.txt_sabun.text().strip()
        password = self.txt_pw.text().strip()

        if not sabun or not password:
            self.lbl_error.setText("사번과 비밀번호를 모두 입력해 주세요.")
            return

        try:
            user = authenticate_employee(self.db_config, sabun, password)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "오류",
                f"로그인 중 오류가 발생했습니다.\n\n{exc}",
            )
            return

        if user:
            self.user = user
            self.accept()
            return

        self.fail_count += 1
        remaining = self.MAX_FAILS - self.fail_count
        if remaining <= 0:
            QMessageBox.critical(
                self,
                "로그인 실패",
                "로그인을 3회 실패하였습니다.\n프로그램을 종료합니다.",
            )
            self.reject()
            return

        self.lbl_error.setText(
            f"사번 또는 비밀번호가 올바르지 않습니다. (남은 시도: {remaining}회)"
        )
        self.txt_pw.clear()
        self.txt_pw.setFocus()


__all__ = [
    "QUERY_LOGIN",
    "LoginUser",
    "authenticate_employee",
    "LoginDialog",
]
