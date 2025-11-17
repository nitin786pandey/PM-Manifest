# Store Name Context Integration

This document explains how store name context is integrated into the analytics workflow, allowing users to mention store names instead of storeIds in queries.

## Overview

The system now supports resolving store names to storeIds automatically, enabling natural language queries like:
- "What's the interaction rate for Acme Store?"
- "Show me analytics for Example Shop"

## Architecture

### Components

1. **Static Configuration** (`config/stores.json`)
   - JSON file mapping store names to storeIds
   - Supports aliases for fuzzy matching
   - Example structure:
     ```json
     {
       "stores": [
         {
           "storeId": "store_123",
           "storeName": "Acme Store",
           "aliases": ["acme", "acme store"]
         }
       ]
     }
     ```

2. **Store Lookup Utility** (`scripts/store_lookup.py`)
   - `get_store_id_from_name(store_name, fuzzy=True)` - Resolves store name to storeId
   - `get_all_stores()` - Returns all configured stores
   - `find_stores_by_pattern(pattern)` - Finds stores matching a pattern
   - Matching strategy:
     1. Exact match (case-insensitive)
     2. Alias match
     3. Partial/contains match (if fuzzy=True)

3. **Store Name Extraction** (`scripts/agent_runner.py`)
   - `extract_store_name_from_text(text)` - Extracts store names from natural language
   - Pattern matching:
     - "for [Store Name]"
     - "in [Store Name]"
     - Direct mentions of known store names

4. **Store Resolution** (`scripts/agent_runner.py`)
   - `resolve_store_id(store_id, store_name, input_text)` - Resolves storeId with priority:
     1. Explicit `--store-id` (highest priority)
     2. Explicit `--store-name` (lookup)
     3. Store name extracted from input text (lowest priority)

5. **API Context Support** (TypeScript)
   - `lib/schemas.ts` - Added `context` field with `storeName` and `storeId`
   - `lib/cursorCloud.ts` - Passes context to Cursor Cloud Agent
   - `app/api/execute-agent/route.ts` - Handles context in API requests

## Usage

### Command Line (Python Script)

```bash
# Option 1: Explicit store name
python agent_runner.py --question "interaction rate" --store-name "Acme Store"

# Option 2: Store name in question (automatic extraction)
python agent_runner.py --question "What's the interaction rate for Acme Store?"

# Option 3: Still supports store-id (backward compatible)
python agent_runner.py --question "interaction rate" --store-id "store_123"
```

### API Usage

```bash
curl -X POST https://your-api/api/execute-agent \
  -H 'Content-Type: application/json' \
  -d '{
    "agentId": "agent_123",
    "input": "What is the interaction rate for Acme Store?",
    "context": {
      "storeName": "Acme Store"
    }
  }'
```

### Slack Integration

The Slack integration automatically extracts store names from the input text. Users can simply mention store names in their questions:

```
/cursor agentId=agent_123 input="What's the interaction rate for Acme Store?"
```

## Configuration

### Adding Stores

Edit `config/stores.json` to add new stores:

```json
{
  "stores": [
    {
      "storeId": "store_123",
      "storeName": "Acme Store",
      "aliases": ["acme", "acme store", "acme inc"]
    },
    {
      "storeId": "store_456",
      "storeName": "Example Shop",
      "aliases": ["example", "example shop"]
    }
  ]
}
```

**Fields:**
- `storeId` (required): The Elasticsearch storeId value
- `storeName` (required): Primary store name for display
- `aliases` (optional): Array of alternative names for matching

## How It Works

1. **User Input**: User provides question with store name (e.g., "interaction rate for Acme Store")

2. **Extraction**: System extracts "Acme Store" from the input text using pattern matching

3. **Resolution**: System looks up "Acme Store" in `config/stores.json` and finds `storeId: "store_123"`

4. **Query Building**: All Elasticsearch queries are built with `storeId.keyword: "store_123"` filter

5. **Execution**: Queries execute with the resolved storeId, returning store-specific results

## Error Handling

- **Store name not found**: System logs a warning and queries all stores (no filter)
- **Multiple matches**: First match is used (consider adding disambiguation in future)
- **Config file missing**: System logs error and falls back to no store filtering
- **Invalid JSON**: System logs error and falls back to no store filtering

## Backward Compatibility

- Existing `--store-id` argument continues to work
- If both `--store-id` and `--store-name` provided, `--store-id` takes precedence
- Queries without store context continue to work (query all stores)

## Future Enhancements

- [ ] Disambiguation for multiple store name matches
- [ ] Store name suggestions when not found
- [ ] Dynamic store lookup from Elasticsearch (alternative to static config)
- [ ] Store name caching with TTL
- [ ] Support for store name patterns/wildcards
