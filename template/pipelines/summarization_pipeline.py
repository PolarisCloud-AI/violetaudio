# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

import time
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from typing import Optional, Tuple


class SummarizationPipeline:
    """
    Text summarization pipeline using HuggingFace transformers.
    Supports multiple languages and model sizes.
    """
    
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        """
        Initialize the summarization pipeline.
        
        Args:
            model_name: HuggingFace model name for summarization
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.model.to(self.device)
        
        # Language code mapping
        self.language_codes = {
            "en": "english",
            "es": "spanish", 
            "fr": "french",
            "de": "german",
            "it": "italian",
            "pt": "portuguese",
            "ru": "russian",
            "ja": "japanese",
            "ko": "korean",
            "zh": "chinese"
        }
    
    def summarize(self, text: str, max_length: int = 130, min_length: int = 30, language: str = "en") -> Tuple[str, float]:
        """
        Summarize text.
        
        Args:
            text: Input text to summarize
            max_length: Maximum length of summary
            min_length: Minimum length of summary
            language: Language code (e.g., 'en', 'es', 'fr')
            
        Returns:
            Tuple of (summary_text, processing_time)
        """
        start_time = time.time()
        
        try:
            # Tokenize input text
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                max_length=1024, 
                truncation=True,
                padding=True
            ).to(self.device)
            
            # Generate summary
            summary_ids = self.model.generate(
                inputs["input_ids"],
                max_length=max_length,
                min_length=min_length,
                length_penalty=2.0,
                num_beams=4,
                early_stopping=True
            )
            
            # Decode summary
            summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            
            processing_time = time.time() - start_time
            
            return summary.strip(), processing_time
            
        except Exception as e:
            processing_time = time.time() - start_time
            raise Exception(f"Summarization failed: {str(e)}")
    
    def get_supported_languages(self) -> list:
        """Get list of supported language codes."""
        return list(self.language_codes.keys())
    
    def validate_language(self, language: str) -> bool:
        """Validate if language is supported."""
        return language in self.language_codes
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "max_input_length": self.tokenizer.model_max_length,
            "vocab_size": self.tokenizer.vocab_size
        }
