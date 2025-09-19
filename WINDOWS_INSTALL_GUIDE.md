# 📋 Windows 설치 가이드 - Document Layout Analyzer

## 🎮 GPU 자동 감지 설치 (권장)

### 자동 설치 (모든 플랫폼)
```bash
# Python 3.11+ 필요
python install_auto.py
```

이 스크립트는:
- ✅ 시스템 자동 감지 (Windows/Mac/Linux)
- ✅ GPU 자동 감지 (NVIDIA/AMD/Apple Silicon)
- ✅ 적절한 PyTorch/PaddlePaddle 버전 자동 설치
- ✅ CUDA 버전별 최적화 패키지 설치

### GPU 감지 테스트
```bash
python detect_gpu.py
```

## 🚨 Windows 설치 시 주요 문제점 및 해결 방법

### 1️⃣ 사전 준비사항

#### 필수 소프트웨어 설치
1. **Python 3.11 이상** (3.11.x 권장, 3.12는 일부 패키지 호환성 문제 가능)
   - [Python 공식 사이트](https://www.python.org/downloads/)에서 다운로드
   - 설치 시 **"Add Python to PATH"** 체크 필수

2. **Visual Studio Build Tools**
   - [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022) 다운로드
   - 설치 시 "Desktop development with C++" 워크로드 선택

3. **Java 17 이상** (konlpy, tabula-py 의존성)
   - [Oracle JDK](https://www.oracle.com/java/technologies/downloads/) 또는 [OpenJDK](https://adoptium.net/) 설치
   - 환경변수 설정:
     ```powershell
     setx JAVA_HOME "C:\Program Files\Java\jdk-17"
     setx PATH "%PATH%;%JAVA_HOME%\bin"
     ```

4. **Git** (선택사항, GitHub 클론용)
   - [Git for Windows](https://git-scm.com/download/win) 다운로드

### 2️⃣ 시스템 의존성 설치

#### LibreOffice 설치
```powershell
# PowerShell 관리자 권한으로 실행
# Chocolatey 사용 시
choco install libreoffice

# 또는 수동 다운로드
# https://www.libreoffice.org/download/download/ 에서 Windows 버전 다운로드
```

#### Tesseract OCR 설치
```powershell
# Chocolatey 사용
choco install tesseract

# 또는 수동 설치
# https://github.com/UB-Mannheim/tesseract/wiki 에서 Windows installer 다운로드
# 설치 후 PATH 환경변수에 추가: C:\Program Files\Tesseract-OCR
```

#### Poppler 설치 (PDF 처리용)
```powershell
# 1. https://github.com/oschwartz10612/poppler-windows/releases/ 에서 다운로드
# 2. C:\poppler 에 압축 해제
# 3. 환경변수 PATH에 C:\poppler\Library\bin 추가
```

### 3️⃣ Python 환경 설정

#### 가상환경 생성 및 활성화
```powershell
# PowerShell에서 실행
cd doc_layout_analyzer
python -m venv venv

# 가상환경 활성화
.\venv\Scripts\Activate.ps1

# 실행 정책 오류 시
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4️⃣ 의존성 패키지 설치

#### requirements.txt 수정 버전 생성
```powershell
# requirements_windows.txt 파일 생성
@"
# Windows용 수정된 의존성 목록
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6

# Configuration & Utilities
pyyaml==6.0.1
python-dotenv==1.0.0
click==8.1.7
tqdm==4.66.1
loguru==0.7.2

# Document Processing
python-docx==1.1.0
python-pptx==0.6.23
PyPDF2==3.0.1
pdfplumber==0.10.3
openpyxl==3.1.2

# Camelot과 Tabula는 별도 설치
# camelot-py[cv]==0.10.1  # 주석 처리
# tabula-py==2.9.0  # 주석 처리

# OCR & Layout Analysis (CPU 버전)
paddlepaddle==2.5.2
paddleocr==2.7.3

# Alternative OCR
pytesseract==0.3.10
easyocr==1.7.0

# Image Processing
opencv-python==4.8.1.78
Pillow==10.1.0
scikit-image==0.22.0
numpy==1.24.4

# Vector Database
qdrant-client==1.7.0
chromadb==0.4.18

# Text Processing
spacy==3.7.2
# konlpy는 별도 설치 필요
kiwisolver==1.4.5

# Data Processing
pandas==2.1.4
pyarrow==14.0.1

# HTTP & Async
httpx==0.25.2
aiofiles==23.2.1
aiohttp==3.9.1

# System Monitoring
psutil==5.9.6
py-cpuinfo==9.0.0

# Development & Testing
pytest==7.4.3
pytest-asyncio==0.21.1
black==23.11.0
isort==5.12.0
flake8==6.1.0

# ONNX Runtime (CPU)
onnxruntime==1.16.3
"@ | Out-File -FilePath requirements_windows.txt -Encoding UTF8
```

#### 패키지 설치 단계별 진행
```powershell
# 1. 기본 패키지 설치
pip install --upgrade pip setuptools wheel

# 2. PyTorch CPU 버전 설치
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 3. Transformers 관련 패키지
pip install transformers==4.36.0 sentence-transformers==2.2.2

# 4. 수정된 requirements 설치
pip install -r requirements_windows.txt

# 5. 문제가 있는 패키지 개별 설치
pip install camelot-py[cv]
pip install tabula-py

# 6. konlpy 설치 (Java 설정 후)
pip install konlpy
```

### 5️⃣ 일반적인 오류 해결

#### Error 1: Microsoft Visual C++ 14.0 or greater is required
```powershell
# Visual Studio Build Tools 설치 확인
# 설치 후 시스템 재시작 필요
```

#### Error 2: paddlepaddle 설치 실패
```powershell
# CPU 버전만 설치
pip uninstall paddlepaddle-gpu
pip install paddlepaddle==2.5.2
```

#### Error 3: konlpy 설치/실행 오류
```powershell
# Java 경로 확인
java -version
echo %JAVA_HOME%

# JPype1 재설치
pip uninstall jpype1
pip install jpype1
```

#### Error 4: Tesseract 실행 오류
```powershell
# PATH 확인
where tesseract

# pytesseract 설정
# Python 스크립트에 추가:
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### 6️⃣ 설치 검증 스크립트

```python
# test_installation.py
import sys
import importlib

def check_package(package_name):
    try:
        importlib.import_module(package_name)
        print(f"✅ {package_name} 설치 성공")
        return True
    except ImportError as e:
        print(f"❌ {package_name} 설치 실패: {str(e)}")
        return False

packages = [
    'fastapi', 'uvicorn', 'pydantic',
    'yaml', 'dotenv', 'click', 'tqdm', 'loguru',
    'docx', 'pptx', 'PyPDF2', 'pdfplumber', 'openpyxl',
    'paddle', 'paddleocr', 'pytesseract', 'easyocr',
    'cv2', 'PIL', 'skimage', 'numpy',
    'torch', 'torchvision', 'transformers', 'sentence_transformers',
    'qdrant_client', 'chromadb',
    'spacy', 'pandas', 'pyarrow',
    'httpx', 'aiofiles', 'aiohttp',
    'psutil', 'cpuinfo'
]

print("="*50)
print("Document Layout Analyzer - Windows 설치 검증")
print("="*50)

success_count = 0
for package in packages:
    if check_package(package):
        success_count += 1

print("="*50)
print(f"결과: {success_count}/{len(packages)} 패키지 설치 완료")

# 추가 시스템 체크
print("\n시스템 의존성 확인:")
import subprocess

def check_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {command.split()[0]} 설치 확인")
            return True
    except:
        pass
    print(f"❌ {command.split()[0]} 미설치 또는 PATH 설정 필요")
    return False

check_command("tesseract --version")
check_command("java -version")
```

### 7️⃣ 실행 방법

```powershell
# 가상환경 활성화
.\venv\Scripts\Activate.ps1

# 간단한 하이브리드 처리
python simple_hybrid_usage.py path\to\document.docx

# 완전한 5단계 워크플로우
python complete_workflow.py

# 강화 파이프라인
python enhanced_main.py
```

### 8️⃣ Windows용 배치 스크립트

```batch
@echo off
REM install_windows.bat
echo ========================================
echo Document Layout Analyzer Windows Installer
echo ========================================

REM Python 버전 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python이 설치되지 않았습니다.
    echo https://www.python.org/downloads/ 에서 Python 3.11+ 설치해주세요.
    pause
    exit /b 1
)

REM 가상환경 생성
echo [INFO] 가상환경 생성 중...
python -m venv venv

REM 가상환경 활성화
echo [INFO] 가상환경 활성화...
call venv\Scripts\activate.bat

REM pip 업그레이드
echo [INFO] pip 업그레이드...
python -m pip install --upgrade pip

REM PyTorch 설치
echo [INFO] PyTorch CPU 버전 설치...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

REM 나머지 패키지 설치
echo [INFO] 기타 패키지 설치...
pip install -r requirements_windows.txt

echo ========================================
echo 설치 완료!
echo 사용: venv\Scripts\activate.bat 실행 후
echo       python simple_hybrid_usage.py [문서경로]
echo ========================================
pause
```

### 📝 추가 참고사항

1. **GPU 사용을 원하는 경우**:
   - CUDA 11.8 이상 설치
   - `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`
   - `pip install paddlepaddle-gpu==2.5.2`

2. **네트워크 프록시 환경**:
   ```powershell
   set HTTP_PROXY=http://proxy.company.com:8080
   set HTTPS_PROXY=http://proxy.company.com:8080
   pip install --proxy http://proxy.company.com:8080 [package]
   ```

3. **권한 문제**:
   - PowerShell을 관리자 권한으로 실행
   - 설치 경로에 한글이나 공백이 없도록 주의

4. **문서 처리 테스트**:
   - 먼저 간단한 DOCX 파일로 테스트
   - PDF는 추가 설정 후 테스트 권장

이 가이드를 따라 설치하면 Windows 환경에서도 문서 레이아웃 분석기를 정상적으로 실행할 수 있습니다.