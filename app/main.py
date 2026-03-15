"""
EFDAnalyzer Web Application
Main FastAPI application for file upload and visualization
"""
import os
import uuid
import aiofiles
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Create app instance
app = FastAPI(
    title="EFDAnalyzer Web",
    description="Event-Flow Data Analyzer with SVG visualization",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the base directory (go up two levels from app/main.py)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "app" / "static"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(STATIC_DIR))

# Include API routes
from app.routes import api
app.include_router(api.router, prefix="/api")

# Import drawio to svg converter
import sys
from pathlib import Path
utils_dir = Path(__file__).resolve().parent.parent / "utils"
sys.path.insert(0, str(utils_dir))
from DrawioToSvg import convert_drawio_to_svg

# Session storage (in production, use database or redis)
sessions = {}


@app.get("/", response_class=HTMLResponse)
async def index():
    """Main page - upload files"""
    index_html = STATIC_DIR / "index.html"
    if index_html.exists():
        with open(index_html, 'r', encoding='utf-8') as f:
            return f.read()
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EFDAnalyzer Web</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #333; }
            .upload-section { margin: 20px 0; padding: 20px; border: 2px dashed #ccc; border-radius: 10px; }
            .file-group { margin: 15px 0; }
            label { font-weight: bold; display: block; margin-bottom: 5px; }
            input[type="file"] { margin: 5px 0; }
            button { background: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #45a049; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>EFDAnalyzer Web</h1>
            <p>Upload your draw.io file and CSV data files to visualize activity rates.</p>

            <form id="uploadForm" enctype="multipart/form-data">
                <div class="upload-section">
                    <div class="file-group">
                        <label for="drawioFile">draw.io File (.drawio):</label>
                        <input type="file" id="drawioFile" name="drawioFile" accept=".drawio" required>
                    </div>

                    <div class="file-group">
                        <label>CSV Data Files (6 files required):</label>
                        <input type="file" name="csvFiles" accept=".csv" multiple required>
                        <small>Upload: activity_increase_rates.csv, activity_decrease_rates.csv, activity_average_counts.csv, activity_average_durations.csv, activity_active_average_counts.csv, activity_passive_average_counts.csv</small>
                    </div>

                    <button type="submit">Upload and Analyze</button>
                </div>
            </form>

            <div id="result"></div>
        </div>

        <script>
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData();

                const drawioFile = document.getElementById('drawioFile').files[0];
                const csvFiles = document.querySelector('input[name="csvFiles"]').files;

                if (!drawioFile) {
                    alert('Please select a draw.io file');
                    return;
                }

                if (csvFiles.length < 6) {
                    alert('Please select at least 6 CSV files');
                    return;
                }

                formData.append('drawioFile', drawioFile);
                for (let file of csvFiles) {
                    formData.append('csvFiles', file);
                }

                document.getElementById('result').innerHTML = '<p>Uploading...</p>';

                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    if (data.success) {
                        window.location.href = '/viewer?session=' + data.session_id;
                    } else {
                        document.getElementById('result').innerHTML = '<p style="color:red">Error: ' + data.message + '</p>';
                    }
                } catch (error) {
                    document.getElementById('result').innerHTML = '<p style="color:red">Error: ' + error.message + '</p>';
                }
            });
        </script>
    </body>
    </html>
    """


@app.post("/upload")
async def upload_files(
    drawioFile: UploadFile = File(...),
    csvFiles: List[UploadFile] = File(...)
):
    """
    Handle file uploads
    - 1 drawio file
    - 6 CSV files
    """
    # Validate CSV files
    if len(csvFiles) < 6:
        raise HTTPException(status_code=400, detail="At least 6 CSV files required")

    # Create session ID
    session_id = str(uuid.uuid4())
    session_dir = DATA_DIR / session_id
    session_dir.mkdir(exist_ok=True)

    # Save drawio file
    drawio_path = session_dir / drawioFile.filename
    async with aiofiles.open(drawio_path, 'wb') as f:
        content = await drawioFile.read()
        await f.write(content)

    # Convert drawio to SVG (lightweight approach)
    svg_filename = drawioFile.filename.replace('.drawio', '.svg')
    svg_path = session_dir / svg_filename
    try:
        convert_drawio_to_svg(str(drawio_path), str(svg_path))
        print(f"Converted drawio to SVG: {svg_path}")
    except Exception as e:
        print(f"Error converting drawio to SVG: {e}")

    # Save CSV files
    csv_saved = []
    for csv_file in csvFiles:
        csv_path = session_dir / csv_file.filename
        async with aiofiles.open(csv_path, 'wb') as f:
            content = await csv_file.read()
            await f.write(content)
        csv_saved.append(csv_file.filename)

    # Store session info
    sessions[session_id] = {
        "drawio_file": str(drawio_path),
        "svg_file": str(svg_path),
        "csv_files": csv_saved,
        "session_dir": str(session_dir)
    }

    return {
        "success": True,
        "session_id": session_id,
        "message": "Files uploaded successfully",
        "drawio_file": drawioFile.filename,
        "csv_files": csv_saved
    }


@app.get("/viewer", response_class=HTMLResponse)
async def viewer(session: str):
    """Viewer page with SVG diagram"""
    viewer_html = STATIC_DIR / "viewer.html"
    if viewer_html.exists():
        with open(viewer_html, 'r', encoding='utf-8') as f:
            return f.read()
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EFDAnalyzer Viewer</title>
        <style>
            body { margin: 0; padding: 0; font-family: Arial, sans-serif; }
            .container { display: flex; height: 100vh; }
            #drawioFrame { width: 60%; height: 100%; border: none; }
            #chartPanel { width: 40%; height: 100%; padding: 20px; overflow: auto; background: #f5f5f5; }
            #chartPanel h2 { margin-top: 0; }
            .chart-container { margin: 20px 0; }
            .loading { color: #666; }
            .error { color: #d32f2f; }
        </style>
    </head>
    <body>
        <div class="container">
            <iframe id="drawioFrame" src=""></iframe>
            <div id="chartPanel">
                <h2>Activity Chart</h2>
                <p>Click on a shape in the diagram to view its activity data.</p>
                <div id="chartContent"></div>
            </div>
        </div>

        <script>
            const sessionId = new URLSearchParams(window.location.search).get('session');
            if (!sessionId) {
                document.getElementById('chartContent').innerHTML = '<p class="error">No session found. Please upload files first.</p>';
            }

            // Load draw.io
            // Note: In production, you would serve the uploaded drawio file
            document.getElementById('drawioFrame').src = 'https://app.diagrams.net/';

            // Listen for messages from draw.io
            window.addEventListener('message', function(event) {
                console.log('Received message:', event.data);
            });
        </script>
    </body>
    </html>
    """


@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools():
    """Handle Chrome browser probes (harmless, suppresses 404 log)"""
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "EFDAnalyzer Web"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
