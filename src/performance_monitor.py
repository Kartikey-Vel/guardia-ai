"""
Performance monitoring and optimization module for Guardia-AI system.
Provides real-time system monitoring, adaptive performance tuning, and intelligent resource management.
"""

import time
import threading
import psutil
import os
import json
from collections import deque
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Real-time performance metrics"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    gpu_percent: float = 0.0
    gpu_memory_percent: float = 0.0
    fps: float = 0.0
    inference_time_ms: float = 0.0
    frame_processing_time_ms: float = 0.0
    detection_count: int = 0
    frame_skip_ratio: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'cpu_percent': round(self.cpu_percent, 1),
            'memory_percent': round(self.memory_percent, 1),
            'memory_used_mb': round(self.memory_used_mb, 1),
            'gpu_percent': round(self.gpu_percent, 1),
            'gpu_memory_percent': round(self.gpu_memory_percent, 1),
            'fps': round(self.fps, 1),
            'inference_time_ms': round(self.inference_time_ms, 2),
            'frame_processing_time_ms': round(self.frame_processing_time_ms, 2),
            'detection_count': self.detection_count,
            'frame_skip_ratio': round(self.frame_skip_ratio, 2)
        }

@dataclass
class AdaptiveSettings:
    """Adaptive performance settings based on system load"""
    frameskip: int = 3
    yolo_imgsz: int = 640
    track_interval: int = 5
    vision_enabled: bool = True
    pose_enabled: bool = True
    motion_filter_enabled: bool = True
    detection_confidence: float = 0.25
    max_detections_per_frame: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'frameskip': self.frameskip,
            'yolo_imgsz': self.yolo_imgsz,
            'track_interval': self.track_interval,
            'vision_enabled': self.vision_enabled,
            'pose_enabled': self.pose_enabled,
            'motion_filter_enabled': self.motion_filter_enabled,
            'detection_confidence': self.detection_confidence,
            'max_detections_per_frame': self.max_detections_per_frame
        }

class PerformanceProfiler:
    """Profiles and tracks performance of different system components"""
    
    def __init__(self):
        self.timings: Dict[str, deque] = {}
        self.lock = threading.Lock()
        self.max_history = 100
    
    def time_operation(self, operation_name: str):
        """Context manager for timing operations"""
        return TimingContext(self, operation_name)
    
    def record_timing(self, operation_name: str, duration_ms: float):
        """Record timing for an operation"""
        with self.lock:
            if operation_name not in self.timings:
                self.timings[operation_name] = deque(maxlen=self.max_history)
            self.timings[operation_name].append(duration_ms)
    
    def get_average_timing(self, operation_name: str) -> float:
        """Get average timing for an operation"""
        with self.lock:
            if operation_name not in self.timings or not self.timings[operation_name]:
                return 0.0
            return sum(self.timings[operation_name]) / len(self.timings[operation_name])
    
    def get_performance_report(self) -> Dict[str, Dict[str, float]]:
        """Get comprehensive performance report"""
        with self.lock:
            report = {}
            for op_name, timings in self.timings.items():
                if timings:
                    report[op_name] = {
                        'avg_ms': round(sum(timings) / len(timings), 2),
                        'min_ms': round(min(timings), 2),
                        'max_ms': round(max(timings), 2),
                        'count': len(timings)
                    }
            return report

class TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, profiler: PerformanceProfiler, operation_name: str):
        self.profiler = profiler
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.profiler.record_timing(self.operation_name, duration_ms)

