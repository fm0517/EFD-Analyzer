"""
Plot Generator Service
Generates chart data for frontend ECharts rendering
"""
import pandas as pd
from typing import Optional


class PlotGenerator:
    """Generate chart data from activity data"""

    def __init__(self):
        pass

    def generate_chart(
        self,
        increase_df: pd.DataFrame,
        decrease_df: pd.DataFrame,
        average_df: pd.DataFrame,
        duration_df: Optional[pd.DataFrame],
        activity_name: str,
    ) -> dict:
        """
        Generate chart data for the specified activity (case-insensitive)

        Returns:
            dict: chart data for ECharts rendering
        """
        # Find actual column name (case-preserved)
        activity_lower = activity_name.lower()
        actual_column = None
        for col in increase_df.columns:
            if col.lower() == activity_lower:
                actual_column = col
                break

        if actual_column is None:
            raise ValueError(f"Activity '{activity_name}' not found in data")

        hours = [float(h) for h in increase_df.index.tolist()]
        increase_data = [round(v, 4) for v in increase_df[actual_column].tolist()]
        decrease_data = [round(v, 4) for v in decrease_df[actual_column].tolist()]
        average_data = [round(v, 4) for v in average_df[actual_column].tolist()]

        duration_data = None
        if duration_df is not None and actual_column in duration_df.columns:
            duration_data = [round(v, 4) for v in duration_df[actual_column].tolist()]

        return {
            "activity_name": activity_name,
            "hours": hours,
            "increase_rate": increase_data,
            "decrease_rate": decrease_data,
            "average_count": average_data,
            "average_duration": duration_data,
        }
