import logging
import os
import numpy as np
from flask import current_app

logger = logging.getLogger(__name__)

# Try to import the dataset libraries, but don't fail if they're not available
HF_AVAILABLE = False
try:
    from datasets import load_dataset
    from huggingface_hub import login
    HF_AVAILABLE = True
    logger.info("HuggingFace datasets library imported successfully")
except ImportError:
    logger.warning("HuggingFace datasets library not available")

class HFDatasetManager:
    """Manages the loading and processing of HuggingFace sign language datasets"""
    
    def __init__(self, dataset_name="NAM27/sign-language", cache_dir=None):
        """
        Initialize the dataset manager
        
        Args:
            dataset_name: HuggingFace dataset identifier
            cache_dir: Directory to cache the dataset
        """
        self.dataset_name = dataset_name
        self.cache_dir = cache_dir
        self.dataset = None
        self.class_mapping = None
    
    def load_dataset(self):
        """Load the dataset from HuggingFace"""
        if not HF_AVAILABLE:
            logger.warning("Cannot load dataset: HuggingFace datasets library not available")
            return False
        
        try:
            logger.info(f"Loading dataset '{self.dataset_name}' from HuggingFace...")
            self.dataset = load_dataset(self.dataset_name, cache_dir=self.cache_dir)
            logger.info(f"Dataset loaded successfully with {len(self.dataset['train'])} training examples")
            
            # Extract class mapping if available
            if 'label' in self.dataset['train'].features:
                self.class_mapping = self.dataset['train'].features['label'].names
                logger.info(f"Found {len(self.class_mapping)} classes in the dataset")
            
            return True
        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            return False
    
    def get_class_names(self):
        """Get the class names from the dataset"""
        if self.class_mapping:
            return self.class_mapping
        
        if self.dataset and 'label' in self.dataset['train'].features:
            self.class_mapping = self.dataset['train'].features['label'].names
            return self.class_mapping
        
        return None
    
    def get_sample(self, index=0, split='train'):
        """Get a sample from the dataset"""
        if not self.dataset or split not in self.dataset:
            return None
        
        try:
            if index >= len(self.dataset[split]):
                index = 0
            
            return self.dataset[split][index]
        except Exception as e:
            logger.error(f"Error getting sample: {e}")
            return None

def init_hf_dataset(app):
    """Initialize the HuggingFace dataset in the app context"""
    if not HF_AVAILABLE:
        app.hf_dataset_manager = None
        logger.warning("HuggingFace dataset manager could not be initialized - libraries not available")
        return
    
    dataset_name = app.config.get('HF_DATASET_NAME', 'NAM27/sign-language')
    cache_dir = app.config.get('HF_CACHE_DIR', './data/huggingface')
    
    # Create dataset manager
    app.hf_dataset_manager = HFDatasetManager(dataset_name, cache_dir)
    logger.info(f"HuggingFace dataset manager initialized with dataset: {dataset_name}")
    
    # Load dataset if auto-load is enabled
    if app.config.get('HF_AUTOLOAD', False):
        app.hf_dataset_manager.load_dataset() 