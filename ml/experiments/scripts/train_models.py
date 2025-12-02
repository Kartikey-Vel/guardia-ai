#!/usr/bin/env python3
"""
Guardia AI - Model Training Script
Trains all three models: SkeleGNN, MotionStream, and MoodTiny
Supports both real datasets and synthetic data for demo/testing
"""

import os
import sys
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import numpy as np
from pathlib import Path
from tqdm import tqdm
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.skelegnn import create_skelegnn
from models.motionstream import create_motionstream
from models.moodtiny import create_moodtiny


# ============================================================================
# Synthetic Dataset Classes (for training without real data)
# ============================================================================

class SyntheticSkeletonDataset(Dataset):
    """Generate synthetic skeleton data for SkeleGNN training"""
    
    def __init__(
        self,
        num_samples: int = 1000,
        num_frames: int = 16,
        num_joints: int = 17,
        num_classes: int = 7,
        split: str = 'train'
    ):
        self.num_samples = num_samples
        self.num_frames = num_frames
        self.num_joints = num_joints
        self.num_classes = num_classes
        self.split = split
        
        # Pre-generate samples for consistency
        np.random.seed(42 if split == 'train' else 123)
        self.samples = []
        for _ in range(num_samples):
            label = np.random.randint(0, num_classes)
            # Generate skeleton with class-specific patterns
            skeleton = self._generate_skeleton(label)
            self.samples.append((skeleton, label))
    
    def _generate_skeleton(self, label: int) -> np.ndarray:
        """Generate synthetic skeleton with class-specific motion patterns"""
        # Base pose (standing person)
        base_pose = np.array([
            [0.0, 0.0, 0.0],   # 0: nose
            [-0.1, 0.0, 0.0],  # 1: left_eye
            [0.1, 0.0, 0.0],   # 2: right_eye
            [-0.2, 0.1, 0.0],  # 3: left_ear
            [0.2, 0.1, 0.0],   # 4: right_ear
            [-0.3, 0.5, 0.0],  # 5: left_shoulder
            [0.3, 0.5, 0.0],   # 6: right_shoulder
            [-0.5, 0.7, 0.0],  # 7: left_elbow
            [0.5, 0.7, 0.0],   # 8: right_elbow
            [-0.6, 0.9, 0.0],  # 9: left_wrist
            [0.6, 0.9, 0.0],   # 10: right_wrist
            [-0.2, 1.0, 0.0],  # 11: left_hip
            [0.2, 1.0, 0.0],   # 12: right_hip
            [-0.2, 1.5, 0.0],  # 13: left_knee
            [0.2, 1.5, 0.0],   # 14: right_knee
            [-0.2, 2.0, 0.0],  # 15: left_ankle
            [0.2, 2.0, 0.0],   # 16: right_ankle
        ], dtype=np.float32)
        
        frames = []
        for t in range(self.num_frames):
            pose = base_pose.copy()
            phase = t / self.num_frames * 2 * np.pi
            
            if label == 0:  # normal - subtle movement
                pose += np.random.randn(17, 3) * 0.01
            elif label == 1:  # fight - aggressive arm movements
                pose[7:11] += np.array([np.sin(phase * 4) * 0.3, np.cos(phase * 4) * 0.2, 0])
                pose += np.random.randn(17, 3) * 0.05
            elif label == 2:  # fall - body tilting down
                tilt = t / self.num_frames
                pose[:, 1] += tilt * 0.5
                pose[:, 0] += tilt * 0.3
            elif label == 3:  # running - leg movement
                pose[13:17, 1] += np.sin(phase * 3) * 0.2
                pose[7:11, 1] += np.sin(phase * 3 + np.pi) * 0.1
            elif label == 4:  # trespassing - slow creeping
                pose[:, 0] += t / self.num_frames * 0.5
                pose += np.random.randn(17, 3) * 0.02
            elif label == 5:  # threatening_pose - raised arms
                pose[7:11, 1] -= 0.3
                pose[9:11, 0] *= 1.2
            elif label == 6:  # suspicious_movement - erratic
                pose += np.random.randn(17, 3) * 0.1
                pose[7:11] += np.sin(phase * 6) * 0.2
            
            frames.append(pose)
        
        return np.stack(frames, axis=0)  # (T, J, 3)
    
    def __len__(self):
        return self.num_samples
    
    def __getitem__(self, idx):
        skeleton, label = self.samples[idx]
        return torch.FloatTensor(skeleton), label


