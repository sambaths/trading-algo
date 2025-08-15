import os
from typing import Dict, Any, Optional, List

class BrokerBase:
    """
    Minimal base class for brokers.
    Handles authentication and lists available functions.
    """
    def __init__(self):
        self.authenticated = False
        self.access_token = None
        self.env = os.environ

    def authenticate(self) -> Optional[str]:
        """
        Authenticate with the broker. To be implemented by subclasses.
        Returns access token if successful.
        """
        raise NotImplementedError("Subclasses must implement authenticate()")

    def list_functions(self) -> List[str]:
        """
        List available public methods (excluding private and base methods).
        """
        base_methods = set(dir(BrokerBase))
        all_methods = set(dir(self))
        public_methods = [m for m in all_methods - base_methods if not m.startswith('_')]
        return sorted(public_methods) 