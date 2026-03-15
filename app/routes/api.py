"""
API Routes
Handle process-data endpoint
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

from app.services.data_loader import DataLoader
from app.services.plot_generator import PlotGenerator

# Create router
router = APIRouter()

# Global storage for session data
session_data = {}

# Initialize services
plot_generator = PlotGenerator()


class ProcessDataRequest(BaseModel):
    session_id: str
    label: str


class ProcessDataResponse(BaseModel):
    success: bool
    label: str = ""
    activity_name: str = ""
    chart_data: dict = {}
    message: str = ""


@router.post("/process-data", response_model=ProcessDataResponse)
async def process_data(request: ProcessDataRequest):
    """
    Process click data from draw.io diagram

    1. Receive the clicked label text
    2. Use label directly as activity name
    3. Generate and return the chart
    """
    try:
        # Get session data
        session_id = request.session_id
        label = request.label

        # Check if session exists
        if session_id not in session_data:
            # Try to load session from file
            from pathlib import Path
            base_dir = Path(__file__).resolve().parent.parent.parent
            data_dir = base_dir / "data" / session_id

            if not data_dir.exists():
                return ProcessDataResponse(
                    success=False,
                    label=label,
                    message="Session not found. Please upload files again."
                )

            # Load session data
            loader = DataLoader(str(data_dir))
            if not loader.load_csv_files():
                return ProcessDataResponse(
                    success=False,
                    label=label,
                    message="Failed to load CSV data files."
                )

            session_data[session_id] = loader
        else:
            loader = session_data[session_id]

        # Use label directly as activity name (preprocess: first space -> underscore, remaining spaces removed)
        activity_name = label.replace(" ", "_", 1).replace(" ", "")

        # Check if activity exists in data
        if not loader.has_activity(activity_name):
            return ProcessDataResponse(
                success=False,
                label=label,
                activity_name=activity_name,
                message=f"Activity '{activity_name}' not found in the uploaded data."
            )

        # Generate chart data
        chart_data = plot_generator.generate_chart(
            loader.increase_rates,
            loader.decrease_rates,
            loader.average_counts,
            loader.average_durations,
            activity_name
        )

        return ProcessDataResponse(
            success=True,
            label=label,
            activity_name=activity_name,
            chart_data=chart_data,
            message="Chart generated successfully"
        )

    except Exception as e:
        return ProcessDataResponse(
            success=False,
            label=request.label,
            message=f"Error processing data: {str(e)}"
        )


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get session information"""
    if session_id in session_data:
        loader = session_data[session_id]
        return {
            "session_id": session_id,
            "activities": loader.get_all_activities()
        }

    # Try to load from disk
    base_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = base_dir / "data" / session_id

    if not data_dir.exists():
        return {"error": "Session not found"}

    # Load session data from disk
    loader = DataLoader(str(data_dir))
    if not loader.load_csv_files():
        return {"error": "Failed to load CSV data files"}

    session_data[session_id] = loader
    return {
        "session_id": session_id,
        "activities": loader.get_all_activities()
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its data"""
    if session_id in session_data:
        del session_data[session_id]
        # Also try to delete files
        try:
            from pathlib import Path
            base_dir = Path(__file__).resolve().parent.parent.parent
            data_dir = base_dir / "data" / session_id
            if data_dir.exists():
                import shutil
                shutil.rmtree(data_dir)
        except Exception:
            pass
        return {"success": True}
    return {"error": "Session not found"}


@router.get("/svg/{session_id}")
async def get_svg(session_id: str):
    """Get the SVG content for a session"""
    base_dir = Path(__file__).resolve().parent.parent.parent
    session_dir = base_dir / "data" / session_id

    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Find SVG file in session directory
    svg_files = list(session_dir.glob("*.svg"))
    if not svg_files:
        raise HTTPException(status_code=404, detail="SVG file not found")

    svg_path = svg_files[0]
    with open(svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()

    return {
        "success": True,
        "svg": svg_content
    }
