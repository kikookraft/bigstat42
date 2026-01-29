#!/usr/bin/env python3
"""
Main application for bigstat42
Fetch and analyze cluster usage statistics from 42 API
"""

import argparse
import sys
import os
from datetime import datetime

from bigstat42.api_client import API42Client
from bigstat42.analyzer import UsageAnalyzer
from bigstat42.visualizer import Visualizer


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="Fetch and analyze cluster usage statistics from 42 API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze usage for the last 7 days
  python -m bigstat42.main --campus 1 --days 7
  
  # Analyze usage for the last 30 days with custom output directory
  python -m bigstat42.main --campus 1 --days 30 --output my_stats
  
  # Use custom API credentials
  python -m bigstat42.main --campus 1 --days 14 --uid YOUR_UID --secret YOUR_SECRET
        """
    )
    
    parser.add_argument(
        '--campus',
        type=int,
        default=9,
        help='Campus ID (default: 9 for Lyon)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=60,
        help='Number of days to analyze (default: 7, max: 365)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='output',
        help='Output directory for visualizations (default: output)'
    )
    
    parser.add_argument(
        '--uid',
        type=str,
        help='API UID (if not set in .env file)'
    )
    
    parser.add_argument(
        '--secret',
        type=str,
        help='API Secret (if not set in .env file)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.campus <= 0:
        print("✗ Error: Campus ID must be a positive integer")
        return 1
    
    if args.days < 1 or args.days > 365:
        print("✗ Error: Number of days must be between 1 and 365")
        return 1
    
    print("=" * 70)
    print("BIGSTAT42 - 42 Cluster Usage Statistics")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Campus ID: {args.campus}")
    print(f"  Days to analyze: {args.days}")
    print(f"  Output directory: {args.output}")
    print()
    
    try:
        # Initialize API client
        print("Initializing API client...")
        client = API42Client(api_uid=args.uid, api_secret=args.secret)
        print("✓ API client initialized successfully")
        
        # Fetch location logs
        print(f"\nFetching location logs for the last {args.days} days...")
        print("This may take a while depending on the amount of data...")
        location_logs = client.get_location_logs(args.campus, args.days)
        print(f"✓ Fetched {len(location_logs)} location logs")
        
        if not location_logs:
            print("\n⚠ No location data found for the specified period.")
            print("Please check:")
            print("  - Your API credentials have the correct permissions")
            print("  - The campus ID is correct (common IDs: 1=Paris, 9=Fremont, etc.)")
            print("  - Visit https://api.intra.42.fr/apidoc/guides/web_application_flow for API docs")
            print("  - There is activity data for the specified time period")
            return 1
        
        # Analyze data
        print("\nAnalyzing usage data...")
        analyzer = UsageAnalyzer(location_logs)
        
        # Get summary statistics
        stats = analyzer.get_summary_stats()
        print("✓ Analysis complete")
        
        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY STATISTICS")
        print("=" * 70)
        print(f"Date Range: {stats['date_range']}")
        print(f"Total Sessions: {stats['total_sessions']:,}")
        print(f"Unique Users: {stats['unique_users']:,}")
        print(f"Unique Hosts: {stats['unique_hosts']:,}")
        print(f"Average Session Duration: {stats['average_session_duration_minutes']:.2f} minutes")
        print(f"Total Usage Time: {stats['total_usage_hours']:.2f} hours")
        print("=" * 70)
        
        # Create visualizations
        visualizer = Visualizer(output_dir=args.output)
        
        # Get all data for visualizations
        heatmap_data = analyzer.get_heatmap_data()
        host_heatmap_data = analyzer.get_host_heatmap_data(top_n=20)
        hourly_data = analyzer.get_hourly_usage()
        daily_data = analyzer.get_daily_usage()
        host_data = analyzer.get_host_usage()
        
        # Create all visualizations
        visualizer.create_all_visualizations(
            heatmap_data,
            host_heatmap_data,
            hourly_data,
            daily_data,
            host_data,
            stats
        )
        
        print("\n" + "=" * 70)
        print("✓ All done! Check the output directory for visualizations.")
        print("=" * 70)
        
        return 0
        
    except ValueError as e:
        print(f"\n✗ Configuration error: {e}")
        print("\nPlease ensure you have:")
        print("  1. Created a .env file with API_UID and API_SECRET")
        print("  2. Or provided --uid and --secret command line arguments")
        print("\nSee .env.example for the expected format.")
        return 1
        
    except Exception as e:
        print(f"\n✗ An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