class SyntheticMotionDataset(Dataset):
    """Generate synthetic optical flow data for MotionStream training"""
    
    def __init__(
        self,
        num_samples: int = 500,
        num_frames: int = 8,
        height: int = 64,
        width: int = 64,
        split: str = 'train'
    ):
        self.num_samples = num_samples
        self.num_frames = num_frames
        self.height = height
        self.width = width
        self.split = split
        
        np.random.seed(42 if split == 'train' else 123)
        self.samples = []
        for _ in range(num_samples):
            label = np.random.randint(0, 2)  # 0=normal, 1=anomaly
            flow = self._generate_flow(label)
            self.samples.append((flow, label))
    
    def _generate_flow(self, label: int) -> np.ndarray:
        """Generate synthetic optical flow patterns"""
        flows = []
        for t in range(self.num_frames):
            if label == 0:  # Normal - smooth, predictable flow
                u = np.random.randn(self.height, self.width) * 0.1
                v = np.random.randn(self.height, self.width) * 0.1
                # Add some structure
                x, y = np.meshgrid(np.linspace(-1, 1, self.width), np.linspace(-1, 1, self.height))
                u += np.sin(x * 2) * 0.2
                v += np.cos(y * 2) * 0.2
            else:  # Anomaly - sudden, chaotic flow
                u = np.random.randn(self.height, self.width) * 0.5
                v = np.random.randn(self.height, self.width) * 0.5
                # Add sudden spike in random region
                cx, cy = np.random.randint(10, self.width-10), np.random.randint(10, self.height-10)
                u[cy-5:cy+5, cx-5:cx+5] += np.random.randn() * 2
                v[cy-5:cy+5, cx-5:cx+5] += np.random.randn() * 2
            
            flow = np.stack([u, v], axis=0)  # (2, H, W)
            flows.append(flow)
        
        return np.stack(flows, axis=0).astype(np.float32)  # (T, 2, H, W)
    
    def __len__(self):
        return self.num_samples
    
    def __getitem__(self, idx):
        flow, label = self.samples[idx]
        # Reshape for MotionStream: (T, C, H, W)
        return torch.FloatTensor(flow), float(label)


class SyntheticEmotionDataset(Dataset):
    """Generate synthetic face-like images for MoodTiny training"""
    
    def __init__(
        self,
        num_samples: int = 1000,
        image_size: int = 112,
        num_classes: int = 6,
        split: str = 'train'
    ):
        self.num_samples = num_samples
        self.image_size = image_size
        self.num_classes = num_classes
        self.split = split
        
        np.random.seed(42 if split == 'train' else 123)
        self.samples = []
        for _ in range(num_samples):
            label = np.random.randint(0, num_classes)
            image = self._generate_face_like_image(label)
            self.samples.append((image, label))
    
    def _generate_face_like_image(self, label: int) -> np.ndarray:
        """Generate synthetic face-like patterns"""
        img = np.random.randn(3, self.image_size, self.image_size) * 0.1
        
        # Create base face shape (ellipse)
        y, x = np.ogrid[:self.image_size, :self.image_size]
        center = self.image_size // 2
        mask = ((x - center)**2 / (self.image_size * 0.4)**2 + 
                (y - center)**2 / (self.image_size * 0.5)**2) < 1
        
        # Base skin tone (normalized)
        img[0, mask] = 0.5 + np.random.rand() * 0.2
        img[1, mask] = 0.4 + np.random.rand() * 0.2
        img[2, mask] = 0.3 + np.random.rand() * 0.2
        
        # Add emotion-specific features
        if label == 0:  # neutral
            pass  # base face
        elif label == 1:  # stress
            img[0] += 0.1  # slightly red
            img += np.random.randn(3, self.image_size, self.image_size) * 0.05
        elif label == 2:  # aggression
            img[0] += 0.2  # more red
            # Add frown lines (darker horizontal regions)
            img[:, 30:35, 40:70] -= 0.2
        elif label == 3:  # sadness
            img[2] += 0.1  # slightly blue
            img[:, 70:80, 40:70] += 0.1  # brighter under-eye
        elif label == 4:  # fear
            img += 0.1  # overall brighter (wide-eyed)
            img[:, 20:40, :] += 0.1  # forehead
        elif label == 5:  # anxiety
            img += np.random.randn(3, self.image_size, self.image_size) * 0.08
            img[0] += 0.05
        
        # Normalize
        img = np.clip(img, 0, 1)
        
        # Apply ImageNet normalization
        mean = np.array([0.485, 0.456, 0.406]).reshape(3, 1, 1)
        std = np.array([0.229, 0.224, 0.225]).reshape(3, 1, 1)
        img = (img - mean) / std
        
        return img.astype(np.float32)
    
    def __len__(self):
        return self.num_samples
    
    def __getitem__(self, idx):
        image, label = self.samples[idx]
        return torch.FloatTensor(image), label


