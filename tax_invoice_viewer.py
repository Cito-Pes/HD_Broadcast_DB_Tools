"""
국세청 전자세금계산서 XML 뷰어  v2.0
─────────────────────────────────────
• XSL 의존성 없음 — XML 직접 파싱 후 HTML 렌더링
• 여러 XML 파일을 탭으로 열기 (드래그 앤 드롭 지원)
• 인쇄 / PDF 저장
• Python 3.13 + PySide6
"""

import re
import sys
from pathlib import Path

from PySide6.QtCore    import Qt, QUrl
from PySide6.QtGui     import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel,
    QFileDialog, QMessageBox,
    QStatusBar, QFrame,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtPrintSupport     import QPrinter, QPrintDialog

try:
    from lxml import etree
    LXML_OK = True
except ImportError:
    LXML_OK = False

# ─────────────────────────────────────────────────────────────
# 국세청 KEC 표준 네임스페이스
# ─────────────────────────────────────────────────────────────
NS = ("urn:kr:or:kec:standard:Tax:"
      "ReusableAggregateBusinessInformationEntitySchemaModule:1:0")


# ─────────────────────────────────────────────────────────────
# XML 파싱
# ─────────────────────────────────────────────────────────────
def parse_tax_invoice(xml_path: str) -> dict:
    tree = etree.parse(xml_path)
    root = tree.getroot()

    def nsq(tag):   return f"{{{NS}}}{tag}"
    def ft(el, *parts):
        cur = el
        for p in parts:
            found = cur.find(nsq(p))
            if found is None:
                return ""
            cur = found
        return cur.text.strip() if cur.text else ""

    def fmt_reg(num):
        n = re.sub(r"\D", "", str(num))
        return f"{n[:3]}-{n[3:5]}-{n[5:]}" if len(n) == 10 else num

    def fmt_amt(s):
        try:    return f"{int(s):,}"
        except: return s or ""

    def fmt_date8(s):
        return f"{s[:4]}년 {s[4:6]}월 {s[6:8]}일" if len(s) >= 8 else s

    doc        = root.find(nsq("TaxInvoiceDocument"))
    settlement = root.find(nsq("TaxInvoiceTradeSettlement"))
    invoicer   = settlement.find(nsq("InvoicerParty"))
    invoicee   = settlement.find(nsq("InvoiceeParty"))
    summary    = settlement.find(nsq("SpecifiedMonetarySummation"))
    items      = root.findall(nsq("TaxInvoiceTradeLineItem"))

    type_code    = ft(doc, "TypeCode")
    purpose_code = ft(doc, "PurposeCode")
    doc_type = {
        "0101": "세금계산서",
        "0102": "수정세금계산서",
        "0103": "영세율세금계산서",
    }.get(type_code, "세금계산서")
    purpose = {"01": "청구", "02": "영수"}.get(purpose_code, "")

    parsed_items = []
    for item in items:
        d = ft(item, "PurchaseExpiryDateTime")
        parsed_items.append({
            "date":   f"{d[4:6]}/{d[6:8]}" if len(d) >= 8 else d,
            "name":   ft(item, "NameText"),
            "spec":   ft(item, "CharacteristicText"),
            "qty":    ft(item, "InvoiceQuantity"),
            "unit":   fmt_amt(ft(item, "UnitPriceAmount")),
            "amount": fmt_amt(ft(item, "InvoiceAmount")),
            "tax":    fmt_amt(ft(item, "TotalTax", "CalculatedAmount")),
            "note":   ft(item, "DescriptionText"),
        })

    return {
        "issue_id":    ft(doc, "IssueID"),
        "issue_date":  fmt_date8(ft(doc, "IssueDateTime")),
        "doc_type":    doc_type,
        "purpose":     purpose,
        "invoicer": {
            "reg_no":    fmt_reg(ft(invoicer, "ID")),
            "name":      ft(invoicer, "NameText"),
            "ceo":       ft(invoicer, "SpecifiedPerson",     "NameText"),
            "address":   ft(invoicer, "SpecifiedAddress",    "LineOneText"),
            "biz_type":  ft(invoicer, "TypeCode"),
            "biz_class": ft(invoicer, "ClassificationCode"),
            "email":     ft(invoicer, "DefinedContact",      "URICommunication"),
        },
        "invoicee": {
            "reg_no":    fmt_reg(ft(invoicee, "ID")),
            "name":      ft(invoicee, "NameText"),
            "ceo":       ft(invoicee, "SpecifiedPerson",          "NameText"),
            "address":   ft(invoicee, "SpecifiedAddress",         "LineOneText"),
            "biz_type":  ft(invoicee, "TypeCode"),
            "biz_class": ft(invoicee, "ClassificationCode"),
            "email":     ft(invoicee, "PrimaryDefinedContact",    "URICommunication"),
            "email2":    ft(invoicee, "SecondaryDefinedContact",  "URICommunication"),
        },
        "charge_total": fmt_amt(ft(summary, "ChargeTotalAmount")),
        "tax_total":    fmt_amt(ft(summary, "TaxTotalAmount")),
        "grand_total":  fmt_amt(ft(summary, "GrandTotalAmount")),
        "items": parsed_items,
    }


