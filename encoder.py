import re
import logging
from functools import lru_cache
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Precompile regex patterns for better performance
ADDITION_PATTERN = re.compile(r'$$n\s*\+\s*(\d+)$$\s*%\s*256')
SUBTRACTION_PATTERN = re.compile(r'$$n\s*\-\s*(\d+)\s*\+\s*256$$\s*%\s*256')
XOR_PATTERN = re.compile(r'n\s*\^\s*(\d+)')
NOT_PATTERN = re.compile(r'~n\s*&\s*255')
SHIFT_PATTERN = re.compile(r'$$n\s*<<\s*(\d+)\s*\|\s*\(n\s*&\s*0xFF$$\s*>>\s*(\d+)\)\s*&\s*255')

# Operation type constants for faster dispatch
OP_ADDITION = 1
OP_SUBTRACTION = 2
OP_XOR = 3
OP_NOT = 4
OP_SHIFT = 5
OP_UNKNOWN = 0

# Cache for operation parsing
operation_cache = {}

# Cache for operation functions
@lru_cache(maxsize=128)
def get_operation_type(operation):
    """
    Determine the type of operation and extract parameters.
    Uses a cache to avoid repeated regex matching.
    
    Args:
        operation (str): The operation string
    
    Returns:
        tuple: (operation_type, parameters)
    """
    # Check cache first
    if operation in operation_cache:
        return operation_cache[operation]
    
    # Addition with modulo: (n + X) % 256
    match = ADDITION_PATTERN.match(operation)
    if match:
        result = (OP_ADDITION, int(match.group(1)))
        operation_cache[operation] = result
        return result
    
    # Subtraction with modulo: (n - X + 256) % 256
    match = SUBTRACTION_PATTERN.match(operation)
    if match:
        result = (OP_SUBTRACTION, int(match.group(1)))
        operation_cache[operation] = result
        return result
    
    # Bitwise XOR: n ^ X
    match = XOR_PATTERN.match(operation)
    if match:
        result = (OP_XOR, int(match.group(1)))
        operation_cache[operation] = result
        return result
    
    # Bitwise NOT: ~n & 255
    if NOT_PATTERN.match(operation):
        result = (OP_NOT, None)
        operation_cache[operation] = result
        return result
    
    # Bit shifting: (n << X | (n & 0xFF) >> Y) & 255
    match = SHIFT_PATTERN.match(operation)
    if match:
        result = (OP_SHIFT, (int(match.group(1)), int(match.group(2))))
        operation_cache[operation] = result
        return result
    
    # Special case for the specific bit shifting pattern
    if operation == "(n << 4 | (n & 0xFF) >> 4) & 255":
        result = (OP_SHIFT, (4, 4))
        operation_cache[operation] = result
        return result
    
    # If we get here, we need to parse the operation manually
    result = parse_complex_operation(operation)
    operation_cache[operation] = result
    return result

def parse_complex_operation(operation):
    """
    Parse more complex operations that don't fit the standard patterns.
    
    Args:
        operation (str): The operation string
    
    Returns:
        tuple: (operation_type, parameters)
    """
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
                try:
                    value = int(parts[1].strip())
                    return (OP_ADDITION, value)
                except (ValueError, IndexError):
                    pass
        
        elif "-" in inner_expr and "+" in inner_expr:
            # Subtraction with wrap: (n - X + 256) % 256
            parts = inner_expr.split("-")
            if parts[0].strip() == "n":
                try:
                    sub_parts = parts[1].split("+")
                    value = int(sub_parts[0].strip())
                    return (OP_SUBTRACTION, value)
                except (ValueError, IndexError):
                    pass
    
    # For operations like n ^ X
    if "^" in operation and "n" in operation:
        parts = operation.split("^")
        if parts[0].strip() == "n":
            try:
                value = int(parts[1].strip())
                return (OP_XOR, value)
            except (ValueError, IndexError):
                pass
    
    # If we still can't handle it, return unknown
    return (OP_UNKNOWN, operation)

def apply_operation_fast(n, op_type, params):
    """
    Apply an operation using the optimized dispatch method.
    
    Args:
        n (int): The value to encode
        op_type (int): The operation type constant
        params: The operation parameters
    
    Returns:
        int: The result of applying the operation
    """
    if op_type == OP_ADDITION:
        return (n + params) % 256
    elif op_type == OP_SUBTRACTION:
        return (n - params + 256) % 256
    elif op_type == OP_XOR:
        return n ^ params
    elif op_type == OP_NOT:
        return ~n & 255
    elif op_type == OP_SHIFT:
        left_shift, right_shift = params
        return ((n << left_shift) | ((n & 0xFF) >> right_shift)) & 255
    else:
        # For unknown operations, fall back to the original method
        raise ValueError(f"Unsupported operation type: {op_type} with params {params}")

