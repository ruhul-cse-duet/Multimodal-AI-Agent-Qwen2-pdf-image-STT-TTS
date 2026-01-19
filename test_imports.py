"""
Quick Import Test - Verify all modules can be imported
"""
import os
import sys

# Fix OpenMP duplicate library issue
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# Add project directory to path
project_dir = r'E:\Data Science\ML_and_DL_project\NLP Project\Multimodal Vox Agent AI pdf and image'
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

print("="*60)
print("Testing Project Imports")
print("="*60)

try:
    print("\n[1/6] Testing config...")
    from config import config, Config
    print(f"  - Config loaded")
    print(f"  - LLM Model: {config.LOCAL_LLM_MODEL}")
    print(f"  - Base URL: {config.LLM_STUDIO_BASE_URL}")
    
    print("\n[2/6] Testing LLM wrapper...")
    from utils.llm_wrapper import LocalLLM
    print(f"  - LocalLLM class imported")
    
    print("\n[3/6] Testing document processor...")
    from utils.document_processor import DocumentProcessor
    print(f"  - DocumentProcessor class imported")
    
    print("\n[4/6] Testing vector store...")
    from utils.vector_store import VectorStore
    print(f"  - VectorStore class imported")
    
    print("\n[5/6] Testing audio processor...")
    from utils.audio_processor import AudioProcessor
    print(f"  - AudioProcessor class imported")
    
    print("\n[6/6] Testing multimodal agent...")
    from agents.multimodal_agent import MultimodalAgent
    print(f"  - MultimodalAgent class imported")
    
    print("\n" + "="*60)
    print("SUCCESS: All imports working!")
    print("="*60)
    
    # Test LLM initialization
    print("\n[BONUS] Testing LLM initialization...")
    try:
        llm = LocalLLM()
        print(f"  - LocalLLM initialized")
        print(f"  - Model: {llm.model}")
        print(f"  - Is VLM: {llm.is_vlm}")
        print(f"  - Base URL: {llm.base_url}")
    except Exception as e:
        print(f"  - Warning: Could not initialize LLM (this is OK if LM Studio isn't running)")
        print(f"  - Error: {str(e)}")
    
    print("\n" + "="*60)
    print("PROJECT IS READY TO USE!")
    print("="*60)
    
except Exception as e:
    print(f"\n!!! ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
