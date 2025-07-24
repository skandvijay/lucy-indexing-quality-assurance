#!/usr/bin/env python3

import sqlite3
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse

test_app = FastAPI()

@test_app.get("/test-tags")
async def test_tags():
    """Test endpoint to check tags in database"""
    DB_PATH = "indexing_qa.db"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get records with tags
        cursor.execute("SELECT id, record_id, tags FROM processed_records WHERE tags IS NOT NULL AND tags != '[]' AND tags != '' LIMIT 10;")
        records = cursor.fetchall()
        
        result = []
        for record in records:
            tags_raw = record[2]
            try:
                tags_parsed = json.loads(tags_raw) if tags_raw else []
            except:
                tags_parsed = []
            
            result.append({
                "id": record[0],
                "record_id": record[1], 
                "tags_raw": tags_raw,
                "tags_parsed": tags_parsed
            })
        
        conn.close()
        
        return {
            "status": "success",
            "total_records_with_tags": len(result),
            "records": result
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(test_app, host="127.0.0.1", port=8001) 