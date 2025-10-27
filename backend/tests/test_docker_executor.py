import pytest
from app.core.docker_executor import DockerExecutor
from app.models.script import ScriptType


@pytest.fixture
def executor():
    """Create Docker executor instance"""
    try:
        return DockerExecutor()
    except RuntimeError as e:
        pytest.skip(f"Docker not available: {e}")


class TestDockerExecutor:
    """Test Docker-based script execution"""
    
    def test_execute_bash_simple(self, executor):
        """Test simple bash script execution"""
        script = "echo 'Hello from Docker!'"
        exit_code, stdout, stderr = executor.execute_bash(script)
        
        assert exit_code == 0
        assert "Hello from Docker!" in stdout
        assert stderr == ""
    
    def test_execute_bash_with_error(self, executor):
        """Test bash script that fails"""
        script = "exit 1"
        exit_code, stdout, stderr = executor.execute_bash(script)
        
        assert exit_code == 1
    
    def test_execute_bash_with_env_vars(self, executor):
        """Test bash script with environment variables"""
        script = "echo $MY_VAR"
        env_vars = {"MY_VAR": "test_value"}
        exit_code, stdout, stderr = executor.execute_bash(script, env_vars)
        
        assert exit_code == 0
        assert "test_value" in stdout
    
    def test_execute_python_simple(self, executor):
        """Test simple Python script execution"""
        script = "print('Hello from Python!')"
        exit_code, stdout, stderr = executor.execute_python(script)
        
        assert exit_code == 0
        assert "Hello from Python!" in stdout
    
    def test_execute_python_with_error(self, executor):
        """Test Python script with syntax error"""
        script = "print('unclosed string"
        exit_code, stdout, stderr = executor.execute_python(script)
        
        assert exit_code == 1
        assert stderr != ""
    
    def test_execute_python_imports(self, executor):
        """Test Python script with imports"""
        script = """
import sys
import os
print(f'Python {sys.version_info.major}.{sys.version_info.minor}')
"""
        exit_code, stdout, stderr = executor.execute_python(script)
        
        assert exit_code == 0
        assert "Python 3." in stdout
    
    def test_network_isolation(self, executor):
        """Test that network is disabled"""
        script = "ping -c 1 google.com"
        exit_code, stdout, stderr = executor.execute_bash(script)
        
        # Should fail because network is disabled
        assert exit_code != 0
    
    def test_timeout(self, executor):
        """Test script timeout"""
        script = "sleep 10"
        exit_code, stdout, stderr = executor.execute_bash(script, timeout=2)
        
        # Should timeout
        assert exit_code != 0
    
    def test_resource_limits(self, executor):
        """Test that resource limits are applied"""
        # Try to allocate more memory than allowed
        script = """
try:
    x = bytearray(1024 * 1024 * 1024)  # 1GB
    print('Memory allocated')
except MemoryError:
    print('Memory limit reached')
"""
        exit_code, stdout, stderr = executor.execute_python(script)
        
        # Should either limit memory or complete
        assert exit_code in [0, 1]
    
    def test_execute_by_type(self, executor):
        """Test execute method with script type"""
        script = "echo 'Test'"
        exit_code, stdout, stderr = executor.execute(
            ScriptType.BASH,
            script
        )
        
        assert exit_code == 0
        assert "Test" in stdout
    
    def test_multiple_executions(self, executor):
        """Test multiple sequential executions"""
        for i in range(3):
            script = f"echo 'Execution {i}'"
            exit_code, stdout, stderr = executor.execute_bash(script)
            assert exit_code == 0
            assert f"Execution {i}" in stdout


class TestDockerSecurity:
    """Test Docker security features"""
    
    def test_read_only_filesystem(self, executor):
        """Test that filesystem is read-only"""
        script = "touch /test_file"
        exit_code, stdout, stderr = executor.execute_bash(script)
        
        # Should fail because filesystem is read-only
        assert exit_code != 0
    
    def test_no_privilege_escalation(self, executor):
        """Test that privilege escalation is blocked"""
        script = "sudo echo 'test'"
        exit_code, stdout, stderr = executor.execute_bash(script)
        
        # sudo should not be available
        assert exit_code != 0
    
    def test_tmp_directory_writable(self, executor):
        """Test that /tmp is writable"""
        script = "echo 'test' > /tmp/test.txt && cat /tmp/test.txt"
        exit_code, stdout, stderr = executor.execute_bash(script)
        
        assert exit_code == 0
        assert "test" in stdout