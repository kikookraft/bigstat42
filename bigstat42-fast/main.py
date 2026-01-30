#!/usr/bin/env python3
"""
Main application for bigstat42
Fetch and analyze cluster usage statistics from 42 API
"""

URL = "https://api.raraph.fr/intra-metrics/sessions" # URL to fetch session data
#-> response example: {'sessions': [{'host': 'z1r12p1', 'startTime': 1769657139375, 'endTime': 1769708139235}, {'host': 'z1r8p1', 'startTime': 1769668421566, 'endTime': 1769696742793}, {'host': 'z2r10p8', 'startTime': 1769668603475, 'endTime': 1769711087574}, {'host': 'z2r9p8', 'startTime': 1769669442977, 'endTime': 1769705922935}, {'host': 'z4r2p2', 'startTime': 1769669559336, 'endTime': 1769696319485}, {'host': 'z4r6p1', 'startTime': 1769669805179, 'endTime': 1769695426924}, {'host': 'z4r11p3', 'startTime': 1769669859922, 'endTime': 1769711500128}

UPPER_CLUSTER = "https://cdn.intra.42.fr/cluster/image/129/Io.svg"
LOWER_CLUSTER = "https://cdn.intra.42.fr/cluster/image/130/Discovery.svg"

import requests
import argparse
import sys
from datetime import datetime, timedelta
from collections import defaultdict
import json
import numpy as np


def check_overlap(session1: 'Session', session2: 'Session') -> bool:
    """Check if two sessions overlap in time."""
    start1, end1 = session1.start_time, session1.end_time
    start2, end2 = session2.start_time, session2.end_time

    if end1 is None:
        end1 = datetime.max
    if end2 is None:
        end2 = datetime.max

    return start1 < end2 and start2 < end1

class Session:
    """Class representing a single session on a host."""
    def __init__(self, host: str, start_time: int, end_time: int) -> None:
        self.host = host
        self.start_time = datetime.fromtimestamp(start_time / 1000)
        self.end_time = datetime.fromtimestamp(end_time / 1000) if end_time is not None else None
        self.duration_value = self.end_time - self.start_time if self.end_time else None

    def get_host(self) -> str:
        return self.host
    
    def get_start_time(self) -> datetime:   
        return self.start_time
    
    def get_end_time(self) -> datetime:
        return self.end_time
    
    def get_duration(self) -> timedelta:
        return self.duration_value
    
    def is_active(self, at_time: datetime) -> bool:
        """Check if the session was active at a given time."""
        return self.start_time <= at_time and (self.end_time is None or self.end_time >= at_time)
    
    def update_end_time(self, new_end_time: int) -> None:
        """Update the end time of the session."""
        if new_end_time is None: return
        self.end_time = datetime.fromtimestamp(new_end_time / 1000)
        self.duration_value = self.end_time - self.start_time
    
    def __repr__(self) -> str:
        return f"Session(host={self.host}, start_time={self.start_time}, end_time={self.end_time})"

class Computer:
    """Individual computer with its sessions"""
    def __init__(self, position: int, name: str):
        self.position = position  # 1-8 (position in row)
        self.name = name  # e.g., "z4r1p3"
        self.sessions: list[Session] = []
        self.total_usage: timedelta = timedelta()
    
    def add_session(self, session: Session) -> None:
        """Add session with overlap detection"""
        for existing_session in self.sessions:
            if check_overlap(existing_session, session):
                raise ValueError(f"Overlapping sessions detected on {self.name}: {existing_session} and {session}")
        self.sessions.append(session)
        self.total_usage += session.get_duration() if session.get_duration() else timedelta()
    
    def get_usage_percentage(self, time_window: timedelta) -> float:
        """Calculate usage as percentage of time window"""
        return (self.total_usage.total_seconds() / time_window.total_seconds()) * 100

    def get_total_usage(self) -> timedelta:
        return self.total_usage
    
    def average_session_duration(self) -> timedelta | None:
        """Calculate average session duration"""
        if not self.sessions:
            return None
        total_duration = sum((s.get_duration() for s in self.sessions if s.get_duration()), timedelta())
        return total_duration / len(self.sessions)
    
    def get_session_usage_at_time(self, at_time: datetime) -> float:
        """Calculate usage as float of sessions active at a specific time"""
        if not self.sessions:
            return 0.0
        active_sessions = sum(1 for s in self.sessions if s.is_active(at_time))
        return (active_sessions / len(self.sessions))

    def __repr__(self) -> str:
        return f"Computer(name={self.name}, position={self.position}, total_usage={self.total_usage})"

class Row:
    """A row of computers (1-8 computers per row)"""
    def __init__(self, row_number: int):
        self.row_number = row_number  # R1, R2, etc.
        self.computers: dict[int, Computer] = {}  # position -> Computer
    
    def add_computer(self, computer: Computer) -> None:
        self.computers[computer.position] = computer
    
    def get_computer(self, position: int) -> Computer | None:
        return self.computers.get(position)
    
    def get_row_usage(self) -> dict[int, float]:
        """Get usage percentage for each computer position"""
        return {pos: comp.get_usage_percentage() 
                for pos, comp in self.computers.items()}
    
    def __repr__(self) -> str:
        return f"Row(row_number={self.row_number}, computers={list(self.computers.keys())})"

class Zone:
    """A zone containing multiple rows"""
    def __init__(self, zone_name: str):
        self.zone_name = zone_name  # "Z4", "Z3", etc.
        self.rows: dict[int, Row] = {}  # row_number -> Row
    
    def add_row(self, row: Row) -> None:
        self.rows[row.row_number] = row
    
    def get_row(self, row_number: int) -> Row | None:
        return self.rows.get(row_number)
    
    def get_heatmap_data(self) -> np.ndarray:
        """Generate 2D array for heatmap (rows x positions)"""
        max_row = max(self.rows.keys()) if self.rows else 0
        data = np.zeros((max_row, 8))  # Assuming max 8 computers per row
        
        for row_num, cluster in self.rows.items():
            for pos, computer in cluster.computers.items():
                data[row_num - 1, pos - 1] = computer.get_usage_percentage()
        
        return data


def fetch_data(url: str) -> dict:
    """Fetch data from the given URL and return as JSON."""
    try:
        response: requests.Response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return {}

