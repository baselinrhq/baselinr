"""
Service layer for connection management operations.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy.engine import Engine
from sqlalchemy import text

if TYPE_CHECKING:
    from cryptography.fernet import Fernet

try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logging.warning("cryptography library not available, password encryption disabled")

logger = logging.getLogger(__name__)


class ConnectionService:
    """Service for connection management operations."""
    
    def __init__(self, db_engine: Optional[Engine] = None):
        """
        Initialize connection service.
        
        Args:
            db_engine: Database engine for connection storage
        """
        self.db_engine = db_engine
        self._fernet = self._init_encryption()
        self._ensure_table_exists()
    
    def _init_encryption(self) -> Optional[Any]:
        """Initialize encryption key."""
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("cryptography not available, passwords will be stored in plain text")
            return None
        
        encryption_key = os.getenv("BASELINR_ENCRYPTION_KEY")
        if not encryption_key:
            logger.warning("BASELINR_ENCRYPTION_KEY not set, passwords will be stored in plain text")
            return None
        
        try:
            # If key is not bytes, try to decode it
            if isinstance(encryption_key, str):
                # Try to use as-is (Fernet key is base64-encoded string)
                return Fernet(encryption_key.encode())  # type: ignore
            return Fernet(encryption_key)  # type: ignore
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            return None
    
    def _encrypt_password(self, password: str) -> str:
        """
        Encrypt password before storage.
        
        Args:
            password: Plain text password
            
        Returns:
            Encrypted password (or plain text if encryption unavailable)
        """
        if not password:
            return password
        
        if self._fernet:
            try:
                return self._fernet.encrypt(password.encode()).decode()
            except Exception as e:
                logger.error(f"Failed to encrypt password: {e}")
                return password
        
        return password
    
    def _decrypt_password(self, encrypted: str) -> str:
        """
        Decrypt password for use.
        
        Args:
            encrypted: Encrypted password
            
        Returns:
            Plain text password (or as-is if encryption unavailable)
        """
        if not encrypted:
            return encrypted
        
        if self._fernet:
            try:
                return self._fernet.decrypt(encrypted.encode()).decode()
            except Exception as e:
                logger.error(f"Failed to decrypt password: {e}")
                return encrypted
        
        return encrypted
    
    def _encrypt_connection(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt password fields in connection config.
        
        Args:
            connection: Connection configuration dictionary
            
        Returns:
            Connection with encrypted passwords
        """
        encrypted = connection.copy()
        
        # Encrypt password field
        if 'password' in encrypted and encrypted['password']:
            encrypted['password'] = self._encrypt_password(encrypted['password'])
        
        return encrypted
    
    def _decrypt_connection(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt password fields in connection config.
        
        Args:
            connection: Connection configuration dictionary with encrypted passwords
            
        Returns:
            Connection with decrypted passwords
        """
        decrypted = connection.copy()
        
        # Decrypt password field
        if 'password' in decrypted and decrypted['password']:
            decrypted['password'] = self._decrypt_password(decrypted['password'])
        
        return decrypted
    
    def _ensure_table_exists(self):
        """Ensure connections table exists."""
        if not self.db_engine:
            logger.warning("No database engine, connections will not be persisted")
            return
        
        try:
            with self.db_engine.connect() as conn:
                # Check if table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'baselinr_saved_connections'
                    )
                """))
                
                if not result.fetchone()[0]:
                    # Create table
                    conn.execute(text("""
                        CREATE TABLE baselinr_saved_connections (
                            id VARCHAR(255) PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            connection_json JSONB NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP,
                            last_tested TIMESTAMP
                        )
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX IF NOT EXISTS idx_connections_name 
                        ON baselinr_saved_connections(name)
                    """))
                    
                    conn.commit()
                    logger.info("Created baselinr_saved_connections table")
        except Exception as e:
            logger.error(f"Failed to ensure connections table exists: {e}")
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """
        List all saved connections.
        
        Returns:
            List of connection dictionaries
        """
        if not self.db_engine:
            return []
        
        try:
            with self.db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, name, connection_json, created_at, updated_at, last_tested
                    FROM baselinr_saved_connections
                    ORDER BY created_at DESC
                """))
                
                connections = []
                for row in result:
                    connection_json = row[2]
                    if isinstance(connection_json, str):
                        connection_dict = json.loads(connection_json)
                    else:
                        connection_dict = connection_json
                    
                    # Decrypt passwords
                    connection_dict = self._decrypt_connection(connection_dict)
                    
                    connections.append({
                        "id": row[0],
                        "name": row[1],
                        "connection": connection_dict,
                        "created_at": row[3].isoformat() if isinstance(row[3], datetime) else str(row[3]),
                        "updated_at": row[4].isoformat() if isinstance(row[4], datetime) else str(row[4]) if row[4] else None,
                        "last_tested": row[5].isoformat() if isinstance(row[5], datetime) else str(row[5]) if row[5] else None,
                        "is_active": True,
                    })
                
                return connections
        except Exception as e:
            logger.error(f"Failed to list connections: {e}")
            return []
    
    def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get connection by ID.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            Connection dictionary, or None if not found
        """
        if not self.db_engine:
            return None
        
        try:
            with self.db_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, name, connection_json, created_at, updated_at, last_tested
                    FROM baselinr_saved_connections
                    WHERE id = :id
                """), {"id": connection_id})
                
                row = result.fetchone()
                if not row:
                    return None
                
                connection_json = row[2]
                if isinstance(connection_json, str):
                    connection_dict = json.loads(connection_json)
                else:
                    connection_dict = connection_json
                
                # Decrypt passwords
                connection_dict = self._decrypt_connection(connection_dict)
                
                return {
                    "id": row[0],
                    "name": row[1],
                    "connection": connection_dict,
                    "created_at": row[3].isoformat() if isinstance(row[3], datetime) else str(row[3]),
                    "updated_at": row[4].isoformat() if isinstance(row[4], datetime) else str(row[4]) if row[4] else None,
                    "last_tested": row[5].isoformat() if isinstance(row[5], datetime) else str(row[5]) if row[5] else None,
                    "is_active": True,
                }
        except Exception as e:
            logger.error(f"Failed to get connection: {e}")
            return None
    
    def save_connection(self, name: str, connection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save new connection.
        
        Args:
            name: Connection name
            connection: Connection configuration dictionary
            
        Returns:
            Saved connection dictionary with ID
        """
        if not self.db_engine:
            raise RuntimeError("Database engine not available")
        
        # Generate ID
        connection_id = str(uuid.uuid4())
        
        # Encrypt passwords
        encrypted_connection = self._encrypt_connection(connection)
        
        try:
            with self.db_engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO baselinr_saved_connections (id, name, connection_json, created_at)
                    VALUES (:id, :name, :connection_json, CURRENT_TIMESTAMP)
                """), {
                    "id": connection_id,
                    "name": name,
                    "connection_json": json.dumps(encrypted_connection),
                })
                conn.commit()
                
                logger.info(f"Saved connection: {name} ({connection_id})")
                
                return {
                    "id": connection_id,
                    "name": name,
                    "connection": connection,  # Return original (unencrypted) for response
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": None,
                    "last_tested": None,
                    "is_active": True,
                }
        except Exception as e:
            logger.error(f"Failed to save connection: {e}")
            raise RuntimeError(f"Failed to save connection: {e}")
    
    def update_connection(self, connection_id: str, name: str, connection: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update existing connection.
        
        Args:
            connection_id: Connection identifier
            name: Connection name
            connection: Connection configuration dictionary
            
        Returns:
            Updated connection dictionary
            
        Raises:
            ValueError: If connection not found
        """
        if not self.db_engine:
            raise RuntimeError("Database engine not available")
        
        # Check if connection exists
        existing = self.get_connection(connection_id)
        if not existing:
            raise ValueError(f"Connection not found: {connection_id}")
        
        # Encrypt passwords
        encrypted_connection = self._encrypt_connection(connection)
        
        try:
            with self.db_engine.connect() as conn:
                conn.execute(text("""
                    UPDATE baselinr_saved_connections
                    SET name = :name, 
                        connection_json = :connection_json,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """), {
                    "id": connection_id,
                    "name": name,
                    "connection_json": json.dumps(encrypted_connection),
                })
                conn.commit()
                
                logger.info(f"Updated connection: {name} ({connection_id})")
                
                return {
                    "id": connection_id,
                    "name": name,
                    "connection": connection,  # Return original (unencrypted) for response
                    "created_at": existing["created_at"],
                    "updated_at": datetime.utcnow().isoformat(),
                    "last_tested": existing.get("last_tested"),
                    "is_active": True,
                }
        except Exception as e:
            logger.error(f"Failed to update connection: {e}")
            raise RuntimeError(f"Failed to update connection: {e}")
    
    def delete_connection(self, connection_id: str) -> bool:
        """
        Delete connection.
        
        Args:
            connection_id: Connection identifier
            
        Returns:
            True if deleted, False if not found
        """
        if not self.db_engine:
            raise RuntimeError("Database engine not available")
        
        try:
            with self.db_engine.connect() as conn:
                result = conn.execute(text("""
                    DELETE FROM baselinr_saved_connections
                    WHERE id = :id
                """), {"id": connection_id})
                conn.commit()
                
                deleted = result.rowcount > 0
                if deleted:
                    logger.info(f"Deleted connection: {connection_id}")
                
                return deleted
        except Exception as e:
            logger.error(f"Failed to delete connection: {e}")
            raise RuntimeError(f"Failed to delete connection: {e}")

