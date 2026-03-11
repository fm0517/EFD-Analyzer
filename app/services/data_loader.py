"""
Data Loader Service
Handles loading and processing of CSV data files
"""
import datetime as dt
import pandas as pd
from pathlib import Path
from typing import Optional


class DataLoader:
    """Load and process CSV data files for activity analysis"""

    def __init__(self, session_dir: str):
        self.session_dir = Path(session_dir)
        self.increase_rates: Optional[pd.DataFrame] = None
        self.decrease_rates: Optional[pd.DataFrame] = None
        self.average_counts: Optional[pd.DataFrame] = None
        self.average_durations: Optional[pd.DataFrame] = None
        self.has_durations = False

    def load_csv_files(self) -> bool:
        """Load all CSV files from the session directory"""
        try:
            # Load increase rates
            increase_file = self.session_dir / 'activity_increase_rates.csv'
            if increase_file.exists():
                self.increase_rates = pd.read_csv(increase_file)

            # Load decrease rates
            decrease_file = self.session_dir / 'activity_decrease_rates.csv'
            if decrease_file.exists():
                self.decrease_rates = pd.read_csv(decrease_file)

            # Load average counts
            counts_file = self.session_dir / 'activity_average_counts.csv'
            if counts_file.exists():
                self.average_counts = pd.read_csv(counts_file)

            # Load average durations (optional)
            durations_file = self.session_dir / 'activity_average_durations.csv'
            if durations_file.exists():
                self.average_durations = pd.read_csv(durations_file)
                self.has_durations = True

            # Process the data
            if self.increase_rates is not None:
                self._process_dataframes()
                return True
            return False

        except Exception as e:
            print(f"Error loading CSV files: {e}")
            return False

    def _process_dataframes(self):
        """Process dataframes: convert time to days and hours"""
        dataframes = [self.increase_rates, self.decrease_rates, self.average_counts]
        if self.has_durations:
            dataframes.append(self.average_durations)

        for df in dataframes:
            if df is not None:
                df['Days'] = df['SimulationTime'].apply(self._parse_simulation_time_to_days)

        # Find minimum day
        min_day = min(
            self.increase_rates['Days'].min(),
            self.decrease_rates['Days'].min(),
            self.average_counts['Days'].min()
        )
        if self.has_durations:
            min_day = min(min_day, self.average_durations['Days'].min())

        # Add Hour column
        for df in dataframes:
            if df is not None:
                df['Hour'] = (df['Days'] - min_day + 1) * 24
                df.set_index('Hour', inplace=True)

    @staticmethod
    def _parse_simulation_time_to_days(time_str: str) -> int:
        """Parse SimulationTime string to total days"""
        curr_dt = dt.datetime.strptime(time_str.split()[0], '%Y-%m-%d')
        days = (curr_dt.year - 1) * 365 + curr_dt.timetuple().tm_yday - 1
        return days

    def get_activity_data(self, activity_name: str) -> dict:
        """Get data for a specific activity"""
        if activity_name not in self.increase_rates.columns:
            return None

        return {
            'increase': self.increase_rates[activity_name].to_dict() if activity_name in self.increase_rates.columns else {},
            'decrease': self.decrease_rates[activity_name].to_dict() if activity_name in self.decrease_rates.columns else {},
            'average': self.average_counts[activity_name].to_dict() if activity_name in self.average_counts.columns else {},
            'duration': self.average_durations[activity_name].to_dict() if self.has_durations and activity_name in self.average_durations.columns else {}
        }

    def has_activity(self, activity_name: str) -> bool:
        """Check if an activity exists in the data"""
        if self.increase_rates is None:
            return False
        return activity_name in self.increase_rates.columns

    def get_all_activities(self) -> list:
        """Get list of all available activities"""
        if self.increase_rates is None:
            return []
        # Filter out non-activity columns
        return [col for col in self.increase_rates.columns if col != 'SimulationTime' and col != 'Days']
