#!/usr/bin/env python3
"""
Cluster Visualizer using Pygame
Creates a visual heatmap interface mimicking the cluster layout
"""

import os
import pygame
import json
import sys
import argparse
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Color definitions
COLOR_BACKGROUND = (240, 240, 240)
COLOR_TEXT = (80, 80, 80)
COLOR_ZONE_LABEL = (50, 50, 50)
COLOR_ROW_LABEL = (150, 150, 150)
COLOR_COMPUTER_BORDER = (50, 30, 30)
COLOR_USED = (30, 200, 30)
COLOR_DISABLED = (200, 200, 200)

# Heatmap colors (from cold/unused to hot/heavily used)
HEATMAP_COLORS = [
    (220, 230, 255),  # Very light blue - 0% usage
    (100, 200, 255),  # Light blue - 25% usage
    (100, 255, 100),  # Light green - 50% usage
    (255, 200, 50),   # Orange - 75% usage
    (255, 50, 50),    # Red - 100% usage
]

# Layout configuration
COMPUTER_SIZE = 45
COMPUTER_SPACING = 10
ROW_SPACING = 15
ZONE_SPACING = 80
MARGIN_TOP = 80
MARGIN_LEFT = 100
MARGIN_RIGHT = 50
MARGIN_BOTTOM = 50

# Zone layouts (which zones are on each floor)
# Based on the images provided: Z2, Z1 on upper floor; Z4, Z3 on lower floor
UPPER_ZONES: list[str] = ["z2", "z1"]
LOWER_ZONES: list[str] = ["z4", "z3"]

# Computer positions per zone (approximate layout from images)
ZONE_LAYOUTS: dict[str, dict[str, list[int] | int]] = {
    "z1": {
        "positions_per_row": [0, 2, 3, 4, 5],  # R1: positions 2-5, R2-R12: varies
        "max_position": 5
    },
    "z2": {
        "positions_per_row": [0, 2, 3, 4, 5, 6, 7, 8],  # R1-R12: positions vary
        "max_position": 8
    },
    "z3": {
        "positions_per_row": [0, 2, 3, 4, 5, 6],
        "max_position": 6
    },
    "z4": {
        "positions_per_row": [0, 2, 3, 4, 5, 6, 7],
        "max_position": 7
    }
}


def interpolate_color(value: float, max_value: float = 100.0) -> Tuple[int, int, int]:
    """
    Interpolate color based on usage percentage (0-100)
    Returns RGB tuple
    """
    if value < 0:
        value = 0
    if value > 100:
        value = 100

    if max_value <= 0:
        max_value = 100.0
    if value >= max_value:
        return HEATMAP_COLORS[-1]
    
    # Determine which color segment we're in
    segment_count = len(HEATMAP_COLORS) - 1
    segment = value / max_value * segment_count
    segment_index = int(segment)
    
    if segment_index >= segment_count:
        return HEATMAP_COLORS[-1]
    
    # Interpolate between two colors
    local_t = segment - segment_index
    color1 = HEATMAP_COLORS[segment_index]
    color2 = HEATMAP_COLORS[segment_index + 1]
    
    r = int(color1[0] + (color2[0] - color1[0]) * local_t)
    g = int(color1[1] + (color2[1] - color1[1]) * local_t)
    b = int(color1[2] + (color2[2] - color1[2]) * local_t)
    
    return (r, g, b)

def get_max_percentage_used(cluster_data: Dict[str, Any], time_window: str = "7d") -> float:
    """Get the maximum usage percentage across all computers for scaling"""
    max_used = 0.0
    stats_key = f"{time_window}_stats"
    for zone in cluster_data.get("zones", []):
        for row in zone.get("rows", []):
            for computer in row.get("computers", []):
                stats = computer.get(stats_key, {})
                usage = stats.get("usage_percentage", 0.0)
                if usage > max_used:
                    max_used = usage
    return max_used

