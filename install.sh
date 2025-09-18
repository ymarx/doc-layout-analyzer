#!/bin/bash

# Document Layout Analyzer Installation Script
# CPU/GPU 듀얼 모드 지원 설치

set -e  # 오류 시 종료

echo "🚀 Document Layout Analyzer 설치 시작"
echo "=================================================="

# 색깔 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 시스템 정보 감지
detect_system() {
    log_info "시스템 정보 감지 중..."

    OS=$(uname -s)
    ARCH=$(uname -m)

    case $OS in
        "Linux")
            if command -v lsb_release &> /dev/null; then
                DISTRO=$(lsb_release -si)
                VERSION=$(lsb_release -sr)
            elif [ -f /etc/os-release ]; then
                . /etc/os-release
                DISTRO=$NAME
                VERSION=$VERSION_ID
            else
                DISTRO="Unknown"
                VERSION="Unknown"
            fi
            ;;
        "Darwin")
            DISTRO="macOS"
            VERSION=$(sw_vers -productVersion)
            ;;
        *)
            DISTRO="Unknown"
            VERSION="Unknown"
            ;;
    esac

    log_info "운영체제: $DISTRO $VERSION ($ARCH)"
}

# Python 버전 확인
check_python() {
    log_info "Python 버전 확인 중..."

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_info "Python 버전: $PYTHON_VERSION"

        # Python 3.11+ 확인
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
            log_success "Python 3.11+ 감지됨"
        else
            log_error "Python 3.11 이상이 필요합니다. 현재 버전: $PYTHON_VERSION"
            exit 1
        fi
    else
        log_error "Python3이 설치되지 않았습니다."
        exit 1
    fi
}

# 시스템 의존성 설치
install_system_dependencies() {
    log_info "시스템 의존성 설치 중..."

    case $DISTRO in
        "Ubuntu"|"Debian"*)
            log_info "Ubuntu/Debian 패키지 설치 중..."
            sudo apt-get update
            sudo apt-get install -y \
                libreoffice \
                ocrmypdf \
                tesseract-ocr \
                tesseract-ocr-kor \
                tesseract-ocr-eng \
                python3-pip \
                python3-dev \
                build-essential \
                libopencv-dev \
                pkg-config
            ;;
        "CentOS"|"Red Hat"*|"Fedora")
            log_info "RedHat 계열 패키지 설치 중..."
            if command -v dnf &> /dev/null; then
                sudo dnf install -y libreoffice tesseract tesseract-langpack-kor python3-pip python3-devel gcc-c++
            else
                sudo yum install -y libreoffice tesseract tesseract-langpack-kor python3-pip python3-devel gcc-c++
            fi
            ;;
        "macOS")
            log_info "macOS 패키지 설치 중..."
            if command -v brew &> /dev/null; then
                brew install libreoffice ocrmypdf tesseract tesseract-lang
            else
                log_warning "Homebrew가 설치되지 않았습니다. 수동 설치가 필요할 수 있습니다."
            fi
            ;;
        *)
            log_warning "알 수 없는 운영체제입니다. 수동으로 다음 패키지들을 설치해주세요:"
            log_warning "- LibreOffice"
            log_warning "- OCRmyPDF"
            log_warning "- Tesseract OCR (한국어 지원)"
            ;;
    esac
}

# GPU 지원 확인
check_gpu_support() {
    log_info "GPU 지원 확인 중..."

    GPU_SUPPORT="false"

    # NVIDIA GPU 확인
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits | head -1)
            log_success "NVIDIA GPU 감지: $GPU_INFO"
            GPU_SUPPORT="cuda"
        else
            log_warning "nvidia-smi가 설치되어 있지만 GPU에 접근할 수 없습니다."
        fi
    fi

    # Apple Silicon 확인
    if [ "$DISTRO" = "macOS" ] && [ "$ARCH" = "arm64" ]; then
        log_info "Apple Silicon (M1/M2) 감지됨 - MPS 지원 가능"
        GPU_SUPPORT="mps"
    fi

    if [ "$GPU_SUPPORT" = "false" ]; then
        log_info "GPU를 감지하지 못했습니다. CPU 모드로 설치합니다."
    fi
}

# 가상환경 생성
create_virtual_environment() {
    log_info "Python 가상환경 생성 중..."

    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_success "가상환경 생성 완료"
    else
        log_info "기존 가상환경 발견"
    fi

    # 가상환경 활성화
    source venv/bin/activate
    log_info "가상환경 활성화됨"

    # pip 업그레이드
    pip install --upgrade pip
}

# Python 패키지 설치
install_python_packages() {
    log_info "Python 패키지 설치 중..."

    # PyTorch 설치 (GPU 지원에 따라)
    if [ "$GPU_SUPPORT" = "cuda" ]; then
        log_info "CUDA 지원 PyTorch 설치 중..."
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
        pip install paddlepaddle-gpu==2.5.2
    elif [ "$GPU_SUPPORT" = "mps" ]; then
        log_info "MPS 지원 PyTorch 설치 중..."
        pip install torch torchvision
        pip install paddlepaddle==2.5.2
    else
        log_info "CPU 버전 PyTorch 설치 중..."
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
        pip install paddlepaddle==2.5.2
    fi

    # 기본 패키지 설치
    pip install -r requirements.txt

    log_success "Python 패키지 설치 완료"
}

# 설정 파일 초기화
initialize_config() {
    log_info "설정 파일 초기화 중..."

    # 기본 설정이 없으면 생성
    if [ ! -f "config/config.yaml" ]; then
        mkdir -p config
        cp config/config.yaml.example config/config.yaml 2>/dev/null || true
    fi

    # 로그 디렉토리 생성
    mkdir -p logs
    mkdir -p data/{input,output,models}

    log_success "설정 초기화 완료"
}

# 테스트 실행
run_tests() {
    log_info "시스템 테스트 실행 중..."

    if python test_system.py; then
        log_success "시스템 테스트 통과"
    else
        log_warning "일부 테스트가 실패했습니다. 기능이 제한될 수 있습니다."
    fi
}

# 설치 완료 메시지
installation_complete() {
    echo ""
    echo "=================================================="
    log_success "설치가 완료되었습니다!"
    echo "=================================================="
    echo ""
    echo "🚀 사용법:"
    echo "  1. 가상환경 활성화: source venv/bin/activate"
    echo "  2. 시스템 정보 확인: python main.py --info"
    echo "  3. 문서 분석: python main.py document.pdf"
    echo ""
    echo "📚 추가 정보:"
    echo "  - README.md: 상세 사용법"
    echo "  - config/config.yaml: 설정 파일"
    echo "  - test_system.py: 시스템 테스트"
    echo ""

    if [ "$GPU_SUPPORT" != "false" ]; then
        log_success "GPU 지원이 활성화되었습니다 ($GPU_SUPPORT)"
        echo "  - GPU 사용: python main.py document.pdf --gpu"
    fi

    echo "  - CPU 전용: python main.py document.pdf --cpu-only"
    echo ""
}

# 메인 설치 프로세스
main() {
    echo "CPU/GPU 듀얼 모드 지원 문서 분석 시스템을 설치합니다."
    echo ""

    # 인터랙티브 확인 (non-interactive 환경에서는 건너뛰기)
    if [ -t 0 ]; then
        read -p "계속하시겠습니까? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "설치가 취소되었습니다."
            exit 0
        fi
    fi

    # 설치 단계
    detect_system
    check_python
    install_system_dependencies
    check_gpu_support
    create_virtual_environment
    install_python_packages
    initialize_config
    run_tests
    installation_complete
}

# 스크립트 실행
main "$@"