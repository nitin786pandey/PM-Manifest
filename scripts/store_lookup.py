"""
Store lookup utility to resolve store names to storeIds from static configuration.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional


def get_stores_config_path() -> Path:
	"""
	Get the path to stores.json configuration file.
	Looks for config/stores.json relative to the script directory or workspace root.
	"""
	script_dir = Path(__file__).parent
	workspace_root = script_dir.parent
	config_path = workspace_root / "config" / "stores.json"
	return config_path


def load_stores_config() -> Dict:
	"""
	Load stores configuration from stores.json file.
	Returns the parsed JSON content.
	"""
	config_path = get_stores_config_path()
	if not config_path.exists():
		raise FileNotFoundError(f"Stores configuration file not found: {config_path}")
	
	with open(config_path, "r", encoding="utf-8") as f:
		return json.load(f)


def normalize_store_name(name: str) -> str:
	"""
	Normalize store name for comparison (lowercase, strip whitespace).
	"""
	return name.lower().strip()


def get_store_id_from_name(store_name: str, fuzzy: bool = True) -> Optional[str]:
	"""
	Look up storeId from store name.
	
	Args:
		store_name: The store name to look up
		fuzzy: If True, also check aliases and do partial matching
	
	Returns:
		storeId if found, None otherwise
	"""
	if not store_name:
		return None
	
	try:
		config = load_stores_config()
		stores = config.get("stores", [])
	except (FileNotFoundError, json.JSONDecodeError) as e:
		print(f"Warning: Could not load stores config: {e}", file=os.sys.stderr)
		return None
	
	normalized_input = normalize_store_name(store_name)
	
	# First pass: exact match on storeName
	for store in stores:
		store_name_normalized = normalize_store_name(store.get("storeName", ""))
		if store_name_normalized == normalized_input:
			return store.get("storeId")
	
	if not fuzzy:
		return None
	
	# Second pass: check aliases
	for store in stores:
		aliases = store.get("aliases", [])
		for alias in aliases:
			if normalize_store_name(alias) == normalized_input:
				return store.get("storeId")
	
	# Third pass: partial/contains matching
	for store in stores:
		store_name_normalized = normalize_store_name(store.get("storeName", ""))
		if normalized_input in store_name_normalized or store_name_normalized in normalized_input:
			return store.get("storeId")
		
		aliases = store.get("aliases", [])
		for alias in aliases:
			alias_normalized = normalize_store_name(alias)
			if normalized_input in alias_normalized or alias_normalized in normalized_input:
				return store.get("storeId")
	
	return None


def get_all_stores() -> List[Dict]:
	"""
	Get all stores from configuration.
	
	Returns:
		List of store dictionaries with storeId, storeName, and aliases
	"""
	try:
		config = load_stores_config()
		return config.get("stores", [])
	except (FileNotFoundError, json.JSONDecodeError) as e:
		print(f"Warning: Could not load stores config: {e}", file=os.sys.stderr)
		return []


def find_stores_by_pattern(pattern: str) -> List[Dict]:
	"""
	Find stores matching a pattern (case-insensitive partial match).
	
	Args:
		pattern: Pattern to search for in store names or aliases
	
	Returns:
		List of matching store dictionaries
	"""
	if not pattern:
		return []
	
	normalized_pattern = normalize_store_name(pattern)
	stores = get_all_stores()
	matches = []
	
	for store in stores:
		store_name = normalize_store_name(store.get("storeName", ""))
		if normalized_pattern in store_name:
			matches.append(store)
			continue
		
		aliases = store.get("aliases", [])
		for alias in aliases:
			if normalized_pattern in normalize_store_name(alias):
				matches.append(store)
				break
	
	return matches
