"""Script to download the all-MiniLM-L6-v2 model locally for deployment."""

import os
import sys

# Ensure offline mode variables are disabled so we can actually download!
os.environ.pop("TRANSFORMERS_OFFLINE", None)
os.environ.pop("HF_HUB_OFFLINE", None)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("Error: sentence-transformers is not installed. Run 'pip install sentence-transformers'")
    sys.exit(1)

def main():
    model_name = "all-MiniLM-L6-v2"
    base_dir = os.path.dirname(os.path.abspath(__file__))
    save_path = os.path.join(base_dir, "models", model_name)

    print(f"Downloading {model_name}...")
    print("This may take a few moments.")
    
    # Download and load the model into memory
    model = SentenceTransformer(model_name)
    
    # Save the model to the local directory
    os.makedirs(save_path, exist_ok=True)
    model.save(save_path)
    
    print(f"✅ Model successfully saved to: {save_path}")
    print("You can now run your backend locally without internet access to HuggingFace.")

if __name__ == "__main__":
    main()
