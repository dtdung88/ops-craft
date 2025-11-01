"""
One-time migration script to re-encrypt secrets with dynamic salts
File: backend/migrations/migrate_secrets_encryption.py
"""

from app.db.session import SessionLocal
from app.models.secret import Secret
from app.services.encryption_service import encryption_service, LegacyEncryptionService
import logging

logger = logging.getLogger(__name__)


def migrate_all_secrets():
    """Migrate all secrets from legacy to new encryption"""
    db = SessionLocal()
    legacy_service = LegacyEncryptionService()
    
    try:
        secrets = db.query(Secret).all()
        logger.info(f"Found {len(secrets)} secrets to migrate")
        
        migrated = 0
        for secret in secrets:
            try:
                # Try to decrypt with new format first
                encryption_service.decrypt(secret.encrypted_value)
                logger.info(f"Secret {secret.id} already in new format")
                continue
            except:
                # Decrypt with legacy format
                try:
                    plaintext = legacy_service.decrypt(secret.encrypted_value)
                    
                    # Re-encrypt with new format
                    new_encrypted = encryption_service.encrypt(plaintext)
                    secret.encrypted_value = new_encrypted
                    
                    migrated += 1
                    logger.info(f"Migrated secret {secret.id}")
                except Exception as e:
                    logger.error(f"Failed to migrate secret {secret.id}: {e}")
        
        db.commit()
        logger.info(f"Migration complete: {migrated} secrets migrated")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_all_secrets()