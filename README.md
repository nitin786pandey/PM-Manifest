## Agentic Elasticsearch Analytics Workflow

This repository provides an agentic workflow to analyze Manifest events using Elasticsearch + Python:
- Decompose a natural-language question into sub-questions
- Build Elasticsearch DSL queries (with `createdAt` time field)
- Fetch via curl/requests with ApiKey auth
- Convert JSON hits to pandas DataFrames
- Compute metrics (conversion, AOV, add-to-cart, interaction rate)
- Ask clarifying questions mid-run (CLI)

### Prerequisites
- Python 3.9+
- `pip install pandas requests`
- An Elasticsearch ApiKey with access to indices:
  - `manifest-events-prod-alias,events-prod-alias,bik-internal-events`
- Time field: `createdAt`

### Environment
Copy the example and set values:
```
cp config/env.example .env
```
Then edit `.env`:
```
ELASTIC_BASE_URL=https://elastic.kb.asia-south1.gcp.elastic-cloud.com
ELASTIC_API_KEY=REPLACE_WITH_API_KEY
```
Export env vars for local runs:
```
export $(grep -v '^#' .env | xargs)
```

### curl Example
Create `payload.json`:
```json
{
  "track_total_hits": true,
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        { "range": { "createdAt": { "gte": "now-90d/d", "lte": "now" } } },
        { "term":  { "eventName.keyword": "checkoutCompleted" } }
      ]
    }
  },
  "aggs": {
    "total_sales": { "sum": { "field": "eventProperties.totalAmountUSD" } }
  }
}
```
Run:
```bash
INDICES="manifest-events-prod-alias,events-prod-alias,bik-internal-events"
curl -s -X POST "$ELASTIC_BASE_URL/$INDICES/_search" \
  -H "Content-Type: application/json" \
  -H "Authorization: ApiKey $ELASTIC_API_KEY" \
  -d @payload.json | jq .
```

### Python Modules
- `scripts/es_fetch.py` — Elasticsearch client (mappings, search, pagination)
- `scripts/es_to_df.py` — Convert hits to pandas DataFrame
- `scripts/manifest_analysis.py` — Metrics and helpers
- `scripts/agent_runner.py` — CLI orchestrator (ask clarifications → DSL → fetch → analyze)

### Quickstart (CLI)
```bash
python scripts/agent_runner.py \
  --question "Why interaction rate reduced on last 3 months" \
  --gte "now-90d/d" --lte "now"
```
The runner will use a default definition for “interaction rate” (sessions with `hasInteracted=true` / all sessions), unless you override when prompted.

### Notes
- Prefer aggregations (`size: 0`) for performance.
- Use `.keyword` fields for exact matches.
- If a property is unknown, discover via index mappings.

### References
- Elastic Cloud UI (Api Keys): https://elastic.kb.asia-south1.gcp.elastic-cloud.com/app/management/security/api_keys/


