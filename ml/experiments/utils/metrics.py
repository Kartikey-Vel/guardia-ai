"""
Evaluation metrics for Guardia AI models
"""

import torch
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support,
    confusion_matrix, roc_auc_score, roc_curve
)
from typing import Dict, Tuple, List
import matplotlib.pyplot as plt
import seaborn as sns


class MetricsTracker:
    """Track and compute metrics during training"""
    
    def __init__(self, num_classes: int, class_names: List[str]):
        self.num_classes = num_classes
        self.class_names = class_names
        self.reset()
    
    def reset(self):
        """Reset all metrics"""
        self.predictions = []
        self.targets = []
        self.losses = []
    
    def update(self, preds: torch.Tensor, targets: torch.Tensor, loss: float = None):
        """Update metrics with batch results"""
        if preds.dim() == 2:  # Logits
            preds = torch.argmax(preds, dim=1)
        
        self.predictions.extend(preds.cpu().numpy())
        self.targets.extend(targets.cpu().numpy())
        
        if loss is not None:
            self.losses.append(loss)
    
    def compute(self) -> Dict[str, float]:
        """Compute all metrics"""
        preds = np.array(self.predictions)
        targets = np.array(self.targets)
        
        # Accuracy
        accuracy = accuracy_score(targets, preds)
        
        # Per-class metrics
        precision, recall, f1, support = precision_recall_fscore_support(
            targets, preds, average=None, zero_division=0
        )
        
        # Macro averages
        precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
            targets, preds, average='macro', zero_division=0
        )
        
        # Average loss
        avg_loss = np.mean(self.losses) if self.losses else 0.0
        
        metrics = {
            'accuracy': accuracy,
            'precision_macro': precision_macro,
            'recall_macro': recall_macro,
            'f1_macro': f1_macro,
            'loss': avg_loss
        }
        
        # Add per-class metrics
        for i, class_name in enumerate(self.class_names):
            metrics[f'precision_{class_name}'] = precision[i]
            metrics[f'recall_{class_name}'] = recall[i]
            metrics[f'f1_{class_name}'] = f1[i]
        
        return metrics
    
    def get_confusion_matrix(self) -> np.ndarray:
        """Compute confusion matrix"""
        return confusion_matrix(self.targets, self.predictions)
    
    def plot_confusion_matrix(self, save_path: str = None):
        """Plot confusion matrix"""
        cm = self.get_confusion_matrix()
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(
            cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=self.class_names,
            yticklabels=self.class_names
        )
        plt.xlabel('Predicted')
        plt.ylabel('True')
        plt.title('Confusion Matrix')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()


class AnomalyMetrics:
    """Metrics for anomaly detection (binary classification)"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset metrics"""
        self.scores = []
        self.targets = []
    
    def update(self, scores: torch.Tensor, targets: torch.Tensor):
        """Update with batch results"""
        self.scores.extend(scores.cpu().numpy())
        self.targets.extend(targets.cpu().numpy())
    
    def compute(self, threshold: float = 0.5) -> Dict[str, float]:
        """Compute anomaly detection metrics"""
        scores = np.array(self.scores)
        targets = np.array(self.targets)
        
        # Binary predictions
        preds = (scores > threshold).astype(int)
        
        # Accuracy
        accuracy = accuracy_score(targets, preds)
        
        # Precision, Recall, F1
        precision, recall, f1, _ = precision_recall_fscore_support(
            targets, preds, average='binary', zero_division=0
        )
        
        # AUC-ROC
        try:
            auc = roc_auc_score(targets, scores)
        except:
            auc = 0.0
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'auc': auc,
            'threshold': threshold
        }
    
    def find_optimal_threshold(self) -> Tuple[float, Dict[str, float]]:
        """Find threshold that maximizes F1 score"""
        scores = np.array(self.scores)
        targets = np.array(self.targets)
        
        fpr, tpr, thresholds = roc_curve(targets, scores)
        
        # Compute F1 for each threshold
        best_f1 = 0
        best_threshold = 0.5
        
        for threshold in thresholds:
            preds = (scores > threshold).astype(int)
            _, _, f1, _ = precision_recall_fscore_support(
                targets, preds, average='binary', zero_division=0
            )
            
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = threshold
        
        # Compute metrics at best threshold
        metrics = self.compute(threshold=best_threshold)
        
        return best_threshold, metrics
    
    def plot_roc_curve(self, save_path: str = None):
        """Plot ROC curve"""
        scores = np.array(self.scores)
        targets = np.array(self.targets)
        
        fpr, tpr, _ = roc_curve(targets, scores)
        auc = roc_auc_score(targets, scores)
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, label=f'ROC Curve (AUC = {auc:.3f})')
        plt.plot([0, 1], [0, 1], 'k--', label='Random')
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve - Anomaly Detection')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()


def compute_inference_speed(
    model: torch.nn.Module,
    input_shape: Tuple,
    device: str = 'cuda',
    num_iterations: int = 1000,
    warmup: int = 100
) -> Dict[str, float]:
    """Benchmark model inference speed"""
    import time
    
    model = model.to(device)
    model.eval()
    
    # Create dummy input
    dummy_input = torch.randn(*input_shape).to(device)
    
    # Warmup
    with torch.no_grad():
        for _ in range(warmup):
            _ = model(dummy_input)
    
    # Benchmark
    if device == 'cuda':
        torch.cuda.synchronize()
    
    start_time = time.time()
    
    with torch.no_grad():
        for _ in range(num_iterations):
            _ = model(dummy_input)
    
    if device == 'cuda':
        torch.cuda.synchronize()
    
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time = total_time / num_iterations
    fps = 1.0 / avg_time
    
    return {
        'avg_inference_ms': avg_time * 1000,
        'fps': fps,
        'total_time_s': total_time
    }


def count_parameters(model: torch.nn.Module) -> Dict[str, int]:
    """Count model parameters"""
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    return {
        'total_params': total_params,
        'trainable_params': trainable_params,
        'non_trainable_params': total_params - trainable_params
    }


def plot_training_curves(
    train_losses: List[float],
    val_losses: List[float],
    train_accs: List[float],
    val_accs: List[float],
    save_path: str = None
):
    """Plot training and validation curves"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Loss
    ax1.plot(train_losses, label='Train Loss')
    ax1.plot(val_losses, label='Val Loss')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title('Training and Validation Loss')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Accuracy
    ax2.plot(train_accs, label='Train Accuracy')
    ax2.plot(val_accs, label='Val Accuracy')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy')
    ax2.set_title('Training and Validation Accuracy')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
