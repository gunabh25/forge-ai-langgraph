import collections
from typing import Dict, Any, List

class FilePlanner:
    """Plans the generation order of files based on a project manifest."""

    def __init__(self, manifest: Dict[str, Any]):
        self.manifest = manifest
        self.files = manifest.get("files", [])

    def get_file_queue(self) -> List[str]:
        """Group and sort files into a generation queue.
        
        A simple heuristic based on file path to determine generation order:
        1. Configuration / Core (main.py, config, settings)
        2. Database / Models (models/, schemas/)
        3. Data Access (repositories/)
        4. Business Logic (services/)
        5. API / Presentation (controllers/, routes/)
        6. Infrastructure / Tests / Others (middleware/, tests/, Dockerfile, README)
        """
        # Assign priorities based on path patterns (lower is earlier)
        def get_priority(filepath: str) -> int:
            f = filepath.lower()
            if "config" in f or "settings" in f or f.endswith("main.py") or f.endswith("__init__.py"):
                return 1
            if "model" in f or "schema" in f or "entity" in f:
                return 2
            if "repository" in f or "dao" in f:
                return 3
            if "service" in f or "usecase" in f:
                return 4
            if "controller" in f or "route" in f or "api" in f:
                return 5
            return 6

        # Group files by priority
        groups = collections.defaultdict(list)
        for f in self.files:
            groups[get_priority(f)].append(f)
            
        # Flatten into a single queue
        queue = []
        for priority in sorted(groups.keys()):
            queue.extend(sorted(groups[priority]))
            
        return queue
