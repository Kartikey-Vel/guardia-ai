"""
Google Cloud utilities with environment-based authentication
"""
import os
import json
import tempfile
from typing import Optional, Dict, Any
import logging

from guardia.config.settings import settings

# Try to import Google Cloud packages, handle gracefully if not installed
try:
    from google.cloud import storage, videointelligence, vision
    from google.auth import credentials
    from google.oauth2 import service_account
    from google.auth.exceptions import DefaultCredentialsError
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError as e:
    storage = videointelligence = vision = None
    credentials = service_account = DefaultCredentialsError = None
    GOOGLE_CLOUD_AVAILABLE = False

logger = logging.getLogger(__name__)

class GoogleCloudManager:
    """Google Cloud services manager with environment-based authentication"""
    
    def __init__(self):
        self._storage_client = None
        self._video_client = None
        self._vision_client = None
        self._credentials = None
        
    def _get_credentials(self) -> Optional[Any]:
        """Get Google Cloud credentials from file"""
        if not GOOGLE_CLOUD_AVAILABLE:
            logger.warning("Google Cloud packages not installed")
            return None
            
        if self._credentials:
            return self._credentials
            
        try:
            # Use service account file path
            if settings.google_credentials_path and os.path.exists(settings.google_credentials_path):
                try:
                    self._credentials = service_account.Credentials.from_service_account_file(
                        settings.google_credentials_path,
                        scopes=[
                            'https://www.googleapis.com/auth/cloud-platform',
                            'https://www.googleapis.com/auth/devstorage.read_write'
                        ]
                    )
                    logger.info("Using service account credentials from file")
                    return self._credentials
                except Exception as e:
                    logger.error(f"Error loading credentials from file: {e}")
            
            # Fallback to default credentials (for Google Cloud environments)
            try:
                from google.auth import default
                self._credentials, project = default()
                logger.info("Using default Google Cloud credentials")
                return self._credentials
            except Exception as e:
                logger.warning(f"No Google Cloud credentials found: {e}")
                
        except Exception as e:
            logger.error(f"Error getting Google Cloud credentials: {e}")
            
        return None
    
    def get_storage_client(self) -> Optional[Any]:
        """Get Google Cloud Storage client"""
        if not GOOGLE_CLOUD_AVAILABLE:
            logger.warning("Google Cloud Storage not available - packages not installed")
            return None
            
        if self._storage_client:
            return self._storage_client
            
        credentials = self._get_credentials()
        if not credentials:
            logger.warning("No Google Cloud credentials available for Storage")
            return None
            
        try:
            self._storage_client = storage.Client(
                credentials=credentials,
                project=settings.google_cloud_project_id
            )
            return self._storage_client
        except Exception as e:
            logger.error(f"Error creating Storage client: {e}")
            return None
    
    def get_video_intelligence_client(self) -> Optional[Any]:
        """Get Google Cloud Video Intelligence client"""
        if not GOOGLE_CLOUD_AVAILABLE:
            logger.warning("Google Cloud Video Intelligence not available - packages not installed")
            return None
            
        if self._video_client:
            return self._video_client
            
        credentials = self._get_credentials()
        if not credentials:
            logger.warning("No Google Cloud credentials available for Video Intelligence")
            return None
            
        try:
            self._video_client = videointelligence.VideoIntelligenceServiceClient(
                credentials=credentials
            )
            return self._video_client
        except Exception as e:
            logger.error(f"Error creating Video Intelligence client: {e}")
            return None
    
    def get_vision_client(self) -> Optional[Any]:
        """Get Google Cloud Vision client"""
        if not GOOGLE_CLOUD_AVAILABLE:
            logger.warning("Google Cloud Vision not available - packages not installed")
            return None
            
        if self._vision_client:
            return self._vision_client
            
        credentials = self._get_credentials()
        if not credentials:
            logger.warning("No Google Cloud credentials available for Vision")
            return None
            
        try:
            self._vision_client = vision.ImageAnnotatorClient(
                credentials=credentials
            )
            return self._vision_client
        except Exception as e:
            logger.error(f"Error creating Vision client: {e}")
            return None
    
    def upload_to_storage(self, file_path: str, blob_name: str, bucket_name: str = None) -> bool:
        """Upload file to Google Cloud Storage"""
        client = self.get_storage_client()
        if not client:
            return False
            
        bucket_name = bucket_name or settings.google_storage_bucket
        
        try:
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            with open(file_path, 'rb') as file_data:
                blob.upload_from_file(file_data)
                
            logger.info(f"File {file_path} uploaded to {bucket_name}/{blob_name}")
            return True
        except Exception as e:
            logger.error(f"Error uploading file to storage: {e}")
            return False
    
    def download_from_storage(self, blob_name: str, destination_path: str, bucket_name: str = None) -> bool:
        """Download file from Google Cloud Storage"""
        client = self.get_storage_client()
        if not client:
            return False
            
        bucket_name = bucket_name or settings.google_storage_bucket
        
        try:
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            blob.download_to_filename(destination_path)
            logger.info(f"File {blob_name} downloaded from {bucket_name} to {destination_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading file from storage: {e}")
            return False
    
    def analyze_video(self, video_path: str) -> Optional[Dict[str, Any]]:
        """Analyze video using Google Cloud Video Intelligence"""
        if not settings.enable_video_intelligence:
            logger.info("Video Intelligence is disabled")
            return None
            
        client = self.get_video_intelligence_client()
        if not client:
            return None
            
        try:
            with open(video_path, 'rb') as video_file:
                input_content = video_file.read()
            
            # Configure features for analysis
            features = [
                videointelligence.Feature.PERSON_DETECTION,
                videointelligence.Feature.OBJECT_TRACKING,
                videointelligence.Feature.FACE_DETECTION
            ]
            
            # Start the analysis
            operation = client.annotate_video(
                request={
                    "features": features,
                    "input_content": input_content,
                }
            )
            
            result = operation.result(timeout=300)  # 5 minutes timeout
            
            # Process results
            analysis_result = {
                'person_detections': [],
                'object_annotations': [],
                'face_detections': []
            }
            
            # Process person detection results
            if result.annotation_results[0].person_detection_annotations:
                for person in result.annotation_results[0].person_detection_annotations:
                    analysis_result['person_detections'].append({
                        'confidence': person.confidence,
                        'timestamps': [(track.start_time_offset.total_seconds(), 
                                      track.end_time_offset.total_seconds()) 
                                     for track in person.tracks]
                    })
            
            # Process object tracking results
            if result.annotation_results[0].object_annotations:
                for obj in result.annotation_results[0].object_annotations:
                    analysis_result['object_annotations'].append({
                        'entity': obj.entity.description,
                        'confidence': obj.confidence,
                        'track_id': obj.track_id
                    })
            
            logger.info(f"Video analysis completed for {video_path}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing video: {e}")
            return None
    
    def test_connection(self) -> Dict[str, bool]:
        """Test Google Cloud service connections"""
        results = {
            'storage': False,
            'video_intelligence': False,
            'vision': False
        }
        
        # Test Storage
        storage_client = self.get_storage_client()
        if storage_client:
            try:
                list(storage_client.list_buckets(max_results=1))
                results['storage'] = True
            except Exception as e:
                logger.error(f"Storage connection test failed: {e}")
        
        # Test Video Intelligence
        video_client = self.get_video_intelligence_client()
        if video_client and settings.enable_video_intelligence:
            try:
                # Just test that we can create the client
                results['video_intelligence'] = True
            except Exception as e:
                logger.error(f"Video Intelligence connection test failed: {e}")
        
        # Test Vision
        vision_client = self.get_vision_client()
        if vision_client:
            try:
                # Just test that we can create the client
                results['vision'] = True
            except Exception as e:
                logger.error(f"Vision connection test failed: {e}")
        
        return results

# Global instance
google_cloud = GoogleCloudManager()

# Export main functions for easy import
def get_storage_client():
    return google_cloud.get_storage_client()

def get_video_intelligence_client():
    return google_cloud.get_video_intelligence_client()

def get_vision_client():
    return google_cloud.get_vision_client()

def upload_to_storage(file_path: str, blob_name: str, bucket_name: str = None):
    return google_cloud.upload_to_storage(file_path, blob_name, bucket_name)

def download_from_storage(blob_name: str, destination_path: str, bucket_name: str = None):
    return google_cloud.download_from_storage(blob_name, destination_path, bucket_name)

def analyze_video(video_path: str):
    return google_cloud.analyze_video(video_path)

def test_google_cloud_connection():
    return google_cloud.test_connection()
