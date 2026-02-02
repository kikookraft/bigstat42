#!/usr/bin/env python3
"""
Cluster Visualizer using Pygame
Creates a visual heatmap interface mimicking the cluster layout
"""

import pygame
import json
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# Color definitions
COLOR_BACKGROUND = (240, 240, 240)
COLOR_TEXT = (80, 80, 80)
COLOR_ZONE_LABEL = (50, 50, 50)
COLOR_ROW_LABEL = (150, 150, 150)
COLOR_COMPUTER_BORDER = (30, 30, 30)
COLOR_USED = (70, 200, 70)
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
UPPER_ZONES = ["z2", "z1"]
LOWER_ZONES = ["z4", "z3"]

# Computer positions per zone (approximate layout from images)
ZONE_LAYOUTS = {
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

def get_max_percentage_used(cluster_data: Dict, time_window: str = "7d") -> float:
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

def is_computer_used(computer_data: Dict) -> bool:
    """Determine if a computer is currently in use (has an active session)"""
    sessions = computer_data.get("sessions", [])
    for session in sessions:
        if session.get("end_time") is None:
            return True
    return False

class ComputerRect:
    """Represents a computer position on screen"""
    def __init__(self, name: str, position: int, rect: pygame.Rect, 
                 usage_percent: float, session_count: int, avg_duration: Optional[float], max_usage: float = 100.0, is_used: bool = False):
        self.name = name
        self.position = position
        self.rect = rect
        self.usage_percent = usage_percent
        self.session_count = session_count
        self.avg_duration = avg_duration
        self.color = interpolate_color(usage_percent, max_usage)
        self.is_used = is_used
    
    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        """Draw the computer rectangle with heatmap color"""
        # Fill with heatmap color
        pygame.draw.rect(screen, self.color, self.rect)
        
        # Draw border
        if self.is_used:
            pygame.draw.rect(screen, COLOR_USED, self.rect, 3)
        else:
            pygame.draw.rect(screen, COLOR_COMPUTER_BORDER, self.rect, 2)
        
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
    def __init__(self, json_file: str, time_window: str = "7d"):
        self.json_file = json_file
        self.time_window = time_window
        self.cluster_data = None
        self.computer_rects: List[ComputerRect] = []
        self.hovered_computer: Optional[ComputerRect] = None
        self.max_usage = 100.0  # Default max usage for color scaling
        
        # Load data
        self.load_data()
        
        # Initialize Pygame
        pygame.init()
        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_large = pygame.font.Font(None, 36)
        self.font_tooltip = pygame.font.Font(None, 22)
        
        # Calculate screen size and create display
        self.calculate_layout()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
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
        # Find max dimensions needed
        max_width = 0
        max_height = 0
        
        # Calculate width: 2 zones side by side
        zone_width = 8 * (COMPUTER_SIZE + COMPUTER_SPACING)
        max_width = MARGIN_LEFT + zone_width * 2 + ZONE_SPACING + MARGIN_RIGHT
        
        # Calculate height: 2 floors (upper and lower)
        rows_per_floor = 13  # Max rows per zone
        floor_height = rows_per_floor * (COMPUTER_SIZE + ROW_SPACING)
        max_height = MARGIN_TOP + floor_height * 2 + ZONE_SPACING + MARGIN_BOTTOM + 150  # Extra for legend
        
        self.screen_width = max_width
        self.screen_height = max_height
    
    def get_computer_stats(self, computer_data: Dict) -> Tuple[float, int, Optional[float]]:
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
        floor_offset = 13 * (COMPUTER_SIZE + ROW_SPACING) + ZONE_SPACING
        self.draw_floor(zones_dict, LOWER_ZONES, floor_offset)
    
    def draw_floor(self, zones_dict: Dict, zone_names: List[str], y_offset: int):
        """Draw a floor with multiple zones"""
        for idx, zone_name in enumerate(zone_names):
            if zone_name not in zones_dict:
                continue
            
            zone_data = zones_dict[zone_name]
            x_offset = idx * (8 * (COMPUTER_SIZE + COMPUTER_SPACING) + ZONE_SPACING)
            
            self.draw_zone(zone_data, MARGIN_LEFT + x_offset, MARGIN_TOP + y_offset)
    
    def draw_zone(self, zone_data: Dict, start_x: int, start_y: int):
        """Draw a single zone with all its rows"""
        zone_name = zone_data["zone_name"]
        rows = sorted(zone_data.get("rows", []), key=lambda r: r["row_number"])
        
        for row in rows:
            row_number = row["row_number"]
            row_y = start_y + (row_number - 1) * (COMPUTER_SIZE + ROW_SPACING)
            
            computers = sorted(row.get("computers", []), key=lambda c: c["position"])
            
            for computer in computers:
                position = computer["position"]
                # Position from right to left (8 to 1 for z2, 5 to 1 for z1, etc.)
                computer_x = start_x + (8 - position) * (COMPUTER_SIZE + COMPUTER_SPACING)
                
                # Get statistics
                usage_percent, session_count, avg_duration = self.get_computer_stats(computer)
                
                rect = pygame.Rect(computer_x, row_y, COMPUTER_SIZE, COMPUTER_SIZE)
                computer_rect = ComputerRect(
                    computer["name"],
                    position,
                    rect,
                    usage_percent,
                    session_count,
                    avg_duration,
                    self.max_usage,
                    is_used=is_computer_used(computer)
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
            x_offset = idx * (8 * (COMPUTER_SIZE + COMPUTER_SPACING) + ZONE_SPACING)
            zone_text = self.font_large.render(zone_name.upper(), True, COLOR_ZONE_LABEL)
            self.screen.blit(zone_text, (MARGIN_LEFT + x_offset + 150, MARGIN_TOP - 40))
        
        # Lower zones
        floor_offset = 13 * (COMPUTER_SIZE + ROW_SPACING) + ZONE_SPACING
        for idx, zone_name in enumerate(LOWER_ZONES):
            x_offset = idx * (8 * (COMPUTER_SIZE + COMPUTER_SPACING) + ZONE_SPACING)
            zone_text = self.font_large.render(zone_name.upper(), True, COLOR_ZONE_LABEL)
            self.screen.blit(zone_text, (MARGIN_LEFT + x_offset + 150, MARGIN_TOP + floor_offset - 40))
    
    def draw_row_labels(self):
        """Draw row number labels"""
        for row_num in range(1, 14):
            # Upper floor rows
            row_y = MARGIN_TOP + (row_num - 1) * (COMPUTER_SIZE + ROW_SPACING)
            row_text = self.font_small.render(f"R{row_num}", True, COLOR_ROW_LABEL)
            self.screen.blit(row_text, (MARGIN_LEFT - 40, row_y + COMPUTER_SIZE // 2 - 10))
            
            # Lower floor rows
            floor_offset = 13 * (COMPUTER_SIZE + ROW_SPACING) + ZONE_SPACING
            row_y_lower = MARGIN_TOP + floor_offset + (row_num - 1) * (COMPUTER_SIZE + ROW_SPACING)
            row_text_lower = self.font_small.render(f"R{row_num}", True, COLOR_ROW_LABEL)
            self.screen.blit(row_text_lower, (MARGIN_LEFT - 40, row_y_lower + COMPUTER_SIZE // 2 - 10))
    
    def draw_legend(self):
        """Draw color legend"""
        legend_y = self.screen_height - 120
        legend_x = 50
        
        # Legend title
        legend_title = self.font_medium.render("Usage Legend:", True, COLOR_ZONE_LABEL)
        self.screen.blit(legend_title, (legend_x, legend_y - 30))
        
        # Draw color gradient
        segment_width = 60
        for i, color in enumerate(HEATMAP_COLORS):
            rect = pygame.Rect(legend_x + i * segment_width, legend_y, segment_width, 30)
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, COLOR_COMPUTER_BORDER, rect, 1)
            
            # Labels
            if i == 0:
                label = self.font_small.render("0%", True, COLOR_TEXT)
                self.screen.blit(label, (rect.x, rect.y + 35))
            elif i == len(HEATMAP_COLORS) - 1:
                label = self.font_small.render("100%", True, COLOR_TEXT)
                self.screen.blit(label, (rect.x + segment_width - 30, rect.y + 35))
        
        # Time window selector hint
        hint_text = self.font_small.render("Press 1/7/30/A to change time window", True, COLOR_ROW_LABEL)
        self.screen.blit(hint_text, (legend_x + 400, legend_y + 5))
        
        # Export hint
        export_text = self.font_small.render("Press E to export view", True, COLOR_ROW_LABEL)
        self.screen.blit(export_text, (legend_x + 400, legend_y + 30))

        reload_text = self.font_small.render("Press R to regenerate data", True, COLOR_ROW_LABEL)
        self.screen.blit(reload_text, (legend_x + 400, legend_y + 55))

        last_update = self.cluster_data.get("last_update", "N/A") if self.cluster_data else "N/A"
        update_text = self.font_small.render(f"Last Data Update: {last_update}", True, COLOR_ROW_LABEL)
        self.screen.blit(update_text, (legend_x + 400, legend_y + 80))
    
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
        pygame.draw.rect(self.screen, (255, 255, 220), tooltip_rect)
        pygame.draw.rect(self.screen, COLOR_COMPUTER_BORDER, tooltip_rect, 2)
        
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
                        import subprocess
                        subprocess.run([sys.executable, "bigstat42-fast/main.py"])
                        self.load_data()
                        self.build_layout()
            
            self.draw()
            clock.tick(30)  # 30 FPS
        
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Visualize cluster usage as a heatmap")
    parser.add_argument("json_file", type=str, 
                       help="Path to JSON file generated by main.py (default: cluster.json)")
    parser.add_argument("--time-window", type=str, default="7d", 
                       choices=["1d", "7d", "30d", "all_time"],
                       help="Time window for statistics (default: 7d)")
    
    args = parser.parse_args()
    
    visualizer = ClusterVisualizer(args.json_file, args.time_window)
    visualizer.run()


if __name__ == "__main__":
    main()
