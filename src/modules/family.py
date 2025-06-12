import os
import shutil
from pymongo import MongoClient
from bson import ObjectId
from config.settings import MONGO_DB_URI, MONGO_DB_NAME

client = None
db = None
owners_collection = None

def get_mongo_collections_for_family():
    global client, db, owners_collection
    if owners_collection is not None: # Already initialized
        return True
    if not MONGO_DB_URI:
        print("⚠️ MONGO_DB_URI not set. Skipping MongoDB initialization for family module.")
        return False
    try:
        if client is None: # Initialize client only if it hasn't been
            client = MongoClient(MONGO_DB_URI)
        client.admin.command('ping')
        print("✅ MongoDB connection successful for family module.")
        db = client[MONGO_DB_NAME]
        owners_collection = db["owners"]
        return True
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB (family module): {e}")
        # Reset so an attempt can be made again if called later
        client = None 
        db = None
        owners_collection = None
        return False

# Attempt to initialize when module is loaded
get_mongo_collections_for_family()

def add_family_member(owner_email, name, relation, image_path=None):
    if owners_collection is None:
        print("MongoDB owners collection not available. Attempting to reconnect...")
        if not get_mongo_collections_for_family() or owners_collection is None:
            print("Failed to connect/access MongoDB. Cannot add family member.")
            return False

    owner_query = {"email": owner_email}

    try:
        saved_image_path = None
        if image_path:
            if not os.path.exists(image_path):
                print(f"Warning: Image path does not exist: {image_path}")
            else:
                os.makedirs("faces", exist_ok=True)
                # Sanitize filename components
                safe_name = "".join(c if c.isalnum() else '_' for c in name)
                base_image_name = os.path.basename(image_path)
                safe_base_image_name = "".join(c if c.isalnum() or c in '.-' else '_' for c in base_image_name)
                saved_image_path = f"faces/{safe_name}_family_{safe_base_image_name}"
                shutil.copy2(image_path, saved_image_path)
                print(f"Family member {name} image reference: {saved_image_path}")
        
        family_member_data = {
            "_id": ObjectId(), # Unique ID for the family member within the array
            "name": name,
            "relation": relation,
            "image_reference": saved_image_path,
            # "cloud_person_id": None, # Placeholder for future integration with Video AI person ID
        }

        # Add the family member to the owner's "family" array
        # $push creates the array field if it does not exist.
        update_result = owners_collection.update_one(
            owner_query,
            {"$push": {"family": family_member_data}}
        )

        if update_result.matched_count == 0:
            print(f"Owner with email {owner_email} not found in MongoDB.")
            return False
        
        if update_result.modified_count > 0:
            print(f"Family member '{name}' added to owner '{owner_email}' in MongoDB.")
            return True
        else:
            # This case might occur if the document was matched but not modified.
            # For $push, this is unusual unless there's a very specific edge case or a problem with the update operation itself.
            # One possibility is if the 'family' field exists but is not an array, though $push should error then.
            print(f"Failed to add family member '{name}' for owner '{owner_email}'. Matched: {update_result.matched_count}, Modified: {update_result.modified_count}")
            # You could add more sophisticated checks here if needed, e.g., ensuring 'family' is an array.
            return False

    except Exception as e:
        print(f"Error adding family member to MongoDB: {e}")
        return False

# Example of how to list family members (can be expanded)
def list_family_members(owner_email):
    if owners_collection is None:
        if not get_mongo_collections_for_family() or owners_collection is None:
            print("MongoDB not available for listing family members.")
            return []
            
    owner = owners_collection.find_one({"email": owner_email}, {"family": 1}) # Project only the family field
    if owner and "family" in owner:
        return owner["family"]
    return []

# Example of how to remove a family member (can be expanded)
def remove_family_member(owner_email, family_member_id_str):
    if owners_collection is None:
        if not get_mongo_collections_for_family() or owners_collection is None:
            print("MongoDB not available for removing family member.")
            return False
    try:
        family_member_id = ObjectId(family_member_id_str)
        result = owners_collection.update_one(
            {"email": owner_email},
            {"$pull": {"family": {"_id": family_member_id}}}
        )
        if result.modified_count > 0:
            print(f"Family member with ID {family_member_id_str} removed for owner {owner_email}.")
            return True
        print(f"Family member with ID {family_member_id_str} not found or not removed for owner {owner_email}.")
        return False
    except Exception as e:
        print(f"Error removing family member: {e}")
        return False