@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

echo.
echo ╔══════════════════════════════════════════════╗
echo ║      전자세금계산서 뷰어  빌드 스크립트      ║
echo ║        Python 3.13 + PySide6 + lxml          ║
echo ╚══════════════════════════════════════════════╝
echo.

:: ── 1. Python 확인 ─────────────────────────────
echo [1/5] Python 버전 확인...
python --version > nul 2>&1
if errorlevel 1 (
    echo.
    echo  [오류] Python 을 찾을 수 없습니다.
    echo         https://python.org 에서 Python 3.11 이상을 설치하세요.
    echo         설치 시 "Add Python to PATH" 를 반드시 체크하세요.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo  OK : !PY_VER!

:: ── 2. pip 업그레이드 ──────────────────────────
echo.
echo [2/5] pip 업그레이드...
python -m pip install --upgrade pip --quiet
echo  OK

:: ── 3. 패키지 설치 ────────────────────────────
echo.
echo [3/5] 패키지 설치 (PySide6 / lxml / PyInstaller)
echo       -- 처음 실행 시 수 분이 소요될 수 있습니다 --
echo.
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo  [오류] 패키지 설치 실패. 네트워크 연결을 확인하세요.
    pause
    exit /b 1
)
echo  OK

:: ── 4. 이전 빌드 정리 ─────────────────────────
echo.
echo [4/5] 이전 빌드 파일 정리...
if exist "dist\세금계산서뷰어" (
    rmdir /s /q "dist\세금계산서뷰어"
    echo  이전 dist 삭제 완료
)
if exist "build" (
    rmdir /s /q "build"
    echo  이전 build 삭제 완료
)

:: ── 5. PyInstaller 빌드 ───────────────────────
echo.
echo [5/5] 실행파일 빌드 중...
echo       (3~10분 소요, 잠시 기다려 주세요)
echo.
python -m PyInstaller tax_invoice_viewer.spec --noconfirm
if errorlevel 1 (
    echo.
    echo  [오류] 빌드 실패.
    echo         위의 오류 메시지를 확인하세요.
    pause
    exit /b 1
)

:: ── 완료 ──────────────────────────────────────
echo.
echo ╔══════════════════════════════════════════════╗
echo ║              빌드 완료!                      ║
echo ╠══════════════════════════════════════════════╣
echo ║  실행파일 위치:                              ║
echo ║    dist\세금계산서뷰어\세금계산서뷰어.exe   ║
echo ║                                              ║
echo ║  dist\세금계산서뷰어\ 폴더 전체를           ║
echo ║  배포하거나 원하는 위치로 복사하세요.        ║
echo ╚══════════════════════════════════════════════╝
echo.

:: 빌드 결과 폴더 탐색기로 열기
explorer "dist\세금계산서뷰어"

pause