"""
Dataset loaders for Guardia AI model training
"""

import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
import cv2
import json
import os
from pathlib import Path
from typing import List, Tuple, Optional
import pickle


class SkeletonActionDataset(Dataset):
    """
    Dataset for skeleton-based action recognition
    Compatible with NTU RGB+D and Kinetics-Skeleton formats
    """
    
    def __init__(
        self,
        root: str,
        split: str = 'train',
        num_frames: int = 16,
        num_joints: int = 17,
        actions: Optional[List[str]] = None
    ):
        self.root = Path(root)
        self.split = split
        self.num_frames = num_frames
        self.num_joints = num_joints
        
        # Default Guardia action classes
        self.actions = actions or [
            'normal',
            'fight_detected',
            'fall_detected',
            'running',
            'trespassing',
            'threatening_pose',
            'suspicious_movement'
        ]
        self.action_to_idx = {action: idx for idx, action in enumerate(self.actions)}
        
        self.samples = self._load_samples()
    
    def _load_samples(self) -> List[Tuple[str, int]]:
        """Load skeleton files and labels"""
        samples = []
        split_file = self.root / f'{self.split}.txt'
        
        if split_file.exists():
            with open(split_file, 'r') as f:
                for line in f:
                    skeleton_path, label = line.strip().split()
                    samples.append((skeleton_path, int(label)))
        else:
            # Scan directory structure
            for action_idx, action in enumerate(self.actions):
                action_dir = self.root / self.split / action
                if action_dir.exists():
                    for skeleton_file in action_dir.glob('*.pkl'):
                        samples.append((str(skeleton_file), action_idx))
        
        return samples
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        skeleton_path, label = self.samples[idx]
        
        # Load skeleton data (T, J, C) where T=frames, J=joints, C=coords
        with open(skeleton_path, 'rb') as f:
            skeleton_data = pickle.load(f)
        
        # Normalize to num_frames via sampling or padding
        skeleton_data = self._normalize_frames(skeleton_data)
        
        # Convert to tensor (T, J, C)
        skeleton_tensor = torch.FloatTensor(skeleton_data)
        
        return skeleton_tensor, label
    
    def _normalize_frames(self, skeleton: np.ndarray) -> np.ndarray:
        """Normalize skeleton sequence to fixed number of frames"""
        T, J, C = skeleton.shape
        
        if T == self.num_frames:
            return skeleton
        elif T > self.num_frames:
            # Sample frames uniformly
            indices = np.linspace(0, T - 1, self.num_frames, dtype=int)
            return skeleton[indices]
        else:
            # Pad with last frame
            padding = np.repeat(skeleton[-1:], self.num_frames - T, axis=0)
            return np.concatenate([skeleton, padding], axis=0)


class MotionAnomalyDataset(Dataset):
    """
    Dataset for motion anomaly detection
    Compatible with Avenue, UCSD Ped2 formats
    """
    
    def __init__(
        self,
        root: str,
        split: str = 'train',
        num_frames: int = 8,
        frame_size: Tuple[int, int] = (224, 224),
        optical_flow: bool = True
    ):
        self.root = Path(root)
        self.split = split
        self.num_frames = num_frames
        self.frame_size = frame_size
        self.optical_flow = optical_flow
        
        self.samples = self._load_samples()
    
    def _load_samples(self) -> List[Tuple[str, int]]:
        """Load video clips and anomaly labels"""
        samples = []
        
        # Load annotations
        annotation_file = self.root / f'{self.split}_annotations.json'
        if annotation_file.exists():
            with open(annotation_file, 'r') as f:
                annotations = json.load(f)
            
            for item in annotations:
                video_path = self.root / item['video_path']
                label = item['label']  # 0=normal, 1=anomaly
                samples.append((str(video_path), label))
        else:
            # Scan directory
            for label, folder in enumerate(['normal', 'anomaly']):
                folder_path = self.root / self.split / folder
                if folder_path.exists():
                    for video_file in folder_path.glob('*.mp4'):
                        samples.append((str(video_file), label))
        
        return samples
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        video_path, label = self.samples[idx]
        
        # Extract frames
        frames = self._extract_frames(video_path)
        
        if self.optical_flow:
            # Compute optical flow
            flow = self._compute_optical_flow(frames)
            return torch.FloatTensor(flow), label
        else:
            # Return raw frames
            frames = frames.transpose(0, 3, 1, 2)  # (T, H, W, C) -> (T, C, H, W)
            return torch.FloatTensor(frames), label
    
    def _extract_frames(self, video_path: str) -> np.ndarray:
        """Extract frames from video"""
        cap = cv2.VideoCapture(video_path)
        frames = []
        
        while len(frames) < self.num_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Resize
            frame = cv2.resize(frame, self.frame_size)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = frame.astype(np.float32) / 255.0
            frames.append(frame)
        
        cap.release()
        
        # Pad if needed
        while len(frames) < self.num_frames:
            frames.append(frames[-1])
        
        return np.stack(frames[:self.num_frames])
    
    def _compute_optical_flow(self, frames: np.ndarray) -> np.ndarray:
        """Compute optical flow between consecutive frames"""
        flows = []
        
        for i in range(len(frames) - 1):
            prev = (frames[i] * 255).astype(np.uint8)
            curr = (frames[i + 1] * 255).astype(np.uint8)
            
            prev_gray = cv2.cvtColor(prev, cv2.COLOR_RGB2GRAY)
            curr_gray = cv2.cvtColor(curr, cv2.COLOR_RGB2GRAY)
            
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
            flows.append(flow)
        
        # Add zero flow for last frame
        flows.append(np.zeros_like(flows[0]))
        
        return np.stack(flows)


