import pytest
from unittest.mock import Mock, patch
from app.services.executor_service import ExecutorService, BashExecutor
from app.models.script import ScriptType


class TestExecutorService:
    """Test executor service"""
    
    @pytest.fixture
    def mock_docker_client(self, mocker):
        """Mock Docker client"""
        client = mocker.Mock()
        client.ping.return_value = True
        return client
    
    @patch('docker.from_env')
    def test_executor_initialization(self, mock_docker, mock_docker_client):
        """Test executor initializes Docker client"""
        mock_docker.return_value = mock_docker_client
        
        service = ExecutorService()
        assert service.docker_client is not None
    
    def test_executor_handles_docker_unavailable(self, mocker):
        """Test graceful handling when Docker unavailable"""
        mocker.patch('docker.from_env', side_effect=Exception("Docker not available"))
                
        service = ExecutorService()
        exit_code, stdout, stderr = service.execute(
            ScriptType.BASH,
            "echo test",
            {}
        )
        
        assert exit_code == 1
        assert "Docker not available" in stderr
    
    @patch('docker.from_env')
    def test_bash_executor_success(self, mock_docker, mock_docker_client):
        """Test successful bash execution"""
        # Setup mock container
        mock_container = Mock()
        mock_container.id = "test123456789"
        mock_container.logs.return_value = iter([b"Hello World\n"])
        mock_container.wait.return_value = {"StatusCode": 0}
        
        mock_docker_client.containers.create.return_value = mock_container
        mock_docker.return_value = mock_docker_client
        
        executor = BashExecutor(mock_docker_client)
        exit_code, stdout, stderr = executor.execute(
            "echo 'Hello World'",
            {},
            timeout=300,
            log_callback=None
        )
        
        assert exit_code == 0
        assert "Hello World" in stdout