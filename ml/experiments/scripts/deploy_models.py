"""
Deploy trained models to Guardia AI services
"""

import os
import shutil
from pathlib import Path
import argparse
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def deploy_model(
    model_name: str,
    weights_dir: str,
    service_dir: str,
    version: str = None
) -> bool:
    """
    Deploy ONNX model to service directory
    
    Args:
        model_name: Name of the model (skelegnn, motionstream, moodtiny)
        weights_dir: Directory containing ONNX weights
        service_dir: Service weights directory
        version: Version string (e.g., '1.0.0')
    
    Returns:
        True if deployment successful
    """
    try:
        # Find ONNX file
        weights_path = Path(weights_dir)
        onnx_files = list(weights_path.glob('*.onnx'))
        
        if not onnx_files:
            logger.error(f"No ONNX files found in {weights_dir}")
            return False
        
        # Use quantized version if available, otherwise use full precision
        quantized_files = [f for f in onnx_files if 'int8' in f.name]
        if quantized_files:
            onnx_file = quantized_files[0]
            logger.info(f"Using quantized model: {onnx_file.name}")
        else:
            onnx_file = onnx_files[0]
            logger.info(f"Using model: {onnx_file.name}")
        
        # Create service weights directory
        service_weights_dir = Path(service_dir)
        service_weights_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup existing model if exists
        dest_path = service_weights_dir / f'{model_name}.onnx'
        if dest_path.exists():
            backup_path = service_weights_dir / f'{model_name}_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.onnx'
            shutil.copy(dest_path, backup_path)
            logger.info(f"Backed up existing model to {backup_path}")
        
        # Copy new model
        shutil.copy(onnx_file, dest_path)
        logger.info(f"✓ Deployed {onnx_file.name} to {dest_path}")
        
        # Create model metadata
        metadata = {
            'model_name': model_name,
            'version': version or datetime.now().strftime("%Y%m%d_%H%M%S"),
            'onnx_file': onnx_file.name,
            'file_size_mb': round(onnx_file.stat().st_size / (1024 * 1024), 2),
            'deployed_at': datetime.now().isoformat(),
            'source_path': str(onnx_file)
        }
        
        metadata_path = service_weights_dir / 'model_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✓ Created metadata file: {metadata_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Deployment failed: {e}")
        return False


def deploy_all_models(
    ml_root: str = '../..',
    service_root: str = '../../../services'
):
    """Deploy all trained models to their respective services"""
    
    logger.info("="*60)
    logger.info("Deploying Guardia AI Models")
    logger.info("="*60)
    
    results = {}
    
    # SkeleGNN
    logger.info("\n[1/3] Deploying SkeleGNN...")
    results['skelegnn'] = deploy_model(
        model_name='skelegnn',
        weights_dir=f'{ml_root}/services/models/skelegnn/weights',
        service_dir=f'{service_root}/models/skelegnn/weights',
        version='1.0.0'
    )
    
    # MotionStream
    logger.info("\n[2/3] Deploying MotionStream...")
    results['motionstream'] = deploy_model(
        model_name='motionstream',
        weights_dir=f'{ml_root}/services/models/motionstream/weights',
        service_dir=f'{service_root}/models/motionstream/weights',
        version='1.0.0'
    )
    
    # MoodTiny
    logger.info("\n[3/3] Deploying MoodTiny...")
    results['moodtiny'] = deploy_model(
        model_name='moodtiny',
        weights_dir=f'{ml_root}/services/models/moodtiny/weights',
        service_dir=f'{service_root}/models/moodtiny/weights',
        version='1.0.0'
    )
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("Deployment Summary")
    logger.info("="*60)
    for model_name, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        logger.info(f"{model_name}: {status}")
    logger.info("="*60)
    
    # Check if all successful
    all_success = all(results.values())
    
    if all_success:
        logger.info("\n✓ All models deployed successfully!")
        logger.info("Next steps:")
        logger.info("1. Restart the services: docker-compose restart")
        logger.info("2. Monitor logs: docker-compose logs -f skelegnn motionstream moodtiny")
        logger.info("3. Test inference endpoints")
    else:
        logger.warning("\n✗ Some models failed to deploy. Check logs above.")
    
    return all_success


def verify_deployment(service_root: str = '../../../services'):
    """Verify that models are deployed correctly"""
    logger.info("\n" + "="*60)
    logger.info("Verifying Deployment")
    logger.info("="*60)
    
    models = ['skelegnn', 'motionstream', 'moodtiny']
    
    for model_name in models:
        service_dir = Path(service_root) / 'models' / model_name / 'weights'
        model_path = service_dir / f'{model_name}.onnx'
        metadata_path = service_dir / 'model_metadata.json'
        
        if model_path.exists() and metadata_path.exists():
            file_size_mb = round(model_path.stat().st_size / (1024 * 1024), 2)
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            logger.info(f"\n{model_name}:")
            logger.info(f"  ✓ Model file: {model_path}")
            logger.info(f"  ✓ Size: {file_size_mb} MB")
            logger.info(f"  ✓ Version: {metadata.get('version', 'unknown')}")
            logger.info(f"  ✓ Deployed: {metadata.get('deployed_at', 'unknown')}")
        else:
            logger.error(f"\n{model_name}:")
            logger.error(f"  ✗ Model not found at {model_path}")
    
    logger.info("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(description='Deploy Guardia AI models to services')
    parser.add_argument('--model', type=str, choices=['skelegnn', 'motionstream', 'moodtiny', 'all'],
                        default='all', help='Model to deploy')
    parser.add_argument('--ml-root', type=str, default='../..',
                        help='ML root directory (containing exported models)')
    parser.add_argument('--service-root', type=str, default='../../../services',
                        help='Services root directory')
    parser.add_argument('--verify', action='store_true', help='Verify deployment only')
    
    args = parser.parse_args()
    
    if args.verify:
        verify_deployment(args.service_root)
    else:
        if args.model == 'all':
            deploy_all_models(args.ml_root, args.service_root)
        else:
            # Deploy single model
            weights_dir = f'{args.ml_root}/services/models/{args.model}/weights'
            service_dir = f'{args.service_root}/models/{args.model}/weights'
            
            success = deploy_model(
                model_name=args.model,
                weights_dir=weights_dir,
                service_dir=service_dir
            )
            
            if success:
                logger.info(f"\n✓ {args.model} deployed successfully!")
            else:
                logger.error(f"\n✗ {args.model} deployment failed!")


if __name__ == '__main__':
    main()
