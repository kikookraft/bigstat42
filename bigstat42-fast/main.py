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
    def __init__(self, host: str, start_time: int, end_time: int | None) -> None:
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
    
    def to_dict(self) -> dict[str, str | float | None]:
        return {
            "host": self.host,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration_value.total_seconds() if self.duration_value else None
        }

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
    
    def average_session_duration(self, time_window: timedelta = timedelta()) -> timedelta | None:
        """Calculate average session duration"""
        if not self.sessions:
            return None
        total_duration = sum((s.get_duration() for s in self.sessions if s.get_duration()), timedelta())
        return total_duration / len(self.sessions)
    
    def get_session_number(self, time_window: timedelta = timedelta()) -> int:
        """Get number of sessions in a given time window"""
        if time_window == timedelta():
            return len(self.sessions)
        cutoff_time = datetime.now() - time_window
        return sum(1 for s in self.sessions if s.get_start_time() >= cutoff_time)
    
    def get_session_usage_at_time(self, at_time: datetime) -> float:
        """Calculate usage as float of sessions active at a specific time"""
        if not self.sessions:
            return 0.0
        active_sessions = sum(1 for s in self.sessions if s.is_active(at_time))
        return (active_sessions / len(self.sessions))
    
    def has_active_session(self, at_time: datetime) -> bool:
        """Check if there is any active session at a specific time"""
        return any(s.is_active(at_time) for s in self.sessions)

    def __repr__(self) -> str:
        return f"Computer(name={self.name}, position={self.position}, total_usage={self.total_usage})"
    
    def to_dict(self) -> dict[str, str | int | list[dict[str, str | float | None]] | dict[str, int | float | None]]:
        return {
            "name": self.name,
            "position": self.position,
            "sessions": [s.to_dict() for s in self.sessions],
            "1d_stats": {
                "session_count": self.get_session_number(timedelta(days=1)),
                "usage_percentage": self.get_usage_percentage(timedelta(days=1)),
                "average_session_duration": self.average_session_duration(timedelta(days=1)).total_seconds() if self.average_session_duration(timedelta(days=1)) else None
            },
            "7d_stats": {
                "session_count": self.get_session_number(timedelta(days=7)),
                "usage_percentage": self.get_usage_percentage(timedelta(days=7)),
                "average_session_duration": self.average_session_duration(timedelta(days=7)).total_seconds() if self.average_session_duration(timedelta(days=7)) else None
            },
            "30d_stats": {
                "session_count": self.get_session_number(timedelta(days=30)),
                "usage_percentage": self.get_usage_percentage(timedelta(days=30)),
                "average_session_duration": self.average_session_duration(timedelta(days=30)).total_seconds() if self.average_session_duration(timedelta(days=30)) else None
            },
            "all_time_stats": {
                "session_count": self.get_session_number(),
                "usage_percentage": self.get_usage_percentage(timedelta(days=365*10)),  # assuming 10 years as "all time"
                "average_session_duration": self.average_session_duration(timedelta(days=365*10)).total_seconds() if self.average_session_duration(timedelta(days=365*10)) else None
            },
            "total_usage_seconds": self.total_usage.total_seconds()
        }

class Row:
    """A row of computers (1-8 computers per row)"""
    def __init__(self, row_number: int):
        self.row_number = row_number  # R1, R2, etc.
        self.computers: dict[int, Computer] = {}  # position -> Computer
    
    def add_computer(self, computer: Computer) -> None:
        self.computers[computer.position] = computer
    
    def get_computer(self, position: int) -> Computer | None:
        return self.computers.get(position)
    
    def get_row_usage(self, time_window: timedelta = timedelta()) -> dict[int, float]:
        """Get usage percentage for each computer position"""
        return {pos: comp.get_usage_percentage(time_window) 
                for pos, comp in self.computers.items()}
    
    def __repr__(self) -> str:
        return f"Row(row_number={self.row_number}, computers={list(self.computers.keys())})"
    
    def to_dict(self) -> dict[str, str | int | list[dict[str, str | int | list[dict[str, str | float | None]]]]]:
        return {
            "row_number": self.row_number,
            "computers": [comp.to_dict() for comp in self.computers.values()]
        }