class PerformanceMonitor:
    """Advanced performance monitoring and adaptive optimization"""
    
    def __init__(self, history_size: int = 300):
        self.history_size = history_size
        self.metrics_history: deque = deque(maxlen=history_size)
        self.profiler = PerformanceProfiler()
        self.adaptive_settings = AdaptiveSettings()
        self.lock = threading.Lock()
        
        # Performance thresholds
        self.high_cpu_threshold = 80.0
        self.high_memory_threshold = 85.0
        self.low_fps_threshold = 10.0
        self.high_inference_time_threshold = 100.0  # ms
        
        # Optimization callbacks
        self.optimization_callbacks: List[Callable] = []
        
        # Initialize GPU monitoring if available
        self.gpu_available = self._check_gpu_availability()
        
        logger.info(f"Performance monitor initialized. GPU available: {self.gpu_available}")
    
    def _check_gpu_availability(self) -> bool:
        """Check if GPU monitoring is available"""
        try:
            import GPUtil
            return len(GPUtil.getGPUs()) > 0
        except (ImportError, Exception):
            return False
    
    def _get_gpu_metrics(self) -> Dict[str, float]:
        """Get GPU metrics if available"""
        if not self.gpu_available:
            return {'gpu_percent': 0.0, 'gpu_memory_percent': 0.0}
        
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Use first GPU
                return {
                    'gpu_percent': gpu.load * 100,
                    'gpu_memory_percent': gpu.memoryUtil * 100
                }
        except Exception as e:
            logger.warning(f"Failed to get GPU metrics: {e}")
        
        return {'gpu_percent': 0.0, 'gpu_memory_percent': 0.0}
    
    def record_metrics(self, fps: float = 0.0, inference_time_ms: float = 0.0, 
                      frame_processing_time_ms: float = 0.0, detection_count: int = 0,
                      frame_skip_ratio: float = 0.0):
        """Record current performance metrics"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / 1024 / 1024
            
            # GPU metrics
            gpu_metrics = self._get_gpu_metrics()
            
            # Create metrics object
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                gpu_percent=gpu_metrics['gpu_percent'],
                gpu_memory_percent=gpu_metrics['gpu_memory_percent'],
                fps=fps,
                inference_time_ms=inference_time_ms,
                frame_processing_time_ms=frame_processing_time_ms,
                detection_count=detection_count,
                frame_skip_ratio=frame_skip_ratio
            )
            
            with self.lock:
                self.metrics_history.append(metrics)
            
            # Check for optimization opportunities
            self._check_optimization_triggers(metrics)
            
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
    
    def _check_optimization_triggers(self, metrics: PerformanceMetrics):
        """Check if performance optimization is needed"""
        try:
            optimization_needed = False
            reasons = []
            
            # High CPU usage
            if metrics.cpu_percent > self.high_cpu_threshold:
                optimization_needed = True
                reasons.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
            
            # High memory usage
            if metrics.memory_percent > self.high_memory_threshold:
                optimization_needed = True
                reasons.append(f"High memory usage: {metrics.memory_percent:.1f}%")
            
            # Low FPS
            if metrics.fps < self.low_fps_threshold and metrics.fps > 0:
                optimization_needed = True
                reasons.append(f"Low FPS: {metrics.fps:.1f}")
            
            # High inference time
            if metrics.inference_time_ms > self.high_inference_time_threshold:
                optimization_needed = True
                reasons.append(f"High inference time: {metrics.inference_time_ms:.1f}ms")
            
            if optimization_needed:
                logger.info(f"Performance optimization triggered: {', '.join(reasons)}")
                self._apply_adaptive_optimization(metrics, reasons)
        
        except Exception as e:
            logger.error(f"Failed to check optimization triggers: {e}")
    
    def _apply_adaptive_optimization(self, metrics: PerformanceMetrics, reasons: List[str]):
        """Apply adaptive performance optimizations"""
        try:
            old_settings = self.adaptive_settings.to_dict()
            
            # Adaptive frameskip
            if metrics.cpu_percent > self.high_cpu_threshold or metrics.fps < self.low_fps_threshold:
                self.adaptive_settings.frameskip = min(self.adaptive_settings.frameskip + 1, 8)
            
            # Adaptive image size
            if metrics.inference_time_ms > self.high_inference_time_threshold:
                if self.adaptive_settings.yolo_imgsz > 320:
                    self.adaptive_settings.yolo_imgsz = max(320, self.adaptive_settings.yolo_imgsz - 160)
            
            # Adaptive tracking interval
            if metrics.cpu_percent > self.high_cpu_threshold:
                self.adaptive_settings.track_interval = min(self.adaptive_settings.track_interval + 2, 15)
            
            # Disable heavy features under high load
            if metrics.cpu_percent > 90:
                self.adaptive_settings.vision_enabled = False
                self.adaptive_settings.pose_enabled = False
            elif metrics.cpu_percent < 60:
                self.adaptive_settings.vision_enabled = True
                self.adaptive_settings.pose_enabled = True
            
            # Adaptive detection confidence
            if metrics.detection_count > 50:  # Too many detections
                self.adaptive_settings.detection_confidence = min(0.5, self.adaptive_settings.detection_confidence + 0.05)
            elif metrics.detection_count < 5:
                self.adaptive_settings.detection_confidence = max(0.15, self.adaptive_settings.detection_confidence - 0.05)
            
            new_settings = self.adaptive_settings.to_dict()
            
            # Log changes
            changes = []
            for key, new_val in new_settings.items():
                old_val = old_settings.get(key)
                if old_val != new_val:
                    changes.append(f"{key}: {old_val} -> {new_val}")
            
            if changes:
                logger.info(f"Applied adaptive optimizations: {', '.join(changes)}")
                
                # Notify callbacks
                for callback in self.optimization_callbacks:
                    try:
                        callback(self.adaptive_settings)
                    except Exception as e:
                        logger.error(f"Optimization callback failed: {e}")
        
        except Exception as e:
            logger.error(f"Failed to apply adaptive optimization: {e}")
    
    def add_optimization_callback(self, callback: Callable):
        """Add callback to be called when optimizations are applied"""
        self.optimization_callbacks.append(callback)
    
    def get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """Get the most recent metrics"""
        with self.lock:
            if not self.metrics_history:
                return None
            return self.metrics_history[-1].to_dict()
    
    def get_metrics_history(self, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get metrics history for the specified time period"""
        cutoff_time = time.time() - (minutes * 60)
        with self.lock:
            return [
                metrics.to_dict() 
                for metrics in self.metrics_history 
                if metrics.timestamp >= cutoff_time
            ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        with self.lock:
            if not self.metrics_history:
                return {}
            
            recent_metrics = list(self.metrics_history)[-60:]  # Last 60 samples
            
            # Calculate averages
            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
            avg_fps = sum(m.fps for m in recent_metrics if m.fps > 0) / max(1, len([m for m in recent_metrics if m.fps > 0]))
            avg_inference = sum(m.inference_time_ms for m in recent_metrics if m.inference_time_ms > 0) / max(1, len([m for m in recent_metrics if m.inference_time_ms > 0]))
            
            # Get profiler report
            profiler_report = self.profiler.get_performance_report()
            
            return {
                'summary': {
                    'avg_cpu_percent': round(avg_cpu, 1),
                    'avg_memory_percent': round(avg_memory, 1),
                    'avg_fps': round(avg_fps, 1),
                    'avg_inference_time_ms': round(avg_inference, 2),
                    'samples_collected': len(recent_metrics),
                    'gpu_available': self.gpu_available
                },
                'adaptive_settings': self.adaptive_settings.to_dict(),
                'operation_timings': profiler_report,
                'current_metrics': self.get_current_metrics()
            }
    
    def reset_adaptive_settings(self):
        """Reset adaptive settings to defaults"""
        self.adaptive_settings = AdaptiveSettings()
        logger.info("Adaptive settings reset to defaults")
    
    def save_performance_report(self, filepath: str):
        """Save detailed performance report to file"""
        try:
            report = {
                'timestamp': time.time(),
                'performance_summary': self.get_performance_summary(),
                'metrics_history': self.get_metrics_history(minutes=10),
                'system_info': {
                    'cpu_count': psutil.cpu_count(),
                    'total_memory_gb': round(psutil.virtual_memory().total / 1024**3, 2),
                    'gpu_available': self.gpu_available
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Performance report saved to {filepath}")
        
        except Exception as e:
            logger.error(f"Failed to save performance report: {e}")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
