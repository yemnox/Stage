# app/models/equipment.py
from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
from ..database import db_client

class Equipment:
    def __init__(
        self,
        name: str,
        ip_address: str,
        ligne: str,
        atelier: str,
        status: str = "offline",
        data_rate: float = 0.0,
        last_checked: Optional[datetime] = None,
        _id: Optional[str] = None
    ):
        self._id = _id
        self.name = name
        self.ip_address = ip_address
        self.ligne = ligne
        self.atelier = atelier
        self.status = status
        self.data_rate = data_rate
        self.last_checked = last_checked or datetime.utcnow()

    @property
    def id(self):
        return str(self._id) if self._id else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ip_address": self.ip_address,
            "ligne": self.ligne,
            "atelier": self.atelier,
            "status": self.status,
            "data_rate": self.data_rate,
            "last_checked": self.last_checked
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Equipment':
        return cls(
            _id=str(data.get("_id")),
            name=data["name"],
            ip_address=data["ip_address"],
            ligne=data["ligne"],
            atelier=data["atelier"],
            status=data.get("status", "offline"),
            data_rate=data.get("data_rate", 0.0),
            last_checked=data.get("last_checked")
        )

    @staticmethod
    def get_collection():
        return db_client.db.equipments

    def save(self) -> str:
        equipment_data = self.to_dict()
        if "_id" in equipment_data:
            equipment_data.pop("_id")
        
        if self._id:
            result = self.get_collection().update_one(
                {"_id": ObjectId(self._id)},
                {"$set": equipment_data}
            )
            return str(self._id)
        else:
            result = self.get_collection().insert_one(equipment_data)
            self._id = str(result.inserted_id)
            return self._id

    @classmethod
    def get_by_id(cls, equipment_id: str) -> Optional['Equipment']:
        try:
            result = cls.get_collection().find_one({"_id": ObjectId(equipment_id)})
            if result:
                result["_id"] = str(result["_id"])
                return cls.from_dict(result)
            return None
        except:
            return None

    @classmethod
    def get_all(cls) -> List['Equipment']:
        results = cls.get_collection().find()
        return [cls.from_dict({**equipment, "_id": str(equipment["_id"])}) for equipment in results]

    @classmethod
    def delete(cls, equipment_id: str) -> bool:
        result = cls.get_collection().delete_one({"_id": ObjectId(equipment_id)})
        return result.deleted_count > 0

    @classmethod
    def get_by_ligne(cls, ligne: str) -> List['Equipment']:
        results = cls.get_collection().find({"ligne": ligne})
        return [cls.from_dict({**equipment, "_id": str(equipment["_id"])}) for equipment in results]

    @classmethod
    def get_by_atelier(cls, atelier: str) -> List['Equipment']:
        results = cls.get_collection().find({"atelier": atelier})
        return [cls.from_dict({**equipment, "_id": str(equipment["_id"])}) for equipment in results]