"""
Encoder Injection - A direct approach to make strict_encode available everywhere.
This script modifies Python's built-in eval and exec functions to ensure strict_encode
is always available in any context.
"""
import sys
import builtins
import types
import re
import logging
import inspect
import importlib
import os
from pathlib import Path

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

def inject_encoder():
    """
    Inject the strict_encode function into Python's evaluation mechanism.
    This ensures the function is available in any context.
    """
    try:
        # 1. Add to builtins
        builtins.strict_encode = strict_encode
        logger.info("Added strict_encode to builtins")
        
        # 2. Override eval and exec to include strict_encode in globals
        original_eval = builtins.eval
        original_exec = builtins.exec
        
        def new_eval(expr, globals=None, locals=None):
            if globals is None:
                globals = {}
            globals['strict_encode'] = strict_encode
            return original_eval(expr, globals, locals)
        
        def new_exec(expr, globals=None, locals=None):
            if globals is None:
                globals = {}
            globals['strict_encode'] = strict_encode
            return original_exec(expr, globals, locals)
        
        builtins.eval = new_eval
        builtins.exec = new_exec
        logger.info("Overrode eval and exec functions")
        
        # 3. Add to all existing modules
        for module_name in list(sys.modules.keys()):
            module = sys.modules[module_name]
            try:
                if hasattr(module, "__dict__"):
                    module.__dict__["strict_encode"] = strict_encode
            except Exception:
                pass
        logger.info("Added strict_encode to all existing modules")
        
        # 4. Create import hook to add to new modules
        original_import = builtins.__import__
        
        def import_hook(name, globals=None, locals=None, fromlist=(), level=0):
            module = original_import(name, globals, locals, fromlist, level)
            try:
                if hasattr(module, "__dict__"):
                    module.__dict__["strict_encode"] = strict_encode
            except Exception:
                pass
            return module
        
        builtins.__import__ = import_hook
        logger.info("Created import hook for new modules")
        
        # 5. Find and patch anipy_api source files
        try:
            import anipy_api
            anipy_path = os.path.dirname(anipy_api.__file__)
            logger.info(f"Found anipy_api at: {anipy_path}")
            
            # Find all Python files
            for root, _, files in os.walk(anipy_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Check if the file uses strict_encode
                            if 'strict_encode' in content:
                                logger.info(f"Found strict_encode reference in {file_path}")
                                
                                # Add the function definition to the file
                                if 'def strict_encode(' not in content:
                                    # Create a backup
                                    backup_path = file_path + '.bak'
                                    with open(backup_path, 'w', encoding='utf-8') as f:
                                        f.write(content)
                                    logger.info(f"Created backup at {backup_path}")
                                    
                                    # Add the function definition
                                    encoder_code = """
# Added by encoder_injection.py
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
                                    new_content = encoder_code + content
                                    
                                    with open(file_path, 'w', encoding='utf-8') as f:
                                        f.write(new_content)
                                    
                                    logger.info(f"Added strict_encode function to {file_path}")
                        except Exception as e:
                            logger.error(f"Error processing file {file_path}: {e}")
            
            # Reload all anipy_api modules
            for module_name in list(sys.modules.keys()):
                if module_name.startswith('anipy_api'):
                    try:
                        importlib.reload(sys.modules[module_name])
                        logger.info(f"Reloaded module: {module_name}")
                    except Exception as e:
                        logger.error(f"Error reloading module {module_name}: {e}")
        
        except ImportError:
            logger.error("Could not import anipy_api")
        
        # 6. Create a custom Anime class
        try:
            from anipy_api.anime import Anime as OriginalAnime
            
            # Create a new class that inherits from the original
            class CustomAnime(OriginalAnime):
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
                    
                    # Call the parent method with strict_encode in locals
                    def wrapper(*args, **kwargs):
                        strict_encode_local = strict_encode
                        return super(CustomAnime, self).get_episodes(*args, **kwargs)
                    
                    return wrapper(*args, **kwargs)
                
                def get_videos(self, *args, **kwargs):
                    # Add strict_encode to the instance
                    self.strict_encode = strict_encode
                    
                    # Call the parent method with strict_encode in locals
                    def wrapper(*args, **kwargs):
                        strict_encode_local = strict_encode
                        return super(CustomAnime, self).get_videos(*args, **kwargs)
                    
                    return wrapper(*args, **kwargs)
                
                def get_info(self, *args, **kwargs):
                    # Add strict_encode to the instance
                    self.strict_encode = strict_encode
                    
                    # Call the parent method with strict_encode in locals
                    def wrapper(*args, **kwargs):
                        strict_encode_local = strict_encode
                        return super(CustomAnime, self).get_info(*args, **kwargs)
                    
                    return wrapper(*args, **kwargs)
            
            # Replace the Anime class in the module
            sys.modules[OriginalAnime.__module__].Anime = CustomAnime
            
            # Replace the Anime class in all modules that import it
            for module_name in list(sys.modules.keys()):
                module = sys.modules[module_name]
                try:
                    if hasattr(module, "Anime") and isinstance(module.Anime, type) and module.Anime.__name__ == "Anime":
                        module.Anime = CustomAnime
                        logger.info(f"Replaced Anime class in module: {module_name}")
                except Exception:
                    pass
            
            logger.info("Created and installed custom Anime class")
        
        except Exception as e:
            logger.error(f"Error creating custom Anime class: {e}")
        
        # 7. Create a custom encoder.py file in the current directory
        try:
            encoder_path = os.path.join(os.getcwd(), "encoder.py")
            with open(encoder_path, "w", encoding="utf-8") as f:
                f.write("""
import re
import sys
import builtins

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

# Make the function available globally
builtins.strict_encode = strict_encode

# Add to all modules
for module_name in list(sys.modules.keys()):
    module = sys.modules[module_name]
    try:
        if hasattr(module, "__dict__"):
            module.__dict__["strict_encode"] = strict_encode
    except Exception:
        pass

# Export other functions that might be needed
def encode_string(s, instructions):
    \"\"\"Encode a string using the strict_encode function.\"\"\"
    return [strict_encode(ord(c), instructions) for c in s]

def encode_bytes(b, instructions):
    \"\"\"Encode bytes using the strict_encode function.\"\"\"
    return [strict_encode(c, instructions) for c in b]

def batch_encode(values, instructions):
    \"\"\"Encode multiple values using the strict_encode function.\"\"\"
    return [strict_encode(v, instructions) for v in values]

# Cache for optimization
_cache = {}

def clear_caches():
    \"\"\"Clear the encoder caches.\"\"\"
    global _cache
    _cache = {}

def benchmark(n=1000, instructions="(n + 1) % 256"):
    \"\"\"Benchmark the encoder function.\"\"\"
    import time
    start = time.time()
    for i in range(n):
        strict_encode(i % 256, instructions)
    end = time.time()
    return end - start
""")
            
            logger.info(f"Created encoder.py at {encoder_path}")
            
            # Import the module to make it available
            sys.path.insert(0, os.getcwd())
            import encoder
            logger.info("Imported encoder module")
        
        except Exception as e:
            logger.error(f"Error creating encoder.py: {e}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error injecting encoder: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = inject_encoder()
    if success:
        print("Successfully injected encoder")
    else:
        print("Failed to inject encoder")
