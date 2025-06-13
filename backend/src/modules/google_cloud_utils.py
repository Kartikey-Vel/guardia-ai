"""
Utilities for interacting with Google Cloud Video Intelligence API and Google Cloud Storage.
"""
import os
import sys
# Add parent directory to path to access config
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from google.cloud import videointelligence_v1p3beta1 as videointelligence
from google.cloud import storage
from config.settings import GCS_BUCKET_NAME

def get_video_client():
    """Initializes and returns a Video Intelligence Service Client.

    Ensures that the GOOGLE_APPLICATION_CREDENTIALS environment variable is set.
    """
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("ERROR: The GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Please set it to the path of your service account key JSON file.")
        return None
    
    try:
        client = videointelligence.VideoIntelligenceServiceClient()
        print("✅ Google Cloud Video Intelligence client initialized successfully.")
        return client
    except Exception as e:
        print(f"❌ Failed to initialize Google Cloud Video Intelligence client: {e}")
        return None

def get_storage_client():
    """Initializes and returns a Google Cloud Storage client."""
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        print("ERROR: The GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        return None
    
    try:
        client = storage.Client()
        print("✅ Google Cloud Storage client initialized successfully.")
        return client
    except Exception as e:
        print(f"❌ Failed to initialize Google Cloud Storage client: {e}")
        return None

def upload_video_to_gcs(local_video_path, gcs_blob_name=None, bucket_name=None):
    """
    Upload a local video file to Google Cloud Storage.
    
    Args:
        local_video_path (str): Path to the local video file
        gcs_blob_name (str): Name for the blob in GCS. If None, uses the local filename
        bucket_name (str): GCS bucket name. If None, uses GCS_BUCKET_NAME from settings
    
    Returns:
        str: GCS URI of the uploaded video, or None if upload failed
    """
    if not bucket_name:
        bucket_name = GCS_BUCKET_NAME
    
    if not bucket_name:
        print("❌ No GCS bucket name provided and GCS_BUCKET_NAME not set in settings")
        return None
    
    if not os.path.exists(local_video_path):
        print(f"❌ Local video file not found: {local_video_path}")
        return None
    
    if not gcs_blob_name:
        gcs_blob_name = f"surveillance_videos/{os.path.basename(local_video_path)}"
    
    try:
        client = get_storage_client()
        if not client:
            return None
        
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(gcs_blob_name)
        
        print(f"📤 Uploading {local_video_path} to gs://{bucket_name}/{gcs_blob_name}")
        
        # Upload the file
        blob.upload_from_filename(local_video_path)
        
        gcs_uri = f"gs://{bucket_name}/{gcs_blob_name}"
        print(f"✅ Video uploaded successfully to {gcs_uri}")
        
        return gcs_uri
        
    except Exception as e:
        print(f"❌ Error uploading video to GCS: {e}")
        return None

def analyze_video_from_gcs(gcs_uri, features, client=None):
    """Analyzes a video stored in Google Cloud Storage.

    Args:
        gcs_uri (str): The GCS URI of the video file (e.g., "gs://your-bucket/your-video.mp4").
        features (list): A list of videointelligence.Feature enum values 
                         (e.g., [videointelligence.Feature.LABEL_DETECTION]).
        client: An initialized VideoIntelligenceServiceClient. If None, one will be created.

    Returns:
        The API operation object for the analysis request.
    """
    if not client:
        client = get_video_client()
        if not client:
            return None

    print(f"📹 Analyzing video from GCS: {gcs_uri} with features: {features}")
    
    try:
        operation = client.annotate_video(
            request={
                "input_uri": gcs_uri,
                "features": features,
            }
        )
        print(f"⏳ Video analysis operation started: {operation.operation.name}")
        return operation
    except Exception as e:
        print(f"❌ Error starting video analysis for {gcs_uri}: {e}")
        return None

def get_analysis_results(operation_name, client=None):
    """Retrieves the results of a completed video analysis operation.

    Args:
        operation_name (str): The name of the operation.
        client: An initialized VideoIntelligenceServiceClient. If None, one will be created.
    
    Returns:
        The annotation results or None if an error occurs or operation not finished.
    """
    if not client:
        client = get_video_client()
        if not client:
            return None
            
    # This is a simplified way to get results. For long-running operations,
    # you'd typically poll operation.done() or use operation.result(timeout=...).
    # For this example, we assume the operation might complete quickly or
    # this function is called after confirming completion.
    # A more robust implementation would handle polling.
    try:
        print(f"🔄 Fetching results for operation: {operation_name} (this might take a while)...")
        # operation = client.long_running_grpc_operation(operation_name) # This is not the correct way
        # For now, let's assume the user will handle the operation object directly
        # and call .result() on it. This function is more of a placeholder.
        # A proper implementation would involve `operation.result()` or polling.
        print("⚠️  Note: Result retrieval needs to be handled via the operation object returned by analyze_video_from_gcs.")
        print("Call .result() on that operation object once it's done.")
        # Example:
        # results = operation.result(timeout=180) # timeout in seconds
        # return results
        return None # Placeholder
    except Exception as e:
        print(f"❌ Error fetching analysis results for {operation_name}: {e}")
        return None

# --- Placeholder functions for specific detections ---

def detect_unauthorized_access(annotation_results):
    """Parses annotation results to detect unauthorized access.
    This is a placeholder and needs to be implemented based on how
    you define unauthorized access (e.g., person detection + comparison with known faces/persons
    if using Person Detection and a separate person database).
    """
    print("🔍 Analyzing for unauthorized access (placeholder)...")
    # Example: Look for person detection annotations
    # for result in annotation_results.annotation_results:
    #     for person_annotation in result.person_detection_annotations:
    #         # Logic to determine if the person is unauthorized
    #         pass
    return [] # List of detected unauthorized access events

def detect_burglary(annotation_results):
    """Parses annotation results to detect signs of burglary.
    (e.g., specific objects, broken windows - depends on labels/objects detected)
    """
    print("🔍 Analyzing for burglary (placeholder)...")
    # Example: Look for relevant labels or object tracking
    # for result in annotation_results.annotation_results:
    #     for label_annotation in result.segment_label_annotations:
    #         if label_annotation.entity.description in ["crowbar", "broken glass"]:
    #             # Add to burglary events
    #             pass
    return [] # List of detected burglary events

def detect_fire(annotation_results):
    """Parses annotation results to detect fire or smoke.
    """
    print("🔍 Analyzing for fire (placeholder)...")
    fire_events = []
    if not annotation_results or not annotation_results.annotation_results:
        return fire_events

    for result in annotation_results.annotation_results:
        # Check label annotations
        for label_annotation in result.segment_label_annotations:
            if label_annotation.entity.description.lower() in ["fire", "smoke", "flame"]:
                for segment in label_annotation.segments:
                    fire_events.append({
                        "description": label_annotation.entity.description,
                        "start_time": segment.segment.start_time_offset.total_seconds(),
                        "end_time": segment.segment.end_time_offset.total_seconds(),
                        "confidence": label_annotation.entity.confidence # If available and relevant
                    })
        # Check object tracking annotations (if that feature was used)
        for object_annotation in result.object_annotations:
            if object_annotation.entity.description.lower() in ["fire", "smoke", "flame"]:
                 fire_events.append({
                        "description": object_annotation.entity.description,
                        "start_time": object_annotation.segment.start_time_offset.total_seconds(),
                        "end_time": object_annotation.segment.end_time_offset.total_seconds(),
                        "confidence": object_annotation.confidence
                    })
    if fire_events:
        print(f"🔥 Fire/smoke detected: {fire_events}")
    return fire_events

if __name__ == '__main__':
    # This is for testing the module directly.
    # You'll need to have a video in GCS and GOOGLE_APPLICATION_CREDENTIALS set.
    print("Testing Google Cloud Utils...")
    
    # 1. Initialize client
    test_client = get_video_client()
    if not test_client:
        print("Exiting test due to client initialization failure.")
        exit()

    # 2. Specify GCS URI and features
    # Replace with your actual GCS URI
    test_gcs_uri = "gs://your-bucket-name/your-video-file.mp4" 
    # Example features:
    test_features = [
        videointelligence.Feature.LABEL_DETECTION,
        videointelligence.Feature.OBJECT_TRACKING,
        videointelligence.Feature.PERSON_DETECTION,
        videointelligence.Feature.EXPLICIT_CONTENT_DETECTION
    ]

    print("\n--- Simulating Analysis (make sure GCS URI is valid if you run this) ---")
    # Check if the GCS URI is a placeholder before trying to analyze
    if "your-bucket-name" in test_gcs_uri:
        print(f"SKIPPING analysis: Please replace placeholder GCS URI '{test_gcs_uri}' with a real one.")
    else:
        operation = analyze_video_from_gcs(test_gcs_uri, test_features, client=test_client)
        if operation:
            print("Operation started. In a real application, you would wait for it to complete.")
            print("Example: results = operation.result(timeout=300) # Wait up to 5 minutes")
            # try:
            #     # This will block until the operation is complete or timeout
            #     results = operation.result(timeout=300) 
            #     print("✅ Analysis completed.")
            #     # print(f"Results: {results}") # This can be very verbose
                
            #     # Test parsing functions
            #     fire_detected = detect_fire(results)
            #     print(f"Fire events from test: {fire_detected}")
                
            #     # Add calls to other detection functions here
            #     # burglary_detected = detect_burglary(results)
            #     # print(f"Burglary events from test: {burglary_detected}")
                
            #     # unauthorized_access_detected = detect_unauthorized_access(results)
            #     # print(f"Unauthorized access events from test: {unauthorized_access_detected}")

            # except Exception as e:
            #     print(f"❌ Error during result retrieval or parsing: {e}")
        else:
            print("❌ Analysis operation failed to start.")

    print("\nTest script finished.")
