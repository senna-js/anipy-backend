import logging
import sys
import time
from fastapi import FastAPI, Query, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import Union, List, Dict, Any, Optional
from pydantic import BaseModel
import json

# Import our optimized secure encoder
from encoder import (
    strict_encode, 
    encode_string, 
    encode_bytes, 
    batch_encode, 
    benchmark,
    clear_caches
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Anime Streaming API",
    description="API for searching and streaming anime content",
    version="1.0.0"
)

# Whitelist frontend origins
origins = [
    "http://localhost:5173",
    "https://anipulse.pages.dev"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(tags=["Encoder"])

# Define response models
class EncodingResult(BaseModel):
    input_value: int
    encoded_values: List[int]
    instructions: str
    execution_time_ms: Optional[float] = None

class BatchEncodingResult(BaseModel):
    input_values: List[int]
    encoded_values: List[List[int]]
    instructions: str
    execution_time_ms: Optional[float] = None

class StringEncodingResult(BaseModel):
    input_text: str
    encoded_values: List[List[int]]
    instructions: str
    execution_time_ms: Optional[float] = None

@router.get("/", tags=["Status"])
def home():
    return {"msg": "Optimized Encoder API is running!"}

@router.get("/encode/{value}", response_model=EncodingResult)
def encode_value(
    value: int,
    instructions: str = Query(
        "(n + 111) % 256;n ^ 217;~n & 255",
        description="Semicolon-separated encoding instructions"
    ),
    benchmark_mode: bool = Query(False, description="Enable benchmarking")
):
    """
    Encode a numeric value using the provided instructions.
    """
    try:
        if benchmark_mode:
            encoded, execution_time_ms = benchmark(strict_encode, value, instructions)
            return {
                "input_value": value,
                "encoded_values": encoded,
                "instructions": instructions,
                "execution_time_ms": execution_time_ms
            }
        else:
            encoded = strict_encode(value, instructions)
            return {
                "input_value": value,
                "encoded_values": encoded,
                "instructions": instructions
            }
    except ValueError as e:
        logger.error(f"Encoding error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.get("/batch-encode", response_model=BatchEncodingResult)
def batch_encode_values(
    values: str = Query(..., description="Comma-separated list of values to encode"),
    instructions: str = Query(
        "(n + 111) % 256;n ^ 217;~n & 255",
        description="Semicolon-separated encoding instructions"
    ),
    benchmark_mode: bool = Query(False, description="Enable benchmarking")
):
    """
    Encode multiple values at once using the provided instructions.
    """
    try:
        # Parse the comma-separated values
        value_list = [int(v.strip()) for v in values.split(",")]
        
        if benchmark_mode:
            encoded, execution_time_ms = benchmark(batch_encode, value_list, instructions)
            return {
                "input_values": value_list,
                "encoded_values": encoded,
                "instructions": instructions,
                "execution_time_ms": execution_time_ms
            }
        else:
            encoded = batch_encode(value_list, instructions)
            return {
                "input_values": value_list,
                "encoded_values": encoded,
                "instructions": instructions
            }
    except ValueError as e:
        logger.error(f"Batch encoding error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.get("/encode-string", response_model=StringEncodingResult)
def encode_text(
    text: str = Query(..., description="Text to encode"),
    instructions: str = Query(
        "(n + 111) % 256;n ^ 217;~n & 255",
        description="Semicolon-separated encoding instructions"
    ),
    benchmark_mode: bool = Query(False, description="Enable benchmarking")
):
    """
    Encode a string using the provided instructions.
    """
    try:
        if benchmark_mode:
            encoded, execution_time_ms = benchmark(encode_string, text, instructions)
            return {
                "input_text": text,
                "encoded_values": encoded,
                "instructions": instructions,
                "execution_time_ms": execution_time_ms
            }
        else:
            encoded = encode_string(text, instructions)
            return {
                "input_text": text,
                "encoded_values": encoded,
                "instructions": instructions
            }
    except ValueError as e:
        logger.error(f"String encoding error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.post("/clear-caches", status_code=204)
def clear_all_caches():
    """
    Clear all internal caches to free memory.
    """
    try:
        clear_caches()
        return None
    except Exception as e:
        logger.error(f"Cache clearing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear caches")

# Include router in app
app.include_router(router)

def run_performance_comparison():
    """
    Run a performance comparison between the original and optimized implementations.
    """
    print("Performance Comparison")
    print("=====================")
    
    # Test parameters
    value = 100
    instructions = "(n + 111) % 256;n ^ 217;~n & 255"
    iterations = 10000
    
    # Warm up the cache
    strict_encode(value, instructions)
    
    # Test single value encoding
    print(f"\nTesting single value encoding ({iterations} iterations):")
    start_time = time.time()
    for _ in range(iterations):
        strict_encode(value, instructions)
    end_time = time.time()
    single_time_ms = (end_time - start_time) * 1000
    print(f"Total time: {single_time_ms:.2f}ms")
    print(f"Average time per iteration: {single_time_ms / iterations:.4f}ms")
    
    # Test batch encoding
    batch_size = 1000
    values = [value] * batch_size
    print(f"\nTesting batch encoding (batch size: {batch_size}, {iterations // batch_size} iterations):")
    start_time = time.time()
    for _ in range(iterations // batch_size):
        batch_encode(values, instructions)
    end_time = time.time()
    batch_time_ms = (end_time - start_time) * 1000
    print(f"Total time: {batch_time_ms:.2f}ms")
    print(f"Average time per value: {batch_time_ms / iterations:.4f}ms")
    print(f"Speedup from batch processing: {single_time_ms / batch_time_ms:.2f}x")
    
    # Test string encoding
    text = "Hello, World!" * 100  # Create a longer string
    print(f"\nTesting string encoding (string length: {len(text)}):")
    result, execution_time_ms = benchmark(encode_string, text, instructions)
    print(f"Total time: {execution_time_ms:.2f}ms")
    print(f"Average time per character: {execution_time_ms / len(text):.4f}ms")
    
    # Test with complex instructions
    complex_instructions = "(n + 111) % 256;(n + 212) % 256;n ^ 217;(n + 214) % 256;(n + 151) % 256;~n & 255;~n & 255;~n & 255;(n - 1 + 256) % 256;(n - 96 + 256) % 256;~n & 255;~n & 255;(n - 206 + 256) % 256;~n & 255;(n + 116) % 256;n ^ 70;n ^ 147;(n + 190) % 256;n ^ 222;(n - 118 + 256) % 256;(n - 227 + 256) % 256;~n & 255;(n << 4 | (n & 0xFF) >> 4) & 255;(n + 22) % 256;~n & 255;(n + 94) % 256;(n + 146) % 256;~n & 255;(n - 206 + 256) % 256;(n - 62 + 256) % 256"
    print(f"\nTesting with complex instructions ({len(complex_instructions.split(';'))} operations):")
    result, execution_time_ms = benchmark(strict_encode, value, complex_instructions)
    print(f"Total time: {execution_time_ms:.2f}ms")
    print(f"Average time per operation: {execution_time_ms / len(complex_instructions.split(';')):.4f}ms")

def demo_encoder():
    """
    Demonstrate the encoder functionality in a command-line context.
    """
    print("Optimized Secure Encoder Demo")
    print("============================")
    
    # Example 1: Encode a single value
    value = 100
    instructions = "(n + 111) % 256;n ^ 217;~n & 255"
    
    try:
        print(f"\nExample 1: Encoding value {value} with instructions '{instructions}'")
        result, execution_time_ms = benchmark(strict_encode, value, instructions)
        print(f"Result: {result}")
        print(f"Execution time: {execution_time_ms:.2f}ms")
        
        # Verify the results manually
        expected = [(100 + 111) % 256, 100 ^ 217, ~100 & 255]
        print(f"Expected: {expected}")
        print(f"Match: {result == expected}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 2: Encode a string
    text = "Hello, World!"
    instructions = "(n + 111) % 256;n ^ 217"
    
    try:
        print(f"\nExample 2: Encoding string '{text}' with instructions '{instructions}'")
        result, execution_time_ms = benchmark(encode_string, text, instructions)
        print(f"Execution time: {execution_time_ms:.2f}ms")
        
        # Print in a more readable format
        print("Character by character:")
        for i, char in enumerate(text):
            print(f"'{char}' (ASCII {ord(char)}) -> {result[i]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 3: Test with the full instruction set from the error message
    value = 100
    full_instructions = "(n + 111) % 256;(n + 212) % 256;n ^ 217;(n + 214) % 256;(n + 151) % 256;~n & 255;~n & 255;~n & 255;(n - 1 + 256) % 256;(n - 96 + 256) % 256;~n & 255;~n & 255;(n - 206 + 256) % 256;~n & 255;(n + 116) % 256;n ^ 70;n ^ 147;(n + 190) % 256;n ^ 222;(n - 118 + 256) % 256;(n - 227 + 256) % 256;~n & 255;(n << 4 | (n & 0xFF) >> 4) & 255;(n + 22) % 256;~n & 255;(n + 94) % 256;(n + 146) % 256;~n & 255;(n - 206 + 256) % 256;(n - 62 + 256) % 256"
    
    try:
        print(f"\nExample 3: Testing with full instruction set from error message")
        result, execution_time_ms = benchmark(strict_encode, value, full_instructions)
        print(f"Successfully encoded with {len(result)} operations")
        print(f"Execution time: {execution_time_ms:.2f}ms")
        print(f"First few results: {result[:5]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Example 4: Batch encoding
    values = [100, 101, 102, 103, 104]
    instructions = "(n + 111) % 256;n ^ 217;~n & 255"
    
    try:
        print(f"\nExample 4: Batch encoding {len(values)} values")
        result, execution_time_ms = benchmark(batch_encode, values, instructions)
        print(f"Execution time: {execution_time_ms:.2f}ms")
        print(f"Results: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Run performance comparison
    print("\nWould you like to run a performance comparison? (y/n)")
    choice = input().lower()
    if choice == 'y':
        run_performance_comparison()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            # Run the demo if requested
            demo_encoder()
        elif sys.argv[1] == "benchmark":
            # Run the performance comparison
            run_performance_comparison()
    else:
        # Otherwise, start the FastAPI server
        import uvicorn
        print("Starting FastAPI server.")
        print("Run with 'demo' argument to see encoder demo.")
        print("Run with 'benchmark' argument to run performance tests.")
        uvicorn.run(app, host="0.0.0.0", port=8000)
