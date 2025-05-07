"""
Fix for the 'local variable strict_encode referenced before assignment' error.
This script ensures the strict_encode function is properly defined in all scopes.
"""
import sys
import inspect
import types
import logging
import re
import builtins

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the strict_encode function
def strict_encode(n, instructions):
    """
    Apply a series of encoding transformations to a value n based on the provided instructions.
    This implementation avoids using eval() for better security.
    
    Args:
        n (int): The numeric value to encode
        instructions (str): A string containing semicolon-separated encoding instructions
    
    Returns:
        list: A list of encoded values after applying each instruction
    """
    logger.debug(f"strict_encode called with n={n}, instructions='{instructions}'")
    
    if not isinstance(n, int):
        try:
            n = int(n)
        except (ValueError, TypeError):
            raise ValueError(f"Input 'n' must be an integer, got {type(n)}")
    
    operations = instructions.split(';')
    results = []
    
    for op in operations:
        op = op.strip()
        result = apply_operation(n, op)
        results.append(result)
    
    return results

def apply_operation(n, operation):
    """
    Apply a single encoding operation to the value n.
    
    Args:
        n (int): The value to encode
        operation (str): The operation to apply
    
    Returns:
        int: The result of applying the operation
    """
    # Addition with modulo: (n + X) % 256
    addition_match = re.match(r'$$n\s*\+\s*(\d+)$$\s*%\s*256', operation)
    if addition_match:
        return (n + int(addition_match.group(1))) % 256
    
    # Subtraction with modulo: (n - X + 256) % 256
    subtraction_match = re.match(r'$$n\s*\-\s*(\d+)\s*\+\s*256$$\s*%\s*256', operation)
    if subtraction_match:
        return (n - int(subtraction_match.group(1)) + 256) % 256
    
    # Bitwise XOR: n ^ X
    xor_match = re.match(r'n\s*\^\s*(\d+)', operation)
    if xor_match:
        return n ^ int(xor_match.group(1))
    
    # Bitwise NOT: ~n & 255
    if operation == "~n & 255":
        return ~n & 255
    
    # Bit shifting: (n << 4 | (n & 0xFF) >> 4) & 255
    if operation == "(n << 4 | (n & 0xFF) >> 4) & 255":
        return ((n << 4) | ((n & 0xFF) >> 4)) & 255
    
    # If we get here, none of our patterns matched
    # Let's try to handle the operation based on the operators it contains
    
    # For operations like (n + X) % 256 or (n - X + 256) % 256
    if "%" in operation and "256" in operation:
        # Extract the expression inside the parentheses
        inner_expr = operation.split("%")[0].strip()
        if inner_expr.startswith("(") and inner_expr.endswith(")"):
            inner_expr = inner_expr[1:-1].strip()
        
        if "+" in inner_expr and "-" not in inner_expr:
            # Addition: (n + X) % 256
            parts = inner_expr.split("+")
            if parts[0].strip() == "n":
                value = int(parts[1].strip())
                return (n + value) % 256
        
        elif "-" in inner_expr and "+" in inner_expr:
            # Subtraction with wrap: (n - X + 256) % 256
            parts = inner_expr.split("-")
            if parts[0].strip() == "n":
                sub_parts = parts[1].split("+")
                value = int(sub_parts[0].strip())
                return (n - value + 256) % 256
        
        elif "-" in inner_expr and "+" not in inner_expr:
            # Simple subtraction: (n - X) % 256
            parts = inner_expr.split("-")
            if parts[0].strip() == "n":
                value = int(parts[1].strip())
                return (n - value) % 256
    
    # For operations like n ^ X
    if "^" in operation and "n" in operation:
        parts = operation.split("^")
        if parts[0].strip() == "n":
            value = int(parts[1].strip())
            return n ^ value
    
    # If we still can't handle it, raise an error
    raise ValueError(f"Unsupported operation: {operation}")

