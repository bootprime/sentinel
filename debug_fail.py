import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from core.symbol_mapper import SymbolMapper
    import core.logger
    import core.audit
    
    # Patch logger/audit to verify calls (simple print)
    class MockLogger:
        def system(self, *args, **kwargs): print(f"LOG SYSTEM: {args}")
        def debug(self, *args, **kwargs): print(f"LOG DEBUG: {args}")
        def user(self, *args, **kwargs): print(f"LOG USER: {args}")
        
    class MockAudit:
        def warning(self, *args, **kwargs): print(f"AUDIT WARN: {args}")
        def error(self, *args, **kwargs): print(f"AUDIT ERROR: {args}")
        
    core.logger.logger = MockLogger()
    core.audit.audit = MockAudit()
    
    print("--- Starting Debug ---")
    
    # Test 1: Default Delta Product
    pid = SymbolMapper.to_delta("BTCUSD")
    print(f"BTCUSD -> {pid} (Expected: 27)")
    if pid != 27: print("FAIL Test 1")
    
    # Test 2: Add Product
    SymbolMapper.add_delta_product("TEST", 999)
    pid = SymbolMapper.to_delta("TEST")
    print(f"TEST -> {pid} (Expected: 999)")
    if pid != 999: print("FAIL Test 2")
    
    # Test 3: Load Products
    with open("temp_products.json", "w") as f:
        json.dump({"NEWCOIN": 123}, f)
    
    SymbolMapper.load_delta_products("temp_products.json")
    pid = SymbolMapper.to_delta("NEWCOIN")
    print(f"NEWCOIN -> {pid} (Expected: 123)")
    if pid != 123: print("FAIL Test 3")
    
    os.remove("temp_products.json")
    
    print("--- Debug Complete ---")

except Exception as e:
    print(f"EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