# ============================================================================
# Training Functions
# ============================================================================

def train_skelegnn(args, device):
    """Train SkeleGNN model"""
    print("\n" + "="*60)
    print("Training SkeleGNN - Skeleton Action Recognition")
    print("="*60)
    
    # Create datasets
    train_dataset = SyntheticSkeletonDataset(
        num_samples=args.train_samples,
        num_frames=16,
        num_joints=17,
        num_classes=7,
        split='train'
    )
    val_dataset = SyntheticSkeletonDataset(
        num_samples=args.val_samples,
        num_frames=16,
        num_joints=17,
        num_classes=7,
        split='val'
    )
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    
    # Create model
    model = create_skelegnn(num_classes=7).to(device)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    
    best_acc = 0
    checkpoint_dir = Path(args.checkpoint_dir) / 'skelegnn'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    for epoch in range(1, args.epochs + 1):
        # Train
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        
        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs} [Train]")
        for inputs, targets in pbar:
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = outputs.max(1)
            train_total += targets.size(0)
            train_correct += predicted.eq(targets).sum().item()
            
            pbar.set_postfix({'loss': loss.item(), 'acc': 100.*train_correct/train_total})
        
        scheduler.step()
        
        # Validate
        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for inputs, targets in tqdm(val_loader, desc=f"Epoch {epoch}/{args.epochs} [Val]"):
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                val_loss += loss.item()
                _, predicted = outputs.max(1)
                val_total += targets.size(0)
                val_correct += predicted.eq(targets).sum().item()
        
        train_acc = 100. * train_correct / train_total
        val_acc = 100. * val_correct / val_total
        
        print(f"Epoch {epoch}: Train Acc: {train_acc:.2f}%, Val Acc: {val_acc:.2f}%")
        
        # Save best model
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'accuracy': val_acc,
            }, checkpoint_dir / 'best_model.pth')
            print(f"  ✓ Saved best model (acc: {val_acc:.2f}%)")
    
    print(f"\nSkeleGNN Training Complete! Best Accuracy: {best_acc:.2f}%")
    return model


def train_motionstream(args, device):
    """Train MotionStream model"""
    print("\n" + "="*60)
    print("Training MotionStream - Motion Anomaly Detection")
    print("="*60)
    
    # Create datasets
    train_dataset = SyntheticMotionDataset(
        num_samples=args.train_samples // 2,
        num_frames=8,
        height=64,
        width=64,
        split='train'
    )
    val_dataset = SyntheticMotionDataset(
        num_samples=args.val_samples // 2,
        num_frames=8,
        height=64,
        width=64,
        split='val'
    )
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size // 2, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size // 2, shuffle=False, num_workers=0)
    
    # Create model (lite version for faster training)
    model = create_motionstream(model_type='lite', num_frames=8).to(device)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Loss and optimizer
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr * 0.1, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=5)
    
    best_auc = 0
    checkpoint_dir = Path(args.checkpoint_dir) / 'motionstream'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    for epoch in range(1, args.epochs + 1):
        # Train
        model.train()
        train_loss = 0
        
        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs} [Train]")
        for inputs, targets in pbar:
            inputs = inputs.to(device)
            targets = targets.to(device).float().unsqueeze(1)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            pbar.set_postfix({'loss': loss.item()})
        
        # Validate
        model.eval()
        val_loss = 0
        all_preds = []
        all_targets = []
        
        with torch.no_grad():
            for inputs, targets in tqdm(val_loader, desc=f"Epoch {epoch}/{args.epochs} [Val]"):
                inputs = inputs.to(device)
                targets = targets.to(device).float().unsqueeze(1)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                val_loss += loss.item()
                all_preds.extend(outputs.cpu().numpy().flatten())
                all_targets.extend(targets.cpu().numpy().flatten())
        
        scheduler.step(val_loss)
        
        # Compute AUC
        from sklearn.metrics import roc_auc_score
        try:
            auc = roc_auc_score(all_targets, all_preds)
        except:
            auc = 0.5
        
        print(f"Epoch {epoch}: Train Loss: {train_loss/len(train_loader):.4f}, Val AUC: {auc:.4f}")
        
        # Save best model
        if auc > best_auc:
            best_auc = auc
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'auc': auc,
            }, checkpoint_dir / 'best_model.pth')
            print(f"  ✓ Saved best model (AUC: {auc:.4f})")
    
    print(f"\nMotionStream Training Complete! Best AUC: {best_auc:.4f}")
    return model


