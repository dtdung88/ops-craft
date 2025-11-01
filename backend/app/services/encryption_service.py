"""
Enhanced Encryption Service with Dynamic Salts and Key Rotation
File: backend/app/core/encryption.py
"""

from cryptography.fernet import Fernet
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
    Enhanced encryption service with:
    - Dynamic salt generation per encryption
    - PBKDF2 key derivation
    - Key rotation support
    - Secure defaults
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service
        
        Args:
            master_key: Master key for encryption (defaults to settings.SECRET_KEY)
        """
        self.master_key = master_key or settings.SECRET_KEY
        self._key_cache = {}
    
    def _derive_key(self, salt: bytes, iterations: int = 100000) -> bytes:
        """
        Derive encryption key from master key using PBKDF2
        
        Args:
            salt: Salt for key derivation (16 bytes)
            iterations: Number of PBKDF2 iterations
            
        Returns:
            Derived key (32 bytes, URL-safe base64 encoded)
        """
        # Check cache first (for performance)
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
        
        # Cache the derived key (limit cache size)
        if len(self._key_cache) < 100:
            self._key_cache[cache_key] = key
        
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext with a random salt
        
        The encrypted data format is:
        [16 bytes salt][encrypted data]
        All base64 encoded
        
        Args:
            plaintext: Data to encrypt
            
        Returns:
            Base64 encoded encrypted data with embedded salt
        """
        if not plaintext:
            return ""
        
        try:
            # Generate random salt (16 bytes = 128 bits)
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
        Decrypt ciphertext with embedded salt
        
        Args:
            ciphertext: Base64 encoded encrypted data with salt
            
        Returns:
            Decrypted plaintext
        """
        if not ciphertext:
            return ""
        
        try:
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
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def rotate_key(
        self, 
        old_ciphertext: str, 
        new_master_key: str,
        old_master_key: Optional[str] = None
    ) -> str:
        """
        Rotate encryption key for a value
        
        Args:
            old_ciphertext: Currently encrypted data
            new_master_key: New master key to use
            old_master_key: Old master key (defaults to current)
            
        Returns:
            Re-encrypted data with new key
        """
        try:
            # Decrypt with old key
            old_service = EncryptionService(old_master_key or self.master_key)
            plaintext = old_service.decrypt(old_ciphertext)
            
            # Encrypt with new key
            new_service = EncryptionService(new_master_key)
            new_ciphertext = new_service.encrypt(plaintext)
            
            logger.info("Key rotation successful")
            return new_ciphertext
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise ValueError(f"Key rotation failed: {str(e)}")
    
    def verify_encryption(self, ciphertext: str) -> bool:
        """
        Verify that ciphertext can be decrypted
        
        Args:
            ciphertext: Encrypted data to verify
            
        Returns:
            True if valid and decryptable
        """
        try:
            self.decrypt(ciphertext)
            return True
        except Exception:
            return False
    
    def clear_cache(self):
        """Clear the key derivation cache"""
        self._key_cache.clear()
        logger.debug("Encryption key cache cleared")


class LegacyEncryptionService:
    """
    Legacy encryption service for backward compatibility
    Uses fixed salt (for data encrypted with old method)
    
    Only use this for migrating old data!
    """
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or settings.SECRET_KEY
        # Fixed salt from original implementation
        self.fixed_salt = b'devops_script_manager_salt_v1'
        self.key = self._derive_key()
        self.cipher = Fernet(self.key)
    
    def _derive_key(self) -> bytes:
        """Derive key using fixed salt (legacy method)"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.fixed_salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return key
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt using legacy method"""
        if not ciphertext:
            return ""
        
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Legacy decryption failed: {str(e)}")


def migrate_legacy_encryption(old_ciphertext: str) -> str:
    """
    Migrate data from legacy encryption to new format
    
    Args:
        old_ciphertext: Data encrypted with legacy method
        
    Returns:
        Data re-encrypted with new method
    """
    try:
        # Decrypt using legacy method
        legacy_service = LegacyEncryptionService()
        plaintext = legacy_service.decrypt(old_ciphertext)
        
        # Re-encrypt using new method
        new_service = EncryptionService()
        new_ciphertext = new_service.encrypt(plaintext)
        
        logger.info("Successfully migrated legacy encrypted data")
        return new_ciphertext
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise ValueError(f"Failed to migrate legacy encryption: {str(e)}")


# Global encryption service instance
encryption_service = EncryptionService()