def strict_encode(n, instructions):
    """
    Apply a series of encoding transformations to a value n based on the provided instructions.
    This implementation avoids using eval() for better security and is optimized for performance.
    
    Args:
        n (int): The numeric value to encode
        instructions (str): A string containing semicolon-separated encoding instructions
    
    Returns:
        list: A list of encoded values after applying each instruction
    """
    if not isinstance(n, int):
        try:
            n = int(n)
        except (ValueError, TypeError):
            raise ValueError(f"Input 'n' must be an integer, got {type(n)}")
    
    # Split and strip operations once
    operations = [op.strip() for op in instructions.split(';')]
    results = []
    
    # Pre-allocate the results list for better performance
    results = [0] * len(operations)
    
    # Process operations
    for i, op in enumerate(operations):
        op_type, params = get_operation_type(op)
        try:
            results[i] = apply_operation_fast(n, op_type, params)
        except ValueError:
            # Fall back to the original method for unsupported operations
            logger.warning(f"Using fallback method for operation: {op}")
            results[i] = apply_operation_fallback(n, op)
    
    return results

def apply_operation_fallback(n, operation):
    """
    Fallback method to apply an operation when the fast method fails.
    
    Args:
        n (int): The value to encode
        operation (str): The operation string
    
    Returns:
        int: The result of applying the operation
    """
    # This is the original implementation as a fallback
    # Addition with modulo: (n + X) % 256
    match = ADDITION_PATTERN.match(operation)
    if match:
        return (n + int(match.group(1))) % 256
    
    # Subtraction with modulo: (n - X + 256) % 256
    match = SUBTRACTION_PATTERN.match(operation)
    if match:
        return (n - int(match.group(1)) + 256) % 256
    
    # Bitwise XOR: n ^ X
    match = XOR_PATTERN.match(operation)
    if match:
        return n ^ int(match.group(1))
    
    # Bitwise NOT: ~n & 255
    if operation == "~n & 255":
        return ~n & 255
    
    # Bit shifting from the error message: (n << 4 | (n & 0xFF) >> 4) & 255
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

def batch_encode(values, instructions):
    """
    Encode multiple values at once for better performance.
    
    Args:
        values (list): List of integer values to encode
        instructions (str): The encoding instructions
    
    Returns:
        list: A list of lists, where each inner list contains the encoded values for a value
    """
    # Split and strip operations once
    operations = [op.strip() for op in instructions.split(';')]
    
    # Pre-process operation types and parameters
    op_types_params = [get_operation_type(op) for op in operations]
    
    # Pre-allocate the results list
    results = []
    
    # Process each value
    for n in values:
        if not isinstance(n, int):
            try:
                n = int(n)
            except (ValueError, TypeError):
                raise ValueError(f"Input value must be an integer, got {type(n)}")
        
        # Pre-allocate the results for this value
        value_results = [0] * len(operations)
        
        # Apply operations
        for i, (op_type, params) in enumerate(op_types_params):
            try:
                value_results[i] = apply_operation_fast(n, op_type, params)
            except ValueError:
                # Fall back to the original method for unsupported operations
                value_results[i] = apply_operation_fallback(n, operations[i])
        
        results.append(value_results)
    
    return results

def encode_string(text, instructions):
    """
    Encode a string by applying the encoding instructions to each character.
    Optimized for performance with batch processing.
    
    Args:
        text (str): The string to encode
        instructions (str): The encoding instructions
    
    Returns:
        list: A list of lists, where each inner list contains the encoded values for a character
    """
    # Convert string to character codes
    char_codes = [ord(char) for char in text]
    
    # Use batch encoding for better performance
    return batch_encode(char_codes, instructions)

def encode_bytes(data, instructions):
    """
    Encode bytes by applying the encoding instructions to each byte.
    Optimized for performance with batch processing.
    
    Args:
        data (bytes): The bytes to encode
        instructions (str): The encoding instructions
    
    Returns:
        list: A list of lists, where each inner list contains the encoded values for a byte
    """
    # Use batch encoding for better performance
    return batch_encode(list(data), instructions)

def benchmark(func, *args, **kwargs):
    """
    Benchmark a function's execution time.
    
    Args:
        func: The function to benchmark
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        tuple: (result, execution_time_ms)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    execution_time_ms = (end_time - start_time) * 1000
    return result, execution_time_ms

# Clear the operation cache
def clear_caches():
    """Clear all internal caches to free memory."""
    operation_cache.clear()
    get_operation_type.cache_clear()
