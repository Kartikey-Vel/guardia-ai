"""
Advanced caching and optimization utilities for Guardia-AI system.
Provides intelligent caching for detections, frames, and API responses.
"""

import time
import threading
import hashlib
import pickle
import os
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union
from collections import OrderedDict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    timestamp: float
    access_count: int = 0
    last_access: float = 0.0
    ttl: float = 300.0  # 5 minutes default TTL
    
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl
    
    def access(self):
        self.access_count += 1
        self.last_access = time.time()

class LRUCache:
    """Thread-safe LRU cache with TTL support"""
    
    def __init__(self, max_size: int = 100, default_ttl: float = 300.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry.timestamp > entry.ttl
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        with self.lock:
            self._cleanup_expired()
            
            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired():
                    entry.access()
                    # Move to end (most recently used)
                    self.cache.move_to_end(key)
                    self.hits += 1
                    return entry.data
                else:
                    del self.cache[key]
            
            self.misses += 1
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None):
        """Put item in cache"""
        with self.lock:
            if ttl is None:
                ttl = self.default_ttl
            
            entry = CacheEntry(
                data=value,
                timestamp=time.time(),
                ttl=ttl
            )
            
            if key in self.cache:
                # Update existing
                self.cache[key] = entry
                self.cache.move_to_end(key)
            else:
                # Add new
                self.cache[key] = entry
                
                # Evict oldest if over capacity
                while len(self.cache) > self.max_size:
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
    
    def invalidate(self, key: str):
        """Remove specific key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
    
    def clear(self):
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 3),
                'total_requests': total_requests
            }

class DetectionCache:
    """Specialized cache for YOLO detections with similarity matching"""
    
    def __init__(self, max_size: int = 50, similarity_threshold: float = 0.95):
        self.cache = LRUCache(max_size, default_ttl=10.0)  # Short TTL for detections
        self.similarity_threshold = similarity_threshold
        self.lock = threading.Lock()
    
    def _frame_hash(self, frame: np.ndarray) -> str:
        """Generate hash for frame"""
        # Downsample frame for hashing
        small_frame = cv2.resize(frame, (64, 48))
        return hashlib.md5(small_frame.tobytes()).hexdigest()
    
    def _frames_similar(self, frame1: np.ndarray, frame2: np.ndarray) -> bool:
        """Check if two frames are similar"""
        try:
            # Resize to same small size for comparison
            small1 = cv2.resize(frame1, (32, 24))
            small2 = cv2.resize(frame2, (32, 24))
            
            # Calculate structural similarity
            diff = cv2.absdiff(small1, small2)
            similarity = 1.0 - (np.mean(diff) / 255.0)
            
            return similarity >= self.similarity_threshold
        except Exception:
            return False
    
    def get_detection(self, frame: np.ndarray) -> Optional[Any]:
        """Get cached detection for similar frame"""
        frame_hash = self._frame_hash(frame)
        
        # First try exact hash match
        result = self.cache.get(frame_hash)
        if result is not None:
            return result
        
        # If no exact match, check for similar frames (more expensive)
        with self.lock:
            for key, entry in list(self.cache.cache.items()):
                if not entry.is_expired():
                    cached_frame = entry.data.get('frame')
                    if cached_frame is not None and self._frames_similar(frame, cached_frame):
                        entry.access()
                        return entry.data.get('detections')
        
        return None
    
    def cache_detection(self, frame: np.ndarray, detections: Any):
        """Cache detection result for frame"""
        frame_hash = self._frame_hash(frame)
        
        # Store frame thumbnail and detections
        thumbnail = cv2.resize(frame, (160, 120))
        cache_data = {
            'frame': thumbnail,
            'detections': detections,
            'full_hash': frame_hash
        }
        
        self.cache.put(frame_hash, cache_data, ttl=10.0)

class FrameBuffer:
    """Optimized frame buffer for video processing"""
    
    def __init__(self, buffer_size: int = 30):
        self.buffer_size = buffer_size
        self.frames: OrderedDict[float, np.ndarray] = OrderedDict()
        self.lock = threading.Lock()
    
    def add_frame(self, frame: np.ndarray, timestamp: Optional[float] = None):
        """Add frame to buffer"""
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            self.frames[timestamp] = frame.copy()
            
            # Remove old frames if buffer is full
            while len(self.frames) > self.buffer_size:
                oldest_ts = next(iter(self.frames))
                del self.frames[oldest_ts]
    
    def get_recent_frames(self, count: int = 5) -> List[Tuple[float, np.ndarray]]:
        """Get most recent frames"""
        with self.lock:
            recent_items = list(self.frames.items())[-count:]
            return [(ts, frame.copy()) for ts, frame in recent_items]
    
    def get_frame_at_time(self, target_time: float, tolerance: float = 1.0) -> Optional[np.ndarray]:
        """Get frame closest to target time"""
        with self.lock:
            best_frame = None
            best_diff = float('inf')
            
            for ts, frame in self.frames.items():
                diff = abs(ts - target_time)
                if diff < tolerance and diff < best_diff:
                    best_diff = diff
                    best_frame = frame
            
            return best_frame.copy() if best_frame is not None else None
    
    def clear(self):
        """Clear all frames"""
        with self.lock:
            self.frames.clear()

class APIResponseCache:
    """Cache for API responses with intelligent invalidation"""
    
    def __init__(self, max_size: int = 200):
        self.cache = LRUCache(max_size, default_ttl=60.0)  # 1 minute default
        self.endpoint_ttls = {
            '/api/metrics': 2.0,      # Fast changing
            '/api/events': 5.0,       # Medium changing
            '/api/system': 10.0,      # Slower changing
            '/api/zones': 300.0,      # Rarely changing
            '/api/envs': 300.0,       # Rarely changing
            '/api/summary': 30.0,     # AI generated, expensive
        }
    
    def _get_cache_key(self, endpoint: str, params: Optional[Dict] = None, 
                      user: Optional[str] = None) -> str:
        """Generate cache key for API request"""
        key_parts = [endpoint]
        
        if user:
            key_parts.append(f"user:{user}")
        
        if params:
            # Sort params for consistent key generation
            sorted_params = sorted(params.items())
            params_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            key_parts.append(params_str)
        
        return "|".join(key_parts)
    
    def get_response(self, endpoint: str, params: Optional[Dict] = None, 
                    user: Optional[str] = None) -> Optional[Any]:
        """Get cached API response"""
        cache_key = self._get_cache_key(endpoint, params, user)
        return self.cache.get(cache_key)
    
    def cache_response(self, endpoint: str, response: Any, params: Optional[Dict] = None,
                      user: Optional[str] = None):
        """Cache API response"""
        cache_key = self._get_cache_key(endpoint, params, user)
        ttl = self.endpoint_ttls.get(endpoint, 60.0)
        self.cache.put(cache_key, response, ttl=ttl)
    
    def invalidate_endpoint(self, endpoint: str, user: Optional[str] = None):
        """Invalidate all cached responses for an endpoint"""
        pattern = endpoint
        if user:
            pattern += f"|user:{user}"
        
        # Remove all keys that start with the pattern
        with self.cache.lock:
            keys_to_remove = [
                key for key in self.cache.cache.keys()
                if key.startswith(pattern)
            ]
            for key in keys_to_remove:
                del self.cache.cache[key]

class SmartImageProcessor:
    """Optimized image processing with caching and batch operations"""
    
    def __init__(self):
        self.resize_cache = LRUCache(max_size=100, default_ttl=60.0)
        self.processed_frame_cache = LRUCache(max_size=50, default_ttl=30.0)
    
    def smart_resize(self, image: np.ndarray, target_size: Tuple[int, int], 
                    force_aspect_ratio: bool = True) -> np.ndarray:
        """Optimized resize with caching"""
        # Generate cache key
        img_hash = hashlib.md5(image.tobytes()).hexdigest()[:16]
        cache_key = f"{img_hash}_{target_size[0]}x{target_size[1]}_{force_aspect_ratio}"
        
        # Check cache
        cached = self.resize_cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Perform resize
        if force_aspect_ratio:
            # Maintain aspect ratio with padding
            h, w = image.shape[:2]
            target_w, target_h = target_size
            
            # Calculate scaling factor
            scale = min(target_w / w, target_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            
            # Resize
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            
            # Add padding if needed
            if new_w != target_w or new_h != target_h:
                # Create padded image
                result = np.zeros((target_h, target_w, image.shape[2] if len(image.shape) > 2 else 1), dtype=image.dtype)
                y_offset = (target_h - new_h) // 2
                x_offset = (target_w - new_w) // 2
                result[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
            else:
                result = resized
        else:
            # Simple resize
            result = cv2.resize(image, target_size, interpolation=cv2.INTER_LINEAR)
        
        # Cache result
        self.resize_cache.put(cache_key, result.copy())
        
        return result
    
    def preprocess_frame_batch(self, frames: List[np.ndarray], 
                              target_size: Tuple[int, int]) -> List[np.ndarray]:
        """Batch process multiple frames efficiently"""
        results = []
        
        for frame in frames:
            processed = self.smart_resize(frame, target_size)
            results.append(processed)
        
        return results

# Global cache instances
detection_cache = DetectionCache()
api_cache = APIResponseCache()
image_processor = SmartImageProcessor()
frame_buffer = FrameBuffer()

def get_cache_stats() -> Dict[str, Any]:
    """Get statistics for all caches"""
    return {
        'detection_cache': detection_cache.cache.get_stats(),
        'api_cache': api_cache.cache.get_stats(),
        'resize_cache': image_processor.resize_cache.get_stats(),
        'processed_frame_cache': image_processor.processed_frame_cache.get_stats(),
        'frame_buffer_size': len(frame_buffer.frames)
    }

def clear_all_caches():
    """Clear all caches"""
    detection_cache.cache.clear()
    api_cache.cache.clear()
    image_processor.resize_cache.clear()
    image_processor.processed_frame_cache.clear()
    frame_buffer.clear()
    logger.info("All caches cleared")
