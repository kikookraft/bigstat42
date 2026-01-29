"""
42 API Client for fetching location and user data
"""

import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv


class API42Client:
    """Client for interacting with the 42 API"""
    
    BASE_URL = "https://api.intra.42.fr"
    TOKEN_URL = f"{BASE_URL}/oauth/token"
    
    def __init__(self, api_uid: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize the API client with credentials"""
        load_dotenv()
        
        self.api_uid = api_uid or os.getenv("API_UID")
        self.api_secret = api_secret or os.getenv("API_SECRET")
        
        if not self.api_uid or not self.api_secret:
            raise ValueError("API_UID and API_SECRET must be provided or set in .env file")
        
        self.access_token = None
        self.token_expires_at = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with the 42 API and get an access token"""
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_uid,
            "client_secret": self.api_secret
        }
        
        response = requests.post(self.TOKEN_URL, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        # Token expires in seconds, store the expiration time
        expires_in = token_data.get("expires_in", 7200)
        self.token_expires_at = time.time() + expires_in
    
    def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        if not self.access_token or time.time() >= self.token_expires_at - 60:
            self._authenticate()
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make an authenticated request to the API"""
        self._ensure_authenticated()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def _paginated_request(self, endpoint: str, params: Optional[Dict] = None, max_pages: int = 10000) -> List[Dict]:
        """Make paginated requests to the API"""
        if params is None:
            params = {}
        
        all_results = []
        page = 1
        params["page[size]"] = 100  # Maximum page size
        
        while page <= max_pages:
            params["page[number]"] = page
            
            try:
                results = self._make_request(endpoint, params)
                
                if not results:
                    break
                
                if isinstance(results, list):
                    all_results.extend(results)
                    if len(results) < params["page[size]"]:
                        break
                else:
                    # Single result
                    all_results.append(results)
                    break
                
                page += 1
                
                # Rate limiting: be nice to the API
                time.sleep(0.1)
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    break
                raise
        
        return all_results
    
    def get_campus_locations(self, campus_id: int, start_date: Optional[datetime] = None, 
                            end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Get location logs for a campus
        
        Args:
            campus_id: The campus ID
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            
        Returns:
            List of location log dictionaries
        """
        params = {
            "filter[campus_id]": campus_id,
        }
        
        if start_date:
            params["range[begin_at]"] = f"{start_date.isoformat()},{end_date.isoformat() if end_date else datetime.now().isoformat()}"
        
        return self._paginated_request("/v2/campus/{}/locations".format(campus_id), params)
    
    def get_user_locations(self, user_id: int, start_date: Optional[datetime] = None, 
                          end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Get location logs for a specific user
        
        Args:
            user_id: The user ID
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)
            
        Returns:
            List of location log dictionaries
        """
        params = {}
        
        if start_date:
            params["range[begin_at]"] = f"{start_date.isoformat()},{end_date.isoformat() if end_date else datetime.now().isoformat()}"
        
        return self._paginated_request(f"/v2/users/{user_id}/locations", params)
    
    def get_location_logs(self, campus_id: int, days_back: int = 30) -> List[Dict]:
        """
        Get location logs for a campus for the last N days
        
        Args:
            campus_id: The campus ID (must be positive)
            days_back: Number of days to look back (must be between 1 and 365)
            
        Returns:
            List of location log dictionaries
        """
        if campus_id <= 0:
            raise ValueError("campus_id must be a positive integer")
        
        if days_back < 1 or days_back > 365:
            raise ValueError("days_back must be between 1 and 365")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Use the campus locations endpoint
        return self.get_campus_locations(campus_id, start_date, end_date)
