# app/models/database_models.py
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from bson import ObjectId
from pydantic import BaseModel, Field
from enum import Enum
import bcrypt
from ..database import db_client

# Permission and Role definitions
class Permission(Enum):
    VIEW_DASHBOARD = "VIEW_DASHBOARD"
    MANAGE_DEVICES = "MANAGE_DEVICES"
    MANAGE_USERS = "MANAGE_USERS"
    VIEW_REPORTS = "VIEW_REPORTS"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"

class Role(Enum):
    VIEWER = {
        "name": "viewer",
        "permissions": {Permission.VIEW_DASHBOARD.value}
    }
    OPERATOR = {
        "name": "operator", 
        "permissions": {Permission.VIEW_DASHBOARD.value, Permission.VIEW_REPORTS.value}
    }
    MANAGER = {
        "name": "manager",
        "permissions": {
            Permission.VIEW_DASHBOARD.value, 
            Permission.MANAGE_DEVICES.value,
            Permission.VIEW_REPORTS.value
        }
    }
    ADMIN = {
        "name": "admin",
        "permissions": {
            Permission.VIEW_DASHBOARD.value,
            Permission.MANAGE_DEVICES.value, 
            Permission.MANAGE_USERS.value,
            Permission.VIEW_REPORTS.value,
            Permission.SYSTEM_ADMIN.value
        }
    }

# Pydantic Models for API
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

# User Model
class User:
    def __init__(
        self,
        name: str,
        username: str,
        email: str = None,
        password: str = None,
        role: str = "viewer",
        domain: str = None,
        is_active: bool = True,
        windows_auth: bool = False,
        _id: str = None
    ):
        self._id = ObjectId(_id) if _id else None
        self.name = name
        self.username = username
        self.email = email
        self.password_hash = self._hash_password(password) if password else None
        self.role = role
        self.domain = domain
        self.is_active = is_active
        self.windows_auth = windows_auth
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.last_login = None

    @property
    def id(self):
        return str(self._id) if self._id else None

    @property
    def permissions(self) -> Set[str]:
        """Get permissions for the user's role."""
        for role in Role:
            if role.value["name"] == self.role:
                return set(role.value["permissions"])
        return set()

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == "admin"

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        if not password:
            return None
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str) -> bool:
        """Verify a password against the hash."""
        if not self.password_hash or not password:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "role": self.role,
            "domain": self.domain,
            "is_active": self.is_active,
            "windows_auth": self.windows_auth,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        user = cls(
            _id=str(data.get("_id")),
            name=data["name"],
            username=data["username"],
            email=data.get("email"),
            role=data.get("role", "viewer"),
            domain=data.get("domain"),
            is_active=data.get("is_active", True),
            windows_auth=data.get("windows_auth", False)
        )
        user.password_hash = data.get("password_hash")
        user.created_at = data.get("created_at", datetime.utcnow())
        user.updated_at = data.get("updated_at", datetime.utcnow())
        user.last_login = data.get("last_login")
        return user

    @staticmethod
    def get_collection():
        return db_client.db.users

    def save(self) -> str:
        """Save user to database."""
        self.updated_at = datetime.utcnow()
        user_data = self.to_dict()
        
        if "_id" in user_data:
            user_data.pop("_id")
        
        if self._id:
            result = self.get_collection().update_one(
                {"_id": self._id},
                {"$set": user_data}
            )
            return str(self._id)
        else:
            result = self.get_collection().insert_one(user_data)
            self._id = result.inserted_id
            return str(self._id)

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional['User']:
        try:
            result = cls.get_collection().find_one({"_id": ObjectId(user_id)})
            if result:
                return cls.from_dict(result)
            return None
        except:
            return None

    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        result = cls.get_collection().find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
        if result:
            return cls.from_dict(result)
        return None

    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        result = cls.get_collection().find_one({"email": email})
        if result:
            return cls.from_dict(result)
        return None

    @classmethod
    def get_all(cls) -> List['User']:
        results = cls.get_collection().find()
        return [cls.from_dict(user) for user in results]

    @classmethod
    def delete(cls, user_id: str) -> bool:
        result = cls.get_collection().delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0

    def update_last_login(self):
        """Update the last login timestamp."""
        self.last_login = datetime.utcnow()
        self.get_collection().update_one(
            {"_id": self._id},
            {"$set": {"last_login": self.last_login}}
        )

