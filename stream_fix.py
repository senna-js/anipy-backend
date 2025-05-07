"""
This script provides a targeted fix for the 'local variable strict_encode referenced before assignment' 
error in the stream endpoint.
"""
import sys
import inspect
import types
import logging
import re
import builtins
import importlib

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
    """
    if not isinstance(n, int):
        try:
            n = int(n)
        except (ValueError, TypeError):
            raise ValueError(f"Input 'n' must be an integer, got {type(n)}")
    
    operations = instructions.split(';')
    results = []
    
    for op in operations:
        op = op.strip()
        
        # Addition with modulo: (n + X) % 256
        addition_match = re.match(r'$$n\s*\+\s*(\d+)$$\s*%\s*256', op)
        if addition_match:
            results.append((n + int(addition_match.group(1))) % 256)
            continue
        
        # Subtraction with modulo: (n - X + 256) % 256
        subtraction_match = re.match(r'$$n\s*\-\s*(\d+)\s*\+\s*256$$\s*%\s*256', op)
        if subtraction_match:
            results.append((n - int(subtraction_match.group(1)) + 256) % 256)
            continue
        
        # Bitwise XOR: n ^ X
        xor_match = re.match(r'n\s*\^\s*(\d+)', op)
        if xor_match:
            results.append(n ^ int(xor_match.group(1)))
            continue
        
        # Bitwise NOT: ~n & 255
        if op == "~n & 255":
            results.append(~n & 255)
            continue
        
        # Bit shifting: (n << 4 | (n & 0xFF) >> 4) & 255
        if op == "(n << 4 | (n & 0xFF) >> 4) & 255":
            results.append(((n << 4) | ((n & 0xFF) >> 4)) & 255)
            continue
        
        # If we get here, none of our patterns matched
        # Let's try to handle the operation based on the operators it contains
        
        # For operations like (n + X) % 256 or (n - X + 256) % 256
        if "%" in op and "256" in op:
            # Extract the expression inside the parentheses
            inner_expr = op.split("%")[0].strip()
            if inner_expr.startswith("(") and inner_expr.endswith(")"):
                inner_expr = inner_expr[1:-1].strip()
            
            if "+" in inner_expr and "-" not in inner_expr:
                # Addition: (n + X) % 256
                parts = inner_expr.split("+")
                if parts[0].strip() == "n":
                    value = int(parts[1].strip())
                    results.append((n + value) % 256)
                    continue
            
            elif "-" in inner_expr and "+" in inner_expr:
                # Subtraction with wrap: (n - X + 256) % 256
                parts = inner_expr.split("-")
                if parts[0].strip() == "n":
                    sub_parts = parts[1].split("+")
                    value = int(sub_parts[0].strip())
                    results.append((n - value + 256) % 256)
                    continue
        
        # For operations like n ^ X
        if "^" in op and "n" in op:
            parts = op.split("^")
            if parts[0].strip() == "n":
                value = int(parts[1].strip())
                results.append(n ^ value)
                continue
        
        # If we still can't handle it, raise an error
        raise ValueError(f"Unsupported operation: {op}")
    
    return results

def apply_stream_fix():
    """
    Apply a targeted fix for the stream endpoint.
    This function directly modifies the Anime class methods to ensure strict_encode is available.
    """
    try:
        # 1. Make strict_encode globally available
        builtins.strict_encode = strict_encode
        globals()['strict_encode'] = strict_encode
        
        # 2. Import and reload anipy_api modules
        import anipy_api
        from anipy_api.anime import Anime
        
        # 3. Find all methods in the Anime class
        anime_methods = inspect.getmembers(Anime, predicate=inspect.isfunction)
        
        # 4. Patch each method to ensure strict_encode is available
        for name, method in anime_methods:
            # Skip special methods
            if name.startswith('__') and name.endswith('__'):
                continue
            
            # Get the source code of the method
            try:
                source = inspect.getsource(method)
                
                # Check if the method uses strict_encode
                if 'strict_encode' in source:
                    logger.info(f"Found strict_encode in method: {name}")
                    
                    # Create a wrapper that ensures strict_encode is available
                    def create_wrapper(original_method):
                        def wrapper(self, *args, **kwargs):
                            # Add strict_encode to the method's globals
                            original_method.__globals__['strict_encode'] = strict_encode
                            
                            # Add strict_encode to the instance
                            self.strict_encode = strict_encode
                            
                            # Call the original method
                            return original_method(self, *args, **kwargs)
                        
                        # Copy metadata from the original method
                        wrapper.__name__ = original_method.__name__
                        wrapper.__doc__ = original_method.__doc__
                        wrapper.__module__ = original_method.__module__
                        
                        return wrapper
                    
                    # Apply the wrapper
                    setattr(Anime, name, create_wrapper(method))
                    logger.info(f"Patched method: {name}")
            except Exception as e:
                logger.error(f"Error patching method {name}: {e}")
        
        # 5. Patch the from_search_result method specifically
        original_from_search_result = Anime.from_search_result
        
        @classmethod
        def patched_from_search_result(cls, provider, search_result):
            # Add strict_encode to the class
            cls.strict_encode = staticmethod(strict_encode)
            
            # Add strict_encode to the provider
            provider.strict_encode = strict_encode
            
            # Call the original method
            instance = original_from_search_result(provider, search_result)
            
            # Add strict_encode to the instance
            instance.strict_encode = strict_encode
            
            return instance
        
        # Replace the method
        Anime.from_search_result = patched_from_search_result
        logger.info("Patched Anime.from_search_result method")
        
        # 6. Patch the get_videos method specifically
        if hasattr(Anime, 'get_videos'):
            original_get_videos = Anime.get_videos
            
            def patched_get_videos(self, episode, language=None):
                # Add strict_encode to the instance
                self.strict_encode = strict_encode
                
                # Add strict_encode to the method's globals
                original_get_videos.__globals__['strict_encode'] = strict_encode
                
                # Call the original method
                return original_get_videos(self, episode, language)
            
            # Replace the method
            Anime.get_videos = patched_get_videos
            logger.info("Patched Anime.get_videos method")
        
        # 7. Directly modify the source code of the Anime class
        try:
            # Get the file path of the Anime class
            anime_file = inspect.getfile(Anime)
            logger.info(f"Found Anime class at: {anime_file}")
            
            # Read the file
            with open(anime_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if strict_encode is already defined
            if 'def strict_encode(' not in content:
                # Add the strict_encode function at the top of the file
                strict_encode_code = """
