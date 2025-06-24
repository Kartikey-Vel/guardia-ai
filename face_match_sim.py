#!/usr/bin/env python3
"""
Face Match Simulation Script for Guardia AI
CLI script to test embedding similarity on webcam input
"""
import cv2
import sys
import os
import time
import numpy as np

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from guardia_ai.detection.face_auth import FaceAuthenticator

class FaceMatchSimulator:
    def __init__(self):
        self.face_auth = FaceAuthenticator()
        print("🧪 Guardia AI - Face Match Simulation")
        print("=" * 50)
    
    def real_time_matching(self):
        """Real-time face matching with webcam"""
        print("\n🎥 Starting real-time face matching...")
        print("Press 'q' to quit")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Error: Could not access camera")
            return
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        last_match_time = 0
        match_cooldown = 1.0  # 1 second between matches
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Flip for mirror effect
            frame = cv2.flip(frame, 1)
            current_time = time.time()
            
            # Detect faces
            faces = self.face_auth.face_app.get(frame)
            
            for face in faces:
                bbox = face.bbox.astype(int)
                
                # Draw bounding box
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                
                # Try to match face (with cooldown)
                if current_time - last_match_time > match_cooldown:
                    user = self.face_auth.match_face(frame)
                    last_match_time = current_time
                    
                    if user:
                        # Recognized user - green box
                        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 3)
                        cv2.putText(frame, f"{user['label']}", (bbox[0], bbox[1]-30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(frame, f"Score: {user['score']:.3f}", (bbox[0], bbox[1]-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        print(f"✅ Matched: {user['label']} (Score: {user['score']:.3f})")
                    else:
                        # Unknown user - red box
                        cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 0, 255), 3)
                        cv2.putText(frame, "UNKNOWN", (bbox[0], bbox[1]-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        print("❌ Unknown face detected")
            
            # Add instructions
            cv2.putText(frame, "Face Match Simulation - Press 'q' to quit", (10, 450), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow('Face Match Simulation', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
    
    def batch_similarity_test(self):
        """Test similarity between multiple captures"""
        print("\n🔬 Batch Similarity Test")
        print("This will capture multiple face samples and compare their similarity")
        
        samples = []
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ Error: Could not access camera")
            return
        
        for i in range(3):
            print(f"\nCapturing sample {i+1}/3...")
            print("Position your face and press SPACE")
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame = cv2.flip(frame, 1)
                cv2.putText(frame, f"Sample {i+1}/3 - Press SPACE", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                faces = self.face_auth.face_app.get(frame)
                if faces:
                    bbox = faces[0].bbox.astype(int)
                    cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                
                cv2.imshow('Batch Test', frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord(' ') and faces:
                    embedding = self.face_auth.get_embedding(frame)
                    if embedding is not None:
                        samples.append(embedding)
                        print(f"✅ Sample {i+1} captured")
                        break
                elif key == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Calculate similarities
        if len(samples) == 3:
            print("\n📊 Similarity Results:")
            for i in range(len(samples)):
                for j in range(i+1, len(samples)):
                    sim = self.face_auth.cosine_similarity(samples[i], samples[j])
                    print(f"Sample {i+1} vs Sample {j+1}: {sim:.3f}")
    
    def benchmark_performance(self):
        """Benchmark face recognition performance"""
        print("\n⚡ Performance Benchmark")
        print("This will measure face detection and recognition speed")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Error: Could not access camera")
            return
        
        detection_times = []
        recognition_times = []
        
        for i in range(50):  # 50 frames
            ret, frame = cap.read()
            if not ret:
                break
            
            # Measure detection time
            start_time = time.time()
            faces = self.face_auth.face_app.get(frame)
            detection_time = time.time() - start_time
            detection_times.append(detection_time)
            
            # Measure recognition time (if face detected)
            if faces:
                start_time = time.time()
                user = self.face_auth.match_face(frame)
                recognition_time = time.time() - start_time
                recognition_times.append(recognition_time)
            
            if i % 10 == 0:
                print(f"Progress: {i+1}/50")
        
        cap.release()
        
        # Calculate statistics
        if detection_times:
            avg_detection = np.mean(detection_times) * 1000  # ms
            fps_detection = 1.0 / np.mean(detection_times)
            print(f"\n📈 Detection Performance:")
            print(f"Average detection time: {avg_detection:.2f}ms")
            print(f"Detection FPS: {fps_detection:.1f}")
        
        if recognition_times:
            avg_recognition = np.mean(recognition_times) * 1000  # ms
            fps_recognition = 1.0 / np.mean(recognition_times)
            print(f"\n🎯 Recognition Performance:")
            print(f"Average recognition time: {avg_recognition:.2f}ms")
            print(f"Recognition FPS: {fps_recognition:.1f}")
    
    def export_embeddings(self, output_file="face_embeddings.npz"):
        """Export all face embeddings for analysis"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(self.face_auth.db_path)
            c = conn.cursor()
            c.execute("SELECT label, embedding FROM users WHERE embedding IS NOT NULL")
            users = c.fetchall()
            conn.close()
            
            if not users:
                print("❌ No face embeddings found")
                return
            
            embeddings_dict = {}
            for label, emb_blob in users:
                embedding = np.frombuffer(emb_blob, dtype=np.float32)
                embeddings_dict[label] = embedding
            
            np.savez(output_file, **embeddings_dict)
            print(f"✅ Exported {len(embeddings_dict)} embeddings to {output_file}")
            
        except Exception as e:
            print(f"❌ Error exporting embeddings: {e}")

def main():
    simulator = FaceMatchSimulator()
    
    print("\n🎯 Face Match Simulation Options:")
    print("1. Real-time matching")
    print("2. Batch similarity test")
    print("3. Performance benchmark")
    print("4. Export embeddings")
    print("5. Exit")
    
    while True:
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            simulator.real_time_matching()
        elif choice == '2':
            simulator.batch_similarity_test()
        elif choice == '3':
            simulator.benchmark_performance()
        elif choice == '4':
            filename = input("Enter output filename (default: face_embeddings.npz): ").strip()
            if not filename:
                filename = "face_embeddings.npz"
            simulator.export_embeddings(filename)
        elif choice == '5':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1-5.")

if __name__ == "__main__":
    main()
