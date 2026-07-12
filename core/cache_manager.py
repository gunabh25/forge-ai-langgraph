"""Persistent cache management for workflow artifacts and validation."""
import os
import json
import hashlib
from typing import Dict, Any, Optional

CACHE_FILE = ".forge_cache.json"

class CacheManager:
    def __init__(self, cache_file: str = CACHE_FILE):
        self.cache_file = cache_file
        self.cache_data = self._load_cache()
        
    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"validation": {}, "review": {}}
        
    def _save_cache(self) -> None:
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def generate_hash(*args: str) -> str:
        """Generates a stable MD5 hash from the concatenated string arguments."""
        hasher = hashlib.md5()
        for arg in args:
            hasher.update(str(arg).encode('utf-8'))
        return hasher.hexdigest()

    def get_validation(self, diagram_plan: str, plantuml_content: str) -> Optional[Dict[str, Any]]:
        key = self.generate_hash(diagram_plan, plantuml_content)
        return self.cache_data.get("validation", {}).get(key)
        
    def set_validation(self, diagram_plan: str, plantuml_content: str, result: Dict[str, Any]) -> None:
        key = self.generate_hash(diagram_plan, plantuml_content)
        self.cache_data.setdefault("validation", {})[key] = result
        self._save_cache()

    def get_review(self, plantuml_content: str) -> Optional[Dict[str, Any]]:
        key = self.generate_hash(plantuml_content)
        return self.cache_data.get("review", {}).get(key)
        
    def set_review(self, plantuml_content: str, result: Dict[str, Any]) -> None:
        key = self.generate_hash(plantuml_content)
        self.cache_data.setdefault("review", {})[key] = result
        self._save_cache()
