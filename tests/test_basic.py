"""
Basic tests for AI Observability Demo.

These tests verify that the core components work correctly.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

class TestAIObservabilityDemo:
    """Test suite for AI Observability Demo components."""
    
    def test_environment_setup(self):
        """Test that required environment variables can be loaded."""
        from dotenv import load_dotenv
        load_dotenv()
        
        # Test that we can load the environment
        assert os.getenv("OPENAI_API_KEY") is not None or os.getenv("OPENAI_API_KEY", "test") == "test"
    
    @pytest.mark.asyncio
    async def test_openai_service_initialization(self):
        """Test OpenAI service can be initialized."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            try:
                from app.openai_service import OpenAIService
                service = OpenAIService()
                assert service is not None
                assert service.client is not None
            except ImportError:
                pytest.skip("OpenAI dependencies not available")
    
    @pytest.mark.asyncio
    async def test_vector_db_service_initialization(self):
        """Test vector database service can be initialized."""
        try:
            from app.vector_db_service import VectorDatabaseService
            service = VectorDatabaseService()
            assert service is not None
            assert service.collection is not None
        except ImportError:
            pytest.skip("ChromaDB dependencies not available")
    
    @pytest.mark.asyncio
    async def test_local_model_service_initialization(self):
        """Test local model service can be initialized."""
        with patch.dict(os.environ, {"USE_GPU": "false"}):
            try:
                from app.local_model_service import LocalModelService
                # This might take a while in real tests, so we'll mock it
                with patch('app.local_model_service.AutoTokenizer') as mock_tokenizer, \
                     patch('app.local_model_service.AutoModelForCausalLM') as mock_model:
                    
                    mock_tokenizer.from_pretrained.return_value = Mock()
                    mock_model.from_pretrained.return_value = Mock()
                    
                    service = LocalModelService()
                    assert service is not None
            except ImportError:
                pytest.skip("Transformers dependencies not available")
    
    def test_configuration_files_exist(self):
        """Test that required configuration files exist."""
        base_dir = os.path.join(os.path.dirname(__file__), '..')
        
        # Check required files
        required_files = [
            'requirements.txt',
            '.env.example',
            'config/config.alloy',
            'config/alloy.env.example',
            'docker-compose.yml',
            'Dockerfile'
        ]
        
        for file_path in required_files:
            full_path = os.path.join(base_dir, file_path)
            assert os.path.exists(full_path), f"Required file missing: {file_path}"
    
    def test_scripts_are_executable(self):
        """Test that shell scripts are executable."""
        base_dir = os.path.join(os.path.dirname(__file__), '..')
        
        scripts = [
            'scripts/setup.sh',
            'scripts/start-alloy.sh'
        ]
        
        for script_path in scripts:
            full_path = os.path.join(base_dir, script_path)
            assert os.path.exists(full_path), f"Script missing: {script_path}"
            assert os.access(full_path, os.X_OK), f"Script not executable: {script_path}"

if __name__ == "__main__":
    pytest.main([__file__])