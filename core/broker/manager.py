import json
import os
from .factory import BrokerFactory
from core.audit import audit
from core.config import settings, SystemMode
from core.broker.token_manager import token_manager

class BrokerManager:
    """
    Handles single-broker configuration for Execution Authority.
    Risk enforcement is derived from actual broker fills.
    """
    
    CRED_PATH = "data/credentials.json"
    
    def __init__(self):
        # Default with NullBroker to prevent NoneType errors in Paper/Mock mode
        from .factory import BrokerFactory
        self.execution_broker = BrokerFactory.get_broker("NULL")
        self.data_broker = self.execution_broker
        self._load_and_init()
        
    def _load_and_init(self):
        # Default Template
        if not os.path.exists(self.CRED_PATH):
            template = {
                "MODE": "PAPER",
                "active_broker": "ZERODHA",
                "UPSTOX": {"api_key": "", "api_secret": ""},
                "DHAN": {"client_id": "", "access_token": ""},
                "ZERODHA": {"api_key": "", "access_token": "PASTE_ACCESS_TOKEN_HERE"},
                "DELTA": {"api_key": "", "api_secret": "", "testnet": True}
            }
            try:
                os.makedirs(os.path.dirname(self.CRED_PATH), exist_ok=True)
                with open(self.CRED_PATH, "w") as f:
                    json.dump(template, f, indent=4)
                audit.warning("Credentials template created in data/credentials.json")
            except Exception as e:
                audit.error(f"Failed to create credentials template: {e}")
            return

        try:
            with open(self.CRED_PATH, "r") as f:
                creds = json.load(f)
            
            # Override MODE from credentials.json if present
            mode_str = creds.get("MODE", "PAPER")
            if mode_str == "LIVE":
                settings.MODE = SystemMode.LIVE
            else:
                settings.MODE = SystemMode.PAPER
            
            broker_name = creds.get("active_broker", "ZERODHA")
            
            # Allow "KITE" or "ZERODHA" to resolve to the same thing if needed
            if broker_name == "KITE": 
                broker_name = "ZERODHA"

            # Get instance (with testnet support for Delta)
            testnet = False
            if broker_name == "DELTA":
                config = creds.get(broker_name, {})
                testnet = config.get("testnet", False)
            
            instance = BrokerFactory.get_broker(broker_name, testnet=testnet)
            
            # Auth
            config = creds.get(broker_name, {})
            
            # Safety: Don't auth if config is empty or placeholder in Production
            is_placeholder = False
            token = config.get("access_token")
            if broker_name == "ZERODHA" and token == "PASTE_ACCESS_TOKEN_HERE": is_placeholder = True
            if broker_name == "DHAN" and token == "PASTE_ACCESS_TOKEN_HERE": is_placeholder = True
            # Delta uses api_key instead of access_token
            if broker_name == "DELTA" and not config.get("api_key"): is_placeholder = True

            if settings.MODE == SystemMode.LIVE: 
                if is_placeholder:
                   audit.warning(f"Skipping Broker Auth: Template tokens detected for {broker_name}. Execution disabled.")
                elif instance.authenticate(config):
                    self.execution_broker = instance
                    self.data_broker = instance
                    # Register token with manager (use api_key for Delta)
                    token_to_register = config.get("api_key") if broker_name == "DELTA" else token
                    if token_to_register:
                        token_manager.register_token(broker_name, token_to_register)
                    audit.info(f"Execution Authority Active: {broker_name}")
                else:
                    audit.error(f"Failed to authenticate broker: {broker_name}")
            else:
                # In Paper mode, we still try to auth for Data/LTP fetching 
                # but we'll use a Mock if it fails (not implemented yet).
                if config.get("access_token") != "PASTE_ACCESS_TOKEN_HERE" and instance.authenticate(config):
                     self.execution_broker = instance
                     self.data_broker = instance
                     audit.info(f"Execution Authority Active: {broker_name} (Mode: {settings.MODE})")
                else:
                     audit.warning(f"Running without Broker Link (Paper Mode)")
                
        except Exception as e:
            audit.error(f"Broker System Error: {str(e)}")

    @property
    def broker_name(self) -> str:
        return self.execution_broker.__class__.__name__.replace("Broker", "").upper()

broker_manager = BrokerManager()
