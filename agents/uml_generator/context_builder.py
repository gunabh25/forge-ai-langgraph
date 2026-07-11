class ContextBuilder:
    """
    ContextBuilder is responsible for extracting and summarizing the core architecture
    details from the architecture JSON to provide context for UML generation.
    It deliberately excludes low-level implementation details to keep the focus
    on high-level system design.
    """

    def __init__(self):
        # Keywords that indicate a component is a low-level implementation detail
        self._excluded_keywords = [
            "helper",
            "repository",
            "util",
            "parser",
            "impl",
            "internal",
        ]

    def _should_include(self, name: str) -> bool:
        """
        Check if a component name should be included in the high-level summary.
        Filters out helper classes, repositories, utility modules, parser internals, etc.
        """
        if not name:
            return False
            
        name_lower = name.lower()
        for keyword in self._excluded_keywords:
            if keyword in name_lower:
                return False
        return True

    def _extract_list(self, data: list | None, title: str) -> str:
        """
        Helper to format a list of items (strings or dicts) into a summary section.
        """
        if not data:
            return ""

        lines = [f"## {title}"]
        for item in data:
            if isinstance(item, dict):
                name = item.get("name", "")
                if self._should_include(name):
                    desc = item.get("description", "")
                    if desc:
                        lines.append(f"- {name}: {desc}")
                    else:
                        lines.append(f"- {name}")
            elif isinstance(item, str):
                if self._should_include(item):
                    lines.append(f"- {item}")
        
        # Only return the section if it contains more than just the title
        if len(lines) > 1:
            lines.append("")
            return "\n".join(lines)
        return ""

    def build_summary(self, architecture_json: dict) -> str:
        """
        Builds a concise architecture summary from the provided JSON.

        Args:
            architecture_json (dict): The architecture definition dictionary.

        Returns:
            str: A readable architecture summary formatted as markdown.
        """
        if not architecture_json:
            return "No architecture details provided."

        summary_parts = []

        # 1. System Overview
        overview = architecture_json.get("system_overview", architecture_json.get("overview", ""))
        if overview:
            summary_parts.append(f"## System Overview\n{overview}\n")

        # 2. Primary Actors
        actors = architecture_json.get("primary_actors", architecture_json.get("actors", []))
        actors_section = self._extract_list(actors, "Primary Actors")
        if actors_section:
            summary_parts.append(actors_section)

        # 3. External Systems
        external_systems = architecture_json.get("external_systems", [])
        ext_sys_section = self._extract_list(external_systems, "External Systems")
        if ext_sys_section:
            summary_parts.append(ext_sys_section)

        # 4. Major Business Services
        services = architecture_json.get("major_business_services", architecture_json.get("services", []))
        services_section = self._extract_list(services, "Major Business Services")
        if services_section:
            summary_parts.append(services_section)

        # 5. Major Databases
        databases = architecture_json.get("major_databases", architecture_json.get("databases", []))
        db_section = self._extract_list(databases, "Major Databases")
        if db_section:
            summary_parts.append(db_section)

        # 6. Outputs
        outputs = architecture_json.get("outputs", [])
        outputs_section = self._extract_list(outputs, "Outputs")
        if outputs_section:
            summary_parts.append(outputs_section)

        # 7. Important Relationships
        relationships = architecture_json.get("important_relationships", architecture_json.get("relationships", []))
        if relationships:
            rel_lines = ["## Important Relationships"]
            for rel in relationships:
                if isinstance(rel, dict):
                    source = rel.get("source", "Unknown")
                    target = rel.get("target", "Unknown")
                    
                    # Only include relationship if both source and target are high-level components
                    if self._should_include(source) and self._should_include(target):
                        desc = rel.get("description", "")
                        rel_type = rel.get("type", "interacts with")
                        
                        rel_str = f"- {source} --[{rel_type}]--> {target}"
                        if desc:
                            rel_str += f": {desc}"
                        rel_lines.append(rel_str)
                elif isinstance(rel, str):
                    rel_lines.append(f"- {rel}")
            
            if len(rel_lines) > 1:
                rel_lines.append("")
                summary_parts.append("\n".join(rel_lines))

        return "\n".join(summary_parts).strip()
