"""
Library management module.
Handles adding, updating, and retrieving items from the video library.
"""
import json
from pathlib import Path
from typing import List, Dict
from config import LIBRARY_DIR

class Library:
    def __init__(self, library_dir: str):
        self.library_dir = Path(library_dir)
        self.library_dir.mkdir(parents=True, exist_ok=True)
        
    def add_item(self, item_data: dict) -> str:
        """
        Add a new item to the library.
        
        Args:
            item_data: Processed video data including analysis
            
        Returns:
            str: ID of the added item
        """
        item_id = item_data.get('video_id')
        if not item_id:
            raise ValueError("Item data must include video_id")
            
        # Save item data
        item_path = self.library_dir / f"{item_id}_with_videos.json"
        with open(item_path, 'w') as f:
            json.dump(item_data, f, indent=2)
            
        return item_id
    
    def get_item(self, item_id: str) -> dict:
        """Get item data by ID."""
        item_path = self.library_dir / f"{item_id}_with_videos.json"
        if not item_path.exists():
            raise FileNotFoundError(f"Item {item_id} not found")
            
        with open(item_path) as f:
            return json.load(f)
    
    def get_all_items(self) -> List[Dict]:
        """Get all items in the library."""
        items = []
        for item_path in self.library_dir.glob('*_with_videos.json'):
            with open(item_path) as f:
                items.append(json.load(f))
        return items
    
    def update_item(self, item_id: str, updates: dict) -> dict:
        """Update an existing item."""
        item = self.get_item(item_id)
        item.update(updates)
        
        item_path = self.library_dir / f"{item_id}_with_videos.json"
        with open(item_path, 'w') as f:
            json.dump(item, f, indent=2)
            
        return item

# Create a global library instance
library = Library(str(LIBRARY_DIR))

# Export functions that match the interface expected by __init__.py
def add_to_library(item_data: dict) -> str:
    """Add a new item to the library."""
    return library.add_item(item_data)

def get_library_items() -> List[Dict]:
    """Get all items in the library."""
    return library.get_all_items()

def get_library_item(item_id: str) -> dict:
    """Get a specific item from the library."""
    return library.get_item(item_id)

def update_library_item(item_id: str, updates: dict) -> dict:
    """Update an existing item in the library."""
    return library.update_item(item_id, updates)
