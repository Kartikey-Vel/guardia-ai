#!/usr/bin/env python3
"""
Guardia AI Enhanced System - Main Startup Script

This script initializes and starts the enhanced Guardia AI surveillance system.
It handles:
- Environment configuration
- Dependency checking
- Database initialization
- Service startup
- Error handling and logging
"""

import asyncio
import sys
import logging
import signal
import argparse
from pathlib import Path
from typing import Optional

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from guardia.config.settings import get_settings
    from guardia.utils.logger import setup_logging
    from guardia.db.connection import startup_event, shutdown_event
    from guardia.api.main import create_app
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements_enhanced.txt")
    IMPORTS_AVAILABLE = False

class GuardiaAIServer:
    """Main server class for Guardia AI Enhanced System"""
    
    def __init__(self):
        self.settings = None
        self.app = None
        self.logger = None
        self.running = False
        
    async def initialize(self):
        """Initialize the system components"""
        try:
            if not IMPORTS_AVAILABLE:
                raise RuntimeError("Required modules not available")
            
            # Load settings
            self.settings = get_settings()
            
            # Setup logging
            loggers = setup_logging(
                log_level=self.settings.log_level,
                log_directory=self.settings.log_directory,
                enable_console=True,
                enable_json=False,
                enable_rotation=True
            )
            self.logger = loggers["app"]
            
            self.logger.info("Starting Guardia AI Enhanced System...")
            self.logger.info(f"Version: 2.0.0")
            self.logger.info(f"Environment: {'Development' if self.settings.debug else 'Production'}")
            
            # Check dependencies
            await self._check_dependencies()
            
            # Initialize database
            self.logger.info("Initializing database connection...")
            await startup_event()
            
            # Create FastAPI app
            self.logger.info("Creating FastAPI application...")
            self.app = create_app()
            
            self.logger.info("System initialization completed successfully")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize system: {str(e)}")
            else:
                print(f"Failed to initialize system: {str(e)}")
            raise
    
    async def _check_dependencies(self):
        """Check if all required dependencies are available"""
        missing_deps = []
        
        # Check FastAPI
        try:
            import fastapi
            import uvicorn
        except ImportError:
            missing_deps.append("fastapi, uvicorn")
        
        # Check database dependencies
        try:
            import motor
            import pymongo
        except ImportError:
            missing_deps.append("motor, pymongo")
        
        # Check AI/ML dependencies (optional but recommended)
        try:
            import cv2
        except ImportError:
            self.logger.warning("OpenCV not available - some camera features may be limited")
        
        try:
            import face_recognition
        except ImportError:
            self.logger.warning("face_recognition not available - face detection will use alternatives")
        
        try:
            import mediapipe
        except ImportError:
            self.logger.warning("MediaPipe not available - some detection features may be limited")
        
        if missing_deps:
            raise RuntimeError(f"Missing required dependencies: {', '.join(missing_deps)}")
        
        self.logger.info("All required dependencies are available")
    
    async def start_server(self, host: str = None, port: int = None):
        """Start the web server"""
        try:
            if not self.app:
                raise RuntimeError("Application not initialized")
            
            # Use provided host/port or fall back to settings
            host = host or self.settings.api_host
            port = port or self.settings.api_port
            
            self.logger.info(f"Starting server on {host}:{port}")
            
            # Check if uvicorn is available
            try:
                import uvicorn
                
                # Configure uvicorn
                config = uvicorn.Config(
                    app=self.app,
                    host=host,
                    port=port,
                    log_level="info",
                    access_log=True,
                    reload=self.settings.debug
                )
                
                server = uvicorn.Server(config)
                self.running = True
                
                # Start server
                await server.serve()
                
            except ImportError:
                self.logger.error("uvicorn not available - cannot start web server")
                raise RuntimeError("uvicorn not available")
                
        except Exception as e:
            self.logger.error(f"Failed to start server: {str(e)}")
            raise
    
    async def shutdown(self):
        """Graceful shutdown of the system"""
        try:
            self.logger.info("Shutting down Guardia AI Enhanced System...")
            self.running = False
            
            # Shutdown database connections
            await shutdown_event()
            
            self.logger.info("System shutdown completed")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during shutdown: {str(e)}")
            else:
                print(f"Error during shutdown: {str(e)}")

# Global server instance for signal handling
server_instance: Optional[GuardiaAIServer] = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down gracefully...")
    if server_instance:
        # Create new event loop for shutdown if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(server_instance.shutdown())
    sys.exit(0)

async def main():
    """Main application entry point"""
    global server_instance
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Guardia AI Enhanced System")
    parser.add_argument("--host", default=None, help="Host address to bind to")
    parser.add_argument("--port", type=int, default=None, help="Port to bind to")
    parser.add_argument("--config", default=None, help="Configuration file path")
    parser.add_argument("--log-level", default=None, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       help="Log level override")
    parser.add_argument("--dev", action="store_true", help="Enable development mode")
    
    args = parser.parse_args()
    
    try:
        # Create server instance
        server_instance = GuardiaAIServer()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initialize system
        await server_instance.initialize()
        
        # Override settings if specified
        if args.log_level:
            server_instance.settings.log_level = args.log_level
        if args.dev:
            server_instance.settings.debug = True
        
        # Start server
        await server_instance.start_server(host=args.host, port=args.port)
        
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        if server_instance:
            await server_instance.shutdown()

def run_server():
    """Synchronous wrapper for running the server"""
    if not IMPORTS_AVAILABLE:
        print("ERROR: Required dependencies not available")
        print("Please install dependencies: pip install -r requirements_enhanced.txt")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_server()
