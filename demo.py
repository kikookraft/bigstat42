"""
Demo script to test bigstat42 with sample data (no API credentials needed)
"""

from datetime import datetime, timedelta
import random
from bigstat42.analyzer import UsageAnalyzer
from bigstat42.visualizer import Visualizer


def generate_sample_data(num_days=7, sessions_per_day=50):
    """Generate sample location log data for testing"""
    location_logs = []
    
    # Sample hosts (computer names in cluster)
    hosts = [f"e{row}r{seat}s{num}" 
             for row in range(1, 6) 
             for seat in range(1, 11) 
             for num in range(1, 3)]
    
    # Sample users
    user_ids = list(range(1000, 1100))
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=num_days)
    
    current_date = start_date
    while current_date < end_date:
        # Generate sessions throughout the day
        for _ in range(random.randint(30, sessions_per_day)):
            # Random hour (weighted towards daytime hours)
            hour = random.choices(
                range(24),
                weights=[1, 1, 1, 1, 1, 2, 5, 10, 15, 20, 20, 20, 
                        20, 20, 18, 16, 14, 12, 10, 8, 5, 3, 2, 1]
            )[0]
            
            begin_at = current_date.replace(
                hour=hour,
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            # Random session duration (30 min to 6 hours)
            duration_minutes = random.randint(30, 360)
            end_at = begin_at + timedelta(minutes=duration_minutes)
            
            location_logs.append({
                'user': {
                    'id': random.choice(user_ids),
                    'login': f"user{random.randint(100, 999)}"
                },
                'host': random.choice(hosts),
                'begin_at': begin_at.isoformat(),
                'end_at': end_at.isoformat()
            })
        
        current_date += timedelta(days=1)
    
    return location_logs


def main():
    """Run the demo"""
    print("=" * 70)
    print("BIGSTAT42 DEMO - Testing with Sample Data")
    print("=" * 70)
    print("\nThis demo generates sample cluster usage data and creates visualizations.")
    print("No API credentials needed!\n")
    
    # Generate sample data
    print("Generating sample data...")
    num_days = 14
    location_logs = generate_sample_data(num_days=num_days, sessions_per_day=80)
    print(f"✓ Generated {len(location_logs)} sample location logs for {num_days} days")
    
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
    output_dir = "demo_output"
    visualizer = Visualizer(output_dir=output_dir)
    
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
    print(f"✓ Demo complete! Check the '{output_dir}/' directory for visualizations.")
    print("=" * 70)
    print("\nVisualization files created:")
    print(f"  - {output_dir}/usage_heatmap_day_hour.png")
    print(f"  - {output_dir}/usage_heatmap_hosts_hour.png")
    print(f"  - {output_dir}/hourly_usage.png")
    print(f"  - {output_dir}/daily_usage.png")
    print(f"  - {output_dir}/top_hosts.png")
    print(f"  - {output_dir}/summary.txt")


if __name__ == "__main__":
    main()
