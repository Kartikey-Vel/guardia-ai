"""
SkeleGNN - Skeleton-based Graph Neural Network for Action Recognition
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple


class GraphConvolution(nn.Module):
    """Graph convolution layer"""
    
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features)
    
    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Node features (B, N, F_in)
            adj: Adjacency matrix (N, N)
        Returns:
            Output features (B, N, F_out)
        """
        # Linear transformation
        x = self.linear(x)
        
        # Graph convolution: A * X
        x = torch.matmul(adj, x)
        
        return x


class TemporalConvolution(nn.Module):
    """Temporal convolution over time dimension"""
    
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3):
        super().__init__()
        self.conv = nn.Conv1d(
            in_channels, out_channels,
            kernel_size=kernel_size,
            padding=kernel_size // 2
        )
        self.bn = nn.BatchNorm1d(out_channels)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input (B, C, T)
        Returns:
            Output (B, C, T)
        """
        x = self.conv(x)
        x = self.bn(x)
        x = F.relu(x, inplace=True)
        return x


class STGCNBlock(nn.Module):
    """Spatial-Temporal Graph Convolutional Block"""
    
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        num_joints: int,
        temporal_kernel_size: int = 9,
        dropout: float = 0.5
    ):
        super().__init__()
        
        # Spatial graph convolution
        self.gcn = GraphConvolution(in_channels, out_channels)
        
        # Temporal convolution
        self.tcn = TemporalConvolution(
            num_joints * out_channels,
            num_joints * out_channels,
            kernel_size=temporal_kernel_size
        )
        
        self.bn = nn.BatchNorm2d(out_channels)
        self.dropout = nn.Dropout(dropout)
        
        # Residual connection
        self.residual = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=1),
            nn.BatchNorm2d(out_channels)
        ) if in_channels != out_channels else nn.Identity()
    
    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input (B, C, T, J) where B=batch, C=channels, T=time, J=joints
            adj: Adjacency matrix (J, J)
        Returns:
            Output (B, C, T, J)
        """
        batch_size, in_channels, num_frames, num_joints = x.shape
        
        # Spatial GCN: (B, C, T, J) -> (B*T, J, C)
        x_spatial = x.permute(0, 2, 3, 1).contiguous()
        x_spatial = x_spatial.view(batch_size * num_frames, num_joints, in_channels)
        
        x_spatial = self.gcn(x_spatial, adj)
        
        # Reshape back: (B*T, J, C) -> (B, C, T, J)
        x_spatial = x_spatial.view(batch_size, num_frames, num_joints, -1)
        x_spatial = x_spatial.permute(0, 3, 1, 2).contiguous()
        
        # Temporal CNN: (B, C, T, J) -> (B, C*J, T)
        x_temporal = x_spatial.view(batch_size, -1, num_frames)
        x_temporal = self.tcn(x_temporal)
        
        # Reshape back: (B, C*J, T) -> (B, C, T, J)
        x_temporal = x_temporal.view(batch_size, -1, num_frames, num_joints)
        
        # Batch norm and dropout
        x_temporal = self.bn(x_temporal)
        x_temporal = self.dropout(x_temporal)
        
        # Residual connection
        x_res = self.residual(x)
        
        return F.relu(x_temporal + x_res, inplace=True)


class SkeleGNN(nn.Module):
    """
    Skeleton-based Graph Neural Network for Action Recognition
    """
    
    def __init__(
        self,
        num_classes: int = 7,
        num_joints: int = 17,
        num_frames: int = 16,
        in_channels: int = 3,
        graph_cfg: dict = None
    ):
        super().__init__()
        
        self.num_classes = num_classes
        self.num_joints = num_joints
        self.num_frames = num_frames
        
        # Build skeleton graph adjacency matrix
        self.adj = self._build_adjacency_matrix(graph_cfg)
        
        # STGCN blocks
        self.st_gcn_blocks = nn.ModuleList([
            STGCNBlock(in_channels, 64, num_joints, temporal_kernel_size=9),
            STGCNBlock(64, 128, num_joints, temporal_kernel_size=9),
            STGCNBlock(128, 256, num_joints, temporal_kernel_size=9),
        ])
        
        # Global pooling
        self.global_pool = nn.AdaptiveAvgPool2d(1)
        
        # Classifier
        self.fc = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(128, num_classes)
        )
    
    def _build_adjacency_matrix(self, graph_cfg: dict = None) -> torch.Tensor:
        """Build skeleton graph adjacency matrix"""
        if graph_cfg is None:
            # COCO 17 keypoints default connections
            edges = [
                (0, 1), (0, 2), (1, 3), (2, 4),  # Head
                (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
                (5, 11), (6, 12), (11, 12),  # Torso
                (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
            ]
        else:
            edges = graph_cfg.get('edges', [])
        
        # Build adjacency matrix
        adj = torch.zeros(self.num_joints, self.num_joints)
        
        # Add edges
        for i, j in edges:
            adj[i, j] = 1
            adj[j, i] = 1  # Undirected graph
        
        # Add self-loops
        adj += torch.eye(self.num_joints)
        
        # Normalize adjacency matrix: D^(-1/2) * A * D^(-1/2)
        degree = adj.sum(dim=1)
        degree_inv_sqrt = torch.pow(degree, -0.5)
        degree_inv_sqrt[torch.isinf(degree_inv_sqrt)] = 0.
        
        degree_matrix = torch.diag(degree_inv_sqrt)
        adj_normalized = degree_matrix @ adj @ degree_matrix
        
        return adj_normalized
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input skeleton sequence (B, T, J, C)
               B=batch size, T=num_frames, J=num_joints, C=coordinates (x,y,z or x,y,confidence)
        Returns:
            Class logits (B, num_classes)
        """
        # Reshape to (B, C, T, J)
        x = x.permute(0, 3, 1, 2).contiguous()
        
        # Move adjacency matrix to same device
        adj = self.adj.to(x.device)
        
        # STGCN blocks
        for block in self.st_gcn_blocks:
            x = block(x, adj)
        
        # Global pooling: (B, C, T, J) -> (B, C, 1, 1)
        x = self.global_pool(x)
        
        # Flatten: (B, C, 1, 1) -> (B, C)
        x = x.view(x.size(0), -1)
        
        # Classifier
        x = self.fc(x)
        
        return x


def create_skelegnn(num_classes: int = 7, pretrained: bool = False) -> SkeleGNN:
    """Create SkeleGNN model"""
    model = SkeleGNN(num_classes=num_classes)
    
    if pretrained:
        # Load pretrained weights if available
        pass
    
    return model


if __name__ == '__main__':
    # Test model
    model = create_skelegnn(num_classes=7)
    
    # Dummy input: batch_size=2, num_frames=16, num_joints=17, coords=3
    x = torch.randn(2, 16, 17, 3)
    
    # Forward pass
    output = model(x)
    
    print(f"Input shape: {x.shape}")
    print(f"Output shape: {output.shape}")
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
