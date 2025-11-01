import pytest
from app.core.security_enhanced import InputValidator, RateLimiter
from app.models.script import ScriptType


class TestInputValidator:
    """Test input validation"""
    
    def test_dangerous_pattern_detection(self):
        """Test detection of dangerous patterns"""
        dangerous_script = "rm -rf /"
        is_valid, errors = InputValidator.validate_script_content(
            dangerous_script, 
            "bash"
        )
        assert not is_valid
        assert len(errors) > 0
    
    def test_safe_script_validation(self):
        """Test safe script passes validation"""
        safe_script = "echo 'Hello World'"
        is_valid, errors = InputValidator.validate_script_content(
            safe_script,
            "bash"
        )
        assert is_valid
        assert len(errors) == 0
    
    def test_script_size_limit(self):
        """Test script size limitation"""
        large_script = "a" * 2_000_000  # 2MB
        is_valid, errors = InputValidator.validate_script_content(
            large_script,
            "bash"
        )
        assert not is_valid
            
    def test_sanitize_input(self):
        """Test input sanitization"""
        dirty_input = "<script>alert('xss')</script>Test"
        clean = InputValidator.sanitize_input(dirty_input)
        assert "<script>" not in clean
        assert "Test" in clean
    
    def test_json_depth_validation(self):
        """Test JSON depth validation"""
        shallow = {"a": {"b": {"c": "value"}}}
        assert InputValidator.validate_json_structure(shallow, max_depth=5)
        
        # Create deeply nested structure
        deep = {"level": 1}
        current = deep
        for i in range(10):
            current["nested"] = {"level": i + 2}
            current = current["nested"]
        
        assert not InputValidator.validate_json_structure(deep, max_depth=5)


class TestRateLimiter:
    """Test rate limiting"""
    
    @pytest.fixture
    def redis_client(self, mocker):
        """Mock Redis client"""
        return mocker.Mock()
    
    def test_rate_limit_allows_within_limit(self, redis_client):
        """Test requests within limit are allowed"""
        redis_client.pipeline().execute.return_value = [None, 5, None, None]
        
        limiter = RateLimiter(redis_client)
        assert limiter.check_rate_limit("test_key", max_requests=10, window_seconds=60)
    
    def test_rate_limit_blocks_over_limit(self, redis_client):
        """Test requests over limit are blocked"""
        redis_client.pipeline().execute.return_value = [None, 15, None, None]
        
        limiter = RateLimiter(redis_client)
        assert not limiter.check_rate_limit("test_key", max_requests=10, window_seconds=60)