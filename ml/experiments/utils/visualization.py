"""
Visualization utilities for training monitoring
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import torch
from typing import List, Dict, Optional
import cv2

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


def plot_training_curves(
    history: Dict[str, List[float]],
    save_path: str = None
):
    """
    Plot training and validation curves
    
    Args:
        history: Dictionary with 'train_loss', 'val_loss', 'train_acc', 'val_acc' lists
        save_path: Path to save plot
    """
    epochs = range(1, len(history['train_loss']) + 1)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Loss curves
    ax1.plot(epochs, history['train_loss'], 'b-', label='Train Loss', linewidth=2)
    ax1.plot(epochs, history['val_loss'], 'r-', label='Val Loss', linewidth=2)
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title('Training and Validation Loss')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Accuracy curves
    ax2.plot(epochs, history['train_acc'], 'b-', label='Train Acc', linewidth=2)
    ax2.plot(epochs, history['val_acc'], 'r-', label='Val Acc', linewidth=2)
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy (%)')
    ax2.set_title('Training and Validation Accuracy')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        plt.show()


def visualize_skeleton(
    skeleton: np.ndarray,
    connections: List[tuple] = None,
    save_path: str = None
):
    """
    Visualize skeleton keypoints
    
    Args:
        skeleton: Skeleton keypoints (J, 3) where J=joints, 3=coordinates
        connections: List of joint pairs to connect
        save_path: Path to save visualization
    """
    if connections is None:
        # COCO 17 keypoints connections
        connections = [
            (0, 1), (0, 2), (1, 3), (2, 4),  # Head
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
            (5, 11), (6, 12), (11, 12),  # Torso
            (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
        ]
    
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot joints
    ax.scatter(skeleton[:, 0], skeleton[:, 1], skeleton[:, 2], 
               c='red', s=50, marker='o')
    
    # Plot connections
    for start, end in connections:
        if start < len(skeleton) and end < len(skeleton):
            points = np.array([skeleton[start], skeleton[end]])
            ax.plot(points[:, 0], points[:, 1], points[:, 2], 
                   'b-', linewidth=2)
    
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Skeleton Visualization')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def visualize_optical_flow(
    flow: np.ndarray,
    save_path: str = None
):
    """
    Visualize optical flow as HSV color image
    
    Args:
        flow: Optical flow (H, W, 2)
        save_path: Path to save visualization
    """
    h, w = flow.shape[:2]
    
    # Convert to polar coordinates
    magnitude, angle = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    
    # Create HSV image
    hsv = np.zeros((h, w, 3), dtype=np.uint8)
    hsv[..., 0] = angle * 180 / np.pi / 2  # Hue = direction
    hsv[..., 1] = 255  # Saturation = full
    hsv[..., 2] = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)  # Value = magnitude
    
    # Convert to RGB
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    
    plt.figure(figsize=(10, 8))
    plt.imshow(rgb)
    plt.title('Optical Flow Visualization')
    plt.axis('off')
    
    # Add colorbar for magnitude
    plt.colorbar(plt.cm.ScalarMappable(cmap='jet'), label='Flow Magnitude')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_class_distribution(
    labels: np.ndarray,
    class_names: List[str],
    save_path: str = None
):
    """
    Plot class distribution in dataset
    
    Args:
        labels: Array of class labels
        class_names: List of class names
        save_path: Path to save plot
    """
    unique, counts = np.unique(labels, return_counts=True)
    
    plt.figure(figsize=(10, 6))
    plt.bar(range(len(unique)), counts, color='steelblue')
    plt.xticks(range(len(unique)), [class_names[i] for i in unique], rotation=45, ha='right')
    plt.xlabel('Class')
    plt.ylabel('Number of Samples')
    plt.title('Class Distribution')
    plt.grid(axis='y', alpha=0.3)
    
    # Add count labels on bars
    for i, (idx, count) in enumerate(zip(unique, counts)):
        plt.text(i, count + max(counts) * 0.01, str(count), 
                ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def visualize_predictions(
    images: torch.Tensor,
    predictions: torch.Tensor,
    targets: torch.Tensor,
    class_names: List[str],
    num_samples: int = 8,
    save_path: str = None
):
    """
    Visualize model predictions on sample images
    
    Args:
        images: Batch of images (B, C, H, W)
        predictions: Predicted class indices (B,)
        targets: Ground truth class indices (B,)
        class_names: List of class names
        num_samples: Number of samples to display
        save_path: Path to save visualization
    """
    num_samples = min(num_samples, len(images))
    
    fig, axes = plt.subplots(2, num_samples // 2, figsize=(15, 6))
    axes = axes.flatten()
    
    for i in range(num_samples):
        # Convert tensor to numpy
        img = images[i].permute(1, 2, 0).cpu().numpy()
        
        # Denormalize (assuming ImageNet normalization)
        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        img = img * std + mean
        img = np.clip(img, 0, 1)
        
        # Display
        axes[i].imshow(img)
        
        pred_label = class_names[predictions[i]]
        true_label = class_names[targets[i]]
        color = 'green' if predictions[i] == targets[i] else 'red'
        
        axes[i].set_title(f'Pred: {pred_label}\nTrue: {true_label}', 
                         color=color, fontsize=9)
        axes[i].axis('off')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_feature_maps(
    feature_maps: torch.Tensor,
    num_maps: int = 16,
    save_path: str = None
):
    """
    Visualize feature maps from a convolutional layer
    
    Args:
        feature_maps: Feature maps (1, C, H, W)
        num_maps: Number of feature maps to display
        save_path: Path to save visualization
    """
    feature_maps = feature_maps[0].cpu()  # Remove batch dimension
    num_maps = min(num_maps, feature_maps.shape[0])
    
    fig, axes = plt.subplots(4, num_maps // 4, figsize=(15, 8))
    axes = axes.flatten()
    
    for i in range(num_maps):
        fmap = feature_maps[i].numpy()
        axes[i].imshow(fmap, cmap='viridis')
        axes[i].set_title(f'Map {i}', fontsize=8)
        axes[i].axis('off')
    
    plt.suptitle('Feature Maps Visualization', fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_attention_weights(
    attention_weights: torch.Tensor,
    save_path: str = None
):
    """
    Visualize attention weights as heatmap
    
    Args:
        attention_weights: Attention matrix (seq_len, seq_len)
        save_path: Path to save visualization
    """
    weights = attention_weights.cpu().numpy()
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(weights, cmap='YlOrRd', square=True, cbar_kws={'label': 'Attention Weight'})
    plt.xlabel('Key Position')
    plt.ylabel('Query Position')
    plt.title('Attention Weights Heatmap')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_learning_rate_schedule(
    learning_rates: List[float],
    save_path: str = None
):
    """
    Plot learning rate schedule
    
    Args:
        learning_rates: List of learning rates per epoch/step
        save_path: Path to save plot
    """
    plt.figure(figsize=(10, 6))
    plt.plot(learning_rates, linewidth=2, color='steelblue')
    plt.xlabel('Epoch / Step')
    plt.ylabel('Learning Rate')
    plt.title('Learning Rate Schedule')
    plt.grid(True, alpha=0.3)
    plt.yscale('log')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()


def plot_gradient_flow(
    named_parameters: Dict,
    save_path: str = None
):
    """
    Plot gradient flow through the network
    
    Args:
        named_parameters: Model's named parameters
        save_path: Path to save plot
    """
    ave_grads = []
    max_grads = []
    layers = []
    
    for n, p in named_parameters:
        if p.requires_grad and p.grad is not None:
            layers.append(n)
            ave_grads.append(p.grad.abs().mean().cpu().item())
            max_grads.append(p.grad.abs().max().cpu().item())
    
    plt.figure(figsize=(12, 6))
    plt.bar(np.arange(len(max_grads)), max_grads, alpha=0.5, lw=1, color='c', label='Max')
    plt.bar(np.arange(len(ave_grads)), ave_grads, alpha=0.5, lw=1, color='b', label='Mean')
    plt.hlines(0, 0, len(ave_grads) + 1, lw=2, color='k')
    plt.xticks(range(0, len(ave_grads), 1), layers, rotation=90, fontsize=6)
    plt.xlim(left=0, right=len(ave_grads))
    plt.ylim(bottom=-0.001, top=max(max_grads) * 1.1)
    plt.xlabel('Layers')
    plt.ylabel('Gradient')
    plt.title('Gradient Flow')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
