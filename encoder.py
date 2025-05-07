"""
Secure encoder module for handling encoding operations.
This module provides functions for encoding data without using eval().
"""
import re
import logging
from functools import lru_cache

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pre-compile regex patterns for better performance
ADDITION_PATTERN = re.compile(r'$$n\s*\+\s*(\d+)$$\s*%\s*256')
SUBTRACTION_PATTERN = re.compile(r'$$n\s*\-\s*(\d+)\s*\+\s*256$$\s*%\s*256')
XOR_PATTERN = re.compile(r'n\s*\^\s*(\d+)')

# Operation type constants for faster dispatch
OP_ADD = 1
OP_SUB = 2
OP_XOR = 3
OP_NOT = 4
OP_SHIFT = 5
OP_UNKNOWN = 0

def get_operation_type(operation):
    """
    Determine the type of operation for faster dispatch.
    """
    if ADDITION_PATTERN.match(operation):
        return OP_ADD
    elif SUBTRACTION_PATTERN.match(operation):
        return OP_SUB
    elif XOR_PATTERN.match(operation):
        return OP_XOR
    elif operation == "~n & 255":
        return OP_NOT
    elif operation == "(n << 4 | (n & 0xFF) >> 4) & 255":
        return OP_SHIFT
    return OP_UNKNOWN

@lru_cache(maxsize=1024)
def apply_operation(n, operation, op_type=None):
    """
    Apply a single encoding operation to the value n.
    Uses operation type for faster dispatch.
    
    Args:
        n (int): The value to encode
        operation (str): The operation to apply
        op_type (int, optional): The pre-determined operation type
    
    Returns:
        int: The result of applying the operation
    """
    # Determine operation type if not provided
    if op_type is None:
        op_type = get_operation_type(operation)
    
    # Fast dispatch based on operation type
    if op_type == OP_ADD:
        match = ADDITION_PATTERN.match(operation)
        return (n + int(match.group(1))) % 256
    
    elif op_type == OP_SUB:
        match = SUBTRACTION_PATTERN.match(operation)
        return (n - int(match.group(1)) + 256) % 256
    
    elif op_type == OP_XOR:
        match = XOR_PATTERN.match(operation)
        return n ^ int(match.group(1))
    
    elif op_type == OP_NOT:
        return ~n & 255
    
    elif op_type == OP_SHIFT:
        return ((n << 4) | ((n & 0xFF) >> 4)) & 255
    
    # Fallback for unknown operations
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
    # Log the function call for debugging
    logger.debug(f"strict_encode called with n={n}, instructions='{instructions}'")
    
    if not isinstance(n, int):
        try:
            n = int(n)
        except (ValueError, TypeError):
            raise ValueError(f"Input 'n' must be an integer, got {type(n)}")
    
    operations = instructions.split(';')
    results = []
    
    # Pre-determine operation types for faster processing
    op_types = [get_operation_type(op.strip()) for op in operations]
    
    # Process all operations
    for i, op in enumerate(operations):
        op = op.strip()
        try:
            result = apply_operation(n, op, op_types[i])
            results.append(result)
        except Exception as e:
            logger.error(f"Error applying operation '{op}': {e}")
            raise ValueError(f"Error in operation '{op}': {e}")
    
    return results

def encode_string(text, instructions):
    """
    Encode a string by applying the encoding instructions to each character.
    
    Args:
        text (str): The string to encode
        instructions (str): The encoding instructions
    
    Returns:
        list: A list of lists, where each inner list contains the encoded values for a character
    """
    result = []
    for char in text:
        char_code = ord(char)
        encoded = strict_encode(char_code, instructions)
        result.append(encoded)
    return result

def encode_bytes(data, instructions):
    """
    Encode bytes by applying the encoding instructions to each byte.
    
    Args:
        data (bytes): The bytes to encode
        instructions (str): The encoding instructions
    
    Returns:
        list: A list of lists, where each inner list contains the encoded values for a byte
    """
    result = []
    for byte in data:
        encoded = strict_encode(byte, instructions)
        result.append(encoded)
    return result

def batch_encode(values, instructions):
    """
    Encode multiple values with the same instructions.
    
    Args:
        values (list): List of integers to encode
        instructions (str): The encoding instructions
    
    Returns:
        list: A list of lists, where each inner list contains the encoded values for an input value
    """
    return [strict_encode(val, instructions) for val in values]

# Cache management
def clear_caches():
    """Clear all function caches to free memory."""
    apply_operation.cache_clear()
    logger.info("Encoder caches cleared")

def benchmark(n, instructions, iterations=1000):
    """
    Benchmark the encoder performance.
    
    Args:
        n (int): The value to encode
        instructions (str): The encoding instructions
        iterations (int): Number of iterations for the benchmark
    
    Returns:
        float: Average time per operation in milliseconds
    """
    import time
    
    start_time = time.time()
    for _ in range(iterations):
        strict_encode(n, instructions)
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time = (total_time / iterations) * 1000  # Convert to milliseconds
    
    return avg_time
