#!/usr/bin/env python3
"""
Main application for bigstat42
Fetch and analyze cluster usage statistics from 42 API
"""

URL = "https://api.raraph.fr/intra-metrics/sessions" # URL to fetch session data
#-> response example: {'sessions': [{'host': 'z1r12p1', 'startTime': 1769657139375, 'endTime': 1769708139235}, {'host': 'z1r8p1', 'startTime': 1769668421566, 'endTime': 1769696742793}, {'host': 'z2r10p8', 'startTime': 1769668603475, 'endTime': 1769711087574}, {'host': 'z2r9p8', 'startTime': 1769669442977, 'endTime': 1769705922935}, {'host': 'z4r2p2', 'startTime': 1769669559336, 'endTime': 1769696319485}, {'host': 'z4r6p1', 'startTime': 1769669805179, 'endTime': 1769695426924}, {'host': 'z4r11p3', 'startTime': 1769669859922, 'endTime': 1769711500128}

import requests
import argparse
import sys
from datetime import datetime, timedelta
from collections import defaultdict
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
    def __init__(self, host: str, start_time: int, end_time: int) -> None:
        self.host = host
        self.start_time = datetime.fromtimestamp(start_time / 1000)
        self.end_time = datetime.fromtimestamp(end_time / 1000) if end_time is not None else None

    def duration(self) -> timedelta:
        """Return the duration of the session."""
        return self.end_time - self.start_time

    def get_host(self) -> str:
        return self.host
    
    def get_start_time(self) -> datetime:   
        return self.start_time
    
    def get_end_time(self) -> datetime:
        return self.end_time
    
    def is_active(self, at_time: datetime) -> bool:
        """Check if the session was active at a given time."""
        return self.start_time <= at_time and (self.end_time is None or self.end_time >= at_time)
    
    def __repr__(self) -> str:
        return f"Session(host={self.host}, start_time={self.start_time}, end_time={self.end_time})"

class Computer:
    """Class representing a computer with multiple sessions."""
    def __init__(self, name: str) -> None:
        self.name = name
        self.sessions: list[Session] = []

    def add_session(self, session: 'Session') -> None:
        """Add a session to the computer.
        There should be no overlapping sessions for the same computer.
        """
        for existing_session in self.sessions:
            if check_overlap(existing_session, session):
                raise ValueError(f"Overlapping sessions detected on {self.name}: {existing_session} and {session}")
        self.sessions.append(session)

    def total_usage(self) -> timedelta:
        """Calculate total usage time across all sessions."""
        total = timedelta()
        for session in self.sessions:
            total += session.duration()
        return total
    
    def get_active_sessions(self, at_time: datetime) -> list[Session]:
        """Get all sessions active at a given time."""
        return [session for session in self.sessions if session.is_active(at_time)]
    
    def __repr__(self) -> str:
        return f"Computer(name={self.name}, sessions={self.sessions})"

def fetch_data(url: str) -> dict:
    """Fetch data from the given URL and return as JSON."""
    try:
        response: requests.Response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return {}

