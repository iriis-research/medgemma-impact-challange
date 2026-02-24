#!/usr/bin/env python3
"""
MedGemma Model Download Script
Downloads and caches the MedGemma 1.5 4B model from HuggingFace

Usage:
    python scripts/download_model.py

Requirements:
    - HuggingFace account
    - Accept the MedGemma license at: https://huggingface.co/google/medgemma-1.5-4b-it
    - Set HF_TOKEN environment variable or pass --token argument
"""

import os
import sys
import argparse
import torch

def get_device():
    """Detect the best available device."""
    if torch.backends.mps.is_available():
        return "mps", "Apple Silicon (MPS)"
    elif torch.cuda.is_available():
        return "cuda", f"NVIDIA GPU ({torch.cuda.get_device_name(0)})"
    else:
        return "cpu", "CPU"

def download_model(model_id: str, token: str = None, cache_dir: str = None):
    """Download the MedGemma model and processor."""
    from transformers import AutoProcessor, AutoModelForImageTextToText
    
    device, device_name = get_device()
    print(f"\n🖥️  Detected device: {device_name}")
    print(f"📦 Model ID: {model_id}")
    print(f"📁 Cache directory: {cache_dir or 'default (~/.cache/huggingface)'}")
    print("-" * 50)
    
    # Download processor
    print("\n📥 Downloading processor...")
    processor = AutoProcessor.from_pretrained(
        model_id,
        token=token,
        trust_remote_code=True,
        cache_dir=cache_dir
    )
    print("✅ Processor downloaded successfully!")
    
    # Determine torch dtype
    if device == "mps":
        torch_dtype = torch.float16
        print("\n💡 Using float16 for MPS (Apple Silicon)")
    else:
        torch_dtype = torch.bfloat16
        print(f"\n💡 Using bfloat16 for {device}")
    
    # Download model
    print("\n📥 Downloading model (this may take 10-20 minutes on first run)...")
    print("   Model size: ~8GB")
    
    model = AutoModelForImageTextToText.from_pretrained(
        model_id,
        token=token,
        trust_remote_code=True,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        cache_dir=cache_dir
    )
    print("✅ Model downloaded successfully!")
    
    # Test loading to device
    print(f"\n🧪 Testing model on {device}...")
    if device == "mps":
        model = model.to(device)
    
    print("✅ Model ready for inference!")
    
    # Print memory info
    if device == "mps":
        print(f"\n📊 Note: MPS memory usage will be visible in Activity Monitor")
    elif device == "cuda":
        allocated = torch.cuda.memory_allocated() / 1024**3
        print(f"\n📊 GPU Memory used: {allocated:.2f} GB")
    
    return processor, model

def main():
    parser = argparse.ArgumentParser(description="Download MedGemma model")
    parser.add_argument(
        "--model-id",
        default="google/medgemma-1.5-4b-it",
        help="HuggingFace model ID (default: google/medgemma-1.5-4b-it)"
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("HF_TOKEN"),
        help="HuggingFace token (or set HF_TOKEN env variable)"
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Custom cache directory for model files"
    )
    args = parser.parse_args()
    
    print("=" * 50)
    print("🏥 MedGemma Model Downloader")
    print("=" * 50)
    
    if not args.token:
        print("\n⚠️  Warning: No HuggingFace token provided!")
        print("   MedGemma is a gated model. You need to:")
        print("   1. Create a HuggingFace account: https://huggingface.co/join")
        print("   2. Accept the license: https://huggingface.co/google/medgemma-1.5-4b-it")
        print("   3. Create an access token: https://huggingface.co/settings/tokens")
        print("   4. Set the token: export HF_TOKEN=your_token_here")
        print("\n   Or pass it with: python download_model.py --token YOUR_TOKEN")
        
        response = input("\nDo you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Exiting...")
            sys.exit(0)
    
    try:
        download_model(args.model_id, args.token, args.cache_dir)
        print("\n" + "=" * 50)
        print("🎉 Setup complete! You can now run the backend.")
        print("=" * 50)
        print("\nNext steps:")
        print("  1. Start the services: docker-compose -f docker-compose.services.yml up -d")
        print("  2. Run the backend: python -m uvicorn app.main:app --reload")
        print("  3. Open the API docs: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("  - Make sure you have accepted the MedGemma license on HuggingFace")
        print("  - Check your internet connection")
        print("  - Verify your HuggingFace token is correct")
        sys.exit(1)

if __name__ == "__main__":
    main()

