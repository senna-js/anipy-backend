import os
import sys
import importlib.util
from pathlib import Path

def patch_anipy_api():
    """
    Patch the anipy_api library to include the strict_encode function.
    """
    try:
        import anipy_api
        
        # Get the location of the anipy_api package
        package_dir = Path(anipy_api.__file__).parent
        
        # Import our strict_encode function
        from encoder import strict_encode
        
        # Find all Python files in the package
        python_files = list(package_dir.glob('**/*.py'))
        
        for file_path in python_files:
            # Load the module
            module_name = f"anipy_api.{file_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            
            # Add strict_encode to the module
            module.strict_encode = strict_encode
            
            # Load the module with our patched function
            spec.loader.exec_module(module)
            
            # Replace the module in sys.modules
            sys.modules[module_name] = module
            
        print(f"Successfully patched {len(python_files)} files in anipy_api")
        return True
    except Exception as e:
        print(f"Failed to patch anipy_api: {e}")
        return False

if __name__ == "__main__":
    patch_anipy_api()
