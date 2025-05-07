"""
This script completely replaces the Anime class in the anipy_api library.
"""
import sys
import logging
import re
import importlib
import builtins
import types

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

def replace_anime_class():
    """Replace the Anime class in the anipy_api library."""
    try:
        # Import the original Anime class
        from anipy_api.anime import Anime as OriginalAnime
        
        # Get the module
        anime_module = sys.modules[OriginalAnime.__module__]
        
        # Create a new Anime class that inherits from the original
        class NewAnime(OriginalAnime):
            # Add strict_encode as a class method
            @staticmethod
            def strict_encode(n, instructions):
                return strict_encode(n, instructions)
            
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
            
            def get_episodes(self, *args, **kwargs):
                # Add strict_encode to the instance
                self.strict_encode = strict_encode
                
                # Call the parent method
                return super().get_episodes(*args, **kwargs)
            
            def get_videos(self, *args, **kwargs):
                # Add strict_encode to the instance
                self.strict_encode = strict_encode
                
                # Call the parent method
                return super().get_videos(*args, **kwargs)
            
            def get_info(self, *args, **kwargs):
                # Add strict_encode to the instance
                self.strict_encode = strict_encode
                
                # Call the parent method
                return super().get_info(*args, **kwargs)
        
        # Replace the Anime class in the module
        anime_module.Anime = NewAnime
        
        # Replace the Anime class in all modules that import it
        for module_name in list(sys.modules.keys()):
            module = sys.modules[module_name]
            try:
                if hasattr(module, "Anime") and module.Anime is OriginalAnime:
                    module.Anime = NewAnime
                    logger.info(f"Replaced Anime class in module: {module_name}")
            except Exception:
                pass
        
        # Add strict_encode to all modules
        for module_name in list(sys.modules.keys()):
            module = sys.modules[module_name]
            try:
                if hasattr(module, "__dict__"):
                    module.__dict__["strict_encode"] = strict_encode
                    logger.info(f"Added strict_encode to module: {module_name}")
            except Exception:
                pass
        
        # Add strict_encode to builtins
        builtins.strict_encode = strict_encode
        logger.info("Added strict_encode to builtins")
        
        return True
    except Exception as e:
        logger.error(f"Failed to replace Anime class: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = replace_anime_class()
    if success:
        print("Successfully replaced Anime class")
    else:
        print("Failed to replace Anime class")