def train_moodtiny(args, device):
    """Train MoodTiny model"""
    print("\n" + "="*60)
    print("Training MoodTiny - Emotion Recognition")
    print("="*60)
    
    # Create datasets
    train_dataset = SyntheticEmotionDataset(
        num_samples=args.train_samples,
        image_size=112,
        num_classes=6,
        split='train'
    )
    val_dataset = SyntheticEmotionDataset(
        num_samples=args.val_samples,
        image_size=112,
        num_classes=6,
        split='val'
    )
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    
    # Create model (without pretrained to avoid download issues)
    model = create_moodtiny(model_type='mobilenet', num_classes=6, pretrained=False).to(device)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    
    best_acc = 0
    checkpoint_dir = Path(args.checkpoint_dir) / 'moodtiny'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    for epoch in range(1, args.epochs + 1):
        # Train
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        
        pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs} [Train]")
        for inputs, targets in pbar:
            inputs, targets = inputs.to(device), targets.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = outputs.max(1)
            train_total += targets.size(0)
            train_correct += predicted.eq(targets).sum().item()
            
            pbar.set_postfix({'loss': loss.item(), 'acc': 100.*train_correct/train_total})
        
        scheduler.step()
        
        # Validate
        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for inputs, targets in tqdm(val_loader, desc=f"Epoch {epoch}/{args.epochs} [Val]"):
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                
                val_loss += loss.item()
                _, predicted = outputs.max(1)
                val_total += targets.size(0)
                val_correct += predicted.eq(targets).sum().item()
        
        train_acc = 100. * train_correct / train_total
        val_acc = 100. * val_correct / val_total
        
        print(f"Epoch {epoch}: Train Acc: {train_acc:.2f}%, Val Acc: {val_acc:.2f}%")
        
        # Save best model
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'accuracy': val_acc,
            }, checkpoint_dir / 'best_model.pth')
            print(f"  ✓ Saved best model (acc: {val_acc:.2f}%)")
    
    print(f"\nMoodTiny Training Complete! Best Accuracy: {best_acc:.2f}%")
    return model