# Added by stream_fix.py
import re

def strict_encode(n, instructions):
    \"\"\"
    Apply a series of encoding transformations to a value n based on the provided instructions.
    This implementation avoids using eval() for better security.
    \"\"\"
    if not isinstance(n, int):
        try:
            n = int(n)
        except (ValueError, TypeError):
            raise ValueError(f"Input 'n' must be an integer, got {type(n)}")
    
    operations = instructions.split(';')
    results = []
    
    for op in operations:
        op = op.strip()
        
        # Addition with modulo: (n + X) % 256
        addition_match = re.match(r'\$$n\\s*\\+\\s*(\\d+)\$$\\s*%\\s*256', op)
        if addition_match:
            results.append((n + int(addition_match.group(1))) % 256)
            continue
        
        # Subtraction with modulo: (n - X + 256) % 256
        subtraction_match = re.match(r'\$$n\\s*\\-\\s*(\\d+)\\s*\\+\\s*256\$$\\s*%\\s*256', op)
        if subtraction_match:
            results.append((n - int(subtraction_match.group(1)) + 256) % 256)
            continue
        
        # Bitwise XOR: n ^ X
        xor_match = re.match(r'n\\s*\\^\\s*(\\d+)', op)
        if xor_match:
            results.append(n ^ int(xor_match.group(1)))
            continue
        
        # Bitwise NOT: ~n & 255
        if op == "~n & 255":
            results.append(~n & 255)
            continue
        
        # Bit shifting: (n << 4 | (n & 0xFF) >> 4) & 255
        if op == "(n << 4 | (n & 0xFF) >> 4) & 255":
            results.append(((n << 4) | ((n & 0xFF) >> 4)) & 255)
            continue
        
        # If we get here, none of our patterns matched
        # Let's try to handle the operation based on the operators it contains
        
        # For operations like (n + X) % 256 or (n - X + 256) % 256
        if "%" in op and "256" in op:
            # Extract the expression inside the parentheses
            inner_expr = op.split("%")[0].strip()
            if inner_expr.startswith("(") and inner_expr.endswith(")"):
                inner_expr = inner_expr[1:-1].strip()
            
            if "+" in inner_expr and "-" not in inner_expr:
                # Addition: (n + X) % 256
                parts = inner_expr.split("+")
                if parts[0].strip() == "n":
                    value = int(parts[1].strip())
                    results.append((n + value) % 256)
                    continue
            
            elif "-" in inner_expr and "+" in inner_expr:
                # Subtraction with wrap: (n - X + 256) % 256
                parts = inner_expr.split("-")
                if parts[0].strip() == "n":
                    sub_parts = parts[1].split("+")
                    value = int(sub_parts[0].strip())
                    results.append((n - value + 256) % 256)
                    continue
        
        # For operations like n ^ X
        if "^" in op and "n" in op:
            parts = op.split("^")
            if parts[0].strip() == "n":
                value = int(parts[1].strip())
                results.append(n ^ value)
                continue
        
        # If we still can't handle it, raise an error
        raise ValueError(f"Unsupported operation: {op}")
    
    return results
"""
                
                # Add the function to the top of the file
                new_content = strict_encode_code + content
                
                # Write the modified file
                with open(anime_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                logger.info(f"Added strict_encode function to {anime_file}")
            
            # Reload the module
            importlib.reload(sys.modules[Anime.__module__])
            logger.info(f"Reloaded module: {Anime.__module__}")
        
        except Exception as e:
            logger.error(f"Error modifying source code: {e}")
        
        # 8. Create a custom Anime class with strict_encode built-in
        class CustomAnime(Anime):
            strict_encode = staticmethod(strict_encode)
            
            def __init__(self, *args, **kwargs):
                # Add strict_encode to the instance
                self.strict_encode = strict_encode
                
                # Call the parent constructor
                super().__init__(*args, **kwargs)
            
            @classmethod
            def from_search_result(cls, provider, search_result):
                # Add strict_encode to the provider
                provider.strict_encode = strict_encode
                
                # Call the parent method
                instance = super().from_search_result(provider, search_result)
                
                # Add strict_encode to the instance
                instance.strict_encode = strict_encode
                
                return instance
        
        # Replace the Anime class with our custom one
        sys.modules[Anime.__module__].Anime = CustomAnime
        logger.info("Replaced Anime class with CustomAnime")
        
        return True
    except Exception as e:
        logger.error(f"Failed to apply stream fix: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = apply_stream_fix()
    if success:
        print("Successfully applied stream fix")
    else:
        print("Failed to apply stream fix")
