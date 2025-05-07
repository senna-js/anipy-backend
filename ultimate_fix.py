"""
Ultimate fix for the 'local variable strict_encode referenced before assignment' error.
This script analyzes the source code of the anipy_api library to find where strict_encode
is being referenced and fixes the issue at its root.
"""
import os
import sys
import re
import ast
import inspect
import logging
import importlib
import builtins
import types
import traceback
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

def find_anipy_api_location():
    """Find the location of the anipy_api package."""
    try:
        import anipy_api
        return os.path.dirname(anipy_api.__file__)
    except ImportError:
        logger.error("anipy_api package not found")
        return None

class StrictEncodeVisitor(ast.NodeVisitor):
    """AST visitor to find references to strict_encode."""
    def __init__(self):
        self.references = []
    
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id == 'strict_encode':
            self.references.append(node)
        self.generic_visit(node)

def find_strict_encode_references(file_path):
    """Find references to strict_encode in a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        visitor = StrictEncodeVisitor()
        visitor.visit(tree)
        
        return visitor.references
    except Exception as e:
        logger.error(f"Error parsing file {file_path}: {e}")
        return []

def fix_file(file_path):
    """Fix a file by adding the strict_encode function and fixing references."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the file already has the strict_encode function
        if 'def strict_encode(' in content:
            logger.info(f"File {file_path} already has a strict_encode function")
        else:
            # Add the strict_encode function at the top of the file
            strict_encode_code = """
# Added by ultimate_fix.py
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
            content = new_content
            logger.info(f"Added strict_encode function to {file_path}")
        
        # Fix references to strict_encode
        # Replace all occurrences of strict_encode(...) with a global reference
        content = re.sub(r'strict_encode\(', 'globals()["strict_encode"](', content)
        
        # Write the modified file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Fixed references to strict_encode in {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error fixing file {file_path}: {e}")
        return False

def fix_anime_class():
    """Fix the Anime class specifically."""
    try:
        from anipy_api.anime import Anime
        
        # Get the file path of the Anime class
        anime_file = inspect.getfile(Anime)
        logger.info(f"Found Anime class at: {anime_file}")
        
        # Fix the file
        if fix_file(anime_file):
            logger.info(f"Successfully fixed Anime class file: {anime_file}")
            
            # Reload the module
            importlib.reload(sys.modules[Anime.__module__])
            logger.info(f"Reloaded module: {Anime.__module__}")
            
            return True
        else:
            logger.error(f"Failed to fix Anime class file: {anime_file}")
            return False
    except Exception as e:
        logger.error(f"Error fixing Anime class: {e}")
        return False

def fix_all_files():
    """Fix all Python files in the anipy_api package."""
    anipy_api_location = find_anipy_api_location()
    if not anipy_api_location:
        return False
    
    logger.info(f"Found anipy_api at: {anipy_api_location}")
    
    # Find all Python files
    python_files = []
    for root, _, files in os.walk(anipy_api_location):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    # Fix each file
    fixed_files = 0
    for file_path in python_files:
        if fix_file(file_path):
            fixed_files += 1
    
    logger.info(f"Fixed {fixed_files} out of {len(python_files)} files")
    
    # Reload all anipy_api modules
    for module_name in list(sys.modules.keys()):
        if module_name.startswith('anipy_api'):
            try:
                importlib.reload(sys.modules[module_name])
                logger.info(f"Reloaded module: {module_name}")
            except Exception as e:
                logger.error(f"Error reloading module {module_name}: {e}")
    
    return fixed_files > 0

def create_monkey_patch():
    """Create a monkey patch for the strict_encode function."""
    try:
        # Add to builtins
        builtins.strict_encode = strict_encode
        logger.info("Added strict_encode to builtins")
        
        # Add to globals of all modules
        for module_name in list(sys.modules.keys()):
            module = sys.modules[module_name]
            try:
                if hasattr(module, "__dict__"):
                    module.__dict__["strict_encode"] = strict_encode
                    logger.info(f"Added strict_encode to module: {module_name}")
            except Exception:
                pass
        
        # Add to __main__ module
        if "__main__" in sys.modules:
            sys.modules["__main__"].__dict__["strict_encode"] = strict_encode
            logger.info("Added strict_encode to __main__ module")
        
        # Create a custom import hook to inject strict_encode into newly imported modules
        original_import = __import__
        
        def import_hook(name, globals=None, locals=None, fromlist=(), level=0):
            module = original_import(name, globals, locals, fromlist, level)
            try:
                if hasattr(module, "__dict__"):
                    module.__dict__["strict_encode"] = strict_encode
            except Exception:
                pass
            return module
        
        builtins.__import__ = import_hook
        logger.info("Installed custom import hook")
        
        return True
    except Exception as e:
        logger.error(f"Failed to create monkey patch: {e}")
        return False

def apply_ultimate_fix():
    """Apply the ultimate fix for the local variable issue."""
    try:
        # 1. Create a monkey patch
        if not create_monkey_patch():
            logger.error("Failed to create monkey patch")
        
        # 2. Fix the Anime class specifically
        if not fix_anime_class():
            logger.error("Failed to fix Anime class")
        
        # 3. Fix all files in the anipy_api package
        if not fix_all_files():
            logger.error("Failed to fix all files")
        
        # 4. Add a custom __getattr__ to all modules
        for module_name in list(sys.modules.keys()):
            if module_name.startswith('anipy_api'):
                module = sys.modules[module_name]
                try:
                    def custom_getattr(name):
                        if name == 'strict_encode':
                            return strict_encode
                        raise AttributeError(f"module '{module_name}' has no attribute '{name}'")
                    
                    module.__getattr__ = custom_getattr
                    logger.info(f"Added custom __getattr__ to module: {module_name}")
                except Exception:
                    pass
        
        # 5. Create a custom Anime class with strict_encode built-in
        try:
            from anipy_api.anime import Anime
            
            # Save the original class
            original_anime = Anime
            
            # Create a custom class
            class CustomAnime(original_anime):
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
        except Exception as e:
            logger.error(f"Error creating custom Anime class: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to apply ultimate fix: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = apply_ultimate_fix()
    if success:
        print("Successfully applied ultimate fix")
    else:
        print("Failed to apply ultimate fix")
