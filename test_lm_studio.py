"""
Quick Test Script for LM Studio Multimodal Integration
Tests: Connection, Text Generation, Image Processing
"""

import sys
import base64
import requests
from pathlib import Path
from typing import Dict, Any

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓{Colors.END} {text}")

def print_error(text: str):
    print(f"{Colors.RED}✗{Colors.END} {text}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠{Colors.END} {text}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ{Colors.END} {text}")


def test_lm_studio_connection(base_url: str = "http://localhost:1234/v1") -> bool:
    """Test 1: Check if LM Studio is running"""
    print_header("Test 1: LM Studio Connection")
    
    try:
        response = requests.get(f"{base_url}/models", timeout=220)
        
        if response.status_code == 200:
            models = response.json()
            print_success(f"Connected to LM Studio at {base_url}")
            
            if models.get('data'):
                print_info(f"Available models: {len(models['data'])}")
                for model in models['data']:
                    print(f"  - {model.get('id', 'Unknown')}")
                return True
            else:
                print_warning("No models loaded in LM Studio")
                print_info("Please load a model in LM Studio (Chat tab → Select Model → Load)")
                return False
        else:
            print_error(f"LM Studio returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to LM Studio at {base_url}")
        print_info("Solutions:")
        print_info("  1. Make sure LM Studio is running")
        print_info("  2. Go to Developer tab and click 'Start Server'")
        print_info("  3. Check that port 1234 is not blocked")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        return False


def test_text_generation(base_url: str = "http://localhost:1234/v1", 
                        model_name: str = "qwen3-vl-2b-instruct") -> bool:
    """Test 2: Test basic text generation"""
    print_header("Test 2: Text Generation")
    
    try:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Say 'Hello, I am working!' in one sentence."}
            ],
            "temperature": 0.7,
            "max_tokens": 50
        }
        
        print_info(f"Sending text request to model: {model_name}")
        response = requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result['choices'][0]['message']['content']
            print_success("Text generation working!")
            print(f"\n  Model response: \"{generated_text}\"\n")
            return True
        else:
            print_error(f"Request failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Text generation failed: {str(e)}")
        return False


def test_image_processing(base_url: str = "http://localhost:1234/v1", 
                         model_name: str = "qwen3-vl-2b-instruct",
                         image_path: Path = None) -> bool:
    """Test 3: Test image + text processing (multimodal)"""
    print_header("Test 3: Image Processing (Multimodal)")
    
    # Create a simple test image if none provided
    if image_path is None or not image_path.exists():
        print_info("Creating a test image...")
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a simple test image
            img = Image.new('RGB', (400, 200), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw text
            draw.rectangle([(50, 50), (350, 150)], outline='blue', width=3)
            draw.text((100, 90), "TEST IMAGE", fill='black')
            
            # Save
            test_dir = Path("temp")
            test_dir.mkdir(exist_ok=True)
            image_path = test_dir / "test_image.png"
            img.save(image_path)
            
            print_success(f"Created test image: {image_path}")
        except Exception as e:
            print_error(f"Could not create test image: {str(e)}")
            print_warning("Skipping image processing test")
            return False
    
    try:
        # Read and encode image
        print_info(f"Loading image: {image_path}")
        with open(image_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode()
        
        # Prepare multimodal request
        payload = {
            "model": model_name,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe what you see in this image briefly."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_data}"}
                    }
                ]
            }],
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        print_info(f"Sending multimodal request to model: {model_name}")
        print_info("This may take longer for vision models...")
        
        response = requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result['choices'][0]['message']['content']
            print_success("Multimodal generation working! 🎉")
            print(f"\n  Model's image description: \"{generated_text}\"\n")
            return True
        elif response.status_code == 400:
            print_error("Model doesn't support vision (400 error)")
            print_info("Solutions:")
            print_info(f"  1. Current model: {model_name}")
            print_info("  2. Make sure this is a VLM (Vision-Language Model)")
            print_info("  3. Recommended VLMs:")
            print_info("     - qwen2-vl-2b-instruct (small, fast)")
            print_info("     - qwen2-vl-7b-instruct (better quality)")
            print_info("     - llava-v1.6-mistral-7b")
            print_info("  4. Download in LM Studio: Search → 'qwen2-vl' → Download")
            return False
        else:
            print_error(f"Request failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Image processing failed: {str(e)}")
        return False


def test_python_integration() -> bool:
    """Test 4: Test Python project integration"""
    print_header("Test 4: Python Project Integration")
    
    try:
        # Test imports
        print_info("Testing imports...")
        
        try:
            from config import config
            print_success("✓ config module loaded")
        except ImportError as e:
            print_error(f"Cannot import config: {e}")
            return False
        
        try:
            from utils.llm_wrapper import LocalLLM
            print_success("✓ llm_wrapper module loaded")
        except ImportError as e:
            print_error(f"Cannot import llm_wrapper: {e}")
            return False
        
        # Test LLM initialization
        print_info("Initializing LocalLLM...")
        try:
            llm = LocalLLM()
            print_success(f"✓ LocalLLM initialized")
            print_info(f"  Model: {llm.model}")
            print_info(f"  Base URL: {llm.base_url}")
            print_info(f"  Is VLM: {llm.is_vlm}")
            
            if not llm.is_vlm:
                print_warning("Warning: Model may not support vision")
                print_info("For multimodal, use a VLM like 'qwen2-vl-2b-instruct'")
        except Exception as e:
            print_error(f"Failed to initialize LocalLLM: {e}")
            return False
        
        # Test connection
        print_info("Testing LM Studio connection...")
        if llm._check_connection():
            print_success("✓ Connected to LM Studio")
        else:
            print_error("Cannot connect to LM Studio")
            return False
        
        print_success("\nAll Python integration tests passed! ✅")
        return True
        
    except Exception as e:
        print_error(f"Python integration test failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests"""
    print(f"\n{Colors.BOLD}🧪 LM Studio Multimodal Integration Test Suite{Colors.END}\n")
    
    # Load config
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        base_url = os.getenv("LLM_STUDIO_BASE_URL", "http://localhost:1234/v1").rstrip('/')
        model_name = os.getenv("LOCAL_LLM_MODEL", "qwen3-vl-2b-instruct")
        
        print_info(f"Base URL: {base_url}")
        print_info(f"Model: {model_name}")
    except:
        base_url = "http://localhost:1234/v1"
        model_name = "qwen3-vl-2b-instruct"
        print_warning("Could not load .env file, using defaults")
    
    results = {}
    
    # Run tests
    results['connection'] = test_lm_studio_connection(base_url)
    
    if results['connection']:
        results['text'] = test_text_generation(base_url, model_name)
        results['image'] = test_image_processing(base_url, model_name)
    else:
        print_warning("Skipping remaining tests (LM Studio not connected)")
        results['text'] = False
        results['image'] = False
    
    results['python'] = test_python_integration()
    
    # Summary
    print_header("Test Summary")
    
    total = len(results)
    passed = sum(results.values())
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {test_name.capitalize()}: {status}")
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All tests passed! Your setup is ready to go!{Colors.END}\n")
        print_info("Next steps:")
        print_info("  1. Start backend: python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000")
        print_info("  2. Start frontend: streamlit run frontend/app.py")
        print_info("  3. Open http://localhost:8501 in your browser")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  Some tests failed. Please check the errors above.{Colors.END}\n")
        print_info("Troubleshooting guide: See LM_STUDIO_SETUP.md")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
