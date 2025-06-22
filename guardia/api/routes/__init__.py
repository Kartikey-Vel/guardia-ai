"""
API routes package for Guardia AI Enhanced System

This package contains all API route modules for:
- Authentication and authorization
- User and family management  
- Surveillance operations
- Alert management
- System administration
"""

# Import route modules conditionally to handle missing dependencies gracefully
try:
    from . import auth
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False

try:
    from . import users
    USERS_AVAILABLE = True
except ImportError:
    USERS_AVAILABLE = False

try:
    from . import surveillance
    SURVEILLANCE_AVAILABLE = True
except ImportError:
    SURVEILLANCE_AVAILABLE = False

try:
    from . import alerts
    ALERTS_AVAILABLE = True
except ImportError:
    ALERTS_AVAILABLE = False

try:
    from . import system
    SYSTEM_AVAILABLE = True
except ImportError:
    SYSTEM_AVAILABLE = False

__all__ = []

if AUTH_AVAILABLE:
    __all__.append('auth')
if USERS_AVAILABLE:
    __all__.append('users')
if SURVEILLANCE_AVAILABLE:
    __all__.append('surveillance')
if ALERTS_AVAILABLE:
    __all__.append('alerts')
if SYSTEM_AVAILABLE:
    __all__.append('system')