class EmotionDataset(Dataset):
    """
    Dataset for privacy-first emotion recognition
    Compatible with AffectNet, FER2013 formats
    """
    
    def __init__(
        self,
        root: str,
        split: str = 'train',
        image_size: int = 112,
        blur_background: bool = True,
        emotions: Optional[List[str]] = None
    ):
        self.root = Path(root)
        self.split = split
        self.image_size = image_size
        self.blur_background = blur_background
        
        # Guardia emotion classes
        self.emotions = emotions or [
            'neutral',
            'stress',
            'aggression',
            'sadness',
            'fear',
            'anxiety'
        ]
        self.emotion_to_idx = {emotion: idx for idx, emotion in enumerate(self.emotions)}
        
        self.samples = self._load_samples()
    
    def _load_samples(self) -> List[Tuple[str, int]]:
        """Load image files and emotion labels"""
        samples = []
        
        annotation_file = self.root / f'{self.split}_annotations.csv'
        if annotation_file.exists():
            import pandas as pd
            df = pd.read_csv(annotation_file)
            
            for _, row in df.iterrows():
                image_path = self.root / row['image_path']
                emotion_label = self.emotion_to_idx.get(row['emotion'], 0)
                samples.append((str(image_path), emotion_label))
        else:
            # Scan directory
            for emotion_idx, emotion in enumerate(self.emotions):
                emotion_dir = self.root / self.split / emotion
                if emotion_dir.exists():
                    for img_file in emotion_dir.glob('*.jpg'):
                        samples.append((str(img_file), emotion_idx))
        
        return samples
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        image_path, label = self.samples[idx]
        
        # Load image
        image = cv2.imread(image_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect face and crop
        image = self._crop_face(image)
        
        # Blur background for privacy
        if self.blur_background:
            image = self._blur_background(image)
        
        # Resize
        image = cv2.resize(image, (self.image_size, self.image_size))
        
        # Normalize
        image = image.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        image = (image - mean) / std
        
        # Convert to tensor (C, H, W)
        image = torch.FloatTensor(image.transpose(2, 0, 1))
        
        return image, label
    
    def _crop_face(self, image: np.ndarray) -> np.ndarray:
        """Detect and crop face region"""
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) > 0:
            # Take largest face
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            # Add margin
            margin = int(0.2 * max(w, h))
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(image.shape[1], x + w + margin)
            y2 = min(image.shape[0], y + h + margin)
            return image[y1:y2, x1:x2]
        else:
            return image
    
    def _blur_background(self, image: np.ndarray) -> np.ndarray:
        """Blur background for privacy (simple version)"""
        # In production, use segmentation model for accurate face mask
        blurred = cv2.GaussianBlur(image, (51, 51), 0)
        
        # Create simple ellipse mask for face
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.ellipse(mask, (w//2, h//2), (w//3, h//2), 0, 0, 360, 255, -1)
        mask = mask / 255.0
        mask = mask[:, :, np.newaxis]
        
        # Blend
        result = image * mask + blurred * (1 - mask)
        return result.astype(np.uint8)


def create_dataloaders(
    dataset: Dataset,
    batch_size: int = 32,
    num_workers: int = 4,
    split: str = 'train'
) -> DataLoader:
    """Create dataloader with common settings"""
    shuffle = (split == 'train')
    
    loader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=True,
        drop_last=(split == 'train')
    )
    
    return loader
