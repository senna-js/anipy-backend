"""
This script directly injects the strict_encode function into the anipy_api source code.
"""
import os
import sys
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def inject_strict_encode_function(file_path):
    """Inject the strict_encode function directly into a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the file already has the strict_encode function
        if re.search(r'def\s+strict_encode\s*\(', content):
            logger.info(f"File {file_path} already has a strict_encode function")
            return False
        
        # Add the strict_encode function at the top of the file
        strict_encode_code = """
# Added by inject_strict_encode.py
import re

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
        
        logger.info(f"Successfully injected strict_encode into file: {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error injecting strict_encode into file {file_path}: {e}")
        return False

def inject_strict_encode():
    """Inject the strict_encode function into all relevant anipy_api files."""
    anipy_api_location = find_anipy_api_location()
    if not anipy_api_location:
        return False
    
    logger.info(f"Found anipy_api at: {anipy_api_location}")
    
    # Find files that might be using strict_encode
    files_with_strict_encode = find_files_with_strict_encode(anipy_api_location)
    
    if not files_with_strict_encode:
        logger.warning("No files found that use strict_encode")
        # Inject into all Python files to be safe
        files_to_inject = []
        for root, _, files in os.walk(anipy_api_location):
            for file in files:
                if file.endswith('.py'):
                    files_to_inject.append(os.path.join(root, file))
    else:
        logger.info(f"Found {len(files_with_strict_encode)} files that use strict_encode")
        files_to_inject = files_with_strict_encode
    
    # Inject the function into the files
    injected_files = 0
    for file_path in files_to_inject:
        if inject_strict_encode_function(file_path):
            injected_files += 1
    
    logger.info(f"Injected strict_encode into {injected_files} files")
    
    # Reload the modules to apply the changes
    for module_name in list(sys.modules.keys()):
        if module_name.startswith('anipy_api'):
            try:
                del sys.modules[module_name]
                logger.info(f"Removed module from sys.modules: {module_name}")
            except Exception as e:
                logger.error(f"Error removing module {module_name}: {e}")
    
    return injected_files > 0

if __name__ == "__main__":
    success = inject_strict_encode()
    if success:
        print("Successfully injected strict_encode into anipy_api files")
    else:
        print("Failed to inject strict_encode into anipy_api files")