# ─────────────────────────────────────────────────────────────
# HTML 생성
# ─────────────────────────────────────────────────────────────
def generate_html(d: dict) -> str:
    inv   = d["invoicer"]
    invee = d["invoicee"]

    # 최소 4행 보장
    rows = list(d["items"])
    while len(rows) < 4:
        rows.append({"date":"","name":"","spec":"","qty":"",
                     "unit":"","amount":"","tax":"","note":""})

    item_rows = "".join(f"""
        <tr>
          <td class="tac">{r['date']}</td>
          <td class="tal">{r['name']}</td>
          <td class="tac">{r['spec']}</td>
          <td class="tac">{r['qty']}</td>
          <td class="tar">{r['unit']}</td>
          <td class="tar">{r['amount']}</td>
          <td class="tar">{r['tax']}</td>
          <td class="tac">{r['note']}</td>
        </tr>""" for r in rows)

    chk_y = "☑" if d["purpose"] == "영수" else "☐"
    chk_c = "☑" if d["purpose"] == "청구" else "☐"

    email2_str = (f"&nbsp;/&nbsp;{invee['email2']}"
                  if invee.get("email2") else "")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
  *   {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'맑은 고딕','Malgun Gothic',Arial,sans-serif;
          font-size:11px; background:#eef0f3; padding:24px; }}
  .page {{ background:#fff; width:820px; margin:0 auto;
           border:2px solid #37474f; padding:12px 14px;
           box-shadow:0 2px 8px rgba(0,0,0,.15); }}

  /* ── 제목 ── */
  .title-bar  {{ display:flex; align-items:flex-start; justify-content:space-between;
                 border-bottom:2px solid #37474f; padding-bottom:8px; margin-bottom:8px; }}
  .t-left     {{ display:flex; flex-direction:column; gap:2px; }}
  .t-doctitle {{ font-size:22px; font-weight:900; letter-spacing:6px; color:#1a237e; }}
  .t-doctype  {{ font-size:11px; color:#555; letter-spacing:2px; }}
  .t-right    {{ text-align:right; font-size:11px; line-height:1.9; }}
  .t-right strong {{ font-size:13px; }}
  .chk        {{ font-size:13px; margin-left:10px; }}
  .docid      {{ font-size:9px; color:#999; margin-top:2px; }}

  /* ── 공급자·공급받는자 ── */
  .parties   {{ display:grid; grid-template-columns:1fr 8px 1fr;
                margin-bottom:6px; }}
  .divider   {{ background:#37474f; }}
  table      {{ width:100%; border-collapse:collapse; }}
  td, th     {{ border:1px solid #b0bec5; padding:2px 5px; vertical-align:middle; }}
  .lbl       {{ background:#e3f2fd; font-weight:700; text-align:center;
                white-space:nowrap; width:55px; color:#0d47a1; font-size:10px; }}
  .pt        {{ font-size:12px; font-weight:900; text-align:center;
                color:#fff; padding:4px 0; letter-spacing:6px; }}
  .pt-sup    {{ background:#1565c0; }}
  .pt-rec    {{ background:#1b5e20; }}
  .rno       {{ font-size:13px; font-weight:700; letter-spacing:3px;
                text-align:center; }}

  /* ── 금액 요약 ── */
  .summary   {{ display:flex; border:1px solid #b0bec5;
                margin-bottom:6px; border-radius:2px; overflow:hidden; }}
  .sc        {{ flex:1; text-align:center; padding:5px 8px;
                border-right:1px solid #b0bec5; }}
  .sc:last-child {{ border-right:none; background:#fff8e1; }}
  .sc .sl    {{ font-size:10px; color:#777; letter-spacing:1px; }}
  .sc .sv    {{ font-size:15px; font-weight:800; color:#1a237e; margin-top:1px; }}
  .sc:last-child .sv {{ color:#b71c1c; }}

  /* ── 품목 ── */
  .items-tbl th {{ background:#e8eaf6; text-align:center;
                   font-size:10px; padding:3px; font-weight:700; }}
  .items-tbl td {{ height:24px; }}
  .foot-row td  {{ background:#fafafa; font-weight:700; font-size:12px; }}

  /* 정렬 헬퍼 */
  .tal {{ text-align:left;   padding-left:6px; }}
  .tar {{ text-align:right;  padding-right:6px; }}
  .tac {{ text-align:center; }}

  .footer {{ margin-top:8px; font-size:9px; color:#aaa; text-align:right; }}

  @media print {{
    body  {{ background:#fff; padding:0; }}
    .page {{ border:none; box-shadow:none; width:100%; }}
  }}
</style>
</head>
<body>
<div class="page">

  <!-- 제목 -->
  <div class="title-bar">
    <div class="t-left">
      <div class="t-doctitle">{d['doc_type']}</div>
      <div class="t-doctype">공급자 보관용</div>
      <div class="docid">문서번호 : {d['issue_id']}</div>
    </div>
    <div class="t-right">
      <div>작 성 일 자 &nbsp;<strong>{d['issue_date']}</strong></div>
      <div>
        <span class="chk">{chk_y}</span> 영수
        <span class="chk">{chk_c}</span> 청구
      </div>
    </div>
  </div>

  <!-- 공급자 / 공급받는자 -->
  <div class="parties">

    <table>
      <tr><td colspan="4" class="pt pt-sup">공&nbsp;&nbsp;&nbsp;급&nbsp;&nbsp;&nbsp;자</td></tr>
      <tr>
        <td class="lbl">등 록 번 호</td>
        <td colspan="3" class="rno">{inv['reg_no']}</td>
      </tr>
      <tr>
        <td class="lbl">상&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;호</td>
        <td style="width:42%">{inv['name']}</td>
        <td class="lbl">대 표 자</td>
        <td>{inv['ceo']}</td>
      </tr>
      <tr>
        <td class="lbl">사업장주소</td>
        <td colspan="3">{inv['address']}</td>
      </tr>
      <tr>
        <td class="lbl">업&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;태</td>
        <td>{inv['biz_type']}</td>
        <td class="lbl">종&nbsp;&nbsp;&nbsp;&nbsp;목</td>
        <td>{inv['biz_class']}</td>
      </tr>
      <tr>
        <td class="lbl">이 메 일</td>
        <td colspan="3">{inv['email']}</td>
      </tr>
    </table>

    <div class="divider"></div>

    <table>
      <tr><td colspan="4" class="pt pt-rec">공&nbsp;급&nbsp;받&nbsp;는&nbsp;자</td></tr>
      <tr>
        <td class="lbl">등 록 번 호</td>
        <td colspan="3" class="rno">{invee['reg_no']}</td>
      </tr>
      <tr>
        <td class="lbl">상&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;호</td>
        <td style="width:42%">{invee['name']}</td>
        <td class="lbl">대 표 자</td>
        <td>{invee['ceo']}</td>
      </tr>
      <tr>
        <td class="lbl">사업장주소</td>
        <td colspan="3">{invee['address']}</td>
      </tr>
      <tr>
        <td class="lbl">업&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;태</td>
        <td>{invee['biz_type']}</td>
        <td class="lbl">종&nbsp;&nbsp;&nbsp;&nbsp;목</td>
        <td>{invee['biz_class']}</td>
      </tr>
      <tr>
        <td class="lbl">이 메 일</td>
        <td colspan="3">{invee['email']}{email2_str}</td>
      </tr>
    </table>

  </div>

  <!-- 금액 요약 -->
  <div class="summary">
    <div class="sc">
      <div class="sl">공 급 가 액</div>
      <div class="sv">₩&nbsp;{d['charge_total']}</div>
    </div>
    <div class="sc">
      <div class="sl">세 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 액</div>
      <div class="sv">₩&nbsp;{d['tax_total']}</div>
    </div>
    <div class="sc">
      <div class="sl">합 계 금 액</div>
      <div class="sv">₩&nbsp;{d['grand_total']}</div>
    </div>
  </div>

  <!-- 품목 -->
  <table class="items-tbl">
    <thead>
      <tr>
        <th style="width:50px">월/일</th>
        <th>품&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;목</th>
        <th style="width:55px">규격</th>
        <th style="width:45px">수량</th>
        <th style="width:75px">단가</th>
        <th style="width:80px">공급가액</th>
        <th style="width:70px">세액</th>
        <th style="width:65px">비고</th>
      </tr>
    </thead>
    <tbody>{item_rows}
    </tbody>
    <tfoot>
      <tr class="foot-row">
        <td class="tac" colspan="2">합&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;계</td>
        <td colspan="3"></td>
        <td class="tar">{d['charge_total']}</td>
        <td class="tar">{d['tax_total']}</td>
        <td></td>
      </tr>
    </tfoot>
  </table>

  <div class="footer">※ 이 문서는 「전자세금계산서 발급 및 전송에 관한 규정」에 따라 작성된 전자세금계산서입니다.</div>
</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────
# 탭 위젯 (단일 XML)
# ─────────────────────────────────────────────────────────────
class InvoiceTab(QWidget):
    def __init__(self, xml_path: str, parent=None):
        super().__init__(parent)
        self.xml_path = xml_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web = QWebEngineView()
        layout.addWidget(self.web)

        data = parse_tax_invoice(xml_path)
        html = generate_html(data)
        # setHtml 은 base_url 없이도 인라인 CSS/HTML은 완전히 렌더링됨
        self.web.setHtml(html, QUrl("about:blank"))

    def print_invoice(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() == QPrintDialog.DialogCode.Accepted:
            self.web.page().print(printer, lambda ok: None)

    def save_pdf(self, save_path: str):
        self.web.page().printToPdf(save_path)


# ─────────────────────────────────────────────────────────────
# 메인 윈도우
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("전자세금계산서 뷰어")
        self.resize(940, 720)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 4)
        root.setSpacing(6)

        # ── 툴바 ──
        tb = QHBoxLayout()
        tb.setSpacing(6)

        def btn(text, slot, shortcut=None):
            b = QPushButton(text)
            b.setFixedHeight(32)
            b.clicked.connect(slot)
            if shortcut:
                b.setShortcut(shortcut)
            tb.addWidget(b)
            return b

        self.btn_open  = btn("📂  XML 열기",  self.open_xml_files, "Ctrl+O")
        self.btn_print = btn("🖨  인쇄",       self.print_current,  "Ctrl+P")
        self.btn_pdf   = btn("💾  PDF 저장",   self.save_pdf_current)
        self.btn_close = btn("✕  탭 닫기",     self.close_current_tab, "Ctrl+W")

        for b in (self.btn_print, self.btn_pdf, self.btn_close):
            b.setEnabled(False)

        tb.addStretch()
        root.addLayout(tb)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line)

        # ── 빈 화면 ──
        self.empty = QLabel(
            "XML 세금계산서 파일을 열어주세요\n"
            "(📂 버튼 또는 파일을 창에 드래그)"
        )
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setStyleSheet("color:#aaa; font-size:15px;")

        # ── 탭 ──
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._remove_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.hide()

        root.addWidget(self.empty)
        root.addWidget(self.tabs)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("준비")
        self.setAcceptDrops(True)

    # ── XML 열기 ──
    def open_xml_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "세금계산서 XML 파일 선택", "",
            "XML 세금계산서 (*.xml);;모든 파일 (*.*)"
        )
        for p in paths:
            self._load_xml(p)

    def _load_xml(self, xml_path: str):
        if not LXML_OK:
            QMessageBox.critical(self, "오류",
                "lxml 패키지가 없습니다.\n\npip install lxml")
            return
        try:
            tab  = InvoiceTab(xml_path)
            name = Path(xml_path).stem[:22]
            idx  = self.tabs.addTab(tab, name)
            self.tabs.setTabToolTip(idx, xml_path)
            self.tabs.setCurrentIndex(idx)
            self.empty.hide()
            self.tabs.show()
            self._set_btns(True)
            self.statusBar().showMessage(f"로드 완료: {xml_path}")
        except etree.XMLSyntaxError as e:
            QMessageBox.critical(self, "XML 오류", f"파싱 실패:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "오류", str(e))

    # ── 인쇄 / PDF ──
    def print_current(self):
        if t := self._cur():
            t.print_invoice()

    def save_pdf_current(self):
        if not (t := self._cur()):
            return
        default = Path(t.xml_path).stem + ".pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "PDF 저장", default, "PDF (*.pdf)")
        if path:
            t.save_pdf(path)
            self.statusBar().showMessage(f"PDF 저장: {path}")

    # ── 탭 관리 ──
    def close_current_tab(self):
        self._remove_tab(self.tabs.currentIndex())

    def _remove_tab(self, idx: int):
        if idx < 0:
            return
        self.tabs.removeTab(idx)
        if self.tabs.count() == 0:
            self.tabs.hide()
            self.empty.show()
            self._set_btns(False)

    def _on_tab_changed(self, idx: int):
        self._set_btns(self.tabs.count() > 0)

    def _cur(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, InvoiceTab) else None

    def _set_btns(self, on: bool):
        for b in (self.btn_print, self.btn_pdf, self.btn_close):
            b.setEnabled(on)

    # ── 드래그 앤 드롭 ──
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            if any(u.toLocalFile().lower().endswith(".xml")
                   for u in e.mimeData().urls()):
                e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().endswith(".xml"):
                self._load_xml(p)


# ─────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("전자세금계산서 뷰어")
    app.setStyle("Fusion")

    if not LXML_OK:
        QMessageBox.critical(
            None, "의존 패키지 없음",
            "lxml 이 설치되어 있지 않습니다.\n\n"
            "pip install lxml\n\n설치 후 재실행해 주세요."
        )
        sys.exit(1)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()