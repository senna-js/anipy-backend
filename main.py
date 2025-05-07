import logging
import sys
from fastapi import FastAPI, Query, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import Union, List, Dict, Any, Optional
from pydantic import BaseModel
import json

# Import our secure encoder
from encoder import strict_encode, encode_string, encode_bytes

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

class StringEncodingResult(BaseModel):
    input_text: str
    encoded_values: List[List[int]]
    instructions: str

@router.get("/", tags=["Status"])
def home():
    return {"msg": "Encoder API is running!"}

@router.get("/encode/{value}", response_model=EncodingResult)
def encode_value(
    value: int,
    instructions: str = Query(
        "(n + 111) % 256;n ^ 217;~n & 255",
        description="Semicolon-separated encoding instructions"
    )
):
    """
    Encode a numeric value using the provided instructions.
    """
    try:
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

@router.get("/encode-string", response_model=StringEncodingResult)
def encode_text(
    text: str = Query(..., description="Text to encode"),
    instructions: str = Query(
        "(n + 111) % 256;n ^ 217;~n & 255",
        description="Semicolon-separated encoding instructions"
    )
):
    """
    Encode a string using the provided instructions.
    """
    try:
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

# Include router in app
app.include_router(router)

def demo_encoder():
    """
    Demonstrate the encoder functionality in a command-line context.
    """
    print("Secure Encoder Demo")
    print("===================")
    
    # Example 1: Encode a single value
    value = 100
    instructions = "(n + 111) % 256;n ^ 217;~n & 255"
    
    try:
        print(f"\nExample 1: Encoding value {value} with instructions '{instructions}'")
        result = strict_encode(value, instructions)
        print(f"Result: {result}")
        
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
        result = encode_string(text, instructions)
        print(f"Result: {result}")
        
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
        result = strict_encode(value, full_instructions)
        print(f"Successfully encoded with {len(result)} operations")
        print(f"First few results: {result[:5]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        # Run the demo if requested
        demo_encoder()
    else:
        # Otherwise, start the FastAPI server
        import uvicorn
        print("Starting FastAPI server. Run with 'demo' argument to see encoder demo.")
        uvicorn.run(app, host="0.0.0.0", port=8000)
