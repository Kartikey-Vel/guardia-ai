"""
MoodTiny - Lightweight CNN for Privacy-First Emotion Recognition
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import timm


class MoodTiny(nn.Module):
    """
    Lightweight emotion recognition model using MobileNetV3
    Optimized for edge deployment
    """
    
    def __init__(
        self,
        num_classes: int = 6,
        pretrained: bool = True,
        dropout: float = 0.3
    ):
        super().__init__()
        
        self.num_classes = num_classes
        
        # Use MobileNetV3-Small as backbone (efficient for edge)
        self.backbone = timm.create_model(
            'mobilenetv3_small_100',
            pretrained=pretrained,
            num_classes=0,  # Remove classifier
            global_pool=''
        )
        
        # Feature dimension from MobileNetV3-Small
        self.feature_dim = 576
        
        # Global pooling
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        
        # Emotion classifier
        self.classifier = nn.Sequential(
            nn.Linear(self.feature_dim, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input face images (B, 3, H, W)
        Returns:
            Class logits (B, num_classes)
        """
        # Extract features
        features = self.backbone(x)
        
        # Global pooling
        features = self.global_pool(features)
        features = features.view(features.size(0), -1)
        
        # Classify
        output = self.classifier(features)
        
        return output


class MoodTinyEfficientNet(nn.Module):
    """
    Alternative using EfficientNet-Lite for even better accuracy
    """
    
    def __init__(
        self,
        num_classes: int = 6,
        pretrained: bool = True,
        dropout: float = 0.3
    ):
        super().__init__()
        
        self.num_classes = num_classes
        
        # Use EfficientNet-Lite0 as backbone
        self.backbone = timm.create_model(
            'efficientnet_lite0',
            pretrained=pretrained,
            num_classes=0,
            global_pool=''
        )
        
        # Feature dimension from EfficientNet-Lite0
        self.feature_dim = 1280
        
        # Global pooling
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        
        # Emotion classifier
        self.classifier = nn.Sequential(
            nn.Linear(self.feature_dim, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(256, num_classes)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input face images (B, 3, H, W)
        Returns:
            Class logits (B, num_classes)
        """
        features = self.backbone(x)
        features = self.global_pool(features)
        features = features.view(features.size(0), -1)
        output = self.classifier(features)
        return output


class MoodTinyWithAggregation(nn.Module):
    """
    MoodTiny with crowd mood aggregation for privacy-preserving surveillance
    """
    
    def __init__(
        self,
        num_classes: int = 6,
        pretrained: bool = True
    ):
        super().__init__()
        
        self.num_classes = num_classes
        
        # Per-face emotion classifier
        self.emotion_classifier = MoodTiny(
            num_classes=num_classes,
            pretrained=pretrained
        )
        
        # Crowd mood aggregator (optional - used during inference)
        # Aggregates emotions from multiple faces into overall mood
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input face images (B, 3, H, W)
        Returns:
            Per-face emotion logits (B, num_classes)
        """
        return self.emotion_classifier(x)
    
    def aggregate_crowd_mood(
        self,
        face_emotions: torch.Tensor,
        aggregation: str = 'attention'
    ) -> torch.Tensor:
        """
        Aggregate emotions from multiple faces
        
        Args:
            face_emotions: Emotion probabilities (N, num_classes) for N faces
            aggregation: 'mean', 'max', or 'attention'
        Returns:
            Aggregated mood (num_classes,)
        """
        if aggregation == 'mean':
            # Simple average
            return face_emotions.mean(dim=0)
        
        elif aggregation == 'max':
            # Take strongest emotion per class
            return face_emotions.max(dim=0)[0]
        
        elif aggregation == 'attention':
            # Attention-weighted aggregation
            # Weight faces by their confidence (entropy-based)
            entropy = -(face_emotions * torch.log(face_emotions + 1e-8)).sum(dim=1)
            confidence = 1 - (entropy / torch.log(torch.tensor(self.num_classes)))
            weights = F.softmax(confidence, dim=0)
            
            # Weighted sum
            aggregated = (face_emotions * weights.unsqueeze(1)).sum(dim=0)
            return aggregated
        
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation}")


def create_moodtiny(
    model_type: str = 'mobilenet',
    num_classes: int = 6,
    pretrained: bool = True
) -> nn.Module:
    """Create MoodTiny model"""
    if model_type == 'mobilenet':
        model = MoodTiny(num_classes=num_classes, pretrained=pretrained)
    elif model_type == 'efficientnet':
        model = MoodTinyEfficientNet(num_classes=num_classes, pretrained=pretrained)
    elif model_type == 'aggregation':
        model = MoodTinyWithAggregation(num_classes=num_classes, pretrained=pretrained)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    return model


def create_moodtiny_efficientnet(num_classes: int = 6, pretrained: bool = True) -> MoodTinyEfficientNet:
    """Create MoodTiny with EfficientNet backbone (convenience function)"""
    return create_moodtiny(model_type='efficientnet', num_classes=num_classes, pretrained=pretrained)


def create_moodtiny_with_aggregation(num_classes: int = 6, pretrained: bool = True) -> MoodTinyWithAggregation:
    """Create MoodTiny with crowd aggregation (convenience function)"""
    return create_moodtiny(model_type='aggregation', num_classes=num_classes, pretrained=pretrained)


if __name__ == '__main__':
    # Test MobileNet version
    model_mobile = create_moodtiny(model_type='mobilenet', pretrained=False)
    
    # Dummy input: batch_size=4, channels=3, height=112, width=112
    x = torch.randn(4, 3, 112, 112)
    
    # Forward pass
    output = model_mobile(x)
    
    print(f"MobileNet Model:")
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output.shape}")
    print(f"  Parameters: {sum(p.numel() for p in model_mobile.parameters()):,}")
    
    # Test EfficientNet version
    model_efficient = create_moodtiny(model_type='efficientnet', pretrained=False)
    output_eff = model_efficient(x)
    
    print(f"\nEfficientNet Model:")
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output_eff.shape}")
    print(f"  Parameters: {sum(p.numel() for p in model_efficient.parameters()):,}")
    
    # Test aggregation
    model_agg = create_moodtiny(model_type='aggregation', pretrained=False)
    
    # Multiple faces
    faces = torch.randn(10, 3, 112, 112)  # 10 faces
    face_logits = model_agg(faces)
    face_probs = F.softmax(face_logits, dim=1)
    
    # Aggregate crowd mood
    crowd_mood = model_agg.aggregate_crowd_mood(face_probs, aggregation='attention')
    
    print(f"\nCrowd Aggregation:")
    print(f"  Input faces: {faces.shape[0]}")
    print(f"  Aggregated mood: {crowd_mood.shape}")
    print(f"  Dominant emotion: {crowd_mood.argmax().item()}")