def export_to_onnx(args, device):
    """Export all trained models to ONNX format"""
    print("\n" + "="*60)
    print("Exporting Models to ONNX")
    print("="*60)
    
    checkpoint_dir = Path(args.checkpoint_dir)
    onnx_dir = Path(args.onnx_dir)
    onnx_dir.mkdir(parents=True, exist_ok=True)
    
    # Export SkeleGNN
    print("\n[1/3] Exporting SkeleGNN...")
    skelegnn_ckpt = checkpoint_dir / 'skelegnn' / 'best_model.pth'
    if skelegnn_ckpt.exists():
        model = create_skelegnn(num_classes=7).to(device)
        model.load_state_dict(torch.load(skelegnn_ckpt, map_location=device)['model_state_dict'])
        model.eval()
        
        dummy_input = torch.randn(1, 16, 17, 3).to(device)
        onnx_path = onnx_dir / 'skelegnn.onnx'
        
        torch.onnx.export(
            model, dummy_input, str(onnx_path),
            input_names=['skeleton'],
            output_names=['action_logits'],
            dynamic_axes={'skeleton': {0: 'batch_size'}, 'action_logits': {0: 'batch_size'}},
            opset_version=12
        )
        print(f"  ✓ Saved to {onnx_path}")
    else:
        print(f"  ✗ Checkpoint not found: {skelegnn_ckpt}")
    
    # Export MotionStream
    print("\n[2/3] Exporting MotionStream...")
    motionstream_ckpt = checkpoint_dir / 'motionstream' / 'best_model.pth'
    if motionstream_ckpt.exists():
        model = create_motionstream(model_type='lite', num_frames=8).to(device)
        model.load_state_dict(torch.load(motionstream_ckpt, map_location=device)['model_state_dict'])
        model.eval()
        
        dummy_input = torch.randn(1, 8, 2, 64, 64).to(device)
        onnx_path = onnx_dir / 'motionstream.onnx'
        
        torch.onnx.export(
            model, dummy_input, str(onnx_path),
            input_names=['optical_flow'],
            output_names=['anomaly_score'],
            dynamic_axes={'optical_flow': {0: 'batch_size'}, 'anomaly_score': {0: 'batch_size'}},
            opset_version=12
        )
        print(f"  ✓ Saved to {onnx_path}")
    else:
        print(f"  ✗ Checkpoint not found: {motionstream_ckpt}")
    
    # Export MoodTiny
    print("\n[3/3] Exporting MoodTiny...")
    moodtiny_ckpt = checkpoint_dir / 'moodtiny' / 'best_model.pth'
    if moodtiny_ckpt.exists():
        model = create_moodtiny(model_type='mobilenet', num_classes=6, pretrained=False).to(device)
        model.load_state_dict(torch.load(moodtiny_ckpt, map_location=device)['model_state_dict'])
        model.eval()
        
        dummy_input = torch.randn(1, 3, 112, 112).to(device)
        onnx_path = onnx_dir / 'moodtiny.onnx'
        
        torch.onnx.export(
            model, dummy_input, str(onnx_path),
            input_names=['face_image'],
            output_names=['emotion_logits'],
            dynamic_axes={'face_image': {0: 'batch_size'}, 'emotion_logits': {0: 'batch_size'}},
            opset_version=12
        )
        print(f"  ✓ Saved to {onnx_path}")
    else:
        print(f"  ✗ Checkpoint not found: {moodtiny_ckpt}")
    
    print("\n✓ ONNX Export Complete!")


def main():
    parser = argparse.ArgumentParser(description='Train Guardia AI Models')
    parser.add_argument('--model', type=str, default='all', 
                        choices=['all', 'skelegnn', 'motionstream', 'moodtiny', 'export'],
                        help='Which model to train')
    parser.add_argument('--epochs', type=int, default=10, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--train-samples', type=int, default=1000, help='Number of training samples')
    parser.add_argument('--val-samples', type=int, default=200, help='Number of validation samples')
    parser.add_argument('--checkpoint-dir', type=str, default='./checkpoints', help='Checkpoint directory')
    parser.add_argument('--onnx-dir', type=str, default='./onnx_models', help='ONNX output directory')
    parser.add_argument('--device', type=str, default='auto', help='Device (cuda/cpu/auto)')
    
    args = parser.parse_args()
    
    # Set device
    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)
    
    print(f"\n{'='*60}")
    print("Guardia AI - Model Training Pipeline")
    print(f"{'='*60}")
    print(f"Device: {device}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Training Samples: {args.train_samples}")
    print(f"Checkpoint Dir: {args.checkpoint_dir}")
    
    # Create checkpoint directory
    Path(args.checkpoint_dir).mkdir(parents=True, exist_ok=True)
    
    if args.model in ['all', 'skelegnn']:
        train_skelegnn(args, device)
    
    if args.model in ['all', 'motionstream']:
        train_motionstream(args, device)
    
    if args.model in ['all', 'moodtiny']:
        train_moodtiny(args, device)
    
    if args.model in ['all', 'export']:
        export_to_onnx(args, device)
    
    print("\n" + "="*60)
    print("Training Pipeline Complete!")
    print("="*60)
    print(f"\nCheckpoints saved in: {args.checkpoint_dir}")
    print(f"ONNX models saved in: {args.onnx_dir}")


if __name__ == '__main__':
    main()
