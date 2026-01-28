"""
Data analysis and statistics generation for cluster usage
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from collections import defaultdict


class UsageAnalyzer:
    """Analyze cluster usage data and generate statistics"""
    
    # Maximum valid session duration in minutes (12 hours)
    # Sessions longer than this are likely errors (forgot to log out, etc.)
    MAX_VALID_SESSION_DURATION_MINUTES = 720
    
    def __init__(self, location_logs: List[Dict]):
        """
        Initialize the analyzer with location logs
        
        Args:
            location_logs: List of location log dictionaries from the API
        """
        self.location_logs = location_logs
        self.df = self._prepare_dataframe()
    
    def _prepare_dataframe(self) -> pd.DataFrame:
        """Convert location logs to a pandas DataFrame for analysis"""
        if not self.location_logs:
            return pd.DataFrame()
        
        # Extract relevant fields
        data = []
        for log in self.location_logs:
            # Handle different API response structures
            if 'begin_at' in log and 'end_at' in log:
                data.append({
                    'user_id': log.get('user', {}).get('id') if isinstance(log.get('user'), dict) else log.get('user_id'),
                    'user_login': log.get('user', {}).get('login') if isinstance(log.get('user'), dict) else None,
                    'host': log.get('host'),
                    'begin_at': pd.to_datetime(log.get('begin_at')),
                    'end_at': pd.to_datetime(log.get('end_at')) if log.get('end_at') else None
                })
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Calculate session duration in minutes
        df['duration'] = ((df['end_at'] - df['begin_at']).dt.total_seconds() / 60).where(
            (df['end_at'].notna()) & (df['end_at'] > df['begin_at']), 
            0
        )
        
        # Extract time components for analysis
        df['hour'] = df['begin_at'].dt.hour
        df['day_of_week'] = df['begin_at'].dt.dayofweek  # 0=Monday, 6=Sunday
        df['day_name'] = df['begin_at'].dt.day_name()
        df['date'] = df['begin_at'].dt.date
        df['week'] = df['begin_at'].dt.isocalendar().week
        df['month'] = df['begin_at'].dt.month
        
        return df
    
    def get_hourly_usage(self) -> Dict[int, int]:
        """
        Get usage count by hour of day
        
        Returns:
            Dictionary mapping hour (0-23) to number of sessions
        """
        if self.df.empty:
            return {i: 0 for i in range(24)}
        
        hourly = self.df['hour'].value_counts().to_dict()
        # Fill missing hours with 0
        return {i: hourly.get(i, 0) for i in range(24)}
    
    def get_daily_usage(self) -> Dict[str, int]:
        """
        Get usage count by day of week
        
        Returns:
            Dictionary mapping day name to number of sessions
        """
        if self.df.empty:
            return {}
        
        return self.df['day_name'].value_counts().to_dict()
    
    def get_weekly_usage(self) -> Dict[int, int]:
        """
        Get usage count by week number
        
        Returns:
            Dictionary mapping week number to number of sessions
        """
        if self.df.empty:
            return {}
        
        return self.df['week'].value_counts().to_dict()
    
    def get_monthly_usage(self) -> Dict[int, int]:
        """
        Get usage count by month
        
        Returns:
            Dictionary mapping month number to number of sessions
        """
        if self.df.empty:
            return {}
        
        return self.df['month'].value_counts().to_dict()
    
    def get_host_usage(self) -> Dict[str, int]:
        """
        Get usage count by host/computer
        
        Returns:
            Dictionary mapping host name to number of sessions
        """
        if self.df.empty:
            return {}
        
        return self.df['host'].value_counts().to_dict()
    
    def get_average_session_duration(self) -> float:
        """
        Get average session duration in minutes
        
        Returns:
            Average duration in minutes
        """
        if self.df.empty or 'duration' not in self.df.columns:
            return 0.0
        
        # Filter out very long sessions (likely errors or forgot to log out)
        valid_durations = self.df[self.df['duration'] < self.MAX_VALID_SESSION_DURATION_MINUTES]['duration']
        
        if valid_durations.empty:
            return 0.0
        
        return float(valid_durations.mean())
    
    def get_average_duration_by_host(self) -> Dict[str, float]:
        """
        Get average session duration per host
        
        Returns:
            Dictionary mapping host name to average duration in minutes
        """
        if self.df.empty:
            return {}
        
        # Filter out very long sessions
        valid_df = self.df[self.df['duration'] < self.MAX_VALID_SESSION_DURATION_MINUTES]
        
        if valid_df.empty:
            return {}
        
        avg_by_host = valid_df.groupby('host')['duration'].mean()
        return avg_by_host.to_dict()
    
    def get_heatmap_data(self) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        Get data for creating a heatmap of usage by hour and day of week
        
        Returns:
            Tuple of (2D array of usage counts, day labels, hour labels)
        """
        if self.df.empty:
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            hours = [f"{i:02d}:00" for i in range(24)]
            return np.zeros((7, 24)), days, hours
        
        # Create a pivot table with day of week vs hour
        pivot = pd.crosstab(self.df['day_of_week'], self.df['hour'])
        
        # Ensure all hours are present
        for hour in range(24):
            if hour not in pivot.columns:
                pivot[hour] = 0
        
        # Ensure all days are present
        for day in range(7):
            if day not in pivot.index:
                pivot.loc[day] = 0
        
        # Sort by index and columns
        pivot = pivot.sort_index().sort_index(axis=1)
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        hours = [f"{i:02d}:00" for i in range(24)]
        
        return pivot.values, days, hours
    
    def get_host_heatmap_data(self, top_n: int = 20) -> Tuple[np.ndarray, List[str], List[str]]:
        """
        Get data for creating a heatmap of usage by host and hour
        
        Args:
            top_n: Number of top hosts to include
            
        Returns:
            Tuple of (2D array of usage counts, host labels, hour labels)
        """
        if self.df.empty:
            return np.zeros((1, 24)), ['No data'], [f"{i:02d}:00" for i in range(24)]
        
        # Get top N most used hosts
        top_hosts = self.df['host'].value_counts().head(top_n).index.tolist()
        
        # Filter to only top hosts
        df_filtered = self.df[self.df['host'].isin(top_hosts)]
        
        # Create pivot table
        pivot = pd.crosstab(df_filtered['host'], df_filtered['hour'])
        
        # Ensure all hours are present
        for hour in range(24):
            if hour not in pivot.columns:
                pivot[hour] = 0
        
        # Sort by total usage
        pivot = pivot.loc[top_hosts]
        pivot = pivot.sort_index(axis=1)
        
        hours = [f"{i:02d}:00" for i in range(24)]
        
        return pivot.values, top_hosts, hours
    
    def get_summary_stats(self) -> Dict:
        """
        Get summary statistics
        
        Returns:
            Dictionary with various summary statistics
        """
        if self.df.empty:
            return {
                'total_sessions': 0,
                'unique_users': 0,
                'unique_hosts': 0,
                'average_session_duration_minutes': 0.0,
                'total_usage_hours': 0.0,
                'date_range': 'No data'
            }
        
        total_duration = self.df[self.df['duration'] < self.MAX_VALID_SESSION_DURATION_MINUTES]['duration'].sum()
        
        return {
            'total_sessions': len(self.df),
            'unique_users': self.df['user_id'].nunique(),
            'unique_hosts': self.df['host'].nunique(),
            'average_session_duration_minutes': self.get_average_session_duration(),
            'total_usage_hours': total_duration / 60,
            'date_range': f"{self.df['begin_at'].min()} to {self.df['begin_at'].max()}"
        }
