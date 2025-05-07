import re
import logging

# Set up logging
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
    if not isinstance(n, int):
        try:
            n = int(n)
        except (ValueError, TypeError):
            raise ValueError(f"Input 'n' must be an integer, got {type(n)}")
    
    operations = instructions.split(';')
    results = []
    
    logger.debug(f"Encoding value {n} with {len(operations)} operations")
    
    for op in operations:
        op = op.strip()
        try:
            result = apply_operation(n, op)
            results.append(result)
            logger.debug(f"Operation '{op}' applied: {n} -> {result}")
        except ValueError as e:
            logger.error(f"Error applying operation '{op}': {e}")
            raise
    
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
    
    # Bit shifting from the error message: (n << 4 | (n & 0xFF) >> 4) & 255
    shift_match = re.match(r'$$n\s*<<\s*(\d+)\s*\|\s*\(n\s*&\s*0xFF$$\s*>>\s*(\d+)\)\s*&\s*255', operation)
    if shift_match or operation == "(n << 4 | (n & 0xFF) >> 4) & 255":
        if shift_match:
            left_shift = int(shift_match.group(1))
            right_shift = int(shift_match.group(2))
        else:
            left_shift = 4
            right_shift = 4
        return ((n << left_shift) | ((n & 0xFF) >> right_shift)) & 255
    
    # If we get here, none of our specific patterns matched
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

def decode_sequence(encoded_values, instructions):
    """
    Attempt to decode a sequence of encoded values using the inverse operations.
    Note: This is a best-effort function and may not work for all encoding schemes.
    
    Args:
        encoded_values (list): The list of encoded values
        instructions (str): The original encoding instructions
    
    Returns:
        list: A list of possible original values
    """
    # This is a placeholder for a decode function
    # Implementing a true decoder would require knowledge of the specific encoding scheme
    # and whether it's reversible
    logger.warning("Decode function is not fully implemented and may not work correctly")
    return None

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
