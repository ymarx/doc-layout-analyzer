@echo off
REM Document Layout Analyzer - Windows 자동 설치 스크립트
REM Python 3.11+ 필요

echo ========================================
echo Document Layout Analyzer Windows Installer
echo ========================================
echo.

REM Python 버전 확인
echo [INFO] Python 버전 확인...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python이 설치되지 않았습니다.
    echo https://www.python.org/downloads/ 에서 Python 3.11+ 설치해주세요.
    echo PATH 환경변수에 Python이 추가되었는지 확인하세요.
    pause
    exit /b 1
)

python --version

REM Python 버전 체크 (3.11 이상)
python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11 이상이 필요합니다.
    pause
    exit /b 1
)

REM 가상환경 생성
echo.
echo [INFO] 가상환경 생성 중...
if exist venv (
    echo [INFO] 기존 가상환경 발견. 삭제 후 재생성합니다.
    rmdir /s /q venv
)
python -m venv venv

REM 가상환경 활성화
echo [INFO] 가상환경 활성화...
call venv\Scripts\activate.bat

REM pip 업그레이드
echo.
echo [INFO] pip, setuptools, wheel 업그레이드...
python -m pip install --upgrade pip setuptools wheel

REM PyTorch 설치 (CPU 버전)
echo.
echo [INFO] PyTorch CPU 버전 설치 중... (시간이 걸릴 수 있습니다)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

REM 기본 패키지 설치
echo.
echo [INFO] 기본 패키지 설치 중...
pip install -r requirements_windows.txt

REM 추가 패키지 개별 설치
echo.
echo [INFO] 추가 패키지 설치 중...

REM camelot-py 설치 시도
echo [INFO] camelot-py 설치 시도...
pip install camelot-py[cv] >nul 2>&1
if errorlevel 1 (
    echo [WARNING] camelot-py 설치 실패. PDF 테이블 추출 기능이 제한될 수 있습니다.
)

REM tabula-py 설치 시도
echo [INFO] tabula-py 설치 시도...
pip install tabula-py >nul 2>&1
if errorlevel 1 (
    echo [WARNING] tabula-py 설치 실패. Java가 설치되어 있는지 확인하세요.
)

REM konlpy 설치 시도
echo [INFO] konlpy 설치 시도...
pip install konlpy >nul 2>&1
if errorlevel 1 (
    echo [WARNING] konlpy 설치 실패. 한국어 NLP 기능이 제한될 수 있습니다.
    echo          Java가 설치되어 있는지 확인하세요.
)

REM 디렉토리 생성
echo.
echo [INFO] 필요한 디렉토리 생성...
if not exist logs mkdir logs
if not exist data\input mkdir data\input
if not exist data\output mkdir data\output
if not exist data\models mkdir data\models
if not exist templates\definitions mkdir templates\definitions

REM 설치 확인
echo.
echo [INFO] 설치 확인 중...
python -c "import torch; print(f'PyTorch 버전: {torch.__version__}')" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] PyTorch 설치 확인 실패
) else (
    echo [SUCCESS] PyTorch 설치 확인
)

python -c "import paddleocr; print('PaddleOCR 설치 확인')" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] PaddleOCR 설치 확인 실패
) else (
    echo [SUCCESS] PaddleOCR 설치 확인
)

echo.
echo ========================================
echo 설치 완료!
echo ========================================
echo.
echo 사용 방법:
echo 1. 가상환경 활성화: venv\Scripts\activate.bat
echo 2. 간단한 처리: python simple_hybrid_usage.py [문서경로]
echo 3. 전체 워크플로우: python complete_workflow.py
echo.
echo 추가 설치가 필요한 시스템 도구:
echo - Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
echo - LibreOffice: https://www.libreoffice.org/download/
echo - Java (konlpy/tabula용): https://adoptium.net/
echo.
echo 자세한 내용은 WINDOWS_INSTALL_GUIDE.md 참조
echo ========================================
pause