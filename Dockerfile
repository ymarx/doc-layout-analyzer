# Document Layout Analyzer - Multi-stage Docker Build
# CPU/GPU 듀얼 모드 지원

FROM python:3.11-slim as base

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    # 기본 도구
    wget \
    curl \
    unzip \
    # 이미지 처리
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # PDF 처리
    poppler-utils \
    # OCR
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    # LibreOffice (headless)
    libreoffice \
    # 빌드 도구
    build-essential \
    python3-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# OCRmyPDF 설치
RUN pip install --no-cache-dir ocrmypdf

# Python 의존성 파일 복사
COPY requirements.txt .

# 기본 Python 패키지 설치 (CPU 버전)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir paddlepaddle==2.5.2
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY config/ ./config/
COPY main.py .
COPY test_system.py .

# 데이터 및 로그 디렉토리 생성
RUN mkdir -p data/{input,output,models} logs

# 권한 설정
RUN chmod +x main.py test_system.py

# 포트 노출 (API 서버용)
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import src.core.config; print('OK')" || exit 1

# 기본 명령어
CMD ["python", "main.py", "--info"]

# =============================================================================
# GPU 지원 빌드 (별도 이미지)
# =============================================================================

FROM nvidia/cuda:11.8-runtime-ubuntu22.04 as gpu-base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Python 3.11 설치
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3-pip \
    # 기본 도구
    wget \
    curl \
    unzip \
    # 이미지 처리
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # PDF 처리
    poppler-utils \
    # OCR
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    # LibreOffice (headless)
    libreoffice \
    # 빌드 도구
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Python 기본 설정
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
RUN python3 -m pip install --upgrade pip

# OCRmyPDF 설치
RUN pip install --no-cache-dir ocrmypdf

# Python 의존성 파일 복사
COPY requirements.txt .

# GPU 지원 Python 패키지 설치
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu118
RUN pip install --no-cache-dir paddlepaddle-gpu==2.5.2
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY src/ ./src/
COPY config/ ./config/
COPY main.py .
COPY test_system.py .

# 데이터 및 로그 디렉토리 생성
RUN mkdir -p data/{input,output,models} logs

# 권한 설정
RUN chmod +x main.py test_system.py

# GPU 설정 파일 생성
RUN echo 'system:\n  processing_mode: "gpu"\nocr:\n  paddleocr:\n    use_gpu: true' > config/gpu_config.yaml

# 포트 노출
EXPOSE 8000

# GPU 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD python -c "import torch; print('GPU available:', torch.cuda.is_available())" || exit 1

# GPU 모드로 실행
CMD ["python", "main.py", "--info", "--gpu"]