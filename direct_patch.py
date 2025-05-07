"""
Direct patch for the anipy_api library to fix the strict_encode function error.
This script directly patches the specific modules that need the strict_encode function.
"""
import sys
import inspect
import types
import logging
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def direct_patch():
    """
    Directly patch the anipy_api library to fix the strict_encode function error.
    This function injects the strict_encode function into all relevant places.
    """
    try:
        # 1. Add to builtins
        import builtins
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
        
        # 6. Patch the eval function to handle strict_encode calls
        original_eval = eval
        
        def patched_eval(expr, globals=None, locals=None):
            if globals is None:
                globals = {}
            if 'strict_encode' not in globals:
                globals['strict_encode'] = strict_encode
            return original_eval(expr, globals, locals)
        
        builtins.eval = patched_eval
        logger.info("Patched eval function to include strict_encode")
        
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
        
        # 8. Patch the specific module where the error occurs
        try:
            from anipy_api.anime import Anime
            
            # Save original methods
            original_get_episodes = Anime.get_episodes
            
            # Create patched versions
            def patched_get_episodes(self, lang=None):
                # Ensure strict_encode is available in this context
                import builtins
                if not hasattr(builtins, 'strict_encode'):
                    builtins.strict_encode = strict_encode
                
                # Add to the local namespace of the method
                self.strict_encode = strict_encode
                
                # Add to the class
                if not hasattr(self.__class__, 'strict_encode'):
                    setattr(self.__class__, 'strict_encode', staticmethod(strict_encode))
                
                # Call the original method
                return original_get_episodes(self, lang)
            
            # Replace the methods
            Anime.get_episodes = patched_get_episodes
            logger.info("Patched Anime.get_episodes method")
            
            # 9. Patch the module's exec function if it exists
            if hasattr(Anime, '__module__'):
                module = sys.modules.get(Anime.__module__)
                if module and hasattr(module, '__dict__'):
                    module.__dict__['strict_encode'] = strict_encode
                    logger.info(f"Added strict_encode to module dict: {Anime.__module__}")
            
        except Exception as e:
            logger.error(f"Error patching Anime class: {e}")
        
        # 10. Patch all exec calls in anipy_api modules
        for module_name in list(sys.modules.keys()):
            if module_name.startswith('anipy_api'):
                module = sys.modules[module_name]
                if hasattr(module, '__file__'):
                    try:
                        with open(module.__file__, 'r') as f:
                            content = f.read()
                        
                        if 'exec(' in content or 'eval(' in content:
                            logger.info(f"Module {module_name} contains exec or eval calls")
                            
                            # Try to find and patch all exec and eval calls
                            for name, obj in inspect.getmembers(module):
                                if inspect.isfunction(obj) or inspect.ismethod(obj):
                                    source = inspect.getsource(obj)
                                    if 'exec(' in source or 'eval(' in source:
                                        logger.info(f"Function {name} in {module_name} contains exec or eval calls")
                                        
                                        # Get the function's globals
                                        func_globals = obj.__globals__
                                        
                                        # Add strict_encode to the function's globals
                                        if 'strict_encode' not in func_globals:
                                            func_globals['strict_encode'] = strict_encode
                                            logger.info(f"Added strict_encode to globals of function {name} in {module_name}")
                    except Exception as e:
                        logger.error(f"Error analyzing module {module_name}: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to apply direct patch: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = direct_patch()
    if success:
        print("Successfully applied direct patch")
    else:
        print("Failed to apply direct patch")
