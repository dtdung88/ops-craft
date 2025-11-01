"""
Unified Security Module
Combines authentication, authorization, input validation, and rate limiting
File: backend/app/core/security.py
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Request, HTTPException, status
from collections import defaultdict
import threading
import re
import logging

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# PASSWORD HASHING
# ============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Token decode failed: {e}")
        return None


def create_tokens(user_id: int, username: str, role: str) -> dict:
    """Create both access and refresh tokens"""
    token_data = {
        "sub": username,
        "user_id": user_id,
        "role": role
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """
    Rate limiter with Redis backend (if available) and local fallback
    Thread-safe implementation
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.local_cache = defaultdict(list)
        self.lock = threading.Lock()
        
        # Try to initialize Redis if available
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2
                )
                self.redis_client.ping()
                logger.info("[RATE-LIMITER] Using Redis backend")
            except Exception as e:
                logger.warning(f"[RATE-LIMITER] Redis unavailable, using local cache: {e}")
                self.redis_client = None
        else:
            logger.info("[RATE-LIMITER] Using local cache backend")
    
    def check_rate_limit(
        self, 
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> bool:
        """
        Check if request is within rate limit
        Returns True if allowed, False if rate limit exceeded
        """
        current = int(datetime.utcnow().timestamp())
        window_start = current - window_seconds
        
        # Try Redis first
        if self.redis_client:
            try:
                return self._check_redis(key, max_requests, window_seconds, current, window_start)
            except Exception as e:
                logger.error(f"[RATE-LIMITER] Redis error, falling back to local: {e}")
                # Fall through to local cache
        
        # Fallback to local cache
        return self._check_local(key, max_requests, current, window_start)
    
    def _check_redis(self, key: str, max_requests: int, window_seconds: int, 
                     current: int, window_start: int) -> bool:
        """Check rate limit using Redis"""
        pipe = self.redis_client.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current requests
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {str(current): current})
        # Set expiry
        pipe.expire(key, window_seconds)
        
        results = pipe.execute()
        request_count = results[1]
        
        return request_count < max_requests
    
    def _check_local(self, key: str, max_requests: int, 
                     current: int, window_start: int) -> bool:
        """Check rate limit using local cache"""
        with self.lock:
            # Clean old entries
            self.local_cache[key] = [
                ts for ts in self.local_cache[key] 
                if ts > window_start
            ]
            
            # Check limit
            if len(self.local_cache[key]) >= max_requests:
                return False
            
            # Add current request
            self.local_cache[key].append(current)
            return True
    
    def reset(self, key: str):
        """Reset rate limit for a key"""
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"[RATE-LIMITER] Failed to reset Redis key: {e}")
        
        with self.lock:
            if key in self.local_cache:
                del self.local_cache[key]


# Global rate limiter instance
rate_limiter = RateLimiter(redis_url=settings.REDIS_URL)


# ============================================================================
# INPUT VALIDATION
# ============================================================================

