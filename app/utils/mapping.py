"""
Activity Mapping Utility
Handles mapping between display labels and activity IDs
"""
from pathlib import Path
from typing import Optional


class ActivityMapping:
    """Load and query activity mappings"""

    def __init__(self, mapping_file: str = None):
        if mapping_file is None:
            # Default to conf directory
            base_dir = Path(__file__).resolve().parent.parent.parent
            mapping_file = base_dir / "conf" / "activity_mapping.txt"

        self.mapping_file = Path(mapping_file)
        self.mappings: list[tuple[str, str]] = []  # (display_name, activity_id)
        self._load_mappings()

    def _load_mappings(self):
        """Load mappings from file"""
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        display_name = parts[0].strip()
                        activity_id = parts[1].strip()
                        self.mappings.append((display_name, activity_id))
        except FileNotFoundError:
            print(f"Warning: Mapping file not found at {self.mapping_file}")
        except Exception as e:
            print(f"Error loading mappings: {e}")

    def find_activity(self, label: str) -> Optional[str]:
        """
        Find activity ID by label using fuzzy matching

        Args:
            label: The label text from the draw.io element

        Returns:
            Activity ID if found, None otherwise
        """
        if not label:
            return None

        label_lower = label.lower().strip()

        # First try exact match (case-insensitive)
        for display_name, activity_id in self.mappings:
            if display_name.lower() == label_lower:
                return activity_id

        # Then try contains match
        for display_name, activity_id in self.mappings:
            if display_name.lower() in label_lower or label_lower in display_name.lower():
                return activity_id

        # Try partial match for each word
        label_words = label_lower.split()
        for display_name, activity_id in self.mappings:
            display_lower = display_name.lower()
            # Check if any significant word matches
            for word in label_words:
                if len(word) > 2 and word in display_lower:
                    return activity_id

        return None

    def get_all_mappings(self) -> list[tuple[str, str]]:
        """Get all mappings"""
        return self.mappings

    def has_mapping(self) -> bool:
        """Check if any mappings are loaded"""
        return len(self.mappings) > 0
