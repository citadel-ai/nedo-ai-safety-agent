# Refactor: Google Maps Grounding

## Summary

Replaced the separate Google Places API integration with Vertex AI's built-in **Google Maps grounding** feature.

## Why This Change?

### Before (Google Places API)
```python
# Separate tool + API key required
1. LLM identifies place types → "immigration office"
2. Call Google Places API with query string
3. Manually format results
4. Requires GOOGLE_PLACES_API_KEY env var
```

### After (Google Maps Grounding)
```python
# Built-in Vertex AI integration
1. Ask LLM with google_search_retrieval enabled
2. LLM automatically searches Google Maps and grounds response
3. Extract structured place data from grounding metadata
4. Uses existing Google Cloud project credentials
```

## Benefits

✅ **Simpler Setup**: No separate API key needed  
✅ **Native Integration**: Works seamlessly with Gemini models  
✅ **Richer Data**: Includes place IDs, reviews, photos, context tokens  
✅ **Better Context Understanding**: LLM reasons about places in conversation context  
✅ **Widget Support**: Can render interactive Google Maps widgets (future enhancement)

## What Changed

### Files Modified

1. **`backend/nodes/find_places.py`**
   - Removed Google Places API tool calls
   - Added Google Maps grounding via `tools.google_search_retrieval`
   - Added `_extract_places_from_grounding()` helper function
   - Extracts place data from grounding metadata

2. **`requirements.txt`**
   - Removed `googlemaps>=4.10.0`

3. **`env_template.txt`**
   - Removed `GOOGLE_PLACES_API_KEY`

### Files Deleted

- `backend/tools/google_places.py` - No longer needed

### Documentation Updated

- `MULTI_AGENT_IMPLEMENTATION.md` - Updated to reflect Google Maps grounding approach

## How It Works

### 1. Configure LLM with Google Maps Grounding

```python
llm_configured = ChatVertexAI(
    model="gemini-2.0-flash-exp",
    temperature=0,
    tools=[
        {
            "google_search_retrieval": {
                "dynamic_retrieval_config": {
                    "mode": "MODE_DYNAMIC",
                    "dynamic_threshold": 0.7
                }
            }
        }
    ]
)
```

### 2. Make a Context-Aware Request

```python
prompt = f"""Based on this conversation about Japanese administrative procedures, 
identify and find 2-3 SPECIFIC GOVERNMENT OFFICES near {location}.

User's Question: {query_text}
Answer Provided: {answer_text}
User Location: {location}

Find governmental or public administrative facilities such as:
- Immigration offices/bureaus (出入国在留管理局)
- City halls / Ward offices (市役所/区役所)
- Tax offices (税務署)
..."""

response = llm_configured.invoke(prompt)
```

### 3. Extract Places from Grounding Metadata

```python
def _extract_places_from_grounding(grounding_metadata):
    chunks = grounding_metadata.get("grounding_chunks", [])
    
    for chunk in chunks:
        # Extract place_id, name, address from grounding data
        place_id = chunk.get("place_id")
        title = chunk.get("title")
        address = chunk.get("formatted_address")
        
        # Build Google Maps URL
        maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
        
        places.append({
            "name": title,
            "address": address,
            "place_id": place_id,
            "maps_url": maps_url
        })
```

## Grounding Metadata Structure

The response includes grounding metadata like:

```json
{
  "grounding_metadata": {
    "grounding_chunks": [
      {
        "web": {
          "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
          "title": "Tokyo Regional Immigration Bureau",
          "snippet": "1-3-1 Konan, Minato City, Tokyo 108-8255",
          "uri": "..."
        }
      }
    ]
  }
}
```

## Fallback Behavior

If no places are found via grounding (e.g., authentication issues), the system falls back to generic Google Maps search URLs:

```python
search_url = f"https://www.google.com/maps/search/{search_term}+near+{location}"
```

## Testing

```bash
# 1. Ensure Google Cloud authentication
gcloud auth application-default login

# 2. Start the server
python run_server.py

# 3. Test a query
Ask: "Where can I renew my visa in Tokyo?"

# 4. Check logs for:
📍 Finding useful places near Tokyo using Google Maps grounding
   📍 Extracted 2 places from Google Maps grounding
      ✅ Tokyo Regional Immigration Bureau
      ✅ Shinagawa Immigration Office
✅ Returning 3 useful places
```

## Migration Notes

### No Action Required

If your `.env` had `GOOGLE_PLACES_API_KEY`, you can safely remove it. The system will now use your Google Cloud project credentials automatically.

### Potential Issues

1. **No places returned?**  
   - Check: `gcloud auth application-default login`
   - System falls back to search URLs gracefully

2. **Different place data format?**  
   - Frontend expects: `{name, address, place_id, maps_url}`
   - This format is maintained, so no frontend changes needed

## Future Enhancements

With Google Maps grounding, we can now:

1. **Render Google Maps Widgets** - Show interactive maps using `googleMapsWidgetContextToken`
2. **Include Reviews & Photos** - Display user reviews and place photos
3. **More Accurate Results** - LLM understands context better than keyword search

See: [Google Maps Widget Documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-maps#optional_google_maps_contextual_widget)

## References

- [Grounding with Google Maps](https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/grounding-with-google-maps)
- [Google Search Retrieval Tools](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/inference#tools)
- [Dynamic Retrieval Config](https://cloud.google.com/vertex-ai/generative-ai/docs/grounding/overview#dynamic-retrieval)

