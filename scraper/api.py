from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict
import pandas as pd

app = FastAPI(title="Goose Tour Dates API")

def get_scraped_files() -> List[Dict]:
    """Get all scraped files with their metadata."""
    data_dir = Path("scraper/data/scraped_concerts")
    if not data_dir.exists():
        return []
    
    files = []
    for file in data_dir.glob("tour_dates_*.json"):
        try:
            stats = file.stat()
            files.append({
                "filename": file.name,
                "timestamp": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "size": stats.st_size,
                "type": "json"
            })
        except Exception as e:
            print(f"Error processing file {file}: {e}")
    
    return sorted(files, key=lambda x: x["timestamp"], reverse=True)

@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "Goose Tour Dates API",
        "version": "1.0.0",
        "endpoints": [
            "/files - List all scraped files",
            "/files/latest - Get latest scraped data",
            "/files/{filename} - Get specific file data"
        ]
    }

@app.get("/files")
async def list_files():
    """List all scraped files with their metadata."""
    files = get_scraped_files()
    if not files:
        raise HTTPException(status_code=404, detail="No scraped files found")
    return files

@app.get("/files/latest")
async def get_latest_data():
    """Get the most recent scraped data."""
    files = get_scraped_files()
    if not files:
        raise HTTPException(status_code=404, detail="No scraped files found")
    
    latest_file = files[0]
    file_path = Path("scraper/data/scraped_concerts") / latest_file["filename"]
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return {
            "metadata": latest_file,
            "concerts": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@app.get("/files/{filename}")
async def get_file_data(filename: str):
    """Get data from a specific file."""
    file_path = Path("scraper/data/scraped_concerts") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return {
            "filename": filename,
            "timestamp": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            "concerts": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@app.get("/files/{filename}/csv")
async def get_file_csv(filename: str):
    """Get data from a specific file in CSV format."""
    # Convert JSON filename to CSV filename
    csv_filename = filename.replace('.json', '.csv')
    file_path = Path("scraper/data/scraped_concerts") / csv_filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="CSV file not found")
    
    try:
        df = pd.read_csv(file_path)
        return JSONResponse(content=df.to_dict(orient='records'))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading CSV file: {str(e)}") 