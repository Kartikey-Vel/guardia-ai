#!/usr/bin/env python3
"""
Guardia AI Enhanced System - Configuration Validator
Validates environment configuration and credentials
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from pydantic import ValidationError

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from guardia.config.settings import Settings, get_settings
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install dependencies: pip install -r requirements.txt")
    sys.exit(1)

class ConfigValidator:
    """Configuration validation and reporting"""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        
    def validate_environment_file(self, env_file: str = ".env") -> bool:
        """Validate environment file exists and loads"""
        env_path = Path(env_file)
        
        if not env_path.exists():
            self.errors.append(f"Environment file '{env_file}' not found")
            return False
            
        try:
            load_dotenv(env_path)
            self.info.append(f"✅ Environment file '{env_file}' loaded successfully")
            return True
        except Exception as e:
            self.errors.append(f"Failed to load '{env_file}': {e}")
            return False
    
    def validate_settings(self) -> bool:
        """Validate Pydantic settings"""
        try:
            settings = get_settings()
            self.info.append("✅ Pydantic settings validation passed")
            return True
        except ValidationError as e:
            self.errors.append(f"Settings validation failed: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected settings error: {e}")
            return False
    
    def validate_mongodb_credentials(self, settings: Settings) -> bool:
        """Validate MongoDB connection string"""
        if not settings.mongodb_url:
            self.errors.append("MongoDB URL is required")
            return False
            
        if "mongodb://" not in settings.mongodb_url and "mongodb+srv://" not in settings.mongodb_url:
            self.errors.append("Invalid MongoDB URL format")
            return False
            
        if "localhost" in settings.mongodb_url and settings.environment == "production":
            self.warnings.append("Using localhost MongoDB in production")
            
        self.info.append("✅ MongoDB credentials configured")
        return True
    
    def validate_google_cloud_credentials(self, settings: Settings) -> bool:
        """Validate Google Cloud credentials"""
        if not settings.google_credentials_path:
            self.warnings.append("Google Cloud credentials path not set")
            return False
            
        creds_path = Path(settings.google_credentials_path)
        if not creds_path.exists():
            self.errors.append(f"Google credentials file not found: {settings.google_credentials_path}")
            return False
            
        try:
            with open(creds_path, 'r') as f:
                creds = json.load(f)
                
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in creds]
            
            if missing_fields:
                self.errors.append(f"Google credentials missing fields: {missing_fields}")
                return False
                
            if creds.get('type') != 'service_account':
                self.warnings.append("Google credentials are not service account type")
                
            self.info.append("✅ Google Cloud credentials configured")
            return True
            
        except json.JSONDecodeError:
            self.errors.append("Google credentials file is not valid JSON")
            return False
        except Exception as e:
            self.errors.append(f"Error reading Google credentials: {e}")
            return False
    
    def validate_security_settings(self, settings: Settings) -> bool:
        """Validate security configuration"""
        if not settings.secret_key:
            self.errors.append("SECRET_KEY is required")
            return False
            
        if len(settings.secret_key) < 32:
            self.warnings.append("SECRET_KEY should be at least 32 characters")
            
        if "dev" in settings.secret_key.lower() and settings.environment == "production":
            self.errors.append("Using development SECRET_KEY in production")
            return False
            
        if settings.debug and settings.environment == "production":
            self.warnings.append("Debug mode enabled in production")
            
        self.info.append("✅ Security settings configured")
        return True
    
    def validate_notification_settings(self, settings: Settings) -> bool:
        """Validate notification configuration"""
        issues = False
        
        # Email notifications
        if settings.enable_email_notifications:
            if not all([settings.smtp_host, settings.smtp_username, settings.smtp_password]):
                self.errors.append("Email notifications enabled but SMTP credentials incomplete")
                issues = True
            else:
                self.info.append("✅ Email notifications configured")
        
        # SMS notifications
        if settings.enable_sms_notifications:
            if not all([settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from_number]):
                self.errors.append("SMS notifications enabled but Twilio credentials incomplete")
                issues = True
            else:
                self.info.append("✅ SMS notifications configured")
        
        if not settings.enable_email_notifications and not settings.enable_sms_notifications:
            self.warnings.append("No notification services enabled")
            
        return not issues
    
    def validate_storage_paths(self, settings: Settings) -> bool:
        """Validate storage directory configuration"""
        storage_paths = [
            settings.media_storage_path,
            settings.images_path,
            settings.videos_path,
            settings.faces_path,
            settings.logs_path
        ]
        
        for path in storage_paths:
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.errors.append(f"Cannot create storage directory '{path}': {e}")
                return False
                
        self.info.append("✅ Storage paths configured and accessible")
        return True
    
    def validate_camera_settings(self, settings: Settings) -> bool:
        """Validate camera configuration"""
        if not settings.camera_sources:
            self.warnings.append("No camera sources configured")
            return False
            
        sources = settings.camera_sources.split(',')
        for source in sources:
            source = source.strip()
            if source.isdigit():
                self.info.append(f"USB camera configured: {source}")
            elif source.startswith(('http://', 'https://', 'rtsp://')):
                self.info.append(f"Network camera configured: {source}")
            else:
                self.warnings.append(f"Unknown camera source format: {source}")
                
        self.info.append("✅ Camera sources configured")
        return True
    
    def validate_redis_settings(self, settings: Settings) -> bool:
        """Validate Redis configuration"""
        if settings.redis_host == "localhost" and settings.environment == "production":
            self.warnings.append("Using localhost Redis in production")
            
        self.info.append("✅ Redis settings configured")
        return True
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report"""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "summary": {
                "total_errors": len(self.errors),
                "total_warnings": len(self.warnings),
                "total_info": len(self.info),
                "status": "FAILED" if self.errors else "PASSED" if not self.warnings else "PASSED_WITH_WARNINGS"
            }
        }
    
    def print_report(self):
        """Print colored validation report"""
        print("🔍 Guardia AI Configuration Validation Report")
        print("=" * 50)
        
        # Errors
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"   • {error}")
        
        # Warnings
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        # Info
        if self.info:
            print("\n✅ CONFIGURED:")
            for info in self.info:
                print(f"   • {info}")
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"   • Errors: {len(self.errors)}")
        print(f"   • Warnings: {len(self.warnings)}")
        print(f"   • Configured: {len(self.info)}")
        
        if self.errors:
            print(f"\n❌ Status: CONFIGURATION FAILED")
            print("Please fix the errors above before running the system.")
        elif self.warnings:
            print(f"\n⚠️  Status: CONFIGURATION PASSED WITH WARNINGS")
            print("System can run but consider addressing warnings.")
        else:
            print(f"\n✅ Status: CONFIGURATION VALIDATED")
            print("All settings are properly configured!")

def main():
    """Main validation function"""
    validator = ConfigValidator()
    
    print("🔍 Validating Guardia AI Configuration...")
    print("=" * 50)
    
    # Load environment
    if not validator.validate_environment_file():
        validator.print_report()
        return False
    
    # Validate settings
    if not validator.validate_settings():
        validator.print_report()
        return False
    
    try:
        settings = get_settings()
    except Exception as e:
        validator.errors.append(f"Cannot load settings: {e}")
        validator.print_report()
        return False
    
    # Run all validations
    validations = [
        validator.validate_mongodb_credentials(settings),
        validator.validate_google_cloud_credentials(settings),
        validator.validate_security_settings(settings),
        validator.validate_notification_settings(settings),
        validator.validate_storage_paths(settings),
        validator.validate_camera_settings(settings),
        validator.validate_redis_settings(settings)
    ]
    
    # Print report
    validator.print_report()
    
    # Return overall status
    return len(validator.errors) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
