"""
Unit tests for Delta Exchange Broker
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.broker.delta import DeltaBroker


class TestDeltaBroker:
    """Test Delta Exchange broker implementation"""
    
    def test_init_production(self):
        """Test initialization in production mode"""
        broker = DeltaBroker(testnet=False)
        assert broker.base_url == "https://api.delta.exchange"
        assert broker.api_key is None
        assert broker.api_secret is None
    
    def test_init_testnet(self):
        """Test initialization in testnet mode"""
        broker = DeltaBroker(testnet=True)
        assert broker.base_url == "https://testnet-api.delta.exchange"
    
    def test_generate_signature(self):
        """Test HMAC signature generation"""
        broker = DeltaBroker()
        broker.api_secret = "test_secret"
        
        signature, timestamp = broker._generate_signature("GET", "/v2/profile", "")
        
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex digest length
        assert isinstance(timestamp, str)
        assert timestamp.isdigit()
    
    @patch('core.broker.delta.requests.Session.get')
    def test_authenticate_success(self, mock_get):
        """Test successful authentication"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "user_id": 12345,
                "email": "test@example.com"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        broker = DeltaBroker()
        credentials = {
            "api_key": "test_key",
            "api_secret": "test_secret"
        }
        
        result = broker.authenticate(credentials)
        
        assert result is True
        assert broker.api_key == "test_key"
        assert broker.api_secret == "test_secret"
    
    @patch('core.broker.delta.requests.Session.get')
    def test_authenticate_failure(self, mock_get):
        """Test failed authentication"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": False,
            "error": "Invalid credentials"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        broker = DeltaBroker()
        credentials = {
            "api_key": "bad_key",
            "api_secret": "bad_secret"
        }
        
        result = broker.authenticate(credentials)
        
        assert result is False
    
    def test_authenticate_missing_credentials(self):
        """Test authentication with missing credentials"""
        broker = DeltaBroker()
        
        result = broker.authenticate({"api_key": "test"})  # Missing api_secret
        assert result is False
        
        result = broker.authenticate({"api_secret": "test"})  # Missing api_key
        assert result is False
    
    @patch('core.broker.delta.requests.Session.post')
    def test_place_order_market(self, mock_post):
        """Test placing a market order"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "id": 123456,
                "state": "open"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        broker = DeltaBroker()
        broker.api_key = "test_key"
        broker.api_secret = "test_secret"
        broker._get_product_id = Mock(return_value=27)  # Mock product ID
        
        order_params = {
            "symbol": "BTCUSD",
            "qty": 10,
            "type": "BUY",
            "order_type": "MARKET"
        }
        
        result = broker.place_order(order_params)
        
        assert result["status"] == "success"
        assert result["order_id"] == "123456"
    
    @patch('core.broker.delta.requests.Session.post')
    def test_place_order_stop_loss(self, mock_post):
        """Test placing a stop loss order"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "id": 123457,
                "state": "open"
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        broker = DeltaBroker()
        broker.api_key = "test_key"
        broker.api_secret = "test_secret"
        broker._get_product_id = Mock(return_value=27)
        
        order_params = {
            "symbol": "BTCUSD",
            "qty": 10,
            "type": "SELL",
            "order_type": "SL",
            "trigger_price": 50000.0
        }
        
        result = broker.place_order(order_params)
        
        assert result["status"] == "success"
    
    @patch('core.broker.delta.requests.Session.get')
    def test_get_order_status_complete(self, mock_get):
        """Test getting status of completed order"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "id": 123456,
                "state": "closed",
                "average_fill_price": 50000.0,
                "size": 10
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        broker = DeltaBroker()
        broker.api_key = "test_key"
        broker.api_secret = "test_secret"
        
        result = broker.get_order_status("123456")
        
        assert result["status"] == "COMPLETE"
        assert result["fill_price"] == 50000.0
        assert result["fill_qty"] == 10
    
    @patch('core.broker.delta.requests.Session.get')
    def test_get_order_status_partial(self, mock_get):
        """Test getting status of partially filled order"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "id": 123456,
                "state": "open",
                "average_fill_price": 50000.0,
                "size": 10,
                "filled_size": 5
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        broker = DeltaBroker()
        broker.api_key = "test_key"
        broker.api_secret = "test_secret"
        
        result = broker.get_order_status("123456")
        
        assert result["status"] == "PARTIAL"
        assert result["fill_qty"] == 5
    
    def test_get_product_id(self):
        """Test symbol to product_id mapping"""
        broker = DeltaBroker()
        
        assert broker._get_product_id("BTCUSD") == 27
        assert broker._get_product_id("ETHUSD") == 28
        assert broker._get_product_id("UNKNOWN") is None
    
    @patch('core.broker.delta.requests.Session.delete')
    def test_cancel_order(self, mock_delete):
        """Test cancelling an order"""
        mock_response = Mock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response
        
        broker = DeltaBroker()
        broker.api_key = "test_key"
        broker.api_secret = "test_secret"
        
        result = broker.cancel_order("123456")
        
        assert result is True
    
    @patch('core.broker.delta.requests.Session.get')
    def test_get_ltp(self, mock_get):
        """Test getting last traded price"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "result": {
                "close": 50000.0
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        broker = DeltaBroker()
        broker.api_key = "test_key"
        broker.api_secret = "test_secret"
        broker._get_product_id = Mock(return_value=27)
        
        ltp = broker.get_ltp("BTCUSD")
        
        assert ltp == 50000.0
