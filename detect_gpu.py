#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GPU Detection Utility - 크로스 플랫폼 GPU 감지 및 설정
"""

import subprocess
import sys
import platform
import json
from pathlib import Path


def detect_nvidia_gpu():
    """NVIDIA GPU 감지"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version,compute_cap',
                               '--format=csv,noheader'],
                              capture_output=True, text=True, check=True)

        if result.stdout.strip():
            gpu_info = result.stdout.strip().split('\n')[0].split(', ')

            # CUDA 버전 감지
            cuda_result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            cuda_version = "unknown"
            for line in cuda_result.stdout.split('\n'):
                if 'CUDA Version' in line:
                    cuda_version = line.split('CUDA Version:')[1].split('|')[0].strip()
                    break

            return {
                'type': 'nvidia',
                'name': gpu_info[0],
                'memory': gpu_info[1],
                'driver': gpu_info[2] if len(gpu_info) > 2 else 'unknown',
                'compute_capability': gpu_info[3] if len(gpu_info) > 3 else 'unknown',
                'cuda_version': cuda_version,
                'available': True
            }
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def detect_amd_gpu():
    """AMD GPU 감지 (ROCm)"""
    try:
        # ROCm 감지
        result = subprocess.run(['rocm-smi', '--showproductname'],
                              capture_output=True, text=True, check=True)
        if result.stdout.strip():
            return {
                'type': 'amd',
                'name': result.stdout.strip(),
                'available': True,
                'rocm': True
            }
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def detect_apple_silicon():
    """Apple Silicon 감지"""
    if platform.system() == 'Darwin' and platform.processor() == 'arm':
        try:
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'],
                                  capture_output=True, text=True)
            if 'Apple' in result.stdout:
                return {
                    'type': 'apple',
                    'name': result.stdout.strip(),
                    'available': True,
                    'mps': True
                }
        except:
            pass

    return None


def get_cuda_version_for_pytorch():
    """PyTorch용 CUDA 버전 결정"""
    gpu_info = detect_nvidia_gpu()

    if not gpu_info:
        return None

    cuda_version = gpu_info.get('cuda_version', 'unknown')

    # CUDA 버전에 따른 PyTorch 인덱스 URL 매핑
    if cuda_version != 'unknown':
        try:
            major, minor = cuda_version.split('.')[:2]
            cuda_major = int(major)
            cuda_minor = int(minor)

            if cuda_major >= 12:
                return 'cu121'  # CUDA 12.1
            elif cuda_major == 11:
                if cuda_minor >= 8:
                    return 'cu118'  # CUDA 11.8
                else:
                    return 'cu117'  # CUDA 11.7
            else:
                return 'cu118'  # 기본값
        except:
            pass

    return 'cu118'  # 기본값


def get_system_info():
    """시스템 정보 수집"""
    info = {
        'platform': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'python_version': sys.version,
        'gpu': None,
        'recommended_packages': {}
    }

    # GPU 감지
    gpu = detect_nvidia_gpu() or detect_amd_gpu() or detect_apple_silicon()

    if gpu:
        info['gpu'] = gpu

        # GPU 타입별 권장 패키지
        if gpu['type'] == 'nvidia':
            cuda_version = get_cuda_version_for_pytorch()
            info['recommended_packages'] = {
                'torch': f'torch torchvision --index-url https://download.pytorch.org/whl/{cuda_version}',
                'paddlepaddle': 'paddlepaddle-gpu==2.5.2',
                'onnxruntime': 'onnxruntime-gpu==1.16.3'
            }
        elif gpu['type'] == 'apple':
            info['recommended_packages'] = {
                'torch': 'torch torchvision',
                'paddlepaddle': 'paddlepaddle==2.5.2',
                'onnxruntime': 'onnxruntime==1.16.3'
            }
        elif gpu['type'] == 'amd':
            info['recommended_packages'] = {
                'torch': 'torch torchvision --index-url https://download.pytorch.org/whl/rocm5.6',
                'paddlepaddle': 'paddlepaddle==2.5.2',
                'onnxruntime': 'onnxruntime==1.16.3'
            }
    else:
        # CPU 전용
        info['recommended_packages'] = {
            'torch': 'torch torchvision --index-url https://download.pytorch.org/whl/cpu',
            'paddlepaddle': 'paddlepaddle==2.5.2',
            'onnxruntime': 'onnxruntime==1.16.3'
        }

    return info


