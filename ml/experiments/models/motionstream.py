"""
MotionStream - Temporal CNN/LSTM for Motion Anomaly Detection
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class TemporalCNN(nn.Module):
    """Temporal CNN for motion feature extraction"""
    
    def __init__(self, in_channels: int = 2, hidden_dim: int = 64):
        super().__init__()
        
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_channels, hidden_dim, kernel_size=3, padding=1),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2)
        )
        
        self.conv2 = nn.Sequential(
            nn.Conv2d(hidden_dim, hidden_dim * 2, kernel_size=3, padding=1),
            nn.BatchNorm2d(hidden_dim * 2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2)
        )
        
        self.conv3 = nn.Sequential(
            nn.Conv2d(hidden_dim * 2, hidden_dim * 4, kernel_size=3, padding=1),
            nn.BatchNorm2d(hidden_dim * 4),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2)
        )
        
        self.global_pool = nn.AdaptiveAvgPool2d(1)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Optical flow (B, C, H, W)
        Returns:
            Feature vector (B, hidden_dim * 4)
        """
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.global_pool(x)
        x = x.view(x.size(0), -1)
        return x


class MotionStream(nn.Module):
    """
    Motion anomaly detection using temporal CNN and LSTM
    """
    
    def __init__(
        self,
        num_frames: int = 8,
        input_channels: int = 2,
        hidden_dim: int = 64,
        lstm_layers: int = 2,
        dropout: float = 0.5
    ):
        super().__init__()
        
        self.num_frames = num_frames
        
        # Spatial feature extractor (per-frame CNN)
        self.spatial_encoder = TemporalCNN(input_channels, hidden_dim)
        
        # Temporal modeling (LSTM)
        self.lstm = nn.LSTM(
            input_size=hidden_dim * 4,
            hidden_size=hidden_dim * 2,
            num_layers=lstm_layers,
            batch_first=True,
            dropout=dropout if lstm_layers > 1 else 0,
            bidirectional=True
        )
        
        # Anomaly classifier
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim),  # *4 due to bidirectional
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Optical flow sequence (B, T, C, H, W)
               B=batch, T=num_frames, C=channels (u,v), H=height, W=width
        Returns:
            Anomaly score (B, 1)
        """
        batch_size, num_frames, channels, height, width = x.shape
        
        # Extract spatial features per frame
        # Reshape: (B, T, C, H, W) -> (B*T, C, H, W)
        x = x.view(batch_size * num_frames, channels, height, width)
        
        # Spatial encoding: (B*T, C, H, W) -> (B*T, hidden_dim*4)
        spatial_features = self.spatial_encoder(x)
        
        # Reshape for LSTM: (B*T, F) -> (B, T, F)
        spatial_features = spatial_features.view(batch_size, num_frames, -1)
        
        # Temporal modeling: (B, T, F) -> (B, T, hidden_dim*4)
        temporal_features, _ = self.lstm(spatial_features)
        
        # Take last time step: (B, T, F) -> (B, F)
        temporal_features = temporal_features[:, -1, :]
        
        # Anomaly classification: (B, F) -> (B, 1)
        anomaly_score = self.classifier(temporal_features)
        
        return anomaly_score


class MotionStreamLite(nn.Module):
    """
    Lightweight version for edge deployment
    Uses only CNN without LSTM
    """
    
    def __init__(
        self,
        num_frames: int = 8,
        input_channels: int = 2,
        hidden_dim: int = 32
    ):
        super().__init__()
        
        self.num_frames = num_frames
        
        # 3D CNN for spatiotemporal features
        self.conv3d = nn.Sequential(
            nn.Conv3d(input_channels, hidden_dim, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            nn.BatchNorm3d(hidden_dim),
            nn.ReLU(inplace=True),
            nn.MaxPool3d((1, 2, 2)),
            
            nn.Conv3d(hidden_dim, hidden_dim * 2, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            nn.BatchNorm3d(hidden_dim * 2),
            nn.ReLU(inplace=True),
            nn.MaxPool3d((1, 2, 2)),
            
            nn.Conv3d(hidden_dim * 2, hidden_dim * 4, kernel_size=(3, 3, 3), padding=(1, 1, 1)),
            nn.BatchNorm3d(hidden_dim * 4),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool3d(1)
        )
        
        # Classifier
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(hidden_dim, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Optical flow sequence (B, T, C, H, W)
        Returns:
            Anomaly score (B, 1)
        """
        # Reshape for 3D conv: (B, T, C, H, W) -> (B, C, T, H, W)
        x = x.permute(0, 2, 1, 3, 4).contiguous()
        
        # 3D convolution
        x = self.conv3d(x)
        
        # Flatten: (B, C, 1, 1, 1) -> (B, C)
        x = x.view(x.size(0), -1)
        
        # Classification
        x = self.classifier(x)
        
        return x


def create_motionstream(
    model_type: str = 'full',
    num_frames: int = 8,
    pretrained: bool = False
) -> nn.Module:
    """Create MotionStream model"""
    if model_type == 'full':
        model = MotionStream(num_frames=num_frames)
    elif model_type == 'lite':
        model = MotionStreamLite(num_frames=num_frames)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    if pretrained:
        # Load pretrained weights if available
        pass
    
    return model


def create_motionstream_lite(num_frames: int = 8, pretrained: bool = False) -> MotionStreamLite:
    """Create MotionStream Lite model (convenience function)"""
    return create_motionstream(model_type='lite', num_frames=num_frames, pretrained=pretrained)


if __name__ == '__main__':
    # Test full model
    model_full = create_motionstream(model_type='full')
    
    # Dummy input: batch_size=2, num_frames=8, channels=2 (u,v), height=224, width=224
    x = torch.randn(2, 8, 2, 224, 224)
    
    # Forward pass
    output = model_full(x)
    
    print(f"Full Model:")
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output.shape}")
    print(f"  Parameters: {sum(p.numel() for p in model_full.parameters()):,}")
    
    # Test lite model
    model_lite = create_motionstream(model_type='lite')
    output_lite = model_lite(x)
    
    print(f"\nLite Model:")
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {output_lite.shape}")
    print(f"  Parameters: {sum(p.numel() for p in model_lite.parameters()):,}")
