"""
Machine Learning utilities and model management for Guardia AI Enhanced System

This module provides ML/AI utilities including:
- Model loading and management
- Training data preprocessing
- Model evaluation and metrics
- Custom model implementations
"""

import os
import pickle
import json
import logging
from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime
from pathlib import Path
import numpy as np

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

try:
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

class ModelManager:
    """Model management and versioning system"""
    
    def __init__(self, models_directory: str = "models"):
        self.models_directory = Path(models_directory)
        self.models_directory.mkdir(parents=True, exist_ok=True)
        self.loaded_models: Dict[str, Any] = {}
        self.model_metadata: Dict[str, Dict] = {}
    
    def save_model(self, model: Any, model_name: str, version: str = "latest", 
                   metadata: Optional[Dict] = None) -> str:
        """
        Save model with versioning support
        
        Args:
            model: Model object to save
            model_name: Name of the model
            version: Version identifier
            metadata: Optional model metadata
            
        Returns:
            str: Path to saved model
        """
        try:
            # Create model directory
            model_dir = self.models_directory / model_name / version
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Save model based on type
            if TORCH_AVAILABLE and isinstance(model, (nn.Module, torch.jit.ScriptModule)):
                model_path = model_dir / "model.pth"
                torch.save(model.state_dict(), model_path)
                model_type = "pytorch"
                
            elif TF_AVAILABLE and isinstance(model, (tf.keras.Model, keras.Model)):
                model_path = model_dir / "model.h5"
                model.save(model_path)
                model_type = "tensorflow"
                
            elif SKLEARN_AVAILABLE and hasattr(model, 'fit'):
                model_path = model_dir / "model.pkl"
                if JOBLIB_AVAILABLE:
                    joblib.dump(model, model_path)
                else:
                    with open(model_path, 'wb') as f:
                        pickle.dump(model, f)
                model_type = "sklearn"
                
            else:
                # Generic pickle save
                model_path = model_dir / "model.pkl"
                with open(model_path, 'wb') as f:
                    pickle.dump(model, f)
                model_type = "generic"
            
            # Save metadata
            if metadata is None:
                metadata = {}
            
            metadata.update({
                "model_name": model_name,
                "version": version,
                "model_type": model_type,
                "saved_at": datetime.utcnow().isoformat(),
                "file_path": str(model_path)
            })
            
            metadata_path = model_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved model {model_name} v{version} at {model_path}")
            return str(model_path)
            
        except Exception as e:
            logger.error(f"Failed to save model {model_name}: {str(e)}")
            raise
    
    def load_model(self, model_name: str, version: str = "latest") -> Tuple[Any, Dict]:
        """
        Load model with metadata
        
        Args:
            model_name: Name of the model
            version: Version to load
            
        Returns:
            tuple: (model, metadata)
        """
        try:
            # Check if already loaded
            cache_key = f"{model_name}:{version}"
            if cache_key in self.loaded_models:
                return self.loaded_models[cache_key], self.model_metadata[cache_key]
            
            # Find model directory
            model_dir = self.models_directory / model_name / version
            if not model_dir.exists():
                raise FileNotFoundError(f"Model {model_name} v{version} not found")
            
            # Load metadata
            metadata_path = model_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {"model_type": "unknown"}
            
            # Load model based on type
            model_type = metadata.get("model_type", "unknown")
            
            if model_type == "pytorch" and TORCH_AVAILABLE:
                model_path = model_dir / "model.pth"
                # Note: This requires the model architecture to be defined elsewhere
                # In practice, you'd save the architecture definition too
                state_dict = torch.load(model_path, map_location='cpu')
                model = state_dict  # Return state dict for now
                
            elif model_type == "tensorflow" and TF_AVAILABLE:
                model_path = model_dir / "model.h5"
                model = tf.keras.models.load_model(model_path)
                
            elif model_type == "sklearn" and SKLEARN_AVAILABLE:
                model_path = model_dir / "model.pkl"
                if JOBLIB_AVAILABLE:
                    model = joblib.load(model_path)
                else:
                    with open(model_path, 'rb') as f:
                        model = pickle.load(f)
                        
            else:
                # Try generic pickle load
                model_path = model_dir / "model.pkl"
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
            
            # Cache loaded model
            self.loaded_models[cache_key] = model
            self.model_metadata[cache_key] = metadata
            
            logger.info(f"Loaded model {model_name} v{version}")
            return model, metadata
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all available models with metadata
        
        Returns:
            list: List of model information
        """
        models = []
        
        try:
            for model_dir in self.models_directory.iterdir():
                if model_dir.is_dir():
                    model_name = model_dir.name
                    
                    for version_dir in model_dir.iterdir():
                        if version_dir.is_dir():
                            version = version_dir.name
                            metadata_path = version_dir / "metadata.json"
                            
                            if metadata_path.exists():
                                with open(metadata_path, 'r') as f:
                                    metadata = json.load(f)
                                models.append(metadata)
                            else:
                                models.append({
                                    "model_name": model_name,
                                    "version": version,
                                    "model_type": "unknown"
                                })
            
            return models
            
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            return []
    
    def delete_model(self, model_name: str, version: str = None) -> bool:
        """
        Delete model version or entire model
        
        Args:
            model_name: Name of the model
            version: Specific version to delete (if None, deletes all versions)
            
        Returns:
            bool: Success status
        """
        try:
            if version:
                # Delete specific version
                version_dir = self.models_directory / model_name / version
                if version_dir.exists():
                    import shutil
                    shutil.rmtree(version_dir)
                    
                    # Remove from cache
                    cache_key = f"{model_name}:{version}"
                    if cache_key in self.loaded_models:
                        del self.loaded_models[cache_key]
                        del self.model_metadata[cache_key]
                    
                    logger.info(f"Deleted model {model_name} v{version}")
                    return True
            else:
                # Delete all versions
                model_dir = self.models_directory / model_name
                if model_dir.exists():
                    import shutil
                    shutil.rmtree(model_dir)
                    
                    # Remove from cache
                    cache_keys = [k for k in self.loaded_models.keys() if k.startswith(f"{model_name}:")]
                    for key in cache_keys:
                        del self.loaded_models[key]
                        del self.model_metadata[key]
                    
                    logger.info(f"Deleted all versions of model {model_name}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete model {model_name}: {str(e)}")
            return False

class DataPreprocessor:
    """Data preprocessing utilities for ML training"""
    
    @staticmethod
    def normalize_images(images: np.ndarray, method: str = "minmax") -> np.ndarray:
        """
        Normalize image data
        
        Args:
            images: Array of images
            method: Normalization method ('minmax', 'zscore')
            
        Returns:
            np.ndarray: Normalized images
        """
        try:
            if method == "minmax":
                return images.astype(np.float32) / 255.0
            elif method == "zscore":
                mean = np.mean(images)
                std = np.std(images)
                return (images.astype(np.float32) - mean) / std
            else:
                raise ValueError(f"Unknown normalization method: {method}")
                
        except Exception as e:
            logger.error(f"Failed to normalize images: {str(e)}")
            raise
    
    @staticmethod
    def augment_images(images: np.ndarray, labels: np.ndarray = None, 
                      rotation_range: float = 20, width_shift_range: float = 0.1,
                      height_shift_range: float = 0.1, horizontal_flip: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply data augmentation to images
        
        Args:
            images: Array of images
            labels: Array of labels (optional)
            rotation_range: Rotation range in degrees
            width_shift_range: Width shift range
            height_shift_range: Height shift range
            horizontal_flip: Whether to apply horizontal flip
            
        Returns:
            tuple: (augmented_images, augmented_labels)
        """
        # Placeholder implementation - would use actual augmentation library
        logger.info("Data augmentation applied (placeholder implementation)")
        return images, labels if labels is not None else None
    
    @staticmethod
    def create_training_splits(X: np.ndarray, y: np.ndarray, 
                             test_size: float = 0.2, val_size: float = 0.1,
                             random_state: int = 42) -> Tuple[np.ndarray, ...]:
        """
        Create train/validation/test splits
        
        Args:
            X: Features
            y: Labels
            test_size: Test set proportion
            val_size: Validation set proportion
            random_state: Random seed
            
        Returns:
            tuple: (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available for data splitting")
            return X, None, None, y, None, None
        
        try:
            # Split into train+val and test
            X_temp, X_test, y_temp, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state, stratify=y
            )
            
            # Split train+val into train and val
            val_size_adjusted = val_size / (1 - test_size)
            X_train, X_val, y_train, y_val = train_test_split(
                X_temp, y_temp, test_size=val_size_adjusted, 
                random_state=random_state, stratify=y_temp
            )
            
            logger.info(f"Created splits - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
            return X_train, X_val, X_test, y_train, y_val, y_test
            
        except Exception as e:
            logger.error(f"Failed to create training splits: {str(e)}")
            raise

class ModelEvaluator:
    """Model evaluation and metrics calculation"""
    
    @staticmethod
    def evaluate_classification(y_true: np.ndarray, y_pred: np.ndarray, 
                              class_names: List[str] = None) -> Dict[str, Any]:
        """
        Evaluate classification model performance
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            class_names: Optional class names
            
        Returns:
            dict: Evaluation metrics
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available for evaluation")
            return {"error": "scikit-learn not available"}
        
        try:
            # Calculate metrics
            accuracy = accuracy_score(y_true, y_pred)
            precision, recall, f1, support = precision_recall_fscore_support(
                y_true, y_pred, average='weighted'
            )
            conf_matrix = confusion_matrix(y_true, y_pred)
            
            # Per-class metrics
            precision_per_class, recall_per_class, f1_per_class, _ = precision_recall_fscore_support(
                y_true, y_pred, average=None
            )
            
            metrics = {
                "accuracy": float(accuracy),
                "precision_weighted": float(precision),
                "recall_weighted": float(recall),
                "f1_weighted": float(f1),
                "confusion_matrix": conf_matrix.tolist(),
                "per_class_metrics": {}
            }
            
            # Add per-class metrics
            for i, (p, r, f) in enumerate(zip(precision_per_class, recall_per_class, f1_per_class)):
                class_name = class_names[i] if class_names else f"class_{i}"
                metrics["per_class_metrics"][class_name] = {
                    "precision": float(p),
                    "recall": float(r),
                    "f1": float(f)
                }
            
            logger.info(f"Classification evaluation completed - Accuracy: {accuracy:.3f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to evaluate classification model: {str(e)}")
            raise
    
    @staticmethod
    def evaluate_detection_performance(detections: List[Dict], ground_truth: List[Dict],
                                     iou_threshold: float = 0.5) -> Dict[str, float]:
        """
        Evaluate object detection performance
        
        Args:
            detections: List of detection results
            ground_truth: List of ground truth annotations
            iou_threshold: IoU threshold for matching
            
        Returns:
            dict: Detection metrics
        """
        try:
            # Simplified implementation - would need proper IoU calculation
            # and matching algorithm in production
            
            if not detections and not ground_truth:
                return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
            
            if not detections:
                return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
            
            if not ground_truth:
                return {"precision": 0.0, "recall": 1.0, "f1": 0.0}
            
            # Simple approximation
            num_correct = min(len(detections), len(ground_truth))
            precision = num_correct / len(detections) if detections else 0
            recall = num_correct / len(ground_truth) if ground_truth else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            return {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "num_detections": len(detections),
                "num_ground_truth": len(ground_truth)
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate detection performance: {str(e)}")
            return {"error": str(e)}

class CustomDataset:
    """Custom dataset class for training"""
    
    def __init__(self, X: np.ndarray, y: np.ndarray = None, transform=None):
        self.X = X
        self.y = y
        self.transform = transform
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        sample = self.X[idx]
        
        if self.transform:
            sample = self.transform(sample)
        
        if self.y is not None:
            return sample, self.y[idx]
        return sample

def load_pretrained_model(model_name: str, model_path: str = None) -> Any:
    """
    Load pretrained model from various sources
    
    Args:
        model_name: Name of the model
        model_path: Optional local path to model
        
    Returns:
        Loaded model
    """
    try:
        if model_path and os.path.exists(model_path):
            # Load from local path
            if model_path.endswith('.pth') and TORCH_AVAILABLE:
                return torch.load(model_path, map_location='cpu')
            elif model_path.endswith('.h5') and TF_AVAILABLE:
                return tf.keras.models.load_model(model_path)
            else:
                with open(model_path, 'rb') as f:
                    return pickle.load(f)
        else:
            # Load from model hub or create default
            logger.warning(f"Model {model_name} not found locally")
            return None
            
    except Exception as e:
        logger.error(f"Failed to load pretrained model {model_name}: {str(e)}")
        return None

def calculate_model_size(model: Any) -> Dict[str, Any]:
    """
    Calculate model size and parameter count
    
    Args:
        model: Model object
        
    Returns:
        dict: Model size information
    """
    try:
        if TORCH_AVAILABLE and isinstance(model, nn.Module):
            total_params = sum(p.numel() for p in model.parameters())
            trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
            
            return {
                "total_parameters": total_params,
                "trainable_parameters": trainable_params,
                "model_size_mb": total_params * 4 / (1024 * 1024),  # Assuming float32
                "framework": "pytorch"
            }
            
        elif TF_AVAILABLE and isinstance(model, (tf.keras.Model, keras.Model)):
            total_params = model.count_params()
            
            return {
                "total_parameters": total_params,
                "trainable_parameters": total_params,  # Simplified
                "model_size_mb": total_params * 4 / (1024 * 1024),  # Assuming float32
                "framework": "tensorflow"
            }
        
        else:
            # Generic size estimation
            import sys
            size_bytes = sys.getsizeof(model)
            
            return {
                "total_parameters": "unknown",
                "trainable_parameters": "unknown",
                "model_size_mb": size_bytes / (1024 * 1024),
                "framework": "unknown"
            }
            
    except Exception as e:
        logger.error(f"Failed to calculate model size: {str(e)}")
        return {"error": str(e)}
