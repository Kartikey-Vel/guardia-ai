"""
Face Authentication: Detection, Embedding, Matching
Optimized for low memory usage and speed.
"""
import numpy as np
import sqlite3
import gc

# Lazy import for heavy modules
def get_face_app():
    try:
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(160, 160))  # Lowered det_size for less RAM
        return app
    except ImportError:
        print("⚠️ InsightFace not available. Face recognition disabled.")
        return None

class FaceAuthenticator:
    def __init__(self, db_path="guardia_ai/storage/user_db.sqlite"):
        self.db_path = db_path
        self.face_app = None  # Lazy-load
        self._ensure_db()

    def _ensure_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT,
            pin TEXT,
            embedding BLOB
        )''')
        conn.commit()
        conn.close()

    def add_user(self, label, pin, face_img):
        emb = None
        if face_img is not None:
            emb = self.get_embedding(face_img)
            if emb is None:
                return False
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        emb_bytes = emb.tobytes() if emb is not None else None
        c.execute("INSERT INTO users (label, pin, embedding) VALUES (?, ?, ?)",
                  (label, pin, emb_bytes))
        conn.commit()
        conn.close()
        gc.collect()
        return True

    def verify_pin(self, pin):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT 1 FROM users WHERE pin=? LIMIT 1", (pin,))
        user = c.fetchone()
        conn.close()
        return user is not None

    def get_embedding(self, img):
        if self.face_app is None:
            self.face_app = get_face_app()
        if self.face_app is None:
            return None
        faces = self.face_app.get(img)
        if not faces:
            return None
        return faces[0].embedding

    def match_face(self, img, threshold=0.5):
        emb = self.get_embedding(img)
        if emb is None:
            return None
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, label, embedding FROM users")
        best_score = 0
        best_user = None
        for uid, label, emb_blob in c.fetchall():
            if emb_blob is None:
                continue
            db_emb = np.frombuffer(emb_blob, dtype=np.float32)
            score = np.dot(emb, db_emb) / (np.linalg.norm(emb) * np.linalg.norm(db_emb) + 1e-8)
            if score > best_score and score > threshold:
                best_score = score
                best_user = {"id": uid, "label": label, "score": float(score)}
        conn.close()
        gc.collect()
        return best_user

    @staticmethod
    def cosine_similarity(a, b):
        a = a / np.linalg.norm(a)
        b = b / np.linalg.norm(b)
        return np.dot(a, b)

    def get_all_users(self):
        """Get all registered users"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, label, pin, embedding FROM users")
        users = c.fetchall()
        conn.close()
        
        user_list = []
        for uid, label, pin, emb_blob in users:
            user_list.append({
                "id": uid,
                "label": label,
                "pin": pin,
                "has_face": emb_blob is not None
            })
        return user_list
    
    def delete_user(self, user_id):
        """Delete a user by ID"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id=?", (user_id,))
        deleted = c.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def update_user_pin(self, user_id, new_pin):
        """Update user's PIN"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE users SET pin=? WHERE id=?", (new_pin, user_id))
        updated = c.rowcount > 0
        conn.commit()
        conn.close()
        return updated
    
    def get_user_by_label(self, label):
        """Get user by label"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, label, pin, embedding FROM users WHERE label=?", (label,))
        user = c.fetchone()
        conn.close()
        
        if user:
            uid, label, pin, emb_blob = user
            return {
                "id": uid,
                "label": label,
                "pin": pin,
                "has_face": emb_blob is not None
            }
        return None
    
    def verify_user_credentials(self, label, pin):
        """Verify both label and PIN"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT id, label FROM users WHERE label=? AND pin=?", (label, pin))
        user = c.fetchone()
        conn.close()
        return user is not None
    
    def get_embedding_stats(self):
        """Get statistics about stored embeddings"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users WHERE embedding IS NOT NULL")
        users_with_faces = c.fetchone()[0]
        conn.close()
        
        return {
            "total_users": total_users,
            "users_with_faces": users_with_faces,
            "users_pin_only": total_users - users_with_faces
        }
    
    def export_to_json(self, filename=None):
        """Export user data to JSON file (embeddings as base64)"""
        import json
        import base64
        from datetime import datetime
        
        if filename is None:
            filename = f"guardia_ai_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        users = self.get_all_users()
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_users": len(users),
            "users": []
        }
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        for user in users:
            c.execute("SELECT embedding FROM users WHERE id=?", (user["id"],))
            result = c.fetchone()
            embedding_b64 = None
            
            if result and result[0]:
                embedding_b64 = base64.b64encode(result[0]).decode('utf-8')
            
            export_data["users"].append({
                "label": user["label"],
                "pin": user["pin"],
                "has_face": user["has_face"],
                "embedding_b64": embedding_b64
            })
        
        conn.close()
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filename
    
    def import_from_json(self, filename):
        """Import user data from JSON file"""
        import json
        import base64
        
        try:
            with open(filename, 'r') as f:
                import_data = json.load(f)
            
            imported_count = 0
            errors = []
            
            for user_data in import_data.get("users", []):
                try:
                    label = user_data["label"]
                    pin = user_data["pin"]
                    embedding_b64 = user_data.get("embedding_b64")
                    
                    # Check if user already exists
                    existing_user = self.get_user_by_label(label)
                    if existing_user:
                        errors.append(f"User '{label}' already exists, skipping")
                        continue
                    
                    # Decode embedding if present
                    embedding_blob = None
                    if embedding_b64:
                        embedding_blob = base64.b64decode(embedding_b64)
                    
                    # Insert user
                    conn = sqlite3.connect(self.db_path)
                    c = conn.cursor()
                    c.execute("INSERT INTO users (label, pin, embedding) VALUES (?, ?, ?)",
                              (label, pin, embedding_blob))
                    conn.commit()
                    conn.close()
                    
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Error importing user '{user_data.get('label', 'unknown')}': {e}")
            
            return {
                "imported_count": imported_count,
                "errors": errors,
                "total_in_file": len(import_data.get("users", []))
            }
            
        except Exception as e:
            return {
                "imported_count": 0,
                "errors": [f"Failed to read import file: {e}"],
                "total_in_file": 0
            }
