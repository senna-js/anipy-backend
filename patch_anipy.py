"""
Patch script for anipy_api library to add the strict_encode function.
Run this script before starting your FastAPI server.
"""
import os
import sys
import importlib
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our encoder function
from encoder import strict_encode

def find_anipy_api_location():
    """Find the location of the anipy_api package."""
    try:
        import anipy_api
        return os.path.dirname(anipy_api.__file__)
    except ImportError:
        logger.error("anipy_api package not found")
        return None

def find_files_with_strict_encode(directory):
    """Find files that might be using strict_encode."""
    if not directory or not os.path.exists(directory):
        return []
    
    files_with_strict_encode = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'strict_encode' in content:
                            files_with_strict_encode.append(file_path)
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {e}")
    
    return files_with_strict_encode

def patch_file(file_path):
    """Patch a file to add the strict_encode function."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the file already imports strict_encode
        if re.search(r'from\s+.*\s+import\s+.*strict_encode', content) or re.search(r'import\s+.*strict_encode', content):
            logger.info(f"File {file_path} already imports strict_encode")
            return False
        
        # Add the strict_encode function at the top of the file
        strict_encode_code = """
# Added by patch_anipy.py
def strict_encode(n, instructions):
    \"\"\"
    Apply a series of encoding transformations to a value n based on the provided instructions.
    \"\"\"
    if not isinstance(n, int):
        try:
            n = int(n)
        except (ValueError, TypeError):
            raise ValueError(f"Input 'n' must be an integer, got {type(n)}")
    
    import re
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
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"Successfully patched file: {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error patching file {file_path}: {e}")
        return False

def patch_anipy_api():
    """Patch the anipy_api library to add the strict_encode function."""
    anipy_api_location = find_anipy_api_location()
    if not anipy_api_location:
        return False
    
    logger.info(f"Found anipy_api at: {anipy_api_location}")
    
    # Find files that might be using strict_encode
    files_with_strict_encode = find_files_with_strict_encode(anipy_api_location)
    
    if not files_with_strict_encode:
        logger.warning("No files found that use strict_encode")
        # Patch all Python files to be safe
        files_to_patch = []
        for root, _, files in os.walk(anipy_api_location):
            for file in files:
                if file.endswith('.py'):
                    files_to_patch.append(os.path.join(root, file))
    else:
        logger.info(f"Found {len(files_with_strict_encode)} files that use strict_encode")
        files_to_patch = files_with_strict_encode
    
    # Patch the files
    patched_files = 0
    for file_path in files_to_patch:
        if patch_file(file_path):
            patched_files += 1
    
    logger.info(f"Patched {patched_files} files")
    
    # Reload the modules to apply the patches
    for module_name in list(sys.modules.keys()):
        if module_name.startswith('anipy_api'):
            try:
                importlib.reload(sys.modules[module_name])
                logger.info(f"Reloaded module: {module_name}")
            except Exception as e:
                logger.error(f"Error reloading module {module_name}: {e}")
    
    return patched_files > 0

if __name__ == "__main__":
    success = patch_anipy_api()
    if success:
        print("Successfully patched anipy_api library")
    else:
        print("Failed to patch anipy_api library")