# Equipment Model
class Equipment:
    def __init__(
        self,
        name: str,
        ip_address: str,
        ligne: str,
        atelier: str,
        description: str = None,
        location: str = None,
        equipment_type: str = "network",
        status: str = "offline",
        data_rate: float = 0.0,
        response_time: float = None,
        packet_loss: float = None,
        last_checked: datetime = None,
        is_active: bool = True,
        _id: str = None
    ):
        self._id = ObjectId(_id) if _id else None
        self.name = name
        self.ip_address = ip_address
        self.ligne = ligne
        self.atelier = atelier
        self.description = description
        self.location = location
        self.equipment_type = equipment_type
        self.status = status
        self.data_rate = data_rate
        self.response_time = response_time
        self.packet_loss = packet_loss
        self.last_checked = last_checked or datetime.utcnow()
        self.is_active = is_active
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    @property
    def id(self):
        return str(self._id) if self._id else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ip_address": self.ip_address,
            "ligne": self.ligne,
            "atelier": self.atelier,
            "description": self.description,
            "location": self.location,
            "equipment_type": self.equipment_type,
            "status": self.status,
            "data_rate": self.data_rate,
            "response_time": self.response_time,
            "packet_loss": self.packet_loss,
            "last_checked": self.last_checked,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Equipment':
        return cls(
            _id=str(data.get("_id")),
            name=data["name"],
            ip_address=data["ip_address"],
            ligne=data["ligne"],
            atelier=data["atelier"],
            description=data.get("description"),
            location=data.get("location"),
            equipment_type=data.get("equipment_type", "network"),
            status=data.get("status", "offline"),
            data_rate=data.get("data_rate", 0.0),
            response_time=data.get("response_time"),
            packet_loss=data.get("packet_loss"),
            last_checked=data.get("last_checked"),
            is_active=data.get("is_active", True)
        )

    @staticmethod
    def get_collection():
        return db_client.db.equipment

    def save(self) -> str:
        """Save equipment to database."""
        self.updated_at = datetime.utcnow()
        equipment_data = self.to_dict()
        
        if "_id" in equipment_data:
            equipment_data.pop("_id")
        
        if self._id:
            result = self.get_collection().update_one(
                {"_id": self._id},
                {"$set": equipment_data}
            )
            return str(self._id)
        else:
            result = self.get_collection().insert_one(equipment_data)
            self._id = result.inserted_id
            return str(self._id)

    @classmethod
    def get_by_id(cls, equipment_id: str) -> Optional['Equipment']:
        try:
            result = cls.get_collection().find_one({"_id": ObjectId(equipment_id)})
            if result:
                return cls.from_dict(result)
            return None
        except:
            return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional['Equipment']:
        result = cls.get_collection().find_one({"name": name})
        if result:
            return cls.from_dict(result)
        return None

    @classmethod
    def get_by_ip(cls, ip_address: str) -> Optional['Equipment']:
        result = cls.get_collection().find_one({"ip_address": ip_address})
        if result:
            return cls.from_dict(result)
        return None

    @classmethod
    def get_all(cls, active_only: bool = True) -> List['Equipment']:
        query = {"is_active": True} if active_only else {}
        results = cls.get_collection().find(query)
        return [cls.from_dict(equipment) for equipment in results]

    @classmethod
    def get_by_ligne(cls, ligne: str, active_only: bool = True) -> List['Equipment']:
        query = {"ligne": ligne}
        if active_only:
            query["is_active"] = True
        results = cls.get_collection().find(query)
        return [cls.from_dict(equipment) for equipment in results]

    @classmethod
    def get_by_atelier(cls, atelier: str, active_only: bool = True) -> List['Equipment']:
        query = {"atelier": atelier}
        if active_only:
            query["is_active"] = True
        results = cls.get_collection().find(query)
        return [cls.from_dict(equipment) for equipment in results]

    @classmethod
    def delete(cls, equipment_id: str) -> bool:
        result = cls.get_collection().delete_one({"_id": ObjectId(equipment_id)})
        return result.deleted_count > 0

    def soft_delete(self):
        """Soft delete equipment by setting is_active to False."""
        self.is_active = False
        self.save()

