"""
API Routes
Handle process-data endpoint
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.data_loader import DataLoader
from app.services.plot_generator import PlotGenerator
from app.utils.mapping import ActivityMapping

# Create router
router = APIRouter()

# Global storage for session data
session_data = {}

# Initialize services
mapping = ActivityMapping()
plot_generator = PlotGenerator()


class ProcessDataRequest(BaseModel):
    session_id: str
    label: str


class ProcessDataResponse(BaseModel):
    success: bool
    label: str = ""
    activity_name: str = ""
    chart_image: str = ""
    chart_html: str = ""
    message: str = ""


@router.post("/process-data", response_model=ProcessDataResponse)
async def process_data(request: ProcessDataRequest):
    """
    Process click data from draw.io diagram

    1. Receive the clicked label text
    2. Match it to an activity using activity_mapping.txt
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

        # Find activity by label
        activity_name = mapping.find_activity(label)

        if not activity_name:
            return ProcessDataResponse(
                success=False,
                label=label,
                message=f"No matching activity found for '{label}'. Try clicking on a rectangle with a valid label."
            )

        # Check if activity exists in data
        if not loader.has_activity(activity_name):
            return ProcessDataResponse(
                success=False,
                label=label,
                activity_name=activity_name,
                message=f"Activity '{activity_name}' not found in the uploaded data."
            )

        # Generate chart
        chart_image, chart_html = plot_generator.generate_chart(
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
            chart_image=chart_image,
            chart_html=chart_html,
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
    return {"error": "Session not found"}


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
