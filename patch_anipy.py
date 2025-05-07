"""
Patch script for anipy_api library to add the strict_encode function.
Run this script before starting your FastAPI server.
"""
import os
import sys
import importlib
import inspect
import logging
from pathlib import Path
import types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def patch_anipy_api():
    """
    Patch the anipy_api library to include the strict_encode function.
    This function injects the strict_encode function into all anipy_api modules.
    """
    try:
        # Import our strict_encode function
        from encoder import strict_encode
        
        # Import anipy_api
        import anipy_api
        
        # Add strict_encode to the anipy_api package
        anipy_api.strict_encode = strict_encode
        
        # Add strict_encode to all anipy_api modules
        for module_name in list(sys.modules.keys()):
            if module_name.startswith('anipy_api'):
                module = sys.modules[module_name]
                if not hasattr(module, 'strict_encode'):
                    setattr(module, 'strict_encode', strict_encode)
                    logger.info(f"Added strict_encode to module: {module_name}")
        
        # Add strict_encode to builtins
        import builtins
        builtins.strict_encode = strict_encode
        logger.info("Added strict_encode to builtins")
        
        # Find all classes in anipy_api modules and add strict_encode to their namespaces
        for module_name in list(sys.modules.keys()):
            if module_name.startswith('anipy_api'):
                module = sys.modules[module_name]
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and obj.__module__.startswith('anipy_api'):
                        # Add strict_encode to the class
                        if not hasattr(obj, 'strict_encode'):
                            setattr(obj, 'strict_encode', staticmethod(strict_encode))
                            logger.info(f"Added strict_encode to class: {obj.__name__} in {module_name}")
        
        # Create a module finder that will inject strict_encode into newly imported modules
        class StrictEncodeInjector(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path, target=None):
                if fullname.startswith('anipy_api'):
                    # Get the original spec
                    for finder in sys.meta_path:
                        if finder is not self:
                            spec = finder.find_spec(fullname, path, target)
                            if spec is not None:
                                # Create a custom loader that will inject strict_encode
                                original_loader = spec.loader
                                
                                class CustomLoader:
                                    def create_module(self, spec):
                                        return original_loader.create_module(spec)
                                    
                                    def exec_module(self, module):
                                        # Execute the original module
                                        original_loader.exec_module(module)
                                        
                                        # Inject strict_encode
                                        if not hasattr(module, 'strict_encode'):
                                            module.strict_encode = strict_encode
                                            logger.info(f"Injected strict_encode into newly imported module: {fullname}")
                                
                                spec.loader = types.SimpleNamespace(
                                    create_module=CustomLoader().create_module,
                                    exec_module=CustomLoader().exec_module
                                )
                                return spec
                return None
        
        # Add our injector to sys.meta_path
        sys.meta_path.insert(0, StrictEncodeInjector())
        logger.info("Added StrictEncodeInjector to sys.meta_path")
        
        # Monkey patch the Anime class specifically
        from anipy_api.anime import Anime
        
        # Save the original get_episodes method
        original_get_episodes = Anime.get_episodes
        
        # Create a patched version that ensures strict_encode is available
        def patched_get_episodes(self, lang=None):
            # Ensure strict_encode is available
            if not hasattr(builtins, 'strict_encode'):
                from encoder import strict_encode
                builtins.strict_encode = strict_encode
                logger.info("Re-added strict_encode to builtins during get_episodes call")
            
            # Call the original method
            return original_get_episodes(self, lang)
        
        # Replace the method
        Anime.get_episodes = patched_get_episodes
        logger.info("Monkey patched Anime.get_episodes method")
        
        return True
    except Exception as e:
        logger.error(f"Failed to patch anipy_api: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = patch_anipy_api()
    if success:
        print("Successfully patched anipy_api library")
    else:
        print("Failed to patch anipy_api library")
