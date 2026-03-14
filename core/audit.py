from core.logger import logger

# Backward Compatibility Alias
# This allows existing code using 'from core.audit import audit' to work 
# while getting the benefits of the new logger structure (via the shim methods).
audit = logger
