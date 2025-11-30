"""
Training utilities - common functions for model training
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from typing import Dict, Optional, Callable
import time
from tqdm import tqdm
import wandb


class Trainer:
    """Generic trainer for PyTorch models"""
    
    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        criterion: nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: Optional[torch.optim.lr_scheduler._LRScheduler] = None,
        device: str = 'cuda',
        use_wandb: bool = False
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.criterion = criterion
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.device = device
        self.use_wandb = use_wandb
        
        self.train_losses = []
        self.val_losses = []
        self.train_metrics = []
        self.val_metrics = []
    
    def train_epoch(self, epoch: int, metric_fn: Optional[Callable] = None) -> Dict:
        """Train for one epoch"""
        self.model.train()
        
        total_loss = 0
        num_batches = 0
        
        if metric_fn:
            metric_fn.reset()
        
        pbar = tqdm(self.train_loader, desc=f"Epoch {epoch} [Train]")
        
        for batch_idx, (inputs, targets) in enumerate(pbar):
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(inputs)
            loss = self.criterion(outputs, targets)
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            # Update metrics
            total_loss += loss.item()
            num_batches += 1
            
            if metric_fn:
                metric_fn.update(outputs, targets, loss.item())
            
            # Update progress bar
            pbar.set_postfix({'loss': loss.item()})
        
        avg_loss = total_loss / num_batches
        
        results = {'loss': avg_loss}
        if metric_fn:
            metrics = metric_fn.compute()
            results.update(metrics)
        
        return results
    
    @torch.no_grad()
    def validate(self, metric_fn: Optional[Callable] = None) -> Dict:
        """Validate model"""
        self.model.eval()
        
        total_loss = 0
        num_batches = 0
        
        if metric_fn:
            metric_fn.reset()
        
        pbar = tqdm(self.val_loader, desc="Validation")
        
        for inputs, targets in pbar:
            inputs = inputs.to(self.device)
            targets = targets.to(self.device)
            
            # Forward pass
            outputs = self.model(inputs)
            loss = self.criterion(outputs, targets)
            
            # Update metrics
            total_loss += loss.item()
            num_batches += 1
            
            if metric_fn:
                metric_fn.update(outputs, targets, loss.item())
            
            pbar.set_postfix({'loss': loss.item()})
        
        avg_loss = total_loss / num_batches
        
        results = {'loss': avg_loss}
        if metric_fn:
            metrics = metric_fn.compute()
            results.update(metrics)
        
        return results
    
    def fit(
        self,
        num_epochs: int,
        metric_fn: Optional[Callable] = None,
        save_best: bool = True,
        checkpoint_dir: str = './checkpoints'
    ):
        """Train model for multiple epochs"""
        import os
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        best_val_loss = float('inf')
        
        for epoch in range(1, num_epochs + 1):
            print(f"\n{'='*60}")
            print(f"Epoch {epoch}/{num_epochs}")
            print(f"{'='*60}")
            
            # Train
            train_results = self.train_epoch(epoch, metric_fn)
            self.train_losses.append(train_results['loss'])
            self.train_metrics.append(train_results)
            
            print(f"Train Loss: {train_results['loss']:.4f}")
            if 'accuracy' in train_results:
                print(f"Train Accuracy: {train_results['accuracy']:.4f}")
            
            # Validate
            val_results = self.validate(metric_fn)
            self.val_losses.append(val_results['loss'])
            self.val_metrics.append(val_results)
            
            print(f"Val Loss: {val_results['loss']:.4f}")
            if 'accuracy' in val_results:
                print(f"Val Accuracy: {val_results['accuracy']:.4f}")
            
            # Learning rate scheduling
            if self.scheduler:
                if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                    self.scheduler.step(val_results['loss'])
                else:
                    self.scheduler.step()
                
                current_lr = self.optimizer.param_groups[0]['lr']
                print(f"Learning Rate: {current_lr:.6f}")
            
            # Log to wandb
            if self.use_wandb:
                log_dict = {
                    'epoch': epoch,
                    'train/loss': train_results['loss'],
                    'val/loss': val_results['loss']
                }
                
                if 'accuracy' in train_results:
                    log_dict['train/accuracy'] = train_results['accuracy']
                    log_dict['val/accuracy'] = val_results['accuracy']
                
                wandb.log(log_dict)
            
            # Save best model
            if save_best and val_results['loss'] < best_val_loss:
                best_val_loss = val_results['loss']
                checkpoint_path = os.path.join(checkpoint_dir, 'best_model.pth')
                
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'train_loss': train_results['loss'],
                    'val_loss': val_results['loss'],
                }, checkpoint_path)
                
                print(f"✓ Saved best model (val_loss: {best_val_loss:.4f})")
            
            # Save checkpoint every 10 epochs
            if epoch % 10 == 0:
                checkpoint_path = os.path.join(checkpoint_dir, f'checkpoint_epoch_{epoch}.pth')
                torch.save({
                    'epoch': epoch,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                }, checkpoint_path)
        
        print(f"\n{'='*60}")
        print("Training Complete!")
        print(f"Best Val Loss: {best_val_loss:.4f}")
        print(f"{'='*60}\n")


def create_optimizer(
    model: nn.Module,
    optimizer_type: str = 'adam',
    lr: float = 0.001,
    weight_decay: float = 1e-4
) -> torch.optim.Optimizer:
    """Create optimizer"""
    if optimizer_type == 'adam':
        return torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    elif optimizer_type == 'adamw':
        return torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    elif optimizer_type == 'sgd':
        return torch.optim.SGD(model.parameters(), lr=lr, momentum=0.9, weight_decay=weight_decay)
    else:
        raise ValueError(f"Unknown optimizer: {optimizer_type}")


def create_scheduler(
    optimizer: torch.optim.Optimizer,
    scheduler_type: str = 'cosine',
    num_epochs: int = 100
) -> torch.optim.lr_scheduler._LRScheduler:
    """Create learning rate scheduler"""
    if scheduler_type == 'cosine':
        return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)
    elif scheduler_type == 'step':
        return torch.optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.1)
    elif scheduler_type == 'plateau':
        return torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=10)
    else:
        raise ValueError(f"Unknown scheduler: {scheduler_type}")


def save_checkpoint(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    metrics: Dict,
    filepath: str
):
    """Save training checkpoint"""
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'metrics': metrics
    }, filepath)


def load_checkpoint(
    filepath: str,
    model: nn.Module,
    optimizer: Optional[torch.optim.Optimizer] = None
) -> Dict:
    """Load training checkpoint"""
    checkpoint = torch.load(filepath)
    
    model.load_state_dict(checkpoint['model_state_dict'])
    
    if optimizer and 'optimizer_state_dict' in checkpoint:
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    
    return checkpoint
