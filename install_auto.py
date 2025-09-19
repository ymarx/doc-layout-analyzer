#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cross-Platform Auto Installer with GPU Detection
자동으로 시스템을 감지하고 적절한 패키지를 설치합니다.
"""

import subprocess
import sys
import os
import platform
from pathlib import Path
import json


def run_command(cmd, check=True):
    """명령 실행 헬퍼"""
    print(f"실행: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        if result.stdout:
            print(result.stdout)
        if result.stderr and result.returncode != 0:
            print(f"경고: {result.stderr}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"오류: {e}")
        return False


def check_python_version():
    """Python 버전 확인"""
    if sys.version_info < (3, 11):
        print(f"❌ Python 3.11 이상이 필요합니다. 현재: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def create_venv():
    """가상환경 생성"""
    venv_path = Path("venv")

    if venv_path.exists():
        print("기존 가상환경이 발견되었습니다.")
        response = input("삭제하고 새로 생성하시겠습니까? [y/N]: ")
        if response.lower() == 'y':
            import shutil
            shutil.rmtree(venv_path)
        else:
            print("기존 가상환경을 사용합니다.")
            return

    print("가상환경 생성 중...")
    run_command(f"{sys.executable} -m venv venv")


def activate_venv():
    """가상환경 활성화 경로 반환"""
    system = platform.system()

    if system == "Windows":
        activate = Path("venv/Scripts/activate.bat")
        python = Path("venv/Scripts/python.exe")
    else:
        activate = Path("venv/bin/activate")
        python = Path("venv/bin/python")

    if not python.exists():
        print("❌ 가상환경 생성 실패")
        sys.exit(1)

    return str(python)


def detect_gpu():
    """GPU 감지 및 정보 반환"""
    print("\nGPU 감지 중...")

    # detect_gpu.py 실행
    result = subprocess.run([sys.executable, "detect_gpu.py"],
                          capture_output=True, text=True)

    # GPU 설정 파일 읽기
    config_path = Path("config/gpu_config.json")
    if config_path.exists():
        with open(config_path, 'r') as f:
            gpu_info = json.load(f)
            return gpu_info
    return None


def install_packages(python_exe):
    """패키지 설치"""
    print("\n패키지 설치 시작...")

    # pip 업그레이드
    print("pip 업그레이드 중...")
    run_command(f"{python_exe} -m pip install --upgrade pip setuptools wheel")

    # 크로스 플랫폼 requirements 설치
    print("\n기본 패키지 설치 중...")
    if not run_command(f"{python_exe} -m pip install -r requirements_cross_platform.txt"):
        print("⚠️ 일부 기본 패키지 설치 실패. 계속 진행합니다.")

    # GPU 정보 기반 패키지 설치
    gpu_info = detect_gpu()

    if gpu_info and gpu_info.get('gpu'):
        gpu = gpu_info['gpu']
        gpu_type = gpu['type']

        print(f"\n✅ {gpu_type.upper()} GPU 감지됨: {gpu['name']}")

        if gpu_type == 'nvidia':
            # CUDA 버전 확인
            cuda_version = gpu.get('cuda_version', 'unknown')
            print(f"CUDA 버전: {cuda_version}")

            # PyTorch CUDA 버전 결정
            if 'cuda_version' in gpu and gpu['cuda_version'] != 'unknown':
                major = int(gpu['cuda_version'].split('.')[0])
                if major >= 12:
                    cuda_index = 'cu121'
                elif major == 11:
                    cuda_index = 'cu118'
                else:
                    cuda_index = 'cu118'  # 기본값
            else:
                cuda_index = 'cu118'  # 기본값

            print(f"PyTorch CUDA {cuda_index} 설치 중...")
            run_command(f"{python_exe} -m pip install torch torchvision --index-url https://download.pytorch.org/whl/{cuda_index}")
            run_command(f"{python_exe} -m pip install paddlepaddle-gpu==2.5.2")
            run_command(f"{python_exe} -m pip install onnxruntime-gpu==1.16.3")

        elif gpu_type == 'apple':
            print("Apple Silicon MPS 지원 버전 설치 중...")
            run_command(f"{python_exe} -m pip install torch torchvision")
            run_command(f"{python_exe} -m pip install paddlepaddle==2.5.2")
            run_command(f"{python_exe} -m pip install onnxruntime==1.16.3")

        elif gpu_type == 'amd':
            print("AMD ROCm 지원 버전 설치 중...")
            run_command(f"{python_exe} -m pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm5.6")
            run_command(f"{python_exe} -m pip install paddlepaddle==2.5.2")
            run_command(f"{python_exe} -m pip install onnxruntime==1.16.3")

    else:
        print("\n❌ GPU를 감지하지 못했습니다. CPU 버전 설치 중...")
        run_command(f"{python_exe} -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")
        run_command(f"{python_exe} -m pip install paddlepaddle==2.5.2")
        run_command(f"{python_exe} -m pip install onnxruntime==1.16.3")

    # 선택적 패키지 설치 시도
    print("\n선택적 패키지 설치 시도 중...")
    optional_packages = [
        ("camelot-py[cv]", "PDF 테이블 추출"),
        ("tabula-py", "PDF 테이블 추출 (Java 필요)"),
        ("konlpy", "한국어 NLP (Java 필요)")
    ]

    for package, description in optional_packages:
        print(f"\n{package} ({description}) 설치 시도...")
        if not run_command(f"{python_exe} -m pip install {package}", check=False):
            print(f"⚠️ {package} 설치 실패. {description} 기능이 제한될 수 있습니다.")


def create_directories():
    """필요한 디렉토리 생성"""
    print("\n디렉토리 구조 생성 중...")

    directories = [
        'logs',
        'data/input',
        'data/output',
        'data/models',
        'templates/definitions',
        'config'
    ]

    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ {dir_path}")


def run_test(python_exe):
    """설치 테스트"""
    print("\n설치 테스트 실행 중...")
    run_command(f"{python_exe} test_installation.py")


def create_launcher_script():
    """실행 스크립트 생성"""
    system = platform.system()

    if system == "Windows":
        launcher_path = Path("run.bat")
        content = """@echo off
