"""
Visualization module for creating heatmaps and charts
"""

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from typing import Dict, List, Tuple, Optional
import os


class Visualizer:
    """Create visualizations for cluster usage data"""
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize the visualizer
        
        Args:
            output_dir: Directory to save output files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Set style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (12, 8)
    
    def create_heatmap(self, data: np.ndarray, row_labels: List[str], 
                      col_labels: List[str], title: str, 
                      filename: str, cmap: str = "YlOrRd"):
        """
        Create a heatmap visualization
        
        Args:
            data: 2D array of values
            row_labels: Labels for rows
            col_labels: Labels for columns
            title: Title for the plot
            filename: Filename to save the plot
            cmap: Color map to use
        """
        try:
            plt.figure(figsize=(16, 8))
            
            # Create heatmap
            sns.heatmap(data, annot=True, fmt='.0f', cmap=cmap, 
                       xticklabels=col_labels, yticklabels=row_labels,
                       cbar_kws={'label': 'Number of Sessions'})
            
            plt.title(title, fontsize=16, fontweight='bold')
            plt.xlabel('Hour of Day', fontsize=12)
            plt.ylabel('', fontsize=12)
            plt.tight_layout()
            
            filepath = os.path.join(self.output_dir, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"Heatmap saved to: {filepath}")
            return filepath
        except Exception as e:
            plt.close()  # Ensure figure is closed even on error
            print(f"Error creating heatmap: {e}")
            raise
    
    def create_hourly_usage_chart(self, hourly_data: Dict[int, int], filename: str = "hourly_usage.png"):
        """
        Create a bar chart of hourly usage
        
        Args:
            hourly_data: Dictionary mapping hour to usage count
            filename: Filename to save the plot
        """
        plt.figure(figsize=(14, 6))
        
        hours = sorted(hourly_data.keys())
        counts = [hourly_data[h] for h in hours]
        
        plt.bar(hours, counts, color='steelblue', alpha=0.8)
        plt.xlabel('Hour of Day', fontsize=12)
        plt.ylabel('Number of Sessions', fontsize=12)
        plt.title('Cluster Usage by Hour of Day', fontsize=16, fontweight='bold')
        plt.xticks(hours)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Hourly usage chart saved to: {filepath}")
        return filepath
    
    def create_daily_usage_chart(self, daily_data: Dict[str, int], filename: str = "daily_usage.png"):
        """
        Create a bar chart of daily usage
        
        Args:
            daily_data: Dictionary mapping day name to usage count
            filename: Filename to save the plot
        """
        plt.figure(figsize=(12, 6))
        
        # Order days properly
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        days = [d for d in day_order if d in daily_data]
        counts = [daily_data[d] for d in days]
        
        plt.bar(days, counts, color='coral', alpha=0.8)
        plt.xlabel('Day of Week', fontsize=12)
        plt.ylabel('Number of Sessions', fontsize=12)
        plt.title('Cluster Usage by Day of Week', fontsize=16, fontweight='bold')
        plt.xticks(rotation=45)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Daily usage chart saved to: {filepath}")
        return filepath
    
    def create_top_hosts_chart(self, host_data: Dict[str, int], top_n: int = 20, 
                              filename: str = "top_hosts.png"):
        """
        Create a bar chart of most used hosts
        
        Args:
            host_data: Dictionary mapping host to usage count
            top_n: Number of top hosts to display
            filename: Filename to save the plot
        """
        plt.figure(figsize=(14, 8))
        
        # Get top N hosts
        sorted_hosts = sorted(host_data.items(), key=lambda x: x[1], reverse=True)[:top_n]
        hosts = [h[0] for h in sorted_hosts]
        counts = [h[1] for h in sorted_hosts]
        
        plt.barh(hosts, counts, color='mediumseagreen', alpha=0.8)
        plt.xlabel('Number of Sessions', fontsize=12)
        plt.ylabel('Host', fontsize=12)
        plt.title(f'Top {top_n} Most Used Computers', fontsize=16, fontweight='bold')
        plt.gca().invert_yaxis()  # Highest at top
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Top hosts chart saved to: {filepath}")
        return filepath
    
    def create_summary_report(self, stats: Dict, filename: str = "summary.txt"):
        """
        Create a text summary report
        
        Args:
            stats: Dictionary with summary statistics
            filename: Filename to save the report
        """
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w') as f:
                f.write("=" * 60 + "\n")
                f.write("CLUSTER USAGE STATISTICS SUMMARY\n")
                f.write("=" * 60 + "\n\n")
                
                f.write(f"Date Range: {stats.get('date_range', 'N/A')}\n\n")
                
                f.write(f"Total Sessions: {stats.get('total_sessions', 0):,}\n")
                f.write(f"Unique Users: {stats.get('unique_users', 0):,}\n")
                f.write(f"Unique Hosts: {stats.get('unique_hosts', 0):,}\n\n")
                
                avg_duration = stats.get('average_session_duration_minutes', 0)
                f.write(f"Average Session Duration: {avg_duration:.2f} minutes ({avg_duration/60:.2f} hours)\n")
                
                total_hours = stats.get('total_usage_hours', 0)
                f.write(f"Total Usage Time: {total_hours:.2f} hours ({total_hours/24:.2f} days)\n\n")
                
                f.write("=" * 60 + "\n")
            
            print(f"Summary report saved to: {filepath}")
            return filepath
        except IOError as e:
            print(f"Error writing summary report: {e}")
            raise
    
    def create_all_visualizations(self, heatmap_data: Tuple[np.ndarray, List[str], List[str]],
                                 host_heatmap_data: Tuple[np.ndarray, List[str], List[str]],
                                 hourly_data: Dict[int, int],
                                 daily_data: Dict[str, int],
                                 host_data: Dict[str, int],
                                 stats: Dict):
        """
        Create all visualizations and reports
        
        Args:
            heatmap_data: Data for day/hour heatmap
            host_heatmap_data: Data for host/hour heatmap
            hourly_data: Hourly usage data
            daily_data: Daily usage data
            host_data: Host usage data
            stats: Summary statistics
        """
        print("\nGenerating visualizations...")
        print("-" * 60)
        
        # Create heatmaps
        data, days, hours = heatmap_data
        self.create_heatmap(data, days, hours, 
                          "Cluster Usage Heatmap - Day vs Hour",
                          "usage_heatmap_day_hour.png")
        
        host_data_array, host_labels, hour_labels = host_heatmap_data
        if len(host_labels) > 1 or host_labels[0] != 'No data':
            self.create_heatmap(host_data_array, host_labels, hour_labels,
                              "Cluster Usage Heatmap - Top Hosts vs Hour",
                              "usage_heatmap_hosts_hour.png")
        
        # Create charts
        self.create_hourly_usage_chart(hourly_data)
        self.create_daily_usage_chart(daily_data)
        self.create_top_hosts_chart(host_data)
        
        # Create summary report
        self.create_summary_report(stats)
        
        print("-" * 60)
        print(f"\nAll visualizations saved to: {self.output_dir}/")
