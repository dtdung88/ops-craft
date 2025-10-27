from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os
from app.core.config import settings


class EncryptionService:
    """Service for encrypting and decrypting secrets"""
    
    def __init__(self):
        """Initialize encryption service with key from settings"""
        self.key = self._derive_key(settings.SECRET_KEY)
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        # Use a fixed salt for key derivation (in production, consider rotating)
        salt = b'devops_script_manager_salt_v1'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string value"""
        if not plaintext:
            return ""
        
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt an encrypted string"""
        if not ciphertext:
            return ""
        
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def rotate_key(self, old_password: str, new_password: str, encrypted_value: str) -> str:
        """Rotate encryption key for a value"""
        # Decrypt with old key
        old_service = EncryptionService()
        old_service.key = old_service._derive_key(old_password)
        old_service.cipher = Fernet(old_service.key)
        plaintext = old_service.decrypt(encrypted_value)
        
        # Encrypt with new key
        new_service = EncryptionService()
        new_service.key = new_service._derive_key(new_password)
        new_service.cipher = Fernet(new_service.key)
        return new_service.encrypt(plaintext)


# Global encryption service instance
encryption_service = EncryptionService()