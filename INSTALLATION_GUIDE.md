# 📚 통합 설치 가이드 - Document Layout Analyzer

## 🚀 빠른 시작 (모든 운영체제)

### 1. 자동 설치 (권장) 🎯

```bash
# Python 3.11+ 필수
git clone https://github.com/yourusername/doc-layout-analyzer.git
cd doc-layout-analyzer

# 자동 설치 스크립트 실행 (GPU 자동 감지)
python install_auto.py
```

**자동 설치 기능:**
- ✅ 운영체제 자동 감지 (Windows/macOS/Linux)
- ✅ GPU 자동 감지 및 설정
  - NVIDIA GPU → CUDA 버전별 최적화
  - Apple Silicon → MPS 지원
  - AMD GPU → ROCm 지원
  - GPU 없음 → CPU 최적화
- ✅ 가상환경 자동 생성
- ✅ 모든 의존성 자동 설치
- ✅ 디렉토리 구조 자동 생성

### 2. GPU 확인 방법

```bash
# GPU 감지 및 권장 설정 확인
python detect_gpu.py

# GPU 설정과 함께 설치 스크립트 생성
python detect_gpu.py --generate-script
```

## 🖥️ 운영체제별 상세 가이드

### Windows 🪟

#### 사전 준비사항
1. **Python 3.11+** 설치
   - [Python.org](https://www.python.org/downloads/)에서 다운로드
   - ⚠️ "Add Python to PATH" 체크 필수

2. **Visual Studio Build Tools**
   - [다운로드](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)
   - "Desktop development with C++" 선택

3. **NVIDIA GPU 사용자** (선택사항)
   - [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) 설치
   - [cuDNN](https://developer.nvidia.com/cudnn) 설치

#### Windows 자동 설치
```powershell
# PowerShell 관리자 권한으로 실행
python install_auto.py

# 또는 배치 파일 사용
install_windows.bat
```

### macOS 🍎

#### 사전 준비사항
```bash
# Homebrew 설치 (없는 경우)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.11+ 설치
brew install python@3.11

# 시스템 도구 설치
brew install tesseract
brew install --cask libreoffice
```

#### macOS 자동 설치
```bash
python3 install_auto.py
```

### Linux 🐧

#### Ubuntu/Debian
```bash
# 시스템 패키지 설치
sudo apt-get update
sudo apt-get install -y python3.11 python3-pip python3-venv
sudo apt-get install -y tesseract-ocr tesseract-ocr-kor libreoffice

# 자동 설치
python3 install_auto.py
```

#### Fedora/RHEL
```bash
# 시스템 패키지 설치
sudo dnf install -y python3.11 python3-pip
sudo dnf install -y tesseract tesseract-langpack-kor libreoffice

# 자동 설치
python3 install_auto.py
```

## 📦 크로스 플랫폼 Requirements 구조

### 파일 구조
```
requirements_cross_platform.txt  # 플랫폼 독립적 패키지
detect_gpu.py                    # GPU 감지 및 설정
install_auto.py                  # 자동 설치 스크립트
```

### 수동 설치 방법

1. **기본 패키지 설치**
```bash
pip install -r requirements_cross_platform.txt
```

2. **GPU/CPU 패키지 설치**

#### NVIDIA GPU (CUDA 11.8+)
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install paddlepaddle-gpu==2.5.2
pip install onnxruntime-gpu==1.16.3
```

#### NVIDIA GPU (CUDA 12.1+)
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install paddlepaddle-gpu==2.5.2
pip install onnxruntime-gpu==1.16.3
```

#### Apple Silicon (M1/M2/M3)
```bash
pip install torch torchvision
pip install paddlepaddle==2.5.2
pip install onnxruntime==1.16.3
```

#### AMD GPU (ROCm)
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm5.6
pip install paddlepaddle==2.5.2
pip install onnxruntime==1.16.3
```

#### CPU Only
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install paddlepaddle==2.5.2
pip install onnxruntime==1.16.3
```

## 🔍 설치 검증

### 자동 테스트
```bash
python test_installation.py
```

### GPU 동작 확인
```python
import torch
print(f"PyTorch 버전: {torch.__version__}")
print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU 이름: {torch.cuda.get_device_name(0)}")
```

## 🛠️ 문제 해결

### Windows 문제 해결

#### Visual C++ 오류
```
오류: Microsoft Visual C++ 14.0 or greater is required
해결: Visual Studio Build Tools 설치 후 재시작
```

#### CUDA 버전 불일치
```bash
# CUDA 버전 확인
nvidia-smi

# PyTorch 재설치 (CUDA 버전에 맞게)
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu[버전]
```

### macOS 문제 해결

#### Apple Silicon 호환성
```bash
# Rosetta 2 설치 (필요시)
softwareupdate --install-rosetta

# ARM64 네이티브 패키지 우선 설치
arch -arm64 pip install [package]
```

### Linux 문제 해결

#### 권한 오류
```bash
# pip 권한 오류시
pip install --user [package]

# 또는 가상환경 사용
python3 -m venv venv
source venv/bin/activate
```

## 📊 성능 최적화

### GPU 메모리 관리
```python
import torch

# GPU 메모리 제한 설정
torch.cuda.set_per_process_memory_fraction(0.8)

# 메모리 캐시 정리
torch.cuda.empty_cache()
```

### CPU 멀티프로세싱
```python
import multiprocessing as mp

# CPU 코어 수 확인
num_cores = mp.cpu_count()
print(f"사용 가능한 CPU 코어: {num_cores}")

# 워커 수 설정
num_workers = min(4, num_cores - 1)
```

## 🚀 실행 방법

### 기본 실행
```bash
# 간단한 처리
python simple_hybrid_usage.py document.docx

# 전체 워크플로우
python complete_workflow.py

# 강화 파이프라인
python enhanced_main.py
```

### GPU 모드 강제
```bash
# GPU 사용 강제
python main.py --gpu document.pdf

# CPU 사용 강제
python main.py --cpu-only document.pdf
```

## 📝 설정 파일

### GPU 설정 확인
```bash
cat config/gpu_config.json
```

### 시스템 설정 수정
```yaml
# config/config.yaml
system:
  device: "auto"  # auto, cuda, cpu, mps
  gpu_memory_fraction: 0.8
  num_workers: 4
```

## 🆘 추가 지원

- **Windows 상세 가이드**: [WINDOWS_INSTALL_GUIDE.md](WINDOWS_INSTALL_GUIDE.md)
- **프로젝트 가이드**: [PROJECT_GUIDE.md](PROJECT_GUIDE.md)
- **GitHub Issues**: 문제 발생시 이슈 등록

## ✅ 체크리스트

설치 전:
- [ ] Python 3.11+ 설치
- [ ] Git 설치 (선택사항)
- [ ] 시스템 도구 설치 (Tesseract, LibreOffice 등)

설치 후:
- [ ] `python test_installation.py` 실행 성공
- [ ] GPU 감지 확인 (GPU 있는 경우)
- [ ] 샘플 문서 처리 테스트
- [ ] 출력 디렉토리 확인