#!/usr/bin/env python3
"""
Visualization script for bigstat42
Generate graphs showing cluster usage patterns across different days of the week
"""

import json
import os
import numpy as np
import matplotlib.pyplot as plt
import argparse
from datetime import datetime


def load_cluster_data(filepath: str) -> dict:
    """Load cluster data from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def time_to_minutes(time_str: str) -> int:
    """Convert time string HH:MM to minutes since midnight."""
    hours, minutes = map(int, time_str.split(':'))
    return hours * 60 + minutes


def plot_average_weekly_usage(data: dict, output_file: str = None):
    """Plot average usage across all days of the week."""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c', '#34495e']
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    weekend = ['Saturday', 'Sunday']
    
    plt.figure(figsize=(16, 10))
    
    for idx, day in enumerate(days):
        sessions_graph = data['weeks_stats'][day]['sessions_graph']
        times = sorted(sessions_graph.keys(), key=time_to_minutes)
        values = [sessions_graph[t] for t in times]
        time_minutes = [time_to_minutes(t) for t in times]
        
        plt.subplot(3, 3, idx + 1)
        plt.plot(time_minutes, values, color=colors[idx], linewidth=2)
        plt.fill_between(time_minutes, values, alpha=0.3, color=colors[idx])
        plt.title(f'{day}', fontsize=12, fontweight='bold')
        plt.xlabel('Hour of Day', fontsize=10)
        plt.ylabel('Concurrent Users', fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # Set x-axis to show hours
        plt.xticks(range(0, 1440, 180), [f'{h:02d}:00' for h in range(0, 24, 3)], rotation=45)
        
        # Add peak value annotation
        max_val = max(values)
        max_idx = values.index(max_val)
        max_time = times[max_idx]
        plt.annotate(f'Peak: {max_val}', 
                    xy=(time_minutes[max_idx], max_val),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                    fontsize=8)
    
    # Add overall title and layout
    plt.subplot(3, 3, 8)
    plt.axis('off')
    last_update = data.get('last_update', 'Unknown')
    info_text = f"Cluster Usage Statistics\n\nLast Update: {last_update}\n\n"
    info_text += "Average concurrent users per 10-minute intervals\n"
    info_text += "calculated across all occurrences of each day"
    plt.text(0.5, 0.5, info_text, ha='center', va='center', 
             fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Add inset plot: Weekday vs Weekend comparison in position 9 (bottom right)
    ax_inset = plt.subplot(3, 3, 9)
    
    # Calculate weekday average
    weekday_data = {}
    for day in weekdays:
        sessions_graph = data['weeks_stats'][day]['sessions_graph']
        for time_slot, value in sessions_graph.items():
            if time_slot not in weekday_data:
                weekday_data[time_slot] = []
            weekday_data[time_slot].append(value)
    
    weekday_avg = {t: np.mean(v) for t, v in weekday_data.items()}
    
    # Calculate weekend average
    weekend_data = {}
    for day in weekend:
        sessions_graph = data['weeks_stats'][day]['sessions_graph']
        for time_slot, value in sessions_graph.items():
            if time_slot not in weekend_data:
                weekend_data[time_slot] = []
            weekend_data[time_slot].append(value)
    
    weekend_avg = {t: np.mean(v) for t, v in weekend_data.items()}
    
    # Plot averages
    times = sorted(weekday_avg.keys(), key=time_to_minutes)
    time_minutes = [time_to_minutes(t) for t in times]
    
    weekday_values = [weekday_avg[t] for t in times]
    weekend_values = [weekend_avg[t] for t in times]
    
    ax_inset.plot(time_minutes, weekday_values, color='#0066cc', linewidth=2, 
                  label='Weekday Avg', alpha=0.9)
    ax_inset.fill_between(time_minutes, weekday_values, alpha=0.3, color='#0066cc')
    
    ax_inset.plot(time_minutes, weekend_values, color='#cc0000', linewidth=2, 
                  label='Weekend Avg', alpha=0.9)
    ax_inset.fill_between(time_minutes, weekend_values, alpha=0.3, color='#cc0000')
    
    ax_inset.set_title('Weekday vs Weekend', fontsize=10, fontweight='bold')
    ax_inset.set_xlabel('Hour of Day', fontsize=8)
    ax_inset.set_ylabel('Concurrent Users', fontsize=8)
    ax_inset.grid(True, alpha=0.3)
    ax_inset.legend(loc='upper left', fontsize=7)
    ax_inset.set_xticks(range(0, 1440, 360))
    ax_inset.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 6)], fontsize=7, rotation=45)
    ax_inset.tick_params(axis='y', labelsize=7)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Average weekly usage plot saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()


def plot_weekly_comparison(data: dict, output_file: str = None):
    """Plot all days on a single graph for comparison."""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c', '#34495e']
    
    plt.figure(figsize=(16, 8))
    
    for idx, day in enumerate(days):
        sessions_graph = data['weeks_stats'][day]['sessions_graph']
        times = sorted(sessions_graph.keys(), key=time_to_minutes)
        values = [sessions_graph[t] for t in times]
        time_minutes = [time_to_minutes(t) for t in times]
        
        plt.plot(time_minutes, values, color=colors[idx], linewidth=2, 
                label=day, alpha=0.8)
    
    plt.title('Weekly Cluster Usage Comparison - All Days', fontsize=16, fontweight='bold')
    plt.xlabel('Hour of Day', fontsize=12)
    plt.ylabel('Average Concurrent Users', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left', fontsize=10)
    
    # Set x-axis to show hours
    plt.xticks(range(0, 1440, 60), [f'{h:02d}:00' for h in range(0, 24)], rotation=45)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Weekly comparison plot saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()


def plot_weekday_vs_weekend(data: dict, output_file: str = None):
    """Plot weekday average vs weekend average."""
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    weekend = ['Saturday', 'Sunday']
    
    plt.figure(figsize=(14, 6))
    
    # Calculate weekday average
    weekday_data = {}
    for day in weekdays:
        sessions_graph = data['weeks_stats'][day]['sessions_graph']
        for time_slot, value in sessions_graph.items():
            if time_slot not in weekday_data:
                weekday_data[time_slot] = []
            weekday_data[time_slot].append(value)
    
    weekday_avg = {t: np.mean(v) for t, v in weekday_data.items()}
    
    # Calculate weekend average
    weekend_data = {}
    for day in weekend:
        sessions_graph = data['weeks_stats'][day]['sessions_graph']
        for time_slot, value in sessions_graph.items():
            if time_slot not in weekend_data:
                weekend_data[time_slot] = []
            weekend_data[time_slot].append(value)
    
    weekend_avg = {t: np.mean(v) for t, v in weekend_data.items()}
    
    # Plot
    times = sorted(weekday_avg.keys(), key=time_to_minutes)
    time_minutes = [time_to_minutes(t) for t in times]
    
    weekday_values = [weekday_avg[t] for t in times]
    weekend_values = [weekend_avg[t] for t in times]
    
    plt.plot(time_minutes, weekday_values, color='#3498db', linewidth=3, 
             label='Weekday Average (Mon-Fri)', alpha=0.8)
    plt.fill_between(time_minutes, weekday_values, alpha=0.3, color='#3498db')
    
    plt.plot(time_minutes, weekend_values, color='#e74c3c', linewidth=3, 
             label='Weekend Average (Sat-Sun)', alpha=0.8)
    plt.fill_between(time_minutes, weekend_values, alpha=0.3, color='#e74c3c')
    
    plt.title('Weekday vs Weekend Usage Comparison', fontsize=16, fontweight='bold')
    plt.xlabel('Hour of Day', fontsize=12)
    plt.ylabel('Average Concurrent Users', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left', fontsize=12)
    
    # Set x-axis to show hours
    plt.xticks(range(0, 1440, 60), [f'{h:02d}:00' for h in range(0, 24)], rotation=45)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Weekday vs weekend plot saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()


def plot_heatmap(data: dict, output_file: str = None):
    """Create a heatmap showing usage across days and hours."""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Prepare data matrix
    sessions_graph = data['weeks_stats']['Monday']['sessions_graph']
    times = sorted(sessions_graph.keys(), key=time_to_minutes)
    
    matrix = np.zeros((len(days), len(times)))
    
    for day_idx, day in enumerate(days):
        sessions_graph = data['weeks_stats'][day]['sessions_graph']
        for time_idx, time_slot in enumerate(times):
            matrix[day_idx][time_idx] = sessions_graph[time_slot]
    
    plt.figure(figsize=(20, 8))
    
    im = plt.imshow(matrix, aspect='auto', cmap='YlOrRd', interpolation='nearest')
    
    plt.colorbar(im, label='Concurrent Users')
    plt.yticks(range(len(days)), days)
    
    # Show every 12th time slot (every 2 hours)
    time_labels = [times[i] if i % 12 == 0 else '' for i in range(len(times))]
    plt.xticks(range(len(times)), time_labels, rotation=45)
    
    plt.xlabel('Time of Day', fontsize=12)
    plt.ylabel('Day of Week', fontsize=12)
    plt.title('Cluster Usage Heatmap - Weekly Pattern', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Heatmap saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Visualize cluster usage statistics"
    )
    parser.add_argument(
        '--input', 
        type=str, 
        default='cluster.json',
        help='Input JSON file with cluster data (default: cluster.json)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help='Output directory for generated plots (default: current directory)'
    )
    parser.add_argument(
        '--format',
        type=str,
        default='png',
        choices=['png', 'pdf', 'svg'],
        help='Output format for plots (default: png)'
    )
    parser.add_argument(
        '--show',
        action='store_true',
        help='Display plots interactively instead of saving to files'
    )
    parser.add_argument(
        '--plot',
        type=str,
        nargs='+',
        choices=['individual', 'comparison', 'weekday-weekend', 'heatmap', 'all'],
        default=['all'],
        help='Which plots to generate (default: all)'
    )
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading data from {args.input}...")
    data = load_cluster_data(args.input)
    
    plots_to_generate = args.plot
    if 'all' in plots_to_generate:
        plots_to_generate = ['individual', 'comparison', 'weekday-weekend', 'heatmap']
    
    output_prefix = None if args.show else f"{args.output_dir}/cluster_usage/"
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    if not os.path.exists(f"{args.output_dir}/cluster_usage"):
        os.makedirs(f"{args.output_dir}/cluster_usage")
    
    # Generate requested plots
    if 'individual' in plots_to_generate:
        print("\nGenerating individual days plot...")
        output_file = None if args.show else f"{output_prefix}_individual.{args.format}"
        plot_average_weekly_usage(data, output_file)
    
    if 'comparison' in plots_to_generate:
        print("\nGenerating weekly comparison plot...")
        output_file = None if args.show else f"{output_prefix}_comparison.{args.format}"
        plot_weekly_comparison(data, output_file)
    
    if 'weekday-weekend' in plots_to_generate:
        print("\nGenerating weekday vs weekend plot...")
        output_file = None if args.show else f"{output_prefix}_weekday_vs_weekend.{args.format}"
        plot_weekday_vs_weekend(data, output_file)
    
    if 'heatmap' in plots_to_generate:
        print("\nGenerating heatmap...")
        output_file = None if args.show else f"{output_prefix}_heatmap.{args.format}"
        plot_heatmap(data, output_file)
    
    print("\nVisualization complete!")


if __name__ == "__main__":
    main()