def generate_install_commands(info):
    """설치 명령 생성"""
    commands = []

    if info.get('gpu'):
        gpu_type = info['gpu']['type']

        if gpu_type == 'nvidia':
            cuda_version = get_cuda_version_for_pytorch()
            commands.append(f"# NVIDIA GPU 감지됨 - CUDA {info['gpu'].get('cuda_version', 'unknown')}")
            commands.append(f"pip install torch torchvision --index-url https://download.pytorch.org/whl/{cuda_version}")
            commands.append("pip install paddlepaddle-gpu==2.5.2")
            commands.append("pip install onnxruntime-gpu==1.16.3")

        elif gpu_type == 'apple':
            commands.append("# Apple Silicon 감지됨 - MPS 지원")
            commands.append("pip install torch torchvision")
            commands.append("pip install paddlepaddle==2.5.2")
            commands.append("pip install onnxruntime==1.16.3")

        elif gpu_type == 'amd':
            commands.append("# AMD GPU 감지됨 - ROCm 지원")
            commands.append("pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm5.6")
            commands.append("pip install paddlepaddle==2.5.2")
            commands.append("pip install onnxruntime==1.16.3")
    else:
        commands.append("# GPU를 감지하지 못했습니다 - CPU 버전 설치")
        commands.append("pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")
        commands.append("pip install paddlepaddle==2.5.2")
        commands.append("pip install onnxruntime==1.16.3")

    return commands


def save_config(info):
    """GPU 설정 저장"""
    config_path = Path('config') / 'gpu_config.json'
    config_path.parent.mkdir(exist_ok=True)

    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

    print(f"GPU 설정이 {config_path}에 저장되었습니다.")


def main():
    """메인 실행"""
    print("="*60)
    print("GPU 감지 유틸리티")
    print("="*60)

    info = get_system_info()

    print(f"\n시스템: {info['platform']} {info['architecture']}")
    print(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

    if info.get('gpu'):
        gpu = info['gpu']
        print(f"\n✅ GPU 감지됨!")
        print(f"  타입: {gpu['type'].upper()}")
        print(f"  이름: {gpu['name']}")
        if gpu['type'] == 'nvidia':
            print(f"  메모리: {gpu.get('memory', 'unknown')}")
            print(f"  드라이버: {gpu.get('driver', 'unknown')}")
            print(f"  CUDA: {gpu.get('cuda_version', 'unknown')}")
            print(f"  Compute Capability: {gpu.get('compute_capability', 'unknown')}")
    else:
        print("\n❌ GPU를 감지하지 못했습니다. CPU 모드로 실행됩니다.")

    print("\n권장 설치 명령:")
    print("-"*40)
    commands = generate_install_commands(info)
    for cmd in commands:
        print(cmd)

    # 설정 저장
    save_config(info)

    # 설치 스크립트 생성 여부 확인
    if len(sys.argv) > 1 and sys.argv[1] == '--generate-script':
        script_name = 'install_gpu.bat' if info['platform'] == 'Windows' else 'install_gpu.sh'

        with open(script_name, 'w') as f:
            if info['platform'] == 'Windows':
                f.write("@echo off\n")
                f.write("REM GPU 자동 감지 설치 스크립트\n\n")
            else:
                f.write("#!/bin/bash\n")
                f.write("# GPU 자동 감지 설치 스크립트\n\n")

            for cmd in commands:
                if not cmd.startswith('#'):
                    f.write(cmd + '\n')

        print(f"\n설치 스크립트 '{script_name}'이 생성되었습니다.")

    return info


if __name__ == "__main__":
    main()