"""
Plot Generator Service
Generates charts from activity data
"""
import base64
import io
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import pandas as pd
from typing import Optional

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


class PlotGenerator:
    """Generate charts from activity data"""

    def __init__(self):
        pass

    def generate_chart(
        self,
        increase_df: pd.DataFrame,
        decrease_df: pd.DataFrame,
        average_df: pd.DataFrame,
        duration_df: Optional[pd.DataFrame],
        activity_name: str,
        figsize: tuple = (12, 8)
    ) -> tuple[str, str]:
        """
        Generate a chart for the specified activity

        Returns:
            tuple: (base64_image, html_chart)
        """
        if activity_name not in increase_df.columns:
            raise ValueError(f"Activity '{activity_name}' not found in data")

        # Create figure with 2 subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
        fig.suptitle(f"{activity_name}", fontsize=14, fontweight="bold", y=0.995)

        # Subplot 1: Increase and Decrease Rates
        ax1.plot(
            increase_df.index,
            increase_df[activity_name],
            label="Increase Rate",
            linewidth=2,
            color="#2ecc71",
            alpha=0.8
        )
        ax1.plot(
            decrease_df.index,
            decrease_df[activity_name],
            label="Decrease Rate",
            linewidth=2,
            color="#e74c3c",
            alpha=0.8
        )
        ax1.set_xlabel("Hour", fontsize=10, fontweight="bold")
        ax1.set_ylabel("Rate", fontsize=10, fontweight="bold")
        ax1.set_title("Activity Rates", fontsize=11, fontweight="bold", pad=10)
        ax1.legend(loc="upper left", fontsize=9, framealpha=0.9)
        ax1.grid(True, alpha=0.3, linestyle="--")

        # Subplot 2: Average Count and Duration
        if duration_df is not None and activity_name in duration_df.columns:
            ax2_twin = ax2.twinx()

            line1 = ax2.plot(
                average_df.index,
                average_df[activity_name],
                label="Average Count",
                linewidth=2,
                color="#3498db",
                alpha=0.8
            )
            line2 = ax2_twin.plot(
                duration_df.index,
                duration_df[activity_name],
                label="Average Duration (hours)",
                linewidth=2,
                color="#9b59b6",
                alpha=0.8,
                linestyle='--'
            )

            ax2.set_xlabel("Hour", fontsize=10, fontweight="bold")
            ax2.set_ylabel("Average Count", fontsize=10, fontweight="bold")
            ax2_twin.set_ylabel("Average Duration (hours)", fontsize=10, fontweight="bold")
            ax2.set_title("Activity Count and Duration", fontsize=11, fontweight="bold", pad=10)

            lines = line1 + line2
            labels = [line.get_label() for line in lines]
            ax2.legend(lines, labels, loc="upper left", fontsize=9, framealpha=0.9)
        else:
            ax2.plot(
                average_df.index,
                average_df[activity_name],
                label="Average Count",
                linewidth=2,
                color="#3498db",
                alpha=0.8
            )
            ax2.set_xlabel("Hour", fontsize=10, fontweight="bold")
            ax2.set_ylabel("Average Count", fontsize=10, fontweight="bold")
            ax2.set_title("Activity Count", fontsize=11, fontweight="bold", pad=10)
            ax2.legend(loc="upper left", fontsize=9, framealpha=0.9)

        ax2.grid(True, alpha=0.3, linestyle="--")
        plt.tight_layout()

        # Convert to base64
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        img_buffer.seek(0)
        base64_image = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        plt.close(fig)

        # Generate simple HTML chart (can be replaced with Plotly)
        html_chart = self._generate_simple_html(
            increase_df, decrease_df, average_df, duration_df, activity_name
        )

        return f"data:image/png;base64,{base64_image}", html_chart

    def _generate_simple_html(
        self,
        increase_df: pd.DataFrame,
        decrease_df: pd.DataFrame,
        average_df: pd.DataFrame,
        duration_df: Optional[pd.DataFrame],
        activity_name: str
    ) -> str:
        """Generate a simple HTML chart (fallback)"""
        # Get data as lists
        hours = increase_df.index.tolist()
        increase_data = increase_df[activity_name].tolist()
        decrease_data = decrease_df[activity_name].tolist()
        average_data = average_df[activity_name].tolist()

        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 10px;">
            <h4 style="margin-top: 0;">{activity_name}</h4>
            <div style="margin: 10px 0;">
                <svg width="100%" height="200" viewBox="0 0 {len(hours) * 40} 200">
                    <!-- Increase Rate (green) -->
                    <polyline
                        fill="none"
                        stroke="#2ecc71"
                        stroke-width="2"
                        points="{','.join([f'{i * 40},{200 - v * 10}' for i, v in enumerate(increase_data[:10])])}"
                    />
                    <!-- Decrease Rate (red) -->
                    <polyline
                        fill="none"
                        stroke="#e74c3c"
                        stroke-width="2"
                        points="{','.join([f'{i * 40},{200 - v * 10}' for i, v in enumerate(decrease_data[:10])])}"
                    />
                    <!-- Average Count (blue) -->
                    <polyline
                        fill="none"
                        stroke="#3498db"
                        stroke-width="2"
                        points="{','.join([f'{i * 40},{200 - v / 100}' for i, v in enumerate(average_data[:10])])}"
                    />
                </svg>
            </div>
            <div style="display: flex; gap: 15px; font-size: 12px;">
                <span style="color: #2ecc71;">● Increase Rate</span>
                <span style="color: #e74c3c;">● Decrease Rate</span>
                <span style="color: #3498db;">● Average Count</span>
            </div>
        </div>
        """
        return html
