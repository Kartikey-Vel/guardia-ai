"""
ONNX export utilities for deploying PyTorch models
"""

import torch
import onnx
import onnxruntime as ort
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_to_onnx(
    model: torch.nn.Module,
    input_shape: Tuple,
    output_path: str,
    opset_version: int = 14,
    dynamic_axes: Dict[str, Any] = None,
    input_names: list = None,
    output_names: list = None
) -> bool:
    """
    Export PyTorch model to ONNX format
    
    Args:
        model: PyTorch model
        input_shape: Input tensor shape (e.g., (1, 16, 17, 3))
        output_path: Path to save ONNX model
        opset_version: ONNX opset version
        dynamic_axes: Dynamic axes for variable input sizes
        input_names: Names for input tensors
        output_names: Names for output tensors
    
    Returns:
        True if export successful
    """
    try:
        model.eval()
        
        # Create dummy input
        dummy_input = torch.randn(*input_shape)
        
        # Default names
        if input_names is None:
            input_names = ['input']
        if output_names is None:
            output_names = ['output']
        
        # Export to ONNX
        logger.info(f"Exporting model to ONNX: {output_path}")
        
        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=input_names,
            output_names=output_names,
            dynamic_axes=dynamic_axes,
            verbose=False
        )
        
        # Verify ONNX model
        onnx_model = onnx.load(output_path)
        onnx.checker.check_model(onnx_model)
        
        logger.info(f"✓ ONNX export successful: {output_path}")
        
        # Print model info
        file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        logger.info(f"  Model size: {file_size_mb:.2f} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ ONNX export failed: {e}")
        return False


def validate_onnx_model(
    onnx_path: str,
    pytorch_model: torch.nn.Module,
    input_shape: Tuple,
    tolerance: float = 1e-5
) -> bool:
    """
    Validate ONNX model against PyTorch model
    
    Args:
        onnx_path: Path to ONNX model
        pytorch_model: Original PyTorch model
        input_shape: Input tensor shape
        tolerance: Maximum allowed difference
    
    Returns:
        True if outputs match within tolerance
    """
    try:
        # Create test input
        test_input = torch.randn(*input_shape)
        
        # PyTorch inference
        pytorch_model.eval()
        with torch.no_grad():
            pytorch_output = pytorch_model(test_input).numpy()
        
        # ONNX Runtime inference
        ort_session = ort.InferenceSession(onnx_path)
        ort_inputs = {ort_session.get_inputs()[0].name: test_input.numpy()}
        ort_output = ort_session.run(None, ort_inputs)[0]
        
        # Compare outputs
        max_diff = np.abs(pytorch_output - ort_output).max()
        mean_diff = np.abs(pytorch_output - ort_output).mean()
        
        logger.info(f"Validation results:")
        logger.info(f"  Max difference: {max_diff:.2e}")
        logger.info(f"  Mean difference: {mean_diff:.2e}")
        
        if max_diff < tolerance:
            logger.info(f"✓ ONNX model validation passed")
            return True
        else:
            logger.warning(f"✗ ONNX model validation failed (max diff: {max_diff:.2e})")
            return False
            
    except Exception as e:
        logger.error(f"✗ Validation error: {e}")
        return False


def quantize_onnx_model(
    onnx_path: str,
    output_path: str,
    calibration_data: np.ndarray = None,
    per_channel: bool = False
) -> bool:
    """
    Quantize ONNX model to INT8 for faster inference
    
    Args:
        onnx_path: Path to float32 ONNX model
        output_path: Path to save quantized model
        calibration_data: Calibration data for quantization
        per_channel: Use per-channel quantization
    
    Returns:
        True if quantization successful
    """
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
        
        logger.info(f"Quantizing model to INT8: {output_path}")
        
        quantize_dynamic(
            onnx_path,
            output_path,
            weight_type=QuantType.QInt8,
            per_channel=per_channel
        )
        
        # Compare file sizes
        original_size = Path(onnx_path).stat().st_size / (1024 * 1024)
        quantized_size = Path(output_path).stat().st_size / (1024 * 1024)
        compression = (1 - quantized_size / original_size) * 100
        
        logger.info(f"✓ Quantization successful")
        logger.info(f"  Original: {original_size:.2f} MB")
        logger.info(f"  Quantized: {quantized_size:.2f} MB")
        logger.info(f"  Compression: {compression:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Quantization failed: {e}")
        return False


