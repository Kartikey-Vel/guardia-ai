"""
Batch ONNX export script for all Guardia AI models
"""

import torch
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models.skelegnn import create_skelegnn
from models.motionstream import create_motionstream
from models.moodtiny import create_moodtiny
from utils.export import export_to_onnx, validate_onnx_model, quantize_onnx_model, benchmark_onnx_model

import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_skelegnn(
    checkpoint_path: str,
    output_dir: str = '../../services/models/skelegnn/weights',
    quantize: bool = True
):
    """Export SkeleGNN model to ONNX"""
    logger.info("="*60)
    logger.info("Exporting SkeleGNN")
    logger.info("="*60)
    
    # Create model
    model = create_skelegnn(num_classes=7)
    
    # Load checkpoint
    if os.path.exists(checkpoint_path):
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Loaded checkpoint from {checkpoint_path}")
    else:
        logger.warning(f"Checkpoint not found: {checkpoint_path}. Using random weights.")
    
    model.eval()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Export to ONNX
    input_shape = (1, 16, 17, 3)  # (batch, frames, joints, coords)
    output_path = os.path.join(output_dir, 'skelegnn.onnx')
    
    success = export_to_onnx(
        model=model,
        input_shape=input_shape,
        output_path=output_path,
        opset_version=14,
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}},
        input_names=['input'],
        output_names=['output']
    )
    
    if success:
        # Validate
        validate_onnx_model(output_path, model, input_shape)
        
        # Benchmark
        benchmark_onnx_model(output_path, input_shape, num_iterations=100)
        
        # Quantize
        if quantize:
            quantized_path = os.path.join(output_dir, 'skelegnn_int8.onnx')
            quantize_onnx_model(output_path, quantized_path)
    
    return success


def export_motionstream(
    checkpoint_path: str,
    output_dir: str = '../../services/models/motionstream/weights',
    model_type: str = 'full',
    quantize: bool = True
):
    """Export MotionStream model to ONNX"""
    logger.info("="*60)
    logger.info(f"Exporting MotionStream ({model_type})")
    logger.info("="*60)
    
    # Create model
    model = create_motionstream(model_type=model_type, num_frames=8)
    
    # Load checkpoint
    if os.path.exists(checkpoint_path):
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Loaded checkpoint from {checkpoint_path}")
    else:
        logger.warning(f"Checkpoint not found: {checkpoint_path}. Using random weights.")
    
    model.eval()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Export to ONNX
    input_shape = (1, 8, 2, 224, 224)  # (batch, frames, channels, height, width)
    output_path = os.path.join(output_dir, f'motionstream_{model_type}.onnx')
    
    success = export_to_onnx(
        model=model,
        input_shape=input_shape,
        output_path=output_path,
        opset_version=14,
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}},
        input_names=['input'],
        output_names=['output']
    )
    
    if success:
        # Validate
        validate_onnx_model(output_path, model, input_shape)
        
        # Benchmark
        benchmark_onnx_model(output_path, input_shape, num_iterations=100)
        
        # Quantize
        if quantize:
            quantized_path = os.path.join(output_dir, f'motionstream_{model_type}_int8.onnx')
            quantize_onnx_model(output_path, quantized_path)
    
    return success


def export_moodtiny(
    checkpoint_path: str,
    output_dir: str = '../../services/models/moodtiny/weights',
    model_type: str = 'mobilenet',
    quantize: bool = True
):
    """Export MoodTiny model to ONNX"""
    logger.info("="*60)
    logger.info(f"Exporting MoodTiny ({model_type})")
    logger.info("="*60)
    
    # Create model
    model = create_moodtiny(model_type=model_type, num_classes=6, pretrained=False)
    
    # Load checkpoint
    if os.path.exists(checkpoint_path):
        checkpoint = torch.load(checkpoint_path, map_location='cpu')
        model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(f"Loaded checkpoint from {checkpoint_path}")
    else:
        logger.warning(f"Checkpoint not found: {checkpoint_path}. Using random weights.")
    
    model.eval()
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Export to ONNX
    input_shape = (1, 3, 112, 112)  # (batch, channels, height, width)
    output_path = os.path.join(output_dir, f'moodtiny_{model_type}.onnx')
    
    success = export_to_onnx(
        model=model,
        input_shape=input_shape,
        output_path=output_path,
        opset_version=14,
        dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}},
        input_names=['input'],
        output_names=['output']
    )
    
    if success:
        # Validate
        validate_onnx_model(output_path, model, input_shape)
        
        # Benchmark
        benchmark_onnx_model(output_path, input_shape, num_iterations=100)
        
        # Quantize
        if quantize:
            quantized_path = os.path.join(output_dir, f'moodtiny_{model_type}_int8.onnx')
            quantize_onnx_model(output_path, quantized_path)
    
    return success


def main():
    parser = argparse.ArgumentParser(description='Export Guardia AI models to ONNX')
    parser.add_argument('--model', type=str, choices=['skelegnn', 'motionstream', 'moodtiny', 'all'], 
                        default='all', help='Model to export')
    parser.add_argument('--checkpoint-dir', type=str, default='../checkpoints',
                        help='Directory containing model checkpoints')
    parser.add_argument('--quantize', action='store_true', help='Quantize models to INT8')
    
    args = parser.parse_args()
    
    results = {}
    
    # Export SkeleGNN
    if args.model in ['skelegnn', 'all']:
        checkpoint_path = os.path.join(args.checkpoint_dir, 'skelegnn', 'best_model.pth')
        results['skelegnn'] = export_skelegnn(checkpoint_path, quantize=args.quantize)
    
    # Export MotionStream
    if args.model in ['motionstream', 'all']:
        checkpoint_path = os.path.join(args.checkpoint_dir, 'motionstream', 'best_model.pth')
        results['motionstream'] = export_motionstream(
            checkpoint_path,
            model_type='lite',  # Use lite version for edge
            quantize=args.quantize
        )
    
    # Export MoodTiny
    if args.model in ['moodtiny', 'all']:
        checkpoint_path = os.path.join(args.checkpoint_dir, 'moodtiny', 'best_model.pth')
        results['moodtiny'] = export_moodtiny(
            checkpoint_path,
            model_type='mobilenet',
            quantize=args.quantize
        )
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Export Summary")
    logger.info("="*60)
    for model_name, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        logger.info(f"{model_name}: {status}")
    logger.info("="*60)


if __name__ == '__main__':
    main()