# Equipment History Model
class EquipmentHistory:
    def __init__(
        self,
        equipment_id: str,
        timestamp: datetime,
        status: str,
        data_rate: float = 0.0,
        response_time: float = None,
        packet_loss: float = None,
        snmp_data: Dict = None,
        _id: str = None
    ):
        self._id = ObjectId(_id) if _id else None
        self.equipment_id = ObjectId(equipment_id)
        self.timestamp = timestamp
        self.status = status
        self.data_rate = data_rate
        self.response_time = response_time
        self.packet_loss = packet_loss
        self.snmp_data = snmp_data or {}

    @property
    def id(self):
        return str(self._id) if self._id else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "equipment_id": self.equipment_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "data_rate": self.data_rate,
            "response_time": self.response_time,
            "packet_loss": self.packet_loss,
            "snmp_data": self.snmp_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EquipmentHistory':
        return cls(
            _id=str(data.get("_id")),
            equipment_id=str(data["equipment_id"]),
            timestamp=data["timestamp"],
            status=data["status"],
            data_rate=data.get("data_rate", 0.0),
            response_time=data.get("response_time"),
            packet_loss=data.get("packet_loss"),
            snmp_data=data.get("snmp_data", {})
        )

    @staticmethod
    def get_collection():
        return db_client.db.equipment_history

    def save(self) -> str:
        """Save equipment history to database."""
        history_data = self.to_dict()
        
        if "_id" in history_data:
            history_data.pop("_id")
        
        if self._id:
            result = self.get_collection().update_one(
                {"_id": self._id},
                {"$set": history_data}
            )
            return str(self._id)
        else:
            result = self.get_collection().insert_one(history_data)
            self._id = result.inserted_id
            return str(self._id)

    @classmethod
    def get_by_equipment(cls, equipment_id: str, limit: int = 50) -> List['EquipmentHistory']:
        results = cls.get_collection().find(
            {"equipment_id": ObjectId(equipment_id)}
        ).sort("timestamp", -1).limit(limit)
        return [cls.from_dict(history) for history in results]

    @classmethod
    def cleanup_old_records(cls, days: int = 30):
        """Remove records older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = cls.get_collection().delete_many({"timestamp": {"$lt": cutoff_date}})
        return result.deleted_count

# Alert Model
class Alert:
    def __init__(
        self,
        equipment_id: str,
        alert_type: str,
        severity: str,
        message: str,
        timestamp: datetime = None,
        acknowledged: bool = False,
        acknowledged_by: str = None,
        acknowledged_at: datetime = None,
        resolved: bool = False,
        resolved_at: datetime = None,
        _id: str = None
    ):
        self._id = ObjectId(_id) if _id else None
        self.equipment_id = ObjectId(equipment_id)
        self.alert_type = alert_type  # "connectivity", "performance", "threshold"
        self.severity = severity  # "low", "medium", "high", "critical"
        self.message = message
        self.timestamp = timestamp or datetime.utcnow()
        self.acknowledged = acknowledged
        self.acknowledged_by = acknowledged_by
        self.acknowledged_at = acknowledged_at
        self.resolved = resolved
        self.resolved_at = resolved_at

    @property
    def id(self):
        return str(self._id) if self._id else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "equipment_id": self.equipment_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "message": self.message,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        return cls(
            _id=str(data.get("_id")),
            equipment_id=str(data["equipment_id"]),
            alert_type=data["alert_type"],
            severity=data["severity"],
            message=data["message"],
            timestamp=data.get("timestamp"),
            acknowledged=data.get("acknowledged", False),
            acknowledged_by=data.get("acknowledged_by"),
            acknowledged_at=data.get("acknowledged_at"),
            resolved=data.get("resolved", False),
            resolved_at=data.get("resolved_at")
        )

    @staticmethod
    def get_collection():
        return db_client.db.alerts

    def save(self) -> str:
        """Save alert to database."""
        alert_data = self.to_dict()
        
        if "_id" in alert_data:
            alert_data.pop("_id")
        
        if self._id:
            result = self.get_collection().update_one(
                {"_id": self._id},
                {"$set": alert_data}
            )
            return str(self._id)
        else:
            result = self.get_collection().insert_one(alert_data)
            self._id = result.inserted_id
            return str(self._id)

    @classmethod
    def get_active_alerts(cls, limit: int = 100) -> List['Alert']:
        """Get unresolved alerts."""
        results = cls.get_collection().find(
            {"resolved": False}
        ).sort("timestamp", -1).limit(limit)
        return [cls.from_dict(alert) for alert in results]

    @classmethod
    def get_by_equipment(cls, equipment_id: str, limit: int = 50) -> List['Alert']:
        results = cls.get_collection().find(
            {"equipment_id": ObjectId(equipment_id)}
        ).sort("timestamp", -1).limit(limit)
        return [cls.from_dict(alert) for alert in results]

    def acknowledge(self, user_id: str):
        """Acknowledge the alert."""
        self.acknowledged = True
        self.acknowledged_by = user_id
        self.acknowledged_at = datetime.utcnow()
        self.save()

    def resolve(self):
        """Mark alert as resolved."""
        self.resolved = True
        self.resolved_at = datetime.utcnow()
        self.save()

# Configuration Model for storing system settings
class SystemConfig:
    def __init__(
        self,
        key: str,
        value: Any,
        description: str = None,
        updated_by: str = None,
        updated_at: datetime = None,
        _id: str = None
    ):
        self._id = ObjectId(_id) if _id else None
        self.key = key
        self.value = value
        self.description = description
        self.updated_by = updated_by
        self.updated_at = updated_at or datetime.utcnow()

    @property
    def id(self):
        return str(self._id) if self._id else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemConfig':
        return cls(
            _id=str(data.get("_id")),
            key=data["key"],
            value=data["value"],
            description=data.get("description"),
            updated_by=data.get("updated_by"),
            updated_at=data.get("updated_at")
        )

    @staticmethod
    def get_collection():
        return db_client.db.system_config

    def save(self) -> str:
        """Save config to database."""
        self.updated_at = datetime.utcnow()
        config_data = self.to_dict()
        
        if "_id" in config_data:
            config_data.pop("_id")
        
        # Use upsert for config values
        result = self.get_collection().update_one(
            {"key": self.key},
            {"$set": config_data},
            upsert=True
        )
        
        if result.upserted_id:
            self._id = result.upserted_id
        
        return str(self._id) if self._id else str(result.upserted_id)

    @classmethod
    def get_by_key(cls, key: str) -> Optional['SystemConfig']:
        result = cls.get_collection().find_one({"key": key})
        if result:
            return cls.from_dict(result)
        return None

    @classmethod
    def get_all(cls) -> List['SystemConfig']:
        results = cls.get_collection().find()
        return [cls.from_dict(config) for config in results]