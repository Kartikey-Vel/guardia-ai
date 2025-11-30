#!/usr/bin/env python3
"""
Quick Training Script for All Models

Trains SkeleGNN, MotionStream, and MoodTiny models on dummy datasets.
For quick testing - use Jupyter notebooks for full training with visualization.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import torch
import torch.nn as nn
import yaml
from tqdm import tqdm

from models.skelegnn import create_skelegnn
from models.motionstream import create_motionstream_lite
from models.moodtiny import create_moodtiny
from utils.datasets import SkeletonActionDataset, MotionAnomalyDataset, EmotionDataset, create_dataloaders
from utils.metrics import MetricsTracker, AnomalyMetrics
from utils.training import Trainer, create_optimizer, create_scheduler
from utils.export import export_to_onnx, validate_onnx_model


def train_skelegnn():
    """Train SkeleGNN model."""
    print("\n" + "="*80)
    print("Training SkeleGNN (Skeleton Action Recognition)")
    print("="*80)
    
    # Load config
    with open('../configs/skelegnn.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Override for quick training
    config['training']['num_epochs'] = 5
    config['wandb']['enabled'] = False
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")
    
    # Create datasets
    print("Loading datasets...")
    train_dataset = SkeletonActionDataset(
        root=config['dataset']['root'],
        split='train',
        num_frames=config['model']['num_frames'],
        num_joints=config['model']['num_joints'],
        actions=config['classes']
    )
    
    val_dataset = SkeletonActionDataset(
        root=config['dataset']['root'],
        split='val',
        num_frames=config['model']['num_frames'],
        num_joints=config['model']['num_joints'],
        actions=config['classes']
    )
    
    print(f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")
    
    train_loader = create_dataloaders(train_dataset, batch_size=8, num_workers=0, split='train')
    val_loader = create_dataloaders(val_dataset, batch_size=8, num_workers=0, split='val')
    
    # Create model
    print("Creating model...")
    model = create_skelegnn(num_classes=config['model']['num_classes'], pretrained=False)
    model = model.to(device)
    
    # Setup training
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = create_optimizer(model, 'adam', lr=0.001, weight_decay=1e-4)
    scheduler = create_scheduler(optimizer, 'cosine', num_epochs=config['training']['num_epochs'])
    metrics_tracker = MetricsTracker(num_classes=config['model']['num_classes'], class_names=config['classes'])
    
    # Train
    print("Training...")
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        use_wandb=False
    )
    
    trainer.fit(
        num_epochs=config['training']['num_epochs'],
        metric_fn=metrics_tracker,
        save_best=True,
        checkpoint_dir=config['checkpoints']['save_dir']
    )
    
    # Export to ONNX
    print("Exporting to ONNX...")
    onnx_dir = Path('../../services/models/skelegnn/weights')
    onnx_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = str(onnx_dir / 'skelegnn.onnx')
    
    export_to_onnx(
        model=model,
        input_shape=(1, 16, 17, 3),
        output_path=onnx_path,
        opset_version=14
    )
    
    print(f"✓ SkeleGNN training complete! Model saved to {onnx_path}")
    return trainer.val_metrics[-1] if trainer.val_metrics else {}


def train_motionstream():
    """Train MotionStream model."""
    print("\n" + "="*80)
    print("Training MotionStream (Motion Anomaly Detection)")
    print("="*80)
    
    # Load config
    with open('../configs/motionstream.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Override for quick training
    config['training']['num_epochs'] = 5
    config['wandb']['enabled'] = False
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")
    
    # Create datasets
    print("Loading datasets...")
    train_dataset = MotionAnomalyDataset(
        root=config['dataset']['root'],
        split='train',
        num_frames=config['model']['num_frames'],
        frame_size=config['model']['frame_size'],
        compute_flow=True
    )
    
    val_dataset = MotionAnomalyDataset(
        root=config['dataset']['root'],
        split='val',
        num_frames=config['model']['num_frames'],
        frame_size=config['model']['frame_size'],
        compute_flow=True
    )
    
    print(f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")
    
    train_loader = create_dataloaders(train_dataset, batch_size=4, num_workers=0, split='train')
    val_loader = create_dataloaders(val_dataset, batch_size=4, num_workers=0, split='val')
    
    # Create model
    print("Creating model...")
    model = create_motionstream_lite(pretrained=False)
    model = model.to(device)
    
    # Setup training
    pos_weight = torch.tensor([3.0]).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = create_optimizer(model, 'adam', lr=0.0001, weight_decay=1e-4)
    scheduler = create_scheduler(optimizer, 'plateau', num_epochs=config['training']['num_epochs'])
    metrics_tracker = AnomalyMetrics()
    
    # Train
    print("Training...")
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        use_wandb=False
    )
    
    trainer.fit(
        num_epochs=config['training']['num_epochs'],
        metric_fn=metrics_tracker,
        save_best=True,
        checkpoint_dir=config['checkpoints']['save_dir']
    )
    
    # Export to ONNX
    print("Exporting to ONNX...")
    onnx_dir = Path('../../services/models/motionstream/weights')
    onnx_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = str(onnx_dir / 'motionstream_lite.onnx')
    
    export_to_onnx(
        model=model,
        input_shape=(1, 8, 2, 224, 224),
        output_path=onnx_path,
        opset_version=14
    )
    
    print(f"✓ MotionStream training complete! Model saved to {onnx_path}")
    return trainer.val_metrics[-1] if trainer.val_metrics else {}


def train_moodtiny():
    """Train MoodTiny model."""
    print("\n" + "="*80)
    print("Training MoodTiny (Emotion Recognition)")
    print("="*80)
    
    # Load config
    with open('../configs/moodtiny.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Override for quick training
    config['training']['num_epochs'] = 5
    config['wandb']['enabled'] = False
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")
    
    # Create datasets
    print("Loading datasets...")
    train_dataset = EmotionDataset(
        root=config['dataset']['root'],
        split='train',
        img_size=config['model']['img_size'],
        emotions=config['classes'],
        blur_background=False  # Disable for speed
    )
    
    val_dataset = EmotionDataset(
        root=config['dataset']['root'],
        split='test',  # FER2013 uses 'test' instead of 'val'
        img_size=config['model']['img_size'],
        emotions=config['classes'],
        blur_background=False
    )
    
    print(f"Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")
    
    train_loader = create_dataloaders(train_dataset, batch_size=16, num_workers=0, split='train')
    val_loader = create_dataloaders(val_dataset, batch_size=16, num_workers=0, split='val')
    
    # Create model
    print("Creating model...")
    model = create_moodtiny(num_classes=config['model']['num_classes'], pretrained=True)
    model = model.to(device)
    
    # Setup training
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = create_optimizer(model, 'adamw', lr=0.001, weight_decay=0.01)
    scheduler = create_scheduler(optimizer, 'cosine', num_epochs=config['training']['num_epochs'])
    metrics_tracker = MetricsTracker(num_classes=config['model']['num_classes'], class_names=config['classes'])
    
    # Train
    print("Training...")
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        criterion=criterion,
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        use_wandb=False
    )
    
    trainer.fit(
        num_epochs=config['training']['num_epochs'],
        metric_fn=metrics_tracker,
        save_best=True,
        checkpoint_dir=config['checkpoints']['save_dir']
    )
    
    # Export to ONNX
    print("Exporting to ONNX...")
    onnx_dir = Path('../../services/models/moodtiny/weights')
    onnx_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = str(onnx_dir / 'moodtiny_mobilenet.onnx')
    
    export_to_onnx(
        model=model,
        input_shape=(1, 3, 112, 112),
        output_path=onnx_path,
        opset_version=14
    )
    
    print(f"✓ MoodTiny training complete! Model saved to {onnx_path}")
    return trainer.val_metrics[-1] if trainer.val_metrics else {}


def main():
    """Train all models sequentially."""
    print("\n" + "="*80)
    print("GUARDIA AI - TRAIN ALL MODELS")
    print("="*80)
    print("\nThis script trains all three models with dummy datasets.")
    print("For full training with real datasets, use Jupyter notebooks.")
    print("\nModels to train:")
    print("  1. SkeleGNN - Skeleton Action Recognition")
    print("  2. MotionStream - Motion Anomaly Detection")
    print("  3. MoodTiny - Emotion Recognition")
    print("\nEach model will train for 5 epochs (quick test).")
    
    results = {}
    
    try:
        # Train SkeleGNN
        skelegnn_results = train_skelegnn()
        results['skelegnn'] = skelegnn_results
        
        # Train MotionStream
        motionstream_results = train_motionstream()
        results['motionstream'] = motionstream_results
        
        # Train MoodTiny
        moodtiny_results = train_moodtiny()
        results['moodtiny'] = moodtiny_results
        
        # Summary
        print("\n" + "="*80)
        print("TRAINING COMPLETE - SUMMARY")
        print("="*80)
        
        print("\nSkeleGNN Results:")
        print(f"  Accuracy: {skelegnn_results.get('accuracy', 0):.4f}")
        print(f"  F1-Score: {skelegnn_results.get('f1_macro', 0):.4f}")
        
        print("\nMotionStream Results:")
        print(f"  AUC-ROC: {motionstream_results.get('auc_roc', 0):.4f}")
        print(f"  Accuracy: {motionstream_results.get('accuracy', 0):.4f}")
        
        print("\nMoodTiny Results:")
        print(f"  Accuracy: {moodtiny_results.get('accuracy', 0):.4f}")
        print(f"  F1-Score: {moodtiny_results.get('f1_macro', 0):.4f}")
        
        print("\n" + "="*80)
        print("Next Steps:")
        print("="*80)
        print("1. Deploy models: python scripts/deploy_models.py --model all")
        print("2. Restart services: docker-compose restart skelegnn motionstream moodtiny")
        print("3. Test inference: docker-compose logs -f skelegnn")
        print("\nFor production training:")
        print("  - Download real datasets (see ml/datasets/README.md)")
        print("  - Use Jupyter notebooks for full training with visualization")
        print("  - Train for full epochs (60-100) with real data")
        
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")
    except Exception as e:
        print(f"\n\nError during training: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