REM Document Layout Analyzer 실행 스크립트
call venv\\Scripts\\activate.bat
python %*
"""
    else:
        launcher_path = Path("run.sh")
        content = """#!/bin/bash
# Document Layout Analyzer 실행 스크립트
source venv/bin/activate
python "$@"
"""

    with open(launcher_path, 'w') as f:
        f.write(content)

    if system != "Windows":
        os.chmod(launcher_path, 0o755)

    print(f"✅ 실행 스크립트 생성: {launcher_path}")


def main():
    """메인 설치 프로세스"""
    print("="*60)
    print("Document Layout Analyzer - Cross-Platform Auto Installer")
    print("="*60)
    print(f"시스템: {platform.system()} {platform.machine()}")

    # 단계별 설치
    check_python_version()
    create_venv()
    python_exe = activate_venv()
    install_packages(python_exe)
    create_directories()
    create_launcher_script()
    run_test(python_exe)

    # 완료 메시지
    print("\n" + "="*60)
    print("✅ 설치 완료!")
    print("="*60)

    system = platform.system()
    if system == "Windows":
        print("\n사용 방법:")
        print("1. 가상환경 활성화: venv\\Scripts\\activate.bat")
        print("2. 또는 run.bat 사용: run.bat simple_hybrid_usage.py [문서]")
    else:
        print("\n사용 방법:")
        print("1. 가상환경 활성화: source venv/bin/activate")
        print("2. 또는 run.sh 사용: ./run.sh simple_hybrid_usage.py [문서]")

    print("\n추가 시스템 도구 (필요시 설치):")
    print("- Tesseract OCR")
    print("- LibreOffice")
    print("- Java (konlpy/tabula용)")

    # GPU 정보 표시
    gpu_config_path = Path("config/gpu_config.json")
    if gpu_config_path.exists():
        with open(gpu_config_path, 'r') as f:
            gpu_info = json.load(f)
            if gpu_info.get('gpu'):
                print(f"\n🎮 GPU 모드: {gpu_info['gpu']['type'].upper()}")
                print(f"   {gpu_info['gpu']['name']}")


if __name__ == "__main__":
    main()