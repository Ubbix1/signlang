import tempfile
import os
from huggingface_hub import snapshot_download

# Create a temporary directory and download the model
with tempfile.TemporaryDirectory() as tmpdirname:
    model_path = snapshot_download(repo_id='cdsteameight/ISL-SignLanguageTranslation', local_dir=tmpdirname)
    print(f'Files in {model_path}:')
    
    # Walk through the directory and list all files
    for root, dirs, files in os.walk(model_path):
        for file in files:
            full_path = os.path.join(root, file)
            print(full_path)
            
            # Print file size
            size_bytes = os.path.getsize(full_path)
            size_mb = size_bytes / (1024 * 1024)
            print(f'  Size: {size_mb:.2f} MB')
            
            # If it's a Keras model file, print extra info
            if file.endswith('.keras'):
                print(f'  Found Keras model file: {file}') 