def fix_local_variable_issue():
    """
    Fix the 'local variable strict_encode referenced before assignment' error.
    This function ensures the strict_encode function is properly defined in all scopes.
    """
    try:
        # 1. Add to builtins
        builtins.strict_encode = strict_encode
        logger.info("Added strict_encode to builtins")
        
        # 2. Import anipy_api modules
        import anipy_api
        
        # 3. Add to the anipy_api package
        anipy_api.strict_encode = strict_encode
        logger.info("Added strict_encode to anipy_api package")
        
        # 4. Add to all existing anipy_api modules
        for module_name in list(sys.modules.keys()):
            if module_name.startswith('anipy_api'):
                module = sys.modules[module_name]
                if not hasattr(module, 'strict_encode'):
                    setattr(module, 'strict_encode', strict_encode)
                    logger.info(f"Added strict_encode to module: {module_name}")
        
        # 5. Add to all classes in anipy_api modules
        for module_name in list(sys.modules.keys()):
            if module_name.startswith('anipy_api'):
                module = sys.modules[module_name]
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and obj.__module__.startswith('anipy_api'):
                        if not hasattr(obj, 'strict_encode'):
                            setattr(obj, 'strict_encode', staticmethod(strict_encode))
                            logger.info(f"Added strict_encode to class: {obj.__name__} in {module_name}")
        
        # 6. Patch the Anime class specifically
        from anipy_api.anime import Anime
        
        # Save the original __init__ method
        original_init = Anime.__init__
        
        # Create a patched version that ensures strict_encode is available
        def patched_init(self, *args, **kwargs):
            # Add strict_encode to the instance
            self.strict_encode = strict_encode
            
            # Call the original method
            original_init(self, *args, **kwargs)
        
        # Replace the method
        Anime.__init__ = patched_init
        logger.info("Patched Anime.__init__ method")
        
        # Save the original from_search_result method
        original_from_search_result = Anime.from_search_result
        
        # Create a patched version that ensures strict_encode is available
        @classmethod
        def patched_from_search_result(cls, provider, search_result):
            # Ensure strict_encode is available in the class
            cls.strict_encode = staticmethod(strict_encode)
            
            # Call the original method
            instance = original_from_search_result(provider, search_result)
            
            # Add strict_encode to the instance
            instance.strict_encode = strict_encode
            
            return instance
        
        # Replace the method
        Anime.from_search_result = patched_from_search_result
        logger.info("Patched Anime.from_search_result method")
        
        # 7. Create a custom import hook to inject strict_encode into newly imported modules
        class StrictEncodeInjector:
            def __init__(self):
                self.original_import = __import__
            
            def __call__(self, name, globals=None, locals=None, fromlist=(), level=0):
                module = self.original_import(name, globals, locals, fromlist, level)
                
                if name.startswith('anipy_api') or (fromlist and any(item.startswith('anipy_api') for item in fromlist)):
                    if not hasattr(module, 'strict_encode'):
                        module.strict_encode = strict_encode
                        logger.info(f"Injected strict_encode into newly imported module: {name}")
                
                return module
        
        builtins.__import__ = StrictEncodeInjector()
        logger.info("Installed custom import hook")
        
        # 8. Fix the provider module
        from anipy_api.provider import get_provider
        
        # Save the original get_provider function
        original_get_provider = get_provider
        
        # Create a patched version that ensures strict_encode is available
        def patched_get_provider(*args, **kwargs):
            # Call the original function
            provider = original_get_provider(*args, **kwargs)
            
            # Add strict_encode to the provider
            provider.strict_encode = strict_encode
            
            # Add strict_encode to the provider's class
            provider.__class__.strict_encode = staticmethod(strict_encode)
            
            return provider
        
        # Replace the function
        anipy_api.provider.get_provider = patched_get_provider
        logger.info("Patched get_provider function")
        
        return True
    except Exception as e:
        logger.error(f"Failed to fix local variable issue: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = fix_local_variable_issue()
    if success:
        print("Successfully fixed local variable issue")
    else:
        print("Failed to fix local variable issue")
