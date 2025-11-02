"""
Optional: One-time migration script to convert all secrets to new format
File: backend/scripts/migrate_secrets.py

This is OPTIONAL - the encryption service now handles both formats automatically.
Only run this if you want to standardize all secrets to the new format.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.models.secret import Secret
from app.services.encryption_service import encryption_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_all_secrets():
    """
    Migrate all secrets from legacy to new encryption format
    
    Note: This is optional since the encryption service now handles both formats.
    Only run this if you want to standardize all secrets to the new format.
    """
    db = SessionLocal()
    
    try:
        secrets = db.query(Secret).all()
        logger.info(f"Found {len(secrets)} secrets to check")
        
        migrated = 0
        already_new = 0
        failed = 0
        
        for secret in secrets:
            try:
                # Test if already in new format
                if encryption_service._is_new_format(secret.encrypted_value):
                    logger.info(f"Secret {secret.id} ({secret.name}) already in new format")
                    already_new += 1
                    continue
                
                # Decrypt with automatic format detection
                plaintext = encryption_service.decrypt(secret.encrypted_value)
                
                # Re-encrypt with new format
                new_encrypted = encryption_service.encrypt(plaintext)
                secret.encrypted_value = new_encrypted
                
                migrated += 1
                logger.info(f"✓ Migrated secret {secret.id} ({secret.name})")
                
            except Exception as e:
                failed += 1
                logger.error(f"✗ Failed to migrate secret {secret.id} ({secret.name}): {e}")
        
        if failed == 0:
            db.commit()
            logger.info(f"""
Migration Summary:
==================
✓ Already new format: {already_new}
✓ Successfully migrated: {migrated}
✗ Failed: {failed}
Total secrets: {len(secrets)}
""")
        else:
            db.rollback()
            logger.error(f"Migration aborted due to {failed} failures. No changes made.")
            sys.exit(1)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting secret encryption migration...")
    logger.info("This script will convert all secrets to the new encryption format.")
    logger.info("Note: This is OPTIONAL - the service handles both formats automatically.\n")
    
    response = input("Do you want to proceed? (yes/no): ")
    if response.lower() == 'yes':
        migrate_all_secrets()
    else:
        logger.info("Migration cancelled")