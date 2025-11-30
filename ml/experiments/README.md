# ML Experiments - Model Training Infrastructure

PyTorch-based training infrastructure for Guardia AI models with Jupyter notebook workflows.

## Setup

```bash
cd ml/experiments
pip install -r requirements.txt
jupyter notebook
```

## Models

### 1. SkeleGNN - Skeleton Action Recognition
- **Notebook**: `notebooks/skelegnn_training.ipynb`
- **Dataset**: NTU RGB+D, Kinetics-Skeleton
- **Architecture**: Graph Convolutional Network with temporal modeling
- **Classes**: 7 actions (fight, fall, running, trespassing, threatening_pose, suspicious_movement, normal)

### 2. MotionStream - Motion Anomaly Detection
- **Notebook**: `notebooks/motionstream_training.ipynb`
- **Dataset**: Avenue, UCSD Ped2, custom surveillance clips
- **Architecture**: Temporal CNN/LSTM for motion features
- **Output**: Binary anomaly score + threshold

### 3. MoodTiny - Privacy-First Emotion Analysis
- **Notebook**: `notebooks/moodtiny_training.ipynb`
- **Dataset**: AffectNet, FER2013 (with background blur)
- **Architecture**: Lightweight CNN (MobileNetV3/EfficientNet)
- **Classes**: 6 emotions (neutral, stress, aggression, sadness, fear, anxiety)

## Project Structure

```
ml/experiments/
├── notebooks/
│   ├── skelegnn_training.ipynb
│   ├── motionstream_training.ipynb
│   └── moodtiny_training.ipynb
├── utils/
│   ├── datasets.py          # Dataset loaders
│   ├── metrics.py           # Evaluation metrics
│   ├── visualization.py     # Plotting utilities
│   └── export.py            # ONNX export helpers
├── scripts/
│   ├── export_onnx.py       # Batch ONNX export
│   └── deploy_models.py     # Copy models to services
├── configs/
│   ├── skelegnn.yaml
│   ├── motionstream.yaml
│   └── moodtiny.yaml
└── requirements.txt
```

## Training Workflow

### 1. Prepare Dataset
```python
from utils.datasets import SkeletonActionDataset

dataset = SkeletonActionDataset(
    root='../datasets/ntu_rgbd',
    split='train',
    num_frames=16
)
```

### 2. Train Model
```python
import torch
from models.skelegnn import SkeleGNN

model = SkeleGNN(num_classes=7, num_frames=16)
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

for epoch in range(100):
    train_one_epoch(model, dataloader, optimizer)
    validate(model, val_dataloader)
```

### 3. Export to ONNX
```python
from utils.export import export_to_onnx

export_to_onnx(
    model=model,
    input_shape=(1, 16, 17, 3),
    output_path='../../services/models/skelegnn/weights/skelegnn.onnx'
)
```

### 4. Deploy
```bash
python scripts/deploy_models.py --model skelegnn --version 1.0.0
```

## Datasets

### Public Datasets

#### Action Recognition
- **NTU RGB+D**: 60 action classes, 56k skeleton sequences
- **Kinetics-400**: Large-scale video dataset (subset with skeleton annotations)
- **UCF-Crime**: Anomalous action dataset

#### Motion Anomaly
- **Avenue**: Abnormal event detection, 16 training + 21 test videos
- **UCSD Ped2**: Pedestrian dataset with anomalies
- **ShanghaiTech**: Campus surveillance anomaly detection

#### Emotion Recognition
- **AffectNet**: 450k facial expressions, 7 emotions
- **FER2013**: 35k grayscale face images, 7 emotions
- **RAF-DB**: Real-world affective faces

### Custom Data Collection

For production deployment, collect domain-specific data:

```python
# Record from cameras
python utils/collect_data.py \
  --camera rtsp://camera:554/stream \
  --duration 3600 \
  --label normal
```

## Experiment Tracking

### Weights & Biases Integration

```python
import wandb

wandb.init(project='guardia-ai', name='skelegnn-v1')
wandb.config.update({
    'learning_rate': 0.001,
    'batch_size': 32,
    'num_epochs': 100
})

# Log metrics
wandb.log({'train_loss': loss, 'val_accuracy': acc})
```

### TensorBoard

```python
from torch.utils.tensorboard import SummaryWriter

writer = SummaryWriter('runs/skelegnn_experiment_1')
writer.add_scalar('Loss/train', loss, epoch)
writer.add_scalar('Accuracy/val', accuracy, epoch)
```

## Model Optimization

### Quantization (INT8)

```python
from utils.export import quantize_model

quantized_model = quantize_model(
    model=model,
    calibration_loader=calib_loader,
    dtype='int8'
)
```

### Pruning

```python
import torch.nn.utils.prune as prune

# Prune 30% of weights
prune.l1_unstructured(model.conv1, name='weight', amount=0.3)
```

## Benchmarking

### Inference Speed

```python
from utils.metrics import benchmark_inference

results = benchmark_inference(
    model=model,
    input_shape=(1, 16, 17, 3),
    num_iterations=1000,
    device='cuda'
)
# Output: ~15ms per inference on T4 GPU
```

### Model Size

```python
import os

model_size_mb = os.path.getsize('model.onnx') / (1024 * 1024)
print(f"Model size: {model_size_mb:.2f} MB")
```

## Validation

### Test on Edge Hardware

```bash
# Test ONNX model with ONNX Runtime
python scripts/validate_onnx.py \
  --model skelegnn.onnx \
  --input-shape 1,16,17,3 \
  --provider CPUExecutionProvider
```

### Compare PyTorch vs ONNX

```python
from utils.export import compare_outputs

compare_outputs(
    pytorch_model=model,
    onnx_path='model.onnx',
    test_input=sample_input
)
# Output: Max difference: 1e-6 (acceptable)
```

## Tips

1. **Start with pre-trained weights**: Transfer learning from ImageNet/Kinetics reduces training time
2. **Data augmentation**: Random crop, flip, rotation for robustness
3. **Class balancing**: Use weighted loss for imbalanced classes (e.g., rare anomalies)
4. **Early stopping**: Monitor validation loss to prevent overfitting
5. **Gradient clipping**: Stabilize training for RNNs/GNNs

## Common Issues

### CUDA Out of Memory
```python
# Reduce batch size
batch_size = 16  # instead of 32

# Enable gradient checkpointing
model.gradient_checkpointing_enable()
```

### Slow Data Loading
```python
# Increase num_workers
dataloader = DataLoader(dataset, batch_size=32, num_workers=4)

# Use pin_memory for GPU
dataloader = DataLoader(dataset, pin_memory=True)
```

### Poor Convergence
```python
# Learning rate scheduling
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)

# Warmup
for epoch in range(5):
    lr = 0.001 * (epoch + 1) / 5
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr
```

---

**Happy Training!** 🚀
