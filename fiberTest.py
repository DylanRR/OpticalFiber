import pygame
import math
import sys

# Initialize Pygame
pygame.init()

# Get screen dimensions for dual monitor setup
info = pygame.display.Info()
# For dual monitors, we want the total width of both screens
SCREEN_WIDTH = info.current_w * 2  # Assuming two monitors of equal width
SCREEN_HEIGHT = info.current_h

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
BLUE = (0, 100, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
DARK_RED = (139, 0, 0)

# Critical angle for total internal reflection (typical for optical fiber)
CRITICAL_ANGLE = 12.0  # degrees (realistic for glass core to glass cladding)

# Slider dimensions
SLIDER_HEIGHT = 60
SLIDER_Y = SCREEN_HEIGHT - SLIDER_HEIGHT - 20
SLIDER_X = 50
SLIDER_WIDTH = SCREEN_WIDTH - 100
SLIDER_HANDLE_WIDTH = 20

# Fiber dimensions (the main area where light travels)
FIBER_TOP = 50
FIBER_BOTTOM = SLIDER_Y - 50
FIBER_LEFT = 50
FIBER_RIGHT = SCREEN_WIDTH - 50
FIBER_HEIGHT = FIBER_BOTTOM - FIBER_TOP

class OpticalFiberSimulation:
    def __init__(self):
        # Create display spanning both monitors
        # Position the window at the left edge of the primary monitor
        import os
        os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
        
        # Create a window that spans both monitors
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
        pygame.display.set_caption("Optical Fiber Light Path Simulation - Dual Monitor")
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Slider properties
        self.slider_value = 0.5  # 0.0 to 1.0 (center position)
        self.dragging = False
        
        # Font for text
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_F11:
                    # Toggle between windowed and fullscreen
                    current_flags = self.screen.get_flags()
                    if current_flags & pygame.FULLSCREEN:
                        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.NOFRAME)
                    else:
                        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    mouse_x, mouse_y = event.pos
                    # Check if clicking on slider
                    if (SLIDER_Y <= mouse_y <= SLIDER_Y + SLIDER_HEIGHT and
                        SLIDER_X <= mouse_x <= SLIDER_X + SLIDER_WIDTH):
                        self.dragging = True
                        self.update_slider(mouse_x)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    mouse_x, mouse_y = event.pos
                    # Only update if mouse is still in reasonable range
                    if 0 <= mouse_x <= SCREEN_WIDTH:
                        self.update_slider(mouse_x)
    
    def update_slider(self, mouse_x):
        # Calculate slider value based on mouse position with safety bounds
        try:
            relative_x = mouse_x - SLIDER_X
            self.slider_value = max(0.0, min(1.0, relative_x / SLIDER_WIDTH))
        except (ZeroDivisionError, TypeError):
            # Fallback to center position if calculation fails
            self.slider_value = 0.5
    
    def get_angle_from_slider(self):
        # Convert slider value to angle (-89.9 to +89.9 degrees)
        max_angle = 89.9  # degrees
        angle_degrees = (self.slider_value - 0.5) * 2 * max_angle
        return math.radians(angle_degrees)
    
    def calculate_light_path(self):
        # Starting point (left side of fiber, middle height)
        start_x = FIBER_LEFT
        start_y = FIBER_TOP + FIBER_HEIGHT // 2
        
        # Initial direction based on angle
        angle = self.get_angle_from_slider()
        dx = math.cos(angle)
        dy = math.sin(angle)
        
        # Trace the light path with bounces
        path_points = [(start_x, start_y)]
        bounce_angles = []  # Store angle of incidence at each bounce
        bounce_positions = []  # Store bounce positions
        current_x, current_y = start_x, start_y
        
        step_size = 2.0  # Smaller steps for smoother path
        total_distance = 0
        
        while current_x < FIBER_RIGHT:
            # Move one step
            next_x = current_x + dx * step_size
            next_y = current_y + dy * step_size
            
            # Check for bounces off top and bottom walls
            if next_y <= FIBER_TOP:
                # Bounce off top wall
                next_y = FIBER_TOP + (FIBER_TOP - next_y)
                
                # Calculate angle of incidence (angle between ray and normal to surface)
                incident_angle = math.degrees(math.atan2(abs(dy), abs(dx)))
                bounce_angles.append(incident_angle)
                bounce_positions.append((current_x, FIBER_TOP))
                
                dy = -dy  # Reverse vertical direction
            elif next_y >= FIBER_BOTTOM:
                # Bounce off bottom wall
                next_y = FIBER_BOTTOM - (next_y - FIBER_BOTTOM)
                
                # Calculate angle of incidence
                incident_angle = math.degrees(math.atan2(abs(dy), abs(dx)))
                bounce_angles.append(incident_angle)
                bounce_positions.append((current_x, FIBER_BOTTOM))
                
                dy = -dy  # Reverse vertical direction
            
            current_x = next_x
            current_y = next_y
            
            # Add to path (convert to int for drawing)
            path_points.append((int(current_x), int(current_y)))
            
            # Calculate distance
            if len(path_points) > 1:
                prev_point = path_points[-2]
                segment_distance = math.sqrt((current_x - prev_point[0])**2 + (current_y - prev_point[1])**2)
                total_distance += segment_distance
        
        return path_points, total_distance, bounce_angles, bounce_positions
    
    def draw_slider(self):
        # Draw slider track
        pygame.draw.rect(self.screen, GRAY, 
                        (SLIDER_X, SLIDER_Y + SLIDER_HEIGHT//2 - 5, SLIDER_WIDTH, 10))
        
        # Draw slider handle
        handle_x = SLIDER_X + self.slider_value * SLIDER_WIDTH - SLIDER_HANDLE_WIDTH // 2
        pygame.draw.rect(self.screen, WHITE, 
                        (handle_x, SLIDER_Y, SLIDER_HANDLE_WIDTH, SLIDER_HEIGHT))
        
        # Draw angle text in upper right corner
        angle_degrees = math.degrees(self.get_angle_from_slider())
        angle_text = self.font.render(f"Angle: {angle_degrees:.1f}°", True, WHITE)
        angle_rect = angle_text.get_rect()
        self.screen.blit(angle_text, (SCREEN_WIDTH - angle_rect.width - 20, 20))
    
    def draw_fiber(self):
        # Draw fiber walls (top and bottom)
        pygame.draw.line(self.screen, WHITE, (FIBER_LEFT, FIBER_TOP), (FIBER_RIGHT, FIBER_TOP), 3)
        pygame.draw.line(self.screen, WHITE, (FIBER_LEFT, FIBER_BOTTOM), (FIBER_RIGHT, FIBER_BOTTOM), 3)
        
        # Draw fiber sides
        pygame.draw.line(self.screen, WHITE, (FIBER_LEFT, FIBER_TOP), (FIBER_LEFT, FIBER_BOTTOM), 3)
        pygame.draw.line(self.screen, WHITE, (FIBER_RIGHT, FIBER_TOP), (FIBER_RIGHT, FIBER_BOTTOM), 3)
        
        # Fill fiber area with slight transparency
        fiber_surface = pygame.Surface((FIBER_RIGHT - FIBER_LEFT, FIBER_BOTTOM - FIBER_TOP))
        fiber_surface.set_alpha(30)
        fiber_surface.fill(BLUE)
        self.screen.blit(fiber_surface, (FIBER_LEFT, FIBER_TOP))
    
    def draw_light_path(self, path_points, total_distance, bounce_angles, bounce_positions):
        if len(path_points) < 2:
            return
        
        # Determine light color based on current angle and TIR
        current_angle = abs(math.degrees(self.get_angle_from_slider()))
        
        # Color coding for TIR
        if current_angle < CRITICAL_ANGLE:
            light_color = GREEN  # Good TIR - efficient transmission
        elif current_angle < CRITICAL_ANGLE + 10:
            light_color = YELLOW  # Marginal TIR
        else:
            light_color = ORANGE  # Poor TIR - would leak light in real fiber
        
        # Draw the light path with appropriate color
        for i in range(len(path_points) - 1):
            pygame.draw.line(self.screen, light_color, path_points[i], path_points[i + 1], 3)
        
        # Draw bounce points with angle indicators
        for i, (bounce_pos, incident_angle) in enumerate(zip(bounce_positions, bounce_angles)):
            # Color code bounce points based on angle of incidence
            if incident_angle < CRITICAL_ANGLE:
                bounce_color = GREEN
            elif incident_angle < CRITICAL_ANGLE + 10:
                bounce_color = YELLOW
            else:
                bounce_color = RED
            
            # Draw bounce point
            pygame.draw.circle(self.screen, bounce_color, (int(bounce_pos[0]), int(bounce_pos[1])), 6)
            
            # Draw angle of incidence text near first few bounces
            if i < 3:  # Show only first 3 bounces to avoid clutter
                angle_text = self.small_font.render(f"{incident_angle:.1f}°", True, WHITE)
                text_x = int(bounce_pos[0]) + 10
                text_y = int(bounce_pos[1]) - 20
                self.screen.blit(angle_text, (text_x, text_y))
        
        # Draw starting point
        pygame.draw.circle(self.screen, WHITE, (int(path_points[0][0]), int(path_points[0][1])), 7)
        pygame.draw.circle(self.screen, GREEN, (int(path_points[0][0]), int(path_points[0][1])), 5)
        
        # Draw ending point
        if path_points:
            end_point = path_points[-1]
            pygame.draw.circle(self.screen, WHITE, (int(end_point[0]), int(end_point[1])), 7)
            pygame.draw.circle(self.screen, light_color, (int(end_point[0]), int(end_point[1])), 5)
    
    def draw_info(self, total_distance, bounce_angles):
        # Calculate shortest path (straight line)
        shortest_distance = FIBER_RIGHT - FIBER_LEFT
        efficiency = (shortest_distance / total_distance) * 100 if total_distance > 0 else 100
        
        # TIR analysis
        current_angle = abs(math.degrees(self.get_angle_from_slider()))
        tir_status = "EXCELLENT" if current_angle < CRITICAL_ANGLE else "MARGINAL" if current_angle < CRITICAL_ANGLE + 10 else "POOR"
        avg_incident_angle = sum(bounce_angles) / len(bounce_angles) if bounce_angles else 0
        
        # Draw information panel
        info_y = 10
        
        title_text = self.font.render("Optical Fiber Light Path Simulation", True, WHITE)
        self.screen.blit(title_text, (10, info_y))
        info_y += 40
        
        # TIR Status
        tir_color = GREEN if tir_status == "EXCELLENT" else YELLOW if tir_status == "MARGINAL" else ORANGE
        tir_text = self.small_font.render(f"TIR Quality: {tir_status}", True, tir_color)
        self.screen.blit(tir_text, (10, info_y))
        info_y += 25
        
        critical_text = self.small_font.render(f"Critical Angle: {CRITICAL_ANGLE}° (for reference)", True, LIGHT_GRAY)
        self.screen.blit(critical_text, (10, info_y))
        info_y += 25
        
        if bounce_angles:
            avg_angle_text = self.small_font.render(f"Avg Incident Angle: {avg_incident_angle:.1f}°", True, WHITE)
            self.screen.blit(avg_angle_text, (10, info_y))
            info_y += 25
        
        distance_text = self.small_font.render(f"Light Path Distance: {total_distance:.1f} pixels", True, WHITE)
        self.screen.blit(distance_text, (10, info_y))
        info_y += 25
        
        shortest_text = self.small_font.render(f"Shortest Path: {shortest_distance:.1f} pixels", True, WHITE)
        self.screen.blit(shortest_text, (10, info_y))
        info_y += 25
        
        efficiency_text = self.small_font.render(f"Efficiency: {efficiency:.1f}%", True, WHITE)
        self.screen.blit(efficiency_text, (10, info_y))
        info_y += 25
        
        bounces = len([i for i in range(1, len(self.current_path) - 1) 
                      if (self.current_path[i][1] <= FIBER_TOP + 2 or 
                          self.current_path[i][1] >= FIBER_BOTTOM - 2)]) if hasattr(self, 'current_path') else 0
        
        bounce_text = self.small_font.render(f"Wall Bounces: {bounces}", True, WHITE)
        self.screen.blit(bounce_text, (10, info_y))
        
        # Enhanced Instructions
        instructions = [
            "Move slider to change light entry angle",
            "GREEN: Excellent TIR | YELLOW: Marginal | ORANGE: Poor",
            "Numbers show angle of incidence at bounce points",
            "F11: Toggle fullscreen | ESC: Exit"
        ]
        
        for i, instruction in enumerate(instructions):
            inst_text = self.small_font.render(instruction, True, LIGHT_GRAY)
            self.screen.blit(inst_text, (10, SCREEN_HEIGHT - 140 + i * 25))
    
    def run(self):
        while self.running:
            self.handle_events()
            
            # Calculate light path
            path_points, total_distance, bounce_angles, bounce_positions = self.calculate_light_path()
            self.current_path = path_points  # Store for bounce calculation
            
            # Clear screen
            self.screen.fill(BLACK)
            
            # Draw everything
            self.draw_fiber()
            self.draw_light_path(path_points, total_distance, bounce_angles, bounce_positions)
            self.draw_slider()
            self.draw_info(total_distance, bounce_angles)
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS
        
        pygame.quit()
        sys.exit()

# Run the simulation
if __name__ == "__main__":
    simulation = OpticalFiberSimulation()
    simulation.run()