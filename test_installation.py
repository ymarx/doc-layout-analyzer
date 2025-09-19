#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Document Layout Analyzer - 설치 검증 스크립트
Windows/Mac/Linux 호환
"""

import sys
import os
import importlib
import subprocess
from pathlib import Path

def check_python_version():
    """Python 버전 확인"""
    print("="*60)
    print("1. Python 버전 확인")
    print("="*60)

    version = sys.version_info
    print(f"현재 Python 버전: {version.major}.{version.minor}.{version.micro}")

    if version >= (3, 11):
        print("✅ Python 3.11+ 확인")
        return True
    else:
        print("❌ Python 3.11 이상이 필요합니다")
        return False

def check_package(package_name, import_name=None):
    """패키지 설치 확인"""
    if import_name is None:
        import_name = package_name

    try:
        module = importlib.import_module(import_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"  ✅ {package_name:<25} {version}")
        return True
    except ImportError as e:
        print(f"  ❌ {package_name:<25} 설치 실패: {str(e)[:50]}")
        return False

def check_python_packages():
    """Python 패키지 설치 확인"""
    print("\n" + "="*60)
    print("2. Python 패키지 확인")
    print("="*60)

    packages = [
        # Core Framework
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('pydantic', 'pydantic'),
        ('python-multipart', 'multipart'),

        # Configuration
        ('pyyaml', 'yaml'),
        ('python-dotenv', 'dotenv'),
        ('click', 'click'),
        ('tqdm', 'tqdm'),
        ('loguru', 'loguru'),

        # Document Processing
        ('python-docx', 'docx'),
        ('python-pptx', 'pptx'),
        ('PyPDF2', 'PyPDF2'),
        ('pdfplumber', 'pdfplumber'),
        ('openpyxl', 'openpyxl'),

        # OCR & Layout
        ('paddlepaddle', 'paddle'),
        ('paddleocr', 'paddleocr'),
        ('pytesseract', 'pytesseract'),
        ('easyocr', 'easyocr'),

        # Image Processing
        ('opencv-python', 'cv2'),
        ('Pillow', 'PIL'),
        ('scikit-image', 'skimage'),
        ('numpy', 'numpy'),

        # ML & AI
        ('torch', 'torch'),
        ('torchvision', 'torchvision'),
        ('transformers', 'transformers'),
        ('sentence-transformers', 'sentence_transformers'),
        ('onnxruntime', 'onnxruntime'),

        # Vector DB
        ('qdrant-client', 'qdrant_client'),
        ('chromadb', 'chromadb'),

        # Text Processing
        ('spacy', 'spacy'),
        ('pandas', 'pandas'),

        # Async & HTTP
        ('httpx', 'httpx'),
        ('aiofiles', 'aiofiles'),
        ('aiohttp', 'aiohttp'),

        # System
        ('psutil', 'psutil'),
        ('py-cpuinfo', 'cpuinfo'),
    ]

    # Optional packages
    optional_packages = [
        ('camelot-py', 'camelot'),
        ('tabula-py', 'tabula'),
        ('konlpy', 'konlpy'),
    ]

    success_count = 0
    total_count = len(packages)

    print("\n필수 패키지:")
    for package, import_name in packages:
        if check_package(package, import_name):
            success_count += 1

    print("\n선택 패키지 (설치되지 않아도 기본 기능 사용 가능):")
    for package, import_name in optional_packages:
        check_package(package, import_name)

    print(f"\n결과: {success_count}/{total_count} 필수 패키지 설치 완료")
    return success_count == total_count

def check_system_command(command, name=None):
    """시스템 명령어 확인"""
    if name is None:
        name = command.split()[0]

    try:
        if sys.platform == "win32":
            result = subprocess.run(f"where {command.split()[0]}",
                                  shell=True, capture_output=True, text=True)
        else:
            result = subprocess.run(f"which {command.split()[0]}",
                                  shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            # 버전 확인 시도
            version_result = subprocess.run(command,
                                          shell=True, capture_output=True, text=True)
            if version_result.returncode == 0:
                print(f"  ✅ {name} 설치 확인")
                return True

        print(f"  ❌ {name} 미설치 또는 PATH 설정 필요")
        return False
    except Exception as e:
        print(f"  ❌ {name} 확인 실패: {str(e)}")
        return False

def check_system_dependencies():
    """시스템 의존성 확인"""
    print("\n" + "="*60)
    print("3. 시스템 의존성 확인")
    print("="*60)

    dependencies = [
        ("tesseract --version", "Tesseract OCR"),
        ("java -version", "Java Runtime"),
    ]

    if sys.platform != "win32":
        dependencies.append(("libreoffice --version", "LibreOffice"))

    results = []
    for cmd, name in dependencies:
        results.append(check_system_command(cmd, name))

    return all(results)

def check_gpu_support():
    """GPU 지원 확인"""
    print("\n" + "="*60)
    print("4. GPU 지원 확인")
    print("="*60)

    try:
        import torch
        if torch.cuda.is_available():
            print(f"  ✅ CUDA 사용 가능")
            print(f"     GPU 개수: {torch.cuda.device_count()}")
            print(f"     GPU 이름: {torch.cuda.get_device_name(0)}")
            return True
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print(f"  ✅ Apple Silicon MPS 사용 가능")
            return True
        else:
            print(f"  ℹ️  CPU 모드로 실행됩니다")
            return False
    except ImportError:
        print(f"  ❌ PyTorch가 설치되지 않았습니다")
        return False

def check_directories():
    """필요한 디렉토리 확인 및 생성"""
    print("\n" + "="*60)
    print("5. 디렉토리 구조 확인")
    print("="*60)

    directories = [
        'logs',
        'data/input',
        'data/output',
        'data/models',
        'templates/definitions',
        'config'
    ]

    for dir_path in directories:
        path = Path(dir_path)
        if path.exists():
            print(f"  ✅ {dir_path}")
        else:
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"  ✅ {dir_path} (생성됨)")
            except Exception as e:
                print(f"  ❌ {dir_path} 생성 실패: {e}")

def run_simple_test():
    """간단한 동작 테스트"""
    print("\n" + "="*60)
    print("6. 간단한 동작 테스트")
    print("="*60)

    test_results = []

    # FastAPI 테스트
    try:
        from fastapi import FastAPI
        app = FastAPI()
        print("  ✅ FastAPI 초기화 성공")
        test_results.append(True)
    except Exception as e:
        print(f"  ❌ FastAPI 초기화 실패: {e}")
        test_results.append(False)

    # PaddleOCR 테스트
    try:
        from paddleocr import PaddleOCR
        print("  ✅ PaddleOCR 로드 성공 (초기화는 시간이 걸릴 수 있음)")
        test_results.append(True)
    except Exception as e:
        print(f"  ❌ PaddleOCR 로드 실패: {e}")
        test_results.append(False)

    # Document 처리 테스트
    try:
        from docx import Document
        print("  ✅ python-docx 로드 성공")
        test_results.append(True)
    except Exception as e:
        print(f"  ❌ python-docx 로드 실패: {e}")
        test_results.append(False)

    return all(test_results)

def main():
    """메인 테스트 함수"""
    print("\n" + "="*60)
    print("Document Layout Analyzer - 설치 검증")
    print("="*60)
    print(f"운영체제: {sys.platform}")
    print(f"Python 경로: {sys.executable}")

    results = []

    # 각 테스트 실행
    results.append(check_python_version())
    results.append(check_python_packages())
    check_system_dependencies()  # 선택적
    check_gpu_support()  # 정보 제공용
    check_directories()
    results.append(run_simple_test())

    # 최종 결과
    print("\n" + "="*60)
    print("최종 검증 결과")
    print("="*60)

    if all(results):
        print("✅ 모든 필수 구성요소가 정상적으로 설치되었습니다!")
        print("\n다음 명령으로 시스템을 실행할 수 있습니다:")
        if sys.platform == "win32":
            print("  venv\\Scripts\\activate.bat")
        else:
            print("  source venv/bin/activate")
        print("  python simple_hybrid_usage.py [문서경로]")
    else:
        print("⚠️  일부 구성요소가 누락되었습니다.")
        print("\n다음 사항을 확인해주세요:")
        print("1. Python 3.11 이상 설치")
        print("2. requirements_windows.txt 모든 패키지 설치")
        print("3. WINDOWS_INSTALL_GUIDE.md 참조")

    print("\n상세한 설치 가이드:")
    print("- Windows: WINDOWS_INSTALL_GUIDE.md")
    print("- Mac/Linux: README.md")

if __name__ == "__main__":
    main()