class Zone:
    """A zone containing multiple rows"""
    def __init__(self, zone_name: str):
        self.zone_name = zone_name  # "Z4", "Z3", etc.
        self.rows: dict[int, Row] = {}  # row_number -> Row
    
    def add_row(self, row: Row) -> None:
        self.rows[row.row_number] = row
    
    def get_row(self, row_number: int) -> Row | None:
        return self.rows.get(row_number)
    
    def __repr__(self) -> str:
        return f"Zone(zone_name={self.zone_name}, rows={list(self.rows.keys())})"
    
    def to_dict(self) -> dict[str, str | int | list[dict[str, str | int | list[dict[str, str | int | list[dict[str, str | float | None]]]]]]]:
        return {
            "zone_name": self.zone_name,
            "rows": [row.to_dict() for row in self.rows.values()]
        }

class Cluster:
    """Cluster containing multiple zones"""
    def __init__(self):
        self.zones: dict[str, Zone] = {}  # zone_name -> Zone
    
    def add_zone(self, zone: Zone) -> None:
        self.zones[zone.zone_name] = zone
    
    def get_zone(self, zone_name: str) -> Zone | None:
        return self.zones.get(zone_name)
    
    def __repr__(self) -> str:
        return f"Cluster(zones={list(self.zones.keys())})"
    
    def to_dict(self) -> dict[str, list[dict[str, str | int | list[dict[str, str | int | list[dict[str, str | int | list[dict[str, str | float | None]]]]]]]]]:
        return {
            "zones": [zone.to_dict() for zone in self.zones.values()]
        }


def fetch_data(url: str) -> dict[str, list[dict[str, int | str | None]]]:
    """Fetch data from the given URL and return as JSON."""
    try:
        response: requests.Response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return {}

def build_cluster(data: dict[str, list[dict[str, int | str | None]]]) -> Cluster:
    """Build the cluster structure from raw session data."""
    cluster = Cluster()
    for session_data in data.get("sessions", []):
        host_raw = session_data["host"]
        start_time_raw = session_data["startTime"]
        end_time_raw = session_data.get("endTime")
        
        # Type validation and conversion
        if not isinstance(host_raw, str):
            continue
        if not isinstance(start_time_raw, int):
            continue
            
        host = host_raw
        start_time = start_time_raw
        end_time = int(end_time_raw) if isinstance(end_time_raw, int) else None

        # Parse host format like "z1r12p1" -> zone="z1", row=12, position=1
        try:
            parts = host.split('r')
            if len(parts) < 2:
                print(f"Warning: Skipping host with unexpected format (missing 'r'): {host}")
                continue
            zone_name = parts[0]  # e.g., "z1"
            
            row_and_pos = parts[1].split('p')
            if len(row_and_pos) < 2:
                print(f"Warning: Skipping host with unexpected format (missing 'p'): {host}")
                continue
            row_part = row_and_pos[0]  # e.g., "12"
            position_part = row_and_pos[1]  # e.g., "1"
            
            row_number = int(row_part)
            position = int(position_part)
        except (ValueError, IndexError) as e:
            # Skip hosts that don't match expected format
            print(f"Warning: Skipping host with parse error: {host} - {e}")
            continue

        session = Session(host, start_time, end_time)

        zone = cluster.get_zone(zone_name)
        if not zone:
            zone = Zone(zone_name)
            cluster.add_zone(zone)

        row = zone.get_row(row_number)
        if not row:
            row = Row(row_number)
            zone.add_row(row)

        computer = row.get_computer(position)
        if not computer:
            computer = Computer(position, host)
            row.add_computer(computer)

        try:
            computer.add_session(session)
        except ValueError as ve:
            print(f"Warning: {ve}", file=sys.stderr)

    return cluster

def main():
    parser = argparse.ArgumentParser(description="Fetch and analyze cluster usage statistics from 42 API")
    parser.add_argument("--url", type=str, default=URL, help="URL to fetch session data from")
    parser.add_argument("--output", type=str, help="Output file to save the cluster data as JSON")
    args = parser.parse_args()

    data = fetch_data(args.url)
    cluster = build_cluster(data)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(cluster.to_dict(), f, indent=4)
    else:
        with open("cluster.json", "w") as f:
            json.dump(cluster.to_dict(), f, indent=4)

if __name__ == "__main__":
    main()