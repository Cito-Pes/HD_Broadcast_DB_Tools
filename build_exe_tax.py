# =============================================================================
# PyInstaller 전용 Windows 실행 파일(.exe) 빌드 자동화 스크립트
# 파일명: build_exe.py
# =============================================================================

import os
import subprocess
import sys

def build_program():
    print("▶ Windows 배포용 실행 파일(.exe) 빌드를 시작합니다...")
    
    # 주요 타깃 파일 정의
    script_path = "tax_invoice_viewer.py"
    icon_path = os.path.join("img", "ht.ico")
    
    if not os.path.exists(script_path):
        print(f"[오류] 대상 스크립트 '{script_path}'를 찾을 수 없습니다.")
        return

    # PyInstaller 빌드 명령어 설정
    # --noconsole: 실행 시 검은색 프롬프트 창이 뜨지 않도록 처리
    # --onefile: 하나의 독립된 단일 .exe 파일로 병합
    # --add-data: img/ 폴더 안의 png, ico 파일들을 프로그램 내부에 포함시킴
    cmd = [
        "pyinstaller",
        "--noconsole",
        "--onefile",
        f"--icon={icon_path}" if os.path.exists(icon_path) else "",
        "--add-data=img;img",  # 내부 자산 폴더 매핑 (Windows 구조)
        "--name=세금계산서 출력 뷰어_v1",
        script_path
    ]
    
    # 빈 값 제거
    cmd = [arg for arg in cmd if arg]
    
    try:
        # 빌드 프로세스 실행
        subprocess.check_call(cmd)
        print("\n" + "="*60)
        print("🎉 [성공] PyInstaller 빌드가 완료되었습니다!")
        print("👉 결과물 위치: ./dist/세금계산서_출력_뷰어_v1.exe")
        print("="*60 + "\n")
    except subprocess.CalledProcessError as e:
        print(f"\n[오류] 빌드 중 에러가 발생했습니다: {e}")
    except Exception as e:
        print(f"\n[오류] 예상치 못한 오류 발생: {e}")

if __name__ == "__main__":
    build_program()