def is_computer_used(computer_data: Dict[str, Any]) -> bool:
    """Determine if a computer is currently in use (has an active session)"""
    sessions = computer_data.get("sessions", [])
    for session in sessions:
        if session.get("end_time") is None:
            return True
    return False

class ComputerRect:
    """Represents a computer position on screen"""
    def __init__(self, name: str, position: int, rect: pygame.Rect, 
                 usage_percent: float, session_count: int, avg_duration: Optional[float], max_usage: float = 100.0, is_used: bool = False, border_radius: int = 10):
        self.name = name
        self.position = position
        self.rect = rect
        self.usage_percent = usage_percent
        self.session_count = session_count
        self.avg_duration = avg_duration
        self.color = interpolate_color(usage_percent, max_usage)
        self.is_used = is_used
        self.border_radius = border_radius
    
    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        """Draw the computer rectangle with heatmap color"""
        # Fill with heatmap color
        pygame.draw.rect(screen, self.color, self.rect, border_radius=self.border_radius)
        
        # Draw border
        if self.is_used:
            pygame.draw.rect(screen, COLOR_USED, self.rect, int(self.border_radius/2), border_radius=self.border_radius)
        else:
            pygame.draw.rect(screen, COLOR_COMPUTER_BORDER, self.rect, int(self.border_radius/2), border_radius=self.border_radius)
        
        # Draw position number
        text = font.render(str(self.position), True, COLOR_TEXT)
        text_rect = text.get_rect(center=self.rect.center)
        screen.blit(text, text_rect)
    
    def get_tooltip_text(self) -> List[str]:
        """Get tooltip information"""
        avg_str = f"{self.avg_duration/3600:.1f}h" if self.avg_duration else "N/A"
        return [
            f"Computer: {self.name}",
            f"Usage: {self.usage_percent:.1f}%",
            f"Sessions: {self.session_count}",
            f"Avg Duration: {avg_str}"
        ]


class ClusterVisualizer:
    """Main visualizer class"""
    def __init__(self, json_file: str, time_window: str = "7d", scale: float = 1.0):
        self.json_file = json_file
        self.time_window = time_window
        self.scale = scale
        self.cluster_data = None
        self.computer_rects: List[ComputerRect] = []
        self.hovered_computer: Optional[ComputerRect] = None
        self.max_usage = 100.0  # Default max usage for color scaling
        
        # Load data
        self.load_data()
        
        # Initialize Pygame
        pygame.init()
        self.font_small = pygame.font.Font(None, int(20 * scale))
        self.font_medium = pygame.font.Font(None, int(28 * scale))
        self.font_large = pygame.font.Font(None, int(36 * scale))
        self.font_tooltip = pygame.font.Font(None, int(22 * scale))
        
        # Calculate screen size and create display
        self.calculate_layout()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        pygame.display.set_caption(f"Cluster Usage Heatmap - {time_window}")
        
        # Build visual elements
        self.build_layout()
    
    def load_data(self):
        """Load cluster data from JSON file"""
        try:
            with open(self.json_file, 'r') as f:
                self.cluster_data = json.load(f)
            print(f"Loaded cluster data from {self.json_file}")
            self.max_usage = get_max_percentage_used(self.cluster_data, self.time_window)
        except Exception as e:
            print(f"Error loading JSON file: {e}", file=sys.stderr)
            sys.exit(1)
    
    def calculate_layout(self):
        """Calculate screen dimensions based on cluster layout"""
        # Apply scaling to all layout constants
        s = self.scale
        computer_size = int(COMPUTER_SIZE * s)
        computer_spacing = int(COMPUTER_SPACING * s)
        row_spacing = int(ROW_SPACING * s)
        zone_spacing = int(ZONE_SPACING * s)
        margin_top = int(MARGIN_TOP * s)
        margin_left = int(MARGIN_LEFT * s)
        margin_right = int(MARGIN_RIGHT * s)
        margin_bottom = int(MARGIN_BOTTOM * s)
        
        # Store scaled values for use in other methods
        self.computer_size = computer_size
        self.computer_spacing = computer_spacing
        self.row_spacing = row_spacing
        self.zone_spacing = zone_spacing
        self.margin_top = margin_top
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_bottom = margin_bottom
        
        # Calculate width: 2 zones side by side
        zone_width = 8 * (computer_size + computer_spacing)
        max_width = margin_left + zone_width * 2 + zone_spacing + margin_right
        
        # Calculate height: 2 floors (upper and lower)
        rows_per_floor = 13  # Max rows per zone
        floor_height = rows_per_floor * (computer_size + row_spacing)
        max_height = margin_top + floor_height * 2 + zone_spacing + margin_bottom + int(150 * s)  # Extra for legend
        
        self.screen_width = max_width
        self.screen_height = max_height
    
    def get_computer_stats(self, computer_data: Dict[str, Any]) -> Tuple[float, int, Optional[float]]:
        """Extract statistics based on selected time window"""
        stats_key = f"{self.time_window}_stats"
        
        if stats_key in computer_data:
            stats = computer_data[stats_key]
            return (
                stats.get("usage_percentage", 0),
                stats.get("session_count", 0),
                stats.get("average_session_duration")
            )
        return (0, 0, None)
    
    def build_layout(self):
        """Build the layout of all zones and computers"""
        self.computer_rects = []
        
        if not self.cluster_data or "zones" not in self.cluster_data:
            print("No zone data found")
            return
        
        self.max_usage = get_max_percentage_used(self.cluster_data, self.time_window)
        
        # Organize zones
        zones_dict = {zone["zone_name"]: zone for zone in self.cluster_data["zones"]}
        
        # Draw upper floor (Z2, Z1)
        self.draw_floor(zones_dict, UPPER_ZONES, 0)
        
        # Draw lower floor (Z4, Z3)
        floor_offset = 13 * (self.computer_size + self.row_spacing) + self.zone_spacing
        self.draw_floor(zones_dict, LOWER_ZONES, floor_offset)
    
    def draw_floor(self, zones_dict: Dict[str, Any], zone_names: List[str], y_offset: int):
        """Draw a floor with multiple zones"""
        for idx, zone_name in enumerate(zone_names):
            if zone_name not in zones_dict:
                continue
            
            zone_data = zones_dict[zone_name]
            x_offset = idx * (8 * (self.computer_size + self.computer_spacing) + self.zone_spacing)
            
            self.draw_zone(zone_data, self.margin_left + x_offset, self.margin_top + y_offset)
    
    def draw_zone(self, zone_data: Dict[str, Any], start_x: int, start_y: int):
        """Draw a single zone with all its rows"""
        rows = sorted(zone_data.get("rows", []), key=lambda r: r["row_number"])
        
        for row in rows:
            row_number = row["row_number"]
            row_y = start_y + (row_number - 1) * (self.computer_size + self.row_spacing)
            
            computers = sorted(row.get("computers", []), key=lambda c: c["position"])
            
            for computer in computers:
                position = computer["position"]
                # Position from right to left (8 to 1 for z2, 5 to 1 for z1, etc.)
                computer_x = start_x + (8 - position) * (self.computer_size + self.computer_spacing)
                
                # Get statistics
                usage_percent, session_count, avg_duration = self.get_computer_stats(computer)
                
                rect = pygame.Rect(computer_x, row_y, self.computer_size, self.computer_size)
                computer_rect = ComputerRect(
                    computer["name"],
                    position,
                    rect,
                    usage_percent,
                    session_count,
                    avg_duration,
                    self.max_usage,
                    is_used=is_computer_used(computer),
                    border_radius=int(10 * self.scale)
                )
                self.computer_rects.append(computer_rect)
    
    def draw(self):
        """Draw the entire visualization"""
        self.screen.fill(COLOR_BACKGROUND)
        
        # Draw title
        title_text = f"42 Cluster Usage Heatmap - {self.time_window.upper()} View"
        title_surface = self.font_large.render(title_text, True, COLOR_ZONE_LABEL)
        self.screen.blit(title_surface, (self.screen_width // 2 - title_surface.get_width() // 2, 20))
        
        # Draw floor labels
        self.draw_floor_labels()
        
        # Draw zone labels
        self.draw_zone_labels()
        
        # Draw row labels
        self.draw_row_labels()
        
        # Draw all computers
        for computer_rect in self.computer_rects:
            computer_rect.draw(self.screen, self.font_small)
        
        # Draw legend
        self.draw_legend()
        
        # Draw tooltip if hovering
        if self.hovered_computer:
            self.draw_tooltip(self.hovered_computer)
        
        pygame.display.flip()
    
    def draw_floor_labels(self):
        """Draw floor labels (Upper/Lower)"""
        # Upper floor
        # upper_text = self.font_medium.render("UPPER FLOOR", True, COLOR_ZONE_LABEL)
        # self.screen.blit(upper_text, (20, MARGIN_TOP))
        
        # Lower floor
        # floor_offset = 13 * (COMPUTER_SIZE + ROW_SPACING) + ZONE_SPACING
        # lower_text = self.font_medium.render("LOWER FLOOR", True, COLOR_ZONE_LABEL)
        # self.screen.blit(lower_text, (20, MARGIN_TOP + floor_offset))
    
    def draw_zone_labels(self):
        """Draw zone labels"""
        # Upper zones
        for idx, zone_name in enumerate(UPPER_ZONES):
            x_offset = idx * (8 * (self.computer_size + self.computer_spacing) + self.zone_spacing)
            zone_text = self.font_large.render(zone_name.upper(), True, COLOR_ZONE_LABEL)
            self.screen.blit(zone_text, (self.margin_left + x_offset + int(150 * self.scale), self.margin_top - int(40 * self.scale)))
        
        # Lower zones
        floor_offset = 13 * (self.computer_size + self.row_spacing) + self.zone_spacing
        for idx, zone_name in enumerate(LOWER_ZONES):
            x_offset = idx * (8 * (self.computer_size + self.computer_spacing) + self.zone_spacing)
            zone_text = self.font_large.render(zone_name.upper(), True, COLOR_ZONE_LABEL)
            self.screen.blit(zone_text, (self.margin_left + x_offset + int(150 * self.scale), self.margin_top + floor_offset - int(40 * self.scale)))
    
    def draw_row_labels(self):
        """Draw row number labels"""
        for row_num in range(1, 14):
            # Upper floor rows
            row_y = self.margin_top + (row_num - 1) * (self.computer_size + self.row_spacing)
            row_text = self.font_small.render(f"R{row_num}", True, COLOR_ROW_LABEL)
            self.screen.blit(row_text, (self.margin_left - int(40 * self.scale), row_y + self.computer_size // 2 - int(10 * self.scale)))
            
            # Lower floor rows
            floor_offset = 13 * (self.computer_size + self.row_spacing) + self.zone_spacing
            row_y_lower = self.margin_top + floor_offset + (row_num - 1) * (self.computer_size + self.row_spacing)
            row_text_lower = self.font_small.render(f"R{row_num}", True, COLOR_ROW_LABEL)
            self.screen.blit(row_text_lower, (self.margin_left - int(40 * self.scale), row_y_lower + self.computer_size // 2 - int(10 * self.scale)))
    
    def draw_legend(self):
        """Draw color legend"""
        legend_y = self.screen_height - int(120 * self.scale)
        legend_x = int(50 * self.scale)
        
        # Legend title
        legend_title = self.font_medium.render("Usage Legend:", True, COLOR_ZONE_LABEL)
        self.screen.blit(legend_title, (legend_x, legend_y - int(30 * self.scale)))
        
        # Draw color gradient
        segment_width = int(60 * self.scale)
        for i, color in enumerate(HEATMAP_COLORS):
            rect = pygame.Rect(legend_x + i * segment_width, legend_y, segment_width, int(30 * self.scale))
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, COLOR_COMPUTER_BORDER, rect, 1)
            
            # Labels
            if i == 0:
                label = self.font_small.render("0%", True, COLOR_TEXT)
                self.screen.blit(label, (rect.x, rect.y + int(35 * self.scale)))
            elif i == len(HEATMAP_COLORS) - 1:
                label = self.font_small.render("100%", True, COLOR_TEXT)
                self.screen.blit(label, (rect.x + segment_width - int(30 * self.scale), rect.y + int(35 * self.scale)))
        
        # Time window selector hint
        hint_text = self.font_small.render("Press 1/7/30/A to change time window", True, COLOR_ROW_LABEL)
        self.screen.blit(hint_text, (legend_x + int(400 * self.scale), legend_y + int(5 * self.scale)))
        
        # Export hint
        export_text = self.font_small.render("Press E to export view", True, COLOR_ROW_LABEL)
        self.screen.blit(export_text, (legend_x + int(400 * self.scale), legend_y + int(30 * self.scale)))

        reload_text = self.font_small.render("Press R to regenerate data", True, COLOR_ROW_LABEL)
        self.screen.blit(reload_text, (legend_x + int(400 * self.scale), legend_y + int(55 * self.scale)))

        last_update = self.cluster_data.get("last_update", "N/A") if self.cluster_data else "N/A"
        update_text = self.font_small.render(f"Last Data Update: {last_update}", True, COLOR_ROW_LABEL)
        self.screen.blit(update_text, (legend_x + int(400 * self.scale), legend_y + int(80 * self.scale)))
    
    def draw_tooltip(self, computer_rect: ComputerRect):
        """Draw tooltip for hovered computer"""
        mouse_x, mouse_y = pygame.mouse.get_pos()
        
        lines = computer_rect.get_tooltip_text()
        
        # Calculate tooltip size
        padding = 10
        line_height = 25
        max_width = max(self.font_tooltip.render(line, True, COLOR_TEXT).get_width() for line in lines)
        tooltip_width = max_width + padding * 2
        tooltip_height = len(lines) * line_height + padding * 2
        
        # Position tooltip (avoid going off screen)
        tooltip_x = mouse_x + 15
        tooltip_y = mouse_y + 15
        
        if tooltip_x + tooltip_width > self.screen_width:
            tooltip_x = mouse_x - tooltip_width - 15
        if tooltip_y + tooltip_height > self.screen_height:
            tooltip_y = mouse_y - tooltip_height - 15
        
        # Draw tooltip background
        tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, tooltip_width, tooltip_height)
        pygame.draw.rect(self.screen, (250, 250, 250), tooltip_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_COMPUTER_BORDER, tooltip_rect, 2, border_radius=10)
        
        # Draw tooltip text
        for i, line in enumerate(lines):
            text_surface = self.font_tooltip.render(line, True, COLOR_TEXT)
            self.screen.blit(text_surface, (tooltip_x + padding, tooltip_y + padding + i * line_height))
    
    def handle_mouse_motion(self, pos: Tuple[int, int]):
        """Handle mouse motion for tooltip"""
        self.hovered_computer = None
        for computer_rect in self.computer_rects:
            if computer_rect.rect.collidepoint(pos):
                self.hovered_computer = computer_rect
                break
    
    def change_time_window(self, new_window: str):
        """Change the time window and rebuild layout"""
        self.time_window = new_window
        pygame.display.set_caption(f"Cluster Usage Heatmap - {new_window}")
        self.build_layout()
    
    def recalculate_scale_from_window(self, width: int, height: int):
        """Recalculate scale factor based on new window dimensions"""
        # Base dimensions (from original calculation with scale=1.0)
        base_width = MARGIN_LEFT + (8 * (COMPUTER_SIZE + COMPUTER_SPACING)) * 2 + ZONE_SPACING + MARGIN_RIGHT
        base_height = MARGIN_TOP + (13 * (COMPUTER_SIZE + ROW_SPACING)) * 2 + ZONE_SPACING + MARGIN_BOTTOM + 150
        
        # Calculate scale that fits both width and height
        scale_x = width / base_width
        scale_y = height / base_height
        
        # Use the smaller scale to ensure everything fits
        new_scale = min(scale_x, scale_y)
        
        # Clamp scale to reasonable bounds
        new_scale = max(0.3, min(new_scale, 2.0))
        
        return new_scale
    
    def handle_resize(self, width: int, height: int):
        """Handle window resize event"""
        # Update screen dimensions
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        
        # Recalculate scale based on new window size
        self.scale = self.recalculate_scale_from_window(width, height)
        
        # Update fonts with new scale
        self.font_small = pygame.font.Font(None, int(20 * self.scale))
        self.font_medium = pygame.font.Font(None, int(28 * self.scale))
        self.font_large = pygame.font.Font(None, int(36 * self.scale))
        self.font_tooltip = pygame.font.Font(None, int(22 * self.scale))
        
        # Recalculate layout with new scale
        self.calculate_layout()
        self.build_layout()
    
    def export_screenshot(self):
        """Export current view as PNG"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cluster_heatmap_{self.time_window}_{timestamp}.png"
        pygame.image.save(self.screen, filename)
        print(f"Screenshot saved as {filename}")
    
    def run(self):
        """Main event loop"""
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event.w, event.h)
                
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event.pos)
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_1:
                        self.change_time_window("1d")
                    elif event.key == pygame.K_7:
                        self.change_time_window("7d")
                    elif event.key == pygame.K_3:
                        self.change_time_window("30d")
                    elif event.key == pygame.K_a:
                        self.change_time_window("all_time")
                    elif event.key == pygame.K_e:
                        self.export_screenshot()
                    elif event.key == pygame.K_r:
                        # call main.py to regenerate data
                        subprocess.run([sys.executable, "fetch_data.py"])
                        self.load_data()
                        self.build_layout()
            
            self.draw()
            clock.tick(30)  # 30 FPS
        
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Visualize cluster usage as a heatmap")
    parser.add_argument("json_file", type=str, default=None, nargs="?",
                       help="Path to JSON file generated by main.py (default: cluster.json)")
    parser.add_argument("--time-window", type=str, default="1d", 
                       choices=["1d", "7d", "30d", "all_time"],
                       help="Time window for statistics (default: 7d)")
    parser.add_argument("--scale", type=float, default=1.0,
                       help="Scale factor for display (0.5 for 1080p, 1.0 for 4K, default: 1.0)")
    parser.add_argument("--resolution", type=str, choices=["1080p", "4k"], default="1080p", nargs="?",
                       help="Preset resolution (1080p=0.5 scale, 4k=1.0 scale)")
    
    args = parser.parse_args()
    
    # Handle resolution presets
    if args.resolution == "1080p":
        scale = 0.5
    elif args.resolution == "4k":
        scale = 1.0
    else:
        scale = args.scale
    if args.json_file is None:
        if not os.path.exists("cluster.json"):
            print("No JSON file provided and cluster.json not found. Generating data...")
            subprocess.run([sys.executable, "fetch_data.py", "--output", "cluster.json"])
            args.json_file = "cluster.json"
        else:
            print("No JSON file provided. Using existing cluster.json.")
            args.json_file = "cluster.json"
    
    visualizer = ClusterVisualizer(args.json_file, args.time_window, scale)
    visualizer.run()


if __name__ == "__main__":
    main()
