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
import json


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
        # Treat 0 as None since timestamp 0 is Unix epoch (1970-01-01), which is invalid
        self.end_time = datetime.fromtimestamp(end_time / 1000) if end_time is not None and end_time != 0 else None
        self.duration_value: timedelta | None = self.end_time - self.start_time if self.end_time else None

    def get_host(self) -> str:
        return self.host
    
    def get_start_time(self) -> datetime:   
        return self.start_time
    
    def get_end_time(self) -> datetime | None:
        return self.end_time
    
    def get_duration(self) -> float | None:
        return (
            self.duration_value.total_seconds() if self.duration_value 
            else datetime.now().timestamp() - self.start_time.timestamp()
        )
    
    def is_active(self, at_time: datetime) -> bool:
        """Check if the session was active at a given time."""
        return self.start_time <= at_time and (self.end_time is None or self.end_time >= at_time)
    
    def update_end_time(self, new_end_time: int | None) -> None:
        """Update the end time of the session."""
        if new_end_time is None or new_end_time == 0: return
        self.end_time = datetime.fromtimestamp(new_end_time / 1000)
        self.duration_value = self.end_time - self.start_time
    
    def __repr__(self) -> str:
        return f"Session(host={self.host}, start_time={self.start_time}, end_time={self.end_time})"
    
    def to_dict(self) -> dict[str, str | float | None]:
        return {
            "host": self.host,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.get_duration()
        }

class Computer:
    """Individual computer with its sessions"""
    def __init__(self, position: int, name: str):
        self.position = position  # 1-8 (position in row)
        self.name = name  # e.g., "z4r1p3"
        self.sessions: list[Session] = []
    
    def add_session(self, session: Session) -> None:
        """Add session with overlap detection"""
        for existing_session in self.sessions:
            if check_overlap(existing_session, session):
                raise ValueError(f"Overlapping sessions detected on {self.name}: {existing_session} and {session}")
        self.sessions.append(session)
    
    def get_usage_percentage(self, time_window: timedelta) -> float:
        """Calculate usage as percentage of time window"""
        if not self.sessions:
            return 0.0
        now = datetime.now()
        window_start = now - time_window if time_window != timedelta() else datetime.min
        total_time = time_window.total_seconds() if time_window != timedelta() else (now - min(s.get_start_time() for s in self.sessions)).total_seconds()
        
        used_time = 0.0
        for session in self.sessions:
            session_start = session.get_start_time()
            session_end = session.get_end_time() if session.get_end_time() is not None else now
            
            # Only count sessions that overlap with the time window
            if session_end >= window_start and session_start <= now:
                # Calculate the overlap duration
                overlap_start = max(session_start, window_start)
                overlap_end = min(session_end, now)
                overlap_duration = (overlap_end - overlap_start).total_seconds()
                if overlap_duration > 0:
                    used_time += overlap_duration
        
        usage_percentage = (used_time / total_time) * 100 if total_time > 0 else 0.0
        return round(usage_percentage, 2)

    def get_total_usage(self) -> int:
        """Calculate total usage time across all sessions"""
        total_usage = sum((s.get_duration() for s in self.sessions if s.get_duration()), 0)
        return total_usage
    
    def average_session_duration(self, time_window: timedelta = timedelta()) -> int | None:
        """Calculate average session duration"""
        if not self.sessions:
            return None
        total_duration = sum((s.get_duration() for s in self.sessions if s.get_duration()), 0)
        return round(total_duration / len(self.sessions))
    
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
        return f"Computer(name={self.name}, position={self.position}, total_usage={self.get_total_usage()}s, sessions={len(self.sessions)})"
    
    def to_dict(self, first_timestamp: int | None) -> dict[str, str | int | list[dict[str, str | float | None]] | dict[str, int | float | None]]:
        if first_timestamp is None:
            first_timestamp = 0
        # start all the stats from the first timestamp known in the database and adjust accordingly
        time_range = datetime.now() - datetime.fromtimestamp(first_timestamp / 1000)
        if time_range < timedelta(days=30):
            timedelta_30d = time_range
        else:
            timedelta_30d = timedelta(days=30)
        if time_range < timedelta(days=7):
            timedelta_7d = time_range
        else:
            timedelta_7d = timedelta(days=7)
        if time_range < timedelta(days=1):
            timedelta_1d = time_range
        else:
            timedelta_1d = timedelta(days=1)
        return {
            "name": self.name,
            "position": self.position,
            "sessions": [s.to_dict() for s in self.sessions],
            "1d_stats": {
                "session_count": self.get_session_number(timedelta_1d),
                "usage_percentage": self.get_usage_percentage(timedelta_1d),
                "average_session_duration": self.average_session_duration(timedelta_1d) if self.average_session_duration(timedelta_1d) else None
            },
            "7d_stats": {
                "session_count": self.get_session_number(timedelta_7d),
                "usage_percentage": self.get_usage_percentage(timedelta_7d),
                "average_session_duration": self.average_session_duration(timedelta_7d) if self.average_session_duration(timedelta_7d) else None
            },
            "30d_stats": {
                "session_count": self.get_session_number(timedelta_30d),
                "usage_percentage": self.get_usage_percentage(timedelta_30d),
                "average_session_duration": self.average_session_duration(timedelta_30d) if self.average_session_duration(timedelta_30d) else None
            },
            "all_time_stats": {
                "session_count": self.get_session_number(),
                "usage_percentage": self.get_usage_percentage(time_range),  # assuming 10 years as "all time"
                "average_session_duration": self.average_session_duration(time_range) if self.average_session_duration() else None
            },
            "total_usage_seconds": round(self.get_total_usage())
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
    
    def to_dict(self, first_timestamp: int | None) -> dict[str, int | list[dict[str, str | int | list[dict[str, str | float | None]] | dict[str, int | float | None]]]]:
        return {
            "row_number": self.row_number,
            "computers": [comp.to_dict(first_timestamp) for comp in self.computers.values()]
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
    
    def to_dict(self, first_timestamp: int | None) -> dict[str, str | list[dict[str, int | list[dict[str, str | int | list[dict[str, str | float | None]] | dict[str, int | float | None]]]]]]:
        return {
            "zone_name": self.zone_name,
            "rows": [row.to_dict(first_timestamp) for row in self.rows.values()]
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
    
    def to_dict(self, first_timestamp: int | None) -> dict[str, list[dict[str, str | list[dict[str, int | list[dict[str, str | int | list[dict[str, str | float | None]] | dict[str, int | float | None]]]]]]]]:
        return {
            "zones": [zone.to_dict(first_timestamp) for zone in self.zones.values()],
            "last_update": datetime.now().isoformat(sep=" ", timespec="seconds")
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
    
def get_first_timestamp(json_data: dict[str, list[dict[str, int | str | None]]]) -> int | None:
    """Get the earliest startTime from the session data."""
    sessions = json_data.get("sessions", [])
    if not sessions:
        return None
    first_timestamp = min(session["startTime"] for session in sessions if "startTime" in session and isinstance(session["startTime"], int))
    return first_timestamp

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
            json.dump(cluster.to_dict(get_first_timestamp(data)), f, indent=4)
    else:
        with open("cluster.json", "w") as f:
            json.dump(cluster.to_dict(get_first_timestamp(data)), f, indent=4)

if __name__ == "__main__":
    main()