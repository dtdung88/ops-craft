"""
Enhanced Encryption Service with Backward Compatibility
File: backend/app/services/encryption_service.py
"""

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import secrets
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Enhanced encryption service with backward compatibility
    - Supports both legacy (fixed salt) and new (dynamic salt) formats
    - Automatically detects and handles both formats
    """
    
    # Legacy fixed salt for backward compatibility
    LEGACY_SALT = b'devops_script_manager_salt_v1'
    LEGACY_SALT_LENGTH = len(LEGACY_SALT)
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or settings.SECRET_KEY
        self._key_cache = {}
        
        # Initialize legacy cipher for backward compatibility
        self._legacy_cipher = self._create_legacy_cipher()
    
    def _create_legacy_cipher(self) -> Fernet:
        """Create cipher using legacy fixed salt"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.LEGACY_SALT,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return Fernet(key)
    
    def _derive_key(self, salt: bytes, iterations: int = 100000) -> bytes:
        """Derive encryption key from master key using PBKDF2"""
        cache_key = base64.b64encode(salt).decode()
        if cache_key in self._key_cache:
            return self._key_cache[cache_key]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        
        if len(self._key_cache) < 100:
            self._key_cache[cache_key] = key
        
        return key
    
    def _is_new_format(self, ciphertext: str) -> bool:
        """
        Detect if ciphertext uses new format (with embedded salt)
        New format: [16 bytes salt][encrypted data]
        Must be at least 16 bytes + minimum Fernet token size
        """
        try:
            combined = base64.urlsafe_b64decode(ciphertext.encode())
            # New format must be at least 16 (salt) + 57 (min Fernet token)
            return len(combined) >= 73
        except Exception:
            return False
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext with a random salt (NEW FORMAT)
        Format: [16 bytes salt][encrypted data] (base64 encoded)
        """
        if not plaintext:
            return ""
        
        try:
            # Generate random salt
            salt = secrets.token_bytes(16)
            
            # Derive key from salt
            key = self._derive_key(salt)
            cipher = Fernet(key)
            
            # Encrypt
            encrypted = cipher.encrypt(plaintext.encode())
            
            # Combine salt + encrypted data
            combined = salt + encrypted
            
            # Return as base64
            return base64.urlsafe_b64encode(combined).decode()
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext with automatic format detection
        Supports both legacy (fixed salt) and new (dynamic salt) formats
        """
        if not ciphertext:
            return ""
        
        try:
            # Try new format first
            if self._is_new_format(ciphertext):
                try:
                    return self._decrypt_new_format(ciphertext)
                except Exception as e:
                    logger.warning(f"New format decryption failed, trying legacy: {e}")
            
            # Fallback to legacy format
            return self._decrypt_legacy_format(ciphertext)
            
        except Exception as e:
            logger.error(f"Decryption failed for both formats: {e}")
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def _decrypt_new_format(self, ciphertext: str) -> str:
        """Decrypt new format (dynamic salt)"""
        # Decode from base64
        combined = base64.urlsafe_b64decode(ciphertext.encode())
        
        # Extract salt (first 16 bytes) and encrypted data
        salt = combined[:16]
        encrypted = combined[16:]
        
        # Derive key from salt
        key = self._derive_key(salt)
        cipher = Fernet(key)
        
        # Decrypt
        decrypted = cipher.decrypt(encrypted)
        return decrypted.decode()
    
    def _decrypt_legacy_format(self, ciphertext: str) -> str:
        """Decrypt legacy format (fixed salt)"""
        encrypted = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = self._legacy_cipher.decrypt(encrypted)
        return decrypted.decode()
    
    def migrate_to_new_format(self, old_ciphertext: str) -> str:
        """
        Migrate legacy encrypted data to new format
        This should be called during a migration script
        """
        try:
            # Decrypt using automatic detection
            plaintext = self.decrypt(old_ciphertext)
            
            # Re-encrypt using new format
            new_ciphertext = self.encrypt(plaintext)
            
            logger.info("Successfully migrated to new encryption format")
            return new_ciphertext
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise ValueError(f"Failed to migrate encryption: {str(e)}")
    
    def verify_encryption(self, ciphertext: str) -> bool:
        """Verify that ciphertext can be decrypted"""
        try:
            self.decrypt(ciphertext)
            return True
        except Exception:
            return False
    
    def clear_cache(self):
        """Clear the key derivation cache"""
        self._key_cache.clear()
        logger.debug("Encryption key cache cleared")


# Global encryption service instance
encryption_service = EncryptionService()