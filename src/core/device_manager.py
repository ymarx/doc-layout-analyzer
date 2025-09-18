"""
Device Manager - CPU/GPU 자동 관리 및 최적화
"""

import torch
import psutil
import platform
import subprocess
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import gc


logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """디바이스 타입"""
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"  # Apple Silicon GPU


@dataclass
class DeviceInfo:
    """디바이스 정보"""
    device_type: DeviceType
    device_id: int
    name: str
    memory_total: int  # MB
    memory_available: int  # MB
    compute_capability: Optional[float] = None
    is_available: bool = True


class DeviceManager:
    """디바이스 관리자 - CPU/GPU 자동 감지 및 최적화"""

    def __init__(self):
        self.devices: List[DeviceInfo] = []
        self.current_device: Optional[str] = None
        self.fallback_device: str = "cpu"

        # 시스템 정보 수집
        self.system_info = self._collect_system_info()

        # 사용 가능한 디바이스 감지
        self._detect_devices()

        # 기본 디바이스 설정
        self._set_default_device()

        logger.info(f"Device Manager 초기화 완료: {len(self.devices)} devices detected")

    def _collect_system_info(self) -> Dict[str, Any]:
        """시스템 정보 수집"""
        info = {
            "platform": platform.system(),
            "architecture": platform.machine(),
            "cpu_count": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "memory_total": psutil.virtual_memory().total // (1024**2),  # MB
            "python_version": platform.python_version(),
        }

        # CPU 정보
        try:
            if platform.system() == "Linux":
                with open("/proc/cpuinfo", "r") as f:
                    cpu_info = f.read()
                    if "model name" in cpu_info:
                        info["cpu_model"] = cpu_info.split("model name")[1].split(":")[1].split("\n")[0].strip()
            elif platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    info["cpu_model"] = result.stdout.strip()
        except Exception as e:
            logger.debug(f"CPU 정보 수집 실패: {e}")

        return info

    def _detect_devices(self):
        """사용 가능한 디바이스 감지"""
        # CPU (항상 사용 가능)
        cpu_device = DeviceInfo(
            device_type=DeviceType.CPU,
            device_id=0,
            name=self.system_info.get("cpu_model", "CPU"),
            memory_total=self.system_info["memory_total"],
            memory_available=psutil.virtual_memory().available // (1024**2),
            is_available=True
        )
        self.devices.append(cpu_device)

        # CUDA 감지 (NVIDIA GPU)
        self._detect_cuda_devices()

        # MPS 감지 (Apple Silicon)
        self._detect_mps_device()

    def _detect_cuda_devices(self):
        """CUDA 디바이스 감지"""
        try:
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                logger.info(f"CUDA devices detected: {device_count}")

                for i in range(device_count):
                    try:
                        props = torch.cuda.get_device_properties(i)
                        memory_total = props.total_memory // (1024**2)  # MB
                        memory_free = torch.cuda.get_device_properties(i).total_memory

                        # 실제 사용 가능 메모리 확인
                        torch.cuda.set_device(i)
                        torch.cuda.empty_cache()
                        memory_free, _ = torch.cuda.mem_get_info()
                        memory_free = memory_free // (1024**2)  # MB

                        device = DeviceInfo(
                            device_type=DeviceType.CUDA,
                            device_id=i,
                            name=props.name,
                            memory_total=memory_total,
                            memory_available=memory_free,
                            compute_capability=props.major + props.minor * 0.1,
                            is_available=memory_free > 1000  # 최소 1GB 필요
                        )
                        self.devices.append(device)

                        logger.info(f"CUDA Device {i}: {props.name}, "
                                  f"Memory: {memory_free}/{memory_total} MB, "
                                  f"Compute: {device.compute_capability}")

                    except Exception as e:
                        logger.warning(f"CUDA device {i} 정보 수집 실패: {e}")

        except Exception as e:
            logger.debug(f"CUDA 감지 실패: {e}")

    def _detect_mps_device(self):
        """Apple Silicon MPS 감지"""
        try:
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                # MPS 메모리 정보는 정확히 얻기 어려움
                device = DeviceInfo(
                    device_type=DeviceType.MPS,
                    device_id=0,
                    name="Apple Neural Engine",
                    memory_total=8192,  # 추정값
                    memory_available=6144,  # 추정값
                    is_available=True
                )
                self.devices.append(device)
                logger.info("MPS (Apple Silicon) device detected")

        except Exception as e:
            logger.debug(f"MPS 감지 실패: {e}")

    def _set_default_device(self):
        """기본 디바이스 설정"""
        # 사용 가능한 GPU가 있으면 첫 번째 GPU 선택
        gpu_devices = [d for d in self.devices if d.device_type != DeviceType.CPU and d.is_available]

        if gpu_devices:
            best_gpu = max(gpu_devices, key=lambda d: d.memory_available)
            if best_gpu.device_type == DeviceType.CUDA:
                self.current_device = f"cuda:{best_gpu.device_id}"
            elif best_gpu.device_type == DeviceType.MPS:
                self.current_device = "mps"
        else:
            self.current_device = "cpu"

        logger.info(f"기본 디바이스 설정: {self.current_device}")

    def get_optimal_device(self,
                          prefer_gpu: bool = True,
                          min_memory_mb: int = 1000,
                          task_type: str = "inference") -> str:
        """최적 디바이스 반환"""

        if not prefer_gpu:
            return "cpu"

        # GPU 디바이스 중 조건에 맞는 것 찾기
        suitable_devices = []

        for device in self.devices:
            if (device.device_type != DeviceType.CPU and
                device.is_available and
                device.memory_available >= min_memory_mb):

                suitable_devices.append(device)

        if not suitable_devices:
            logger.info(f"조건에 맞는 GPU 없음, CPU 사용")
            return "cpu"

        # 메모리가 가장 많은 디바이스 선택
        best_device = max(suitable_devices, key=lambda d: d.memory_available)

        if best_device.device_type == DeviceType.CUDA:
            return f"cuda:{best_device.device_id}"
        elif best_device.device_type == DeviceType.MPS:
            return "mps"
        else:
            return "cpu"

    def get_optimal_batch_size(self,
                              device: str = None,
                              model_size_mb: int = 1000,
                              sequence_length: int = 512) -> int:
        """최적 배치 크기 계산"""

        device = device or self.current_device

        if device == "cpu":
            # CPU의 경우 메모리와 코어 수 고려
            cpu_cores = self.system_info["cpu_count"]
            memory_gb = self.system_info["memory_total"] // 1024

            # 보수적인 배치 크기
            if memory_gb >= 16:
                return min(32, cpu_cores * 2)
            elif memory_gb >= 8:
                return min(16, cpu_cores)
            else:
                return min(8, cpu_cores)

        else:
            # GPU의 경우
            device_info = self._get_device_info(device)
            if not device_info:
                return 8

            available_memory = device_info.memory_available

            # 대략적인 메모리 사용량 계산
            # (모델 크기 + 배치당 활성화 메모리) * 안전 계수
            activation_per_sample = sequence_length * 4 / 1024  # KB per sample
            memory_per_batch = model_size_mb + (activation_per_sample / 1024)  # MB

            # 안전 계수 적용 (GPU 메모리의 80%만 사용)
            safe_memory = available_memory * 0.8

            optimal_batch = int(safe_memory / memory_per_batch)

            # 실용적인 범위로 제한
            return max(1, min(optimal_batch, 64))

    def _get_device_info(self, device: str) -> Optional[DeviceInfo]:
        """디바이스 정보 반환"""
        if device == "cpu":
            return next((d for d in self.devices if d.device_type == DeviceType.CPU), None)
        elif device.startswith("cuda:"):
            device_id = int(device.split(":")[1])
            return next((d for d in self.devices
                        if d.device_type == DeviceType.CUDA and d.device_id == device_id), None)
        elif device == "mps":
            return next((d for d in self.devices if d.device_type == DeviceType.MPS), None)
        return None

    def monitor_memory_usage(self, device: str = None) -> Dict[str, float]:
        """메모리 사용량 모니터링"""
        device = device or self.current_device

        if device == "cpu":
            memory = psutil.virtual_memory()
            return {
                "total": memory.total // (1024**2),
                "available": memory.available // (1024**2),
                "percent": memory.percent
            }

        elif device.startswith("cuda:"):
            device_id = int(device.split(":")[1])
            torch.cuda.set_device(device_id)

            total = torch.cuda.get_device_properties(device_id).total_memory
            free, used = torch.cuda.mem_get_info()

            return {
                "total": total // (1024**2),
                "available": free // (1024**2),
                "used": used // (1024**2),
                "percent": (used / total) * 100
            }

        return {}

    def cleanup_memory(self, device: str = None):
        """메모리 정리"""
        device = device or self.current_device

        # Python 가비지 컬렉션
        gc.collect()

        if device.startswith("cuda:"):
            torch.cuda.empty_cache()
            logger.debug("CUDA 메모리 캐시 정리 완료")

        elif device == "mps":
            if hasattr(torch.mps, 'empty_cache'):
                torch.mps.empty_cache()
                logger.debug("MPS 메모리 캐시 정리 완료")

    def get_device_utilization(self, device: str = None) -> Dict[str, float]:
        """디바이스 사용률 확인"""
        device = device or self.current_device

        if device == "cpu":
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent
            }

        elif device.startswith("cuda:"):
            try:
                import pynvml
                pynvml.nvmlInit()

                device_id = int(device.split(":")[1])
                handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)

                # GPU 사용률
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)

                # 메모리 사용률
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                memory_percent = (mem_info.used / mem_info.total) * 100

                return {
                    "gpu_percent": util.gpu,
                    "memory_percent": memory_percent,
                    "memory_used": mem_info.used // (1024**2),
                    "memory_total": mem_info.total // (1024**2)
                }

            except ImportError:
                logger.warning("pynvml 라이브러리가 없어 GPU 사용률을 확인할 수 없습니다")
                return {}
            except Exception as e:
                logger.warning(f"GPU 사용률 확인 실패: {e}")
                return {}

        return {}

    def benchmark_device(self, device: str = None, iterations: int = 100) -> Dict[str, float]:
        """디바이스 성능 벤치마크"""
        device = device or self.current_device

        try:
            # 간단한 행렬 곱셈 벤치마크
            size = 1024

            if device == "cpu":
                torch.set_num_threads(self.system_info["cpu_count"])

            # 텐서 생성
            a = torch.randn(size, size, device=device)
            b = torch.randn(size, size, device=device)

            # 워밍업
            for _ in range(10):
                torch.mm(a, b)

            # CPU 동기화
            if device.startswith("cuda:"):
                torch.cuda.synchronize()

            # 벤치마크 실행
            start_time = time.time()

            for _ in range(iterations):
                result = torch.mm(a, b)

            if device.startswith("cuda:"):
                torch.cuda.synchronize()

            end_time = time.time()

            total_time = end_time - start_time
            avg_time = total_time / iterations

            # FLOPS 계산 (대략적)
            flops = (2 * size**3) / avg_time / 1e9  # GFLOPS

            return {
                "total_time": total_time,
                "avg_time_per_op": avg_time,
                "gflops": flops,
                "device": device
            }

        except Exception as e:
            logger.error(f"벤치마크 실패 ({device}): {e}")
            return {"error": str(e)}

    def print_device_info(self):
        """디바이스 정보 출력"""
        print("=== Device Manager 정보 ===")
        print(f"시스템: {self.system_info['platform']} {self.system_info['architecture']}")
        print(f"CPU: {self.system_info.get('cpu_model', 'Unknown')} "
              f"({self.system_info['cpu_count']} cores)")
        print(f"메모리: {self.system_info['memory_total']/1024:.1f} GB")
        print(f"현재 디바이스: {self.current_device}")

        print("\n=== 사용 가능한 디바이스 ===")
        for device in self.devices:
            status = "✓" if device.is_available else "✗"
            memory_info = f"{device.memory_available}/{device.memory_total} MB"

            compute_info = ""
            if device.compute_capability:
                compute_info = f" (Compute {device.compute_capability})"

            print(f"{status} {device.device_type.value}:{device.device_id} - "
                  f"{device.name} - {memory_info}{compute_info}")


# 전역 디바이스 매니저 인스턴스
device_manager = DeviceManager()


def get_device_manager() -> DeviceManager:
    """디바이스 매니저 인스턴스 반환"""
    return device_manager


if __name__ == "__main__":
    # 테스트
    dm = DeviceManager()
    dm.print_device_info()

    # 벤치마크 실행
    print("\n=== 성능 벤치마크 ===")
    for device in dm.devices:
        if device.is_available:
            device_name = f"{device.device_type.value}:{device.device_id}" if device.device_type != DeviceType.CPU else "cpu"
            result = dm.benchmark_device(device_name, iterations=50)
            if "error" not in result:
                print(f"{device_name}: {result['gflops']:.2f} GFLOPS, {result['avg_time_per_op']*1000:.2f} ms/op")