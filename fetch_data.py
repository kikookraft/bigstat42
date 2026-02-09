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
        duration = self.get_duration()
        return {
            "host": self.host,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": round(duration) if duration is not None else None
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
            session_end_raw = session.get_end_time()
            session_end = session_end_raw if session_end_raw is not None else now
            
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
        total_usage: float = 0.0
        for session in self.sessions:
            duration = session.get_duration()
            if duration:
                total_usage += duration
        return int(total_usage)
    
    def average_session_duration(self, time_window: timedelta = timedelta()) -> int | None:
        """Calculate average session duration"""
        if not self.sessions:
            return None
        sesssions_in_window: list[Session] = [s for s in self.sessions if (s.get_start_time() >= datetime.now() - time_window) or time_window == timedelta()]
        total_duration: float = sum(s.get_duration() or 0 for s in sesssions_in_window)
        return round(total_duration / len(sesssions_in_window)) if sesssions_in_window else None
    
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
    
    def to_dict(self, first_timestamp: int | None) -> dict[str, list[dict[str, str | list[dict[str, int | list[dict[str, str | int | list[dict[str, str | float | None]] | dict[str, int | float | None]]]]]]] | str]:
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
    valid_timestamps = [session["startTime"] for session in sessions if "startTime" in session and isinstance(session["startTime"], int)]
    if not valid_timestamps:
        return None
    first_timestamp = min(valid_timestamps)
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


def generate_weeks_stats(cluster:Cluster) -> dict:
    """Generate statistics for each days of the weeks from all known sessions in the cluster"""
    days: dict[str, dict[str, dict[str, int | float]]] = {}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        days[day] = {
            "total": {
                "session_count": 0,
                "usage_seconds": 0
            },
            "average": {
                "session_count": 0,
                "usage_seconds": 0
            }
        }

    def get_day_name(dt: datetime) -> str:
        return dt.strftime("%A")  # Get full weekday name
    
    def weeks_passed(start_time: datetime) -> int:
        now = datetime.now()
        return max(1, (now - start_time).days // 7)  # Ensure at least 1 week to avoid division by zero

    for zone in cluster.zones.values():
        for row in zone.rows.values():
            for computer in row.computers.values():
                for session in computer.sessions:
                    day_name = get_day_name(session.get_start_time())
                    days[day_name]["total"]["session_count"] += 1
                    session_duration: float | None = session.get_duration()
                    if session_duration:
                        # check if the duration does not exceed the current day (if the session is still active or ended on another day)
                        session_end_time = session.get_end_time() or datetime.now()
                        if session_end_time.date() != session.get_start_time().date():
                            # if the session ended on another day, we only count the duration until the end of the start day
                            session_duration = (datetime.combine(session.get_start_time().date(), datetime.max.time()) - session.get_start_time()).total_seconds()
                            session_duration = max(session_duration, 0)  # Ensure non-negative duration
                            # add the remaining duration to the day of the end time if it's different
                            if session_end_time.date() != session.get_start_time().date():
                                end_day_name = get_day_name(session_end_time)
                                remaining_duration = (session_end_time - datetime.combine(session.get_start_time().date(), datetime.max.time())).total_seconds()
                                remaining_duration = max(remaining_duration, 0)  # Ensure non-negative duration
                                days[end_day_name]["total"]["session_count"] += 1  # Count the session for the end day as well
                                days[end_day_name]["total"]["usage_seconds"] += remaining_duration
                        days[day_name]["total"]["usage_seconds"] += session_duration
    # Calculate averages (get the total sessions and usage seconds for each day and divide by the number of ocurrences of that day in the data)
    first_timestamp = get_first_timestamp({"sessions": [s.to_dict() for zone in cluster.zones.values() for row in zone.rows.values() for comp in row.computers.values() for s in comp.sessions]})
    
    # If there are no sessions, return empty stats
    if first_timestamp is None:
        return days
    
    first_datetime = datetime.fromtimestamp(first_timestamp)
    weeks = weeks_passed(first_datetime)
    for day in days:
        total_sessions: int | float = days[day]["total"]["session_count"]
        total_usage: int | float = days[day]["total"]["usage_seconds"]
        days[day]["average"]["session_count"] = round(total_sessions / weeks, 2)  # Average per day of the week
        days[day]["average"]["usage_seconds"] = round(total_usage / weeks, 2)  # Average per day of the week

    return days

def generate_day_stats(cluster: Cluster, day: str) -> dict:
    """Generate average concurrent users for every 10 minutes of a day of the week (00:00 to 23:59)"""
    # Get all sessions
    all_sessions = [s for zone in cluster.zones.values()
                    for row in zone.rows.values()
                    for comp in row.computers.values()
                    for s in comp.sessions]
    
    if not all_sessions:
        return {}
    
    # Find all unique dates for this day of the week in the dataset
    day_dates = set()
    for session in all_sessions:
        current_date = session.get_start_time().date()
        end_date = (session.get_end_time() or datetime.now()).date()
        
        check_date = current_date
        while check_date <= end_date:
            if datetime.combine(check_date, datetime.min.time()).strftime("%A") == day:
                day_dates.add(check_date)
            check_date += timedelta(days=1)
    
    if not day_dates:
        return {}
    
    num_occurrences = len(day_dates)
    
    # Initialize time slots with totals
    time_slot_totals: dict[str, int] = {}
    current_time = datetime.strptime("00:00", "%H:%M")
    end_of_day = datetime.strptime("23:59", "%H:%M")
    
    while current_time <= end_of_day:
        time_slot = current_time.strftime("%H:%M")
        time_slot_totals[time_slot] = 0
        current_time += timedelta(minutes=10)
    
    # For each specific date occurrence of this day of the week
    for specific_date in day_dates:
        slot_time = datetime.strptime("00:00", "%H:%M")
        
        for time_slot in time_slot_totals.keys():
            slot_time = datetime.strptime(time_slot, "%H:%M")
            slot_datetime = datetime.combine(specific_date, slot_time.time())
            slot_end_datetime = slot_datetime + timedelta(minutes=10)
            
            # Count concurrent sessions for this specific time slot on this specific date
            concurrent_count = 0
            for session in all_sessions:
                session_start = session.get_start_time()
                session_end = session.get_end_time() or datetime.now()
                
                # Check if session overlaps with this specific time slot
                if session_start < slot_end_datetime and session_end > slot_datetime:
                    concurrent_count += 1
            
            time_slot_totals[time_slot] += concurrent_count
    
    # Calculate averages
    day_stats: dict[str, int] = {}
    for time_slot, total in time_slot_totals.items():
        day_stats[time_slot] = round(total / num_occurrences)
    
    return day_stats

def generate_all_days_stats(cluster: Cluster) -> dict[str, dict[str, int]]:
    """Generate the number of sessions for every 10 minutes of every day of the week from all known sessions in the cluster"""
    all_days_stats: dict[str, dict[str, int]] = {}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        all_days_stats[day] = generate_day_stats(cluster, day)
    return all_days_stats

def main():
    parser = argparse.ArgumentParser(description="Fetch and analyze cluster usage statistics from 42 custom API")
    parser.add_argument("--url", type=str, default=URL, help="URL to fetch session data from")
    parser.add_argument("--output", type=str, help="Output file to save the cluster data as JSON")
    args = parser.parse_args()

    data = fetch_data(args.url)
    cluster = build_cluster(data)

    def print_output(cluster: Cluster) -> str:
        dict_data = cluster.to_dict(get_first_timestamp(data))
        dict_data["weeks_stats"] = generate_weeks_stats(cluster)
        days_stats = generate_all_days_stats(cluster)
        for day, stats in days_stats.items():
            dict_data["weeks_stats"][day]["sessions_graph"] = stats
        return json.dumps(dict_data, indent=4)

    if args.output:
        with open(args.output, "w") as f:
            f.write(print_output(cluster))
    else:
        with open("cluster.json", "w") as f:
            f.write(print_output(cluster))

if __name__ == "__main__":
    main()