def benchmark_onnx_model(
    onnx_path: str,
    input_shape: Tuple,
    num_iterations: int = 1000,
    provider: str = 'CPUExecutionProvider'
) -> Dict[str, float]:
    """
    Benchmark ONNX model inference speed
    
    Args:
        onnx_path: Path to ONNX model
        input_shape: Input tensor shape
        num_iterations: Number of inference iterations
        provider: Execution provider (CPU, CUDA, TensorRT, etc.)
    
    Returns:
        Benchmark results dictionary
    """
    import time
    
    try:
        # Create session
        ort_session = ort.InferenceSession(onnx_path, providers=[provider])
        
        # Create dummy input
        dummy_input = np.random.randn(*input_shape).astype(np.float32)
        ort_inputs = {ort_session.get_inputs()[0].name: dummy_input}
        
        # Warmup
        for _ in range(100):
            _ = ort_session.run(None, ort_inputs)
        
        # Benchmark
        start_time = time.time()
        for _ in range(num_iterations):
            _ = ort_session.run(None, ort_inputs)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time = total_time / num_iterations
        fps = 1.0 / avg_time
        
        results = {
            'provider': provider,
            'avg_inference_ms': avg_time * 1000,
            'fps': fps,
            'total_time_s': total_time,
            'num_iterations': num_iterations
        }
        
        logger.info(f"Benchmark results ({provider}):")
        logger.info(f"  Avg inference time: {avg_time * 1000:.2f} ms")
        logger.info(f"  Throughput: {fps:.1f} FPS")
        
        return results
        
    except Exception as e:
        logger.error(f"✗ Benchmark failed: {e}")
        return {}


def optimize_onnx_model(
    onnx_path: str,
    output_path: str,
    optimization_level: int = 99
) -> bool:
    """
    Optimize ONNX model using ONNX Runtime optimizations
    
    Args:
        onnx_path: Path to input ONNX model
        output_path: Path to save optimized model
        optimization_level: 1=basic, 2=extended, 99=all
    
    Returns:
        True if optimization successful
    """
    try:
        from onnxruntime.transformers.optimizer import optimize_model
        
        logger.info(f"Optimizing ONNX model: {output_path}")
        
        # Optimize
        optimized_model = optimize_model(
            onnx_path,
            model_type='bert',  # or 'gpt2', 'vit', etc.
            num_heads=0,
            hidden_size=0,
            optimization_options=None,
            opt_level=optimization_level
        )
        
        # Save
        optimized_model.save_model_to_file(output_path)
        
        logger.info(f"✓ Optimization successful: {output_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Optimization failed: {e}")
        return False


def compare_pytorch_onnx_outputs(
    pytorch_model: torch.nn.Module,
    onnx_path: str,
    test_inputs: torch.Tensor
) -> Dict[str, float]:
    """
    Compare outputs between PyTorch and ONNX models
    
    Args:
        pytorch_model: PyTorch model
        onnx_path: Path to ONNX model
        test_inputs: Test input tensors
    
    Returns:
        Comparison statistics
    """
    # PyTorch inference
    pytorch_model.eval()
    with torch.no_grad():
        pytorch_outputs = pytorch_model(test_inputs).numpy()
    
    # ONNX inference
    ort_session = ort.InferenceSession(onnx_path)
    ort_inputs = {ort_session.get_inputs()[0].name: test_inputs.numpy()}
    onnx_outputs = ort_session.run(None, ort_inputs)[0]
    
    # Compute differences
    abs_diff = np.abs(pytorch_outputs - onnx_outputs)
    rel_diff = abs_diff / (np.abs(pytorch_outputs) + 1e-8)
    
    stats = {
        'max_abs_diff': abs_diff.max(),
        'mean_abs_diff': abs_diff.mean(),
        'max_rel_diff': rel_diff.max(),
        'mean_rel_diff': rel_diff.mean(),
        'pytorch_mean': pytorch_outputs.mean(),
        'onnx_mean': onnx_outputs.mean()
    }
    
    logger.info("PyTorch vs ONNX comparison:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value:.6f}")
    
    return stats