class InputValidator:
    """
    Comprehensive input validation and sanitization
    """
    
    # Dangerous patterns for script content
    DANGEROUS_PATTERNS = [
        (r'\brm\s+-rf\s+/', "Recursive deletion of root directory"),
        (r'\bdd\s+if=/dev/', "Direct disk device access"),
        (r':()\{\s*:\|\:&\s*\};:', "Fork bomb pattern"),
        (r'\bcurl\s+.*\|\s*(bash|sh)', "Piping remote content to shell"),
        (r'\bwget\s+.*\|\s*(bash|sh)', "Piping remote content to shell"),
        (r'>/dev/sd[a-z]', "Writing to disk device"),
        (r'\bchmod\s+777', "Insecure file permissions"),
        (r'/etc/(passwd|shadow)', "Access to sensitive system files"),
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bSELECT\b.*\bFROM\b.*\bWHERE\b)",
        r"(--|#|\/\*|\*\/)",
        r"(\bDROP\b|\bDELETE\b|\bTRUNCATE\b|\bUPDATE\b|\bINSERT\b)",
        r"(\bEXEC\b|\bEXECUTE\b)",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]
    
    @classmethod
    def validate_script_content(
        cls, 
        content: str, 
        script_type: str,
        max_size: int = 1_000_000  # 1MB default
    ) -> tuple[bool, List[str]]:
        """
        Validate script content for dangerous patterns
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        # Check size
        if len(content) > max_size:
            errors.append(f"Script content exceeds maximum size ({max_size / 1_000_000}MB)")
        
        # Check for dangerous patterns
        for pattern, description in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                errors.append(f"Dangerous pattern detected: {description}")
        
        # Script-specific validation
        if script_type == "bash":
            if "eval" in content.lower():
                errors.append("Use of 'eval' is discouraged for security reasons")
            if content.count("|") > 10:
                errors.append("Excessive piping detected (potential complexity issue)")
        
        elif script_type == "python":
            if "__import__" in content or "exec(" in content:
                errors.append("Dynamic code execution detected (eval, exec, __import__)")
        
        return len(errors) == 0, errors
    
    @classmethod
    def sanitize_string(
        cls, 
        value: str, 
        max_length: int = 1000,
        allow_newlines: bool = False
    ) -> str:
        """Sanitize user input string"""
        if not value:
            return ""
        
        # Trim length
        value = value[:max_length]
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Remove newlines if not allowed
        if not allow_newlines:
            value = value.replace('\n', ' ').replace('\r', '')
        
        # Strip dangerous HTML/JS
        for pattern in cls.XSS_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        # Strip leading/trailing whitespace
        return value.strip()
    
    @classmethod
    def validate_json_structure(
        cls, 
        data: Dict[str, Any], 
        max_depth: int = 10,
        max_keys: int = 100
    ) -> tuple[bool, Optional[str]]:
        """
        Validate JSON structure to prevent DoS
        Returns: (is_valid, error_message)
        """
        def count_keys(obj, depth=0) -> int:
            if depth > max_depth:
                return max_keys + 1
            
            count = 0
            if isinstance(obj, dict):
                count = len(obj)
                for value in obj.values():
                    count += count_keys(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    count += count_keys(item, depth + 1)
            
            return count
        
        def check_depth(obj, depth=0) -> bool:
            if depth > max_depth:
                return False
            if isinstance(obj, dict):
                return all(check_depth(v, depth + 1) for v in obj.values())
            elif isinstance(obj, list):
                return all(check_depth(item, depth + 1) for item in obj)
            return True
        
        if not check_depth(data):
            return False, f"JSON structure exceeds maximum depth ({max_depth})"
        
        if count_keys(data) > max_keys:
            return False, f"JSON structure exceeds maximum keys ({max_keys})"
        
        return True, None
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @classmethod
    def validate_username(cls, username: str) -> tuple[bool, Optional[str]]:
        """Validate username format"""
        if len(username) < 3:
            return False, "Username must be at least 3 characters"
        if len(username) > 50:
            return False, "Username must be less than 50 characters"
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, hyphens, and underscores"
        return True, None


# ============================================================================
# SECURITY MIDDLEWARE
# ============================================================================

class SecurityMiddleware:
    """
    Security middleware for rate limiting and security headers
    """
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
    
    async def __call__(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path == "/api/v1/health":
            response = await call_next(request)
            return self._add_security_headers(response)
        
        # Rate limiting
        client_ip = request.client.host if request.client else "unknown"
        endpoint = f"{request.method}:{request.url.path}"
        rate_key = f"rate_limit:{client_ip}:{endpoint}"
        
        # Different limits for different endpoints
        max_requests = self._get_rate_limit(endpoint)
        
        if not self.rate_limiter.check_rate_limit(rate_key, max_requests=max_requests, window_seconds=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {max_requests} requests per minute allowed"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        return self._add_security_headers(response)
    
    def _get_rate_limit(self, endpoint: str) -> int:
        """Get rate limit for specific endpoint"""
        # Authentication endpoints - stricter limits
        if "/auth/login" in endpoint or "/auth/register" in endpoint:
            return 5
        
        # Execution endpoints - moderate limits
        if "/executions" in endpoint and "POST" in endpoint:
            return 10
        
        # Read endpoints - generous limits
        if "GET" in endpoint:
            return 100
        
        # Default limit
        return 60
    
    def _add_security_headers(self, response):
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_password_strength(password: str) -> tuple[bool, List[str]]:
    """
    Check password strength
    Returns: (is_strong, list_of_issues)
    """
    issues = []
    
    if len(password) < 8:
        issues.append("Password must be at least 8 characters long")
    
    if not re.search(r'[a-z]', password):
        issues.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'[A-Z]', password):
        issues.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'\d', password):
        issues.append("Password must contain at least one number")
    
    # Optional: special characters
    # if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #     issues.append("Password should contain at least one special character")
    
    return len(issues) == 0, issues