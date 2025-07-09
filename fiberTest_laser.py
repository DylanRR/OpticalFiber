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

# Thickness slider dimensions
THICKNESS_SLIDER_HEIGHT = 40
THICKNESS_SLIDER_WIDTH = 200
THICKNESS_SLIDER_X = SCREEN_WIDTH - 320
THICKNESS_SLIDER_Y = 320
THICKNESS_SLIDER_HANDLE_WIDTH = 15

# Dash gap slider dimensions
DASH_GAP_SLIDER_HEIGHT = 40
DASH_GAP_SLIDER_WIDTH = 200
DASH_GAP_SLIDER_X = SCREEN_WIDTH - 320
DASH_GAP_SLIDER_Y = 380
DASH_GAP_SLIDER_HANDLE_WIDTH = 15

# Dash speed slider dimensions
DASH_SPEED_SLIDER_HEIGHT = 40
DASH_SPEED_SLIDER_WIDTH = 200
DASH_SPEED_SLIDER_X = SCREEN_WIDTH - 320
DASH_SPEED_SLIDER_Y = 440
DASH_SPEED_SLIDER_HANDLE_WIDTH = 15

# Vibrance slider dimensions
VIBRANCE_SLIDER_HEIGHT = 40
VIBRANCE_SLIDER_WIDTH = 200
VIBRANCE_SLIDER_X = SCREEN_WIDTH - 320
VIBRANCE_SLIDER_Y = 500
VIBRANCE_SLIDER_HANDLE_WIDTH = 15

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
        
        # Thickness slider properties
        self.thickness_value = 0.5  # 0.0 to 1.0 (medium thickness)
        self.dragging_thickness = False
        
        # Dash gap slider properties
        self.dash_gap_value = 0.5  # 0.0 to 1.0 (medium gap)
        self.dragging_dash_gap = False
        
        # Dash speed slider properties
        self.dash_speed_value = 0.5  # 0.0 to 1.0 (medium speed)
        self.dragging_dash_speed = False
        
        # Vibrance slider properties
        self.vibrance_value = 0.5  # 0.0 to 1.0 (medium vibrance)
        self.dragging_vibrance = False
        
        # Font for text
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.checkbox_font = pygame.font.Font(None, 28)
        
        # Laser animation properties
        self.time = 0
        self.pulse_intensity = 0
        
        # Global animation offset for continuous dashed line effect
        self.global_dash_offset = 0
        
        # Effect toggle states
        self.effect_toggles = {
            'gradient_glow': True,
            'animated_properties': True,
            'laser_core_halo': True,
            'particle_effects': True,
            'pulsing_segments': False,
            'solid_with_dashes': False  # Sub-effect of pulsing_segments
        }
        
        # Checkbox properties
        self.checkbox_size = 20
        self.checkbox_spacing = 35
        self.checkbox_x = SCREEN_WIDTH - 280
        self.checkbox_y = 80
        
    def get_thickness_multiplier(self):
        """Convert thickness slider value to thickness multiplier (0.5 to 5.0)"""
        return 0.5 + self.thickness_value * 4.5
    
    def get_dash_gap_multiplier(self):
        """Convert dash gap slider value to gap multiplier (0.2 to 2.0)"""
        return 0.2 + self.dash_gap_value * 1.8
    
    def get_dash_speed_multiplier(self):
        """Convert dash speed slider value to speed multiplier (0.1 to 10.0)"""
        return 0.1 + self.dash_speed_value * 9.9
    
    def get_vibrance_multiplier(self):
        """Convert vibrance slider value to intensity multiplier (0.5 to 3.0)"""
        return 0.5 + self.vibrance_value * 2.5
    
    def apply_vibrance(self, color):
        """Apply vibrance multiplier to a color tuple"""
        vibrance = self.get_vibrance_multiplier()
        return tuple(min(255, int(c * vibrance)) for c in color)
        
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
                    
                    # Check if clicking on checkboxes first
                    if self.check_checkbox_click(mouse_x, mouse_y):
                        pass  # Checkbox was clicked and toggled
                    # Check if clicking on vibrance slider
                    elif (VIBRANCE_SLIDER_Y <= mouse_y <= VIBRANCE_SLIDER_Y + VIBRANCE_SLIDER_HEIGHT and
                        VIBRANCE_SLIDER_X <= mouse_x <= VIBRANCE_SLIDER_X + VIBRANCE_SLIDER_WIDTH):
                        self.dragging_vibrance = True
                        self.update_vibrance_slider(mouse_x)
                    # Check if clicking on dash speed slider
                    elif (DASH_SPEED_SLIDER_Y <= mouse_y <= DASH_SPEED_SLIDER_Y + DASH_SPEED_SLIDER_HEIGHT and
                        DASH_SPEED_SLIDER_X <= mouse_x <= DASH_SPEED_SLIDER_X + DASH_SPEED_SLIDER_WIDTH):
                        self.dragging_dash_speed = True
                        self.update_dash_speed_slider(mouse_x)
                    # Check if clicking on dash gap slider
                    elif (DASH_GAP_SLIDER_Y <= mouse_y <= DASH_GAP_SLIDER_Y + DASH_GAP_SLIDER_HEIGHT and
                        DASH_GAP_SLIDER_X <= mouse_x <= DASH_GAP_SLIDER_X + DASH_GAP_SLIDER_WIDTH):
                        self.dragging_dash_gap = True
                        self.update_dash_gap_slider(mouse_x)
                    # Check if clicking on thickness slider
                    elif (THICKNESS_SLIDER_Y <= mouse_y <= THICKNESS_SLIDER_Y + THICKNESS_SLIDER_HEIGHT and
                        THICKNESS_SLIDER_X <= mouse_x <= THICKNESS_SLIDER_X + THICKNESS_SLIDER_WIDTH):
                        self.dragging_thickness = True
                        self.update_thickness_slider(mouse_x)
                    # Check if clicking on angle slider
                    elif (SLIDER_Y <= mouse_y <= SLIDER_Y + SLIDER_HEIGHT and
                        SLIDER_X <= mouse_x <= SLIDER_X + SLIDER_WIDTH):
                        self.dragging = True
                        self.update_slider(mouse_x)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False
                    self.dragging_thickness = False
                    self.dragging_dash_gap = False
                    self.dragging_dash_speed = False
                    self.dragging_vibrance = False
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    mouse_x, mouse_y = event.pos
                    # Only update if mouse is still in reasonable range
                    if 0 <= mouse_x <= SCREEN_WIDTH:
                        self.update_slider(mouse_x)
                elif self.dragging_thickness:
                    mouse_x, mouse_y = event.pos
                    # Only update if mouse is still in reasonable range
                    if 0 <= mouse_x <= SCREEN_WIDTH:
                        self.update_thickness_slider(mouse_x)
                elif self.dragging_dash_gap:
                    mouse_x, mouse_y = event.pos
                    # Only update if mouse is still in reasonable range
                    if 0 <= mouse_x <= SCREEN_WIDTH:
                        self.update_dash_gap_slider(mouse_x)
                elif self.dragging_dash_speed:
                    mouse_x, mouse_y = event.pos
                    # Only update if mouse is still in reasonable range
                    if 0 <= mouse_x <= SCREEN_WIDTH:
                        self.update_dash_speed_slider(mouse_x)
                elif self.dragging_vibrance:
                    mouse_x, mouse_y = event.pos
                    # Only update if mouse is still in reasonable range
                    if 0 <= mouse_x <= SCREEN_WIDTH:
                        self.update_vibrance_slider(mouse_x)
    
    def update_slider(self, mouse_x):
        # Calculate slider value based on mouse position with safety bounds
        try:
            relative_x = mouse_x - SLIDER_X
            self.slider_value = max(0.0, min(1.0, relative_x / SLIDER_WIDTH))
        except (ZeroDivisionError, TypeError):
            # Fallback to center position if calculation fails
            self.slider_value = 0.5
    
    def update_thickness_slider(self, mouse_x):
        # Calculate thickness slider value based on mouse position with safety bounds
        try:
            relative_x = mouse_x - THICKNESS_SLIDER_X
            self.thickness_value = max(0.0, min(1.0, relative_x / THICKNESS_SLIDER_WIDTH))
        except (ZeroDivisionError, TypeError):
            # Fallback to medium thickness if calculation fails
            self.thickness_value = 0.5
    
    def update_dash_gap_slider(self, mouse_x):
        # Calculate dash gap slider value based on mouse position with safety bounds
        try:
            relative_x = mouse_x - DASH_GAP_SLIDER_X
            self.dash_gap_value = max(0.0, min(1.0, relative_x / DASH_GAP_SLIDER_WIDTH))
        except (ZeroDivisionError, TypeError):
            # Fallback to medium gap if calculation fails
            self.dash_gap_value = 0.5
    
    def update_dash_speed_slider(self, mouse_x):
        # Calculate dash speed slider value based on mouse position with safety bounds
        try:
            relative_x = mouse_x - DASH_SPEED_SLIDER_X
            self.dash_speed_value = max(0.0, min(1.0, relative_x / DASH_SPEED_SLIDER_WIDTH))
        except (ZeroDivisionError, TypeError):
            # Fallback to medium speed if calculation fails
            self.dash_speed_value = 0.5
    
    def update_vibrance_slider(self, mouse_x):
        # Calculate vibrance slider value based on mouse position with safety bounds
        try:
            relative_x = mouse_x - VIBRANCE_SLIDER_X
            self.vibrance_value = max(0.0, min(1.0, relative_x / VIBRANCE_SLIDER_WIDTH))
        except (ZeroDivisionError, TypeError):
            # Fallback to medium vibrance if calculation fails
            self.vibrance_value = 0.5
    
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
    
    def draw_laser_beam(self, start_pos, end_pos, base_color, intensity=1.0):
        """Draw a realistic laser beam with glow effect"""
        if start_pos == end_pos:
            return
            
        # Calculate beam properties
        beam_length = math.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
        thickness_multiplier = self.get_thickness_multiplier()
        
        # Pulsing effect based on time (only if animated properties are enabled)
        if self.effect_toggles['animated_properties']:
            pulse = 0.8 + 0.2 * math.sin(self.time * 0.1) * intensity
        else:
            pulse = 1.0 * intensity
        
        # Core laser colors (bright white/colored core)
        if self.effect_toggles['laser_core_halo']:
            core_color = (min(255, int(255 * pulse)), min(255, int(255 * pulse)), min(255, int(255 * pulse)))
            core_color = self.apply_vibrance(core_color)
        else:
            # Simple colored line if core/halo is disabled
            core_color = self.apply_vibrance(base_color)
        
        # Check if pulsing segments are enabled
        if self.effect_toggles['pulsing_segments']:
            # This should not be called directly anymore - handled in draw_light_path
            pass
        else:
            self.draw_solid_beam(start_pos, end_pos, base_color, core_color, thickness_multiplier, pulse, beam_length)
    
    def draw_solid_beam(self, start_pos, end_pos, base_color, core_color, thickness_multiplier, pulse, beam_length):
        """Draw a solid continuous laser beam"""
        # Outer glow colors (based on TIR quality) - only if gradient/glow is enabled
        if self.effect_toggles['gradient_glow']:
            if base_color == GREEN:
                glow_color = (0, min(255, int(150 * pulse)), 0)
            elif base_color == YELLOW:
                glow_color = (min(255, int(200 * pulse)), min(255, int(200 * pulse)), 0)
            else:  # ORANGE/RED
                glow_color = (min(255, int(200 * pulse)), min(255, int(100 * pulse)), 0)
            
            # Apply vibrance to glow colors
            glow_color = self.apply_vibrance(glow_color)
            
            # Draw multiple layers for glow effect (from outer to inner)
            # Outer glow (thickest, most transparent)
            pygame.draw.line(self.screen, glow_color, start_pos, end_pos, int(12 * thickness_multiplier))
            
            # Middle glow
            middle_color = tuple(min(255, int(c * 1.2)) for c in glow_color)
            pygame.draw.line(self.screen, middle_color, start_pos, end_pos, int(8 * thickness_multiplier))
            
            # Inner glow
            inner_color = tuple(min(255, int(c * 1.5)) for c in glow_color)
            pygame.draw.line(self.screen, inner_color, start_pos, end_pos, int(5 * thickness_multiplier))
        
        # Draw the core beam
        if self.effect_toggles['laser_core_halo']:
            # Bright core (thinnest, brightest)
            pygame.draw.line(self.screen, core_color, start_pos, end_pos, max(1, int(2 * thickness_multiplier)))
        else:
            # Simple line
            simple_color = self.apply_vibrance(base_color)
            pygame.draw.line(self.screen, simple_color, start_pos, end_pos, max(1, int(3 * thickness_multiplier)))
        
        # Add sparkle effects for extra realism (only if particle effects are enabled)
        if self.effect_toggles['particle_effects'] and beam_length > 50:  # Only for longer segments
            num_sparkles = max(1, int(beam_length / 100))
            for i in range(num_sparkles):
                # Random position along the beam
                if self.effect_toggles['animated_properties']:
                    t = (i + 0.5) / num_sparkles + 0.1 * math.sin(self.time * 0.3 + i)
                else:
                    t = (i + 0.5) / num_sparkles
                t = max(0, min(1, t))
                
                sparkle_x = int(start_pos[0] + t * (end_pos[0] - start_pos[0]))
                sparkle_y = int(start_pos[1] + t * (end_pos[1] - start_pos[1]))
                
                # Small bright dot
                if self.effect_toggles['animated_properties']:
                    sparkle_intensity = 0.5 + 0.5 * math.sin(self.time * 0.2 + i * 2)
                else:
                    sparkle_intensity = 1.0
                    
                if self.effect_toggles['laser_core_halo']:
                    sparkle_color = tuple(min(255, int(c * sparkle_intensity)) for c in core_color)
                else:
                    sparkle_color = self.apply_vibrance(tuple(min(255, int(c * sparkle_intensity)) for c in base_color))
                pygame.draw.circle(self.screen, sparkle_color, (sparkle_x, sparkle_y), max(1, int(2 * thickness_multiplier * 0.5)))
    
    def draw_faded_solid_base(self, start_pos, end_pos, base_color, core_color, thickness_multiplier, pulse, intensity):
        """Draw a faded solid line as the base for the dashed effect"""
        # Reduce intensity for the faded effect (30-50% of original)
        fade_intensity = intensity * 0.4
        fade_pulse = pulse * 0.4
        
        # Draw faded glow if gradient/glow is enabled
        if self.effect_toggles['gradient_glow']:
            if base_color == GREEN:
                faded_glow_color = (0, min(255, int(150 * fade_pulse)), 0)
            elif base_color == YELLOW:
                faded_glow_color = (min(255, int(200 * fade_pulse)), min(255, int(200 * fade_pulse)), 0)
            else:  # ORANGE/RED
                faded_glow_color = (min(255, int(200 * fade_pulse)), min(255, int(100 * fade_pulse)), 0)
            
            # Apply vibrance to faded glow colors
            faded_glow_color = self.apply_vibrance(faded_glow_color)
            
            # Draw faded glow layers (thinner than normal)
            pygame.draw.line(self.screen, faded_glow_color, start_pos, end_pos, int(8 * thickness_multiplier))
            
            # Middle faded glow
            faded_middle_color = tuple(min(255, int(c * 1.2)) for c in faded_glow_color)
            pygame.draw.line(self.screen, faded_middle_color, start_pos, end_pos, int(5 * thickness_multiplier))
            
            # Inner faded glow
            faded_inner_color = tuple(min(255, int(c * 1.5)) for c in faded_glow_color)
            pygame.draw.line(self.screen, faded_inner_color, start_pos, end_pos, int(3 * thickness_multiplier))
        
        # Draw faded core beam
        if self.effect_toggles['laser_core_halo']:
            faded_core_color = tuple(min(255, int(c * fade_intensity)) for c in core_color)
            pygame.draw.line(self.screen, faded_core_color, start_pos, end_pos, max(1, int(1.5 * thickness_multiplier)))
        else:
            faded_base_color = self.apply_vibrance(tuple(min(255, int(c * fade_intensity)) for c in base_color))
            pygame.draw.line(self.screen, faded_base_color, start_pos, end_pos, max(1, int(2 * thickness_multiplier)))
    
    def draw_pulsing_segments(self, start_pos, end_pos, base_color, core_color, thickness_multiplier, pulse, intensity, cumulative_distance):
        """Draw a moving dashed line like energy bursts traveling through the fiber"""
        
        # If solid_with_dashes is enabled, draw a faded solid line first
        if self.effect_toggles['solid_with_dashes']:
            self.draw_faded_solid_base(start_pos, end_pos, base_color, core_color, thickness_multiplier, pulse, intensity)
        
        # Calculate beam direction and length
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        beam_length = math.sqrt(dx * dx + dy * dy)
        
        if beam_length == 0:
            return
        
        # Normalize direction
        dx_norm = dx / beam_length
        dy_norm = dy / beam_length
        
        # Dash properties - controlled by sliders
        dash_length = 10 * thickness_multiplier     # Dash length based on thickness
        gap_length = 50 * thickness_multiplier * self.get_dash_gap_multiplier()  # Gap controlled by slider
        total_pattern_length = dash_length + gap_length
        
        # Animation offset - uses cumulative distance for continuous flow across segments
        if self.effect_toggles['animated_properties']:
            # Use cumulative distance to make dashes flow continuously across all segments
            # Subtract offset to make dashes move from left to right (in direction of light travel)
            animation_offset = (-self.global_dash_offset + cumulative_distance) % total_pattern_length
        else:
            animation_offset = cumulative_distance % total_pattern_length
        
        # Calculate how many complete patterns fit in the beam
        num_patterns = int((beam_length + total_pattern_length) / total_pattern_length) + 2
        
        # Draw each dash
        for i in range(num_patterns):
            # Calculate dash start position (with animation offset)
            dash_start_distance = i * total_pattern_length - animation_offset
            dash_end_distance = dash_start_distance + dash_length
            
            # Skip if dash is completely before the beam start
            if dash_end_distance < 0:
                continue
            
            # Skip if dash is completely after the beam end
            if dash_start_distance > beam_length:
                break
            
            # Clamp dash to beam boundaries
            dash_start_distance = max(0, dash_start_distance)
            dash_end_distance = min(beam_length, dash_end_distance)
            
            # Skip if dash has no length after clamping
            if dash_start_distance >= dash_end_distance:
                continue
            
            # Calculate actual start and end positions
            dash_start_x = int(start_pos[0] + dx_norm * dash_start_distance)
            dash_start_y = int(start_pos[1] + dy_norm * dash_start_distance)
            dash_end_x = int(start_pos[0] + dx_norm * dash_end_distance)
            dash_end_y = int(start_pos[1] + dy_norm * dash_end_distance)
            
            dash_start = (dash_start_x, dash_start_y)
            dash_end = (dash_end_x, dash_end_y)
            
            # Calculate dash intensity (can add subtle brightness variation)
            dash_intensity = intensity
            if self.effect_toggles['animated_properties']:
                # Optional: Add slight brightness variation to individual dashes
                brightness_variation = 0.9 + 0.1 * math.sin(self.time * 0.05 + i * 0.8)
                dash_intensity *= brightness_variation
            
            # Draw dash glow if enabled
            if self.effect_toggles['gradient_glow']:
                if base_color == GREEN:
                    glow_color = (0, min(255, int(150 * pulse * dash_intensity)), 0)
                elif base_color == YELLOW:
                    glow_color = (min(255, int(200 * pulse * dash_intensity)), min(255, int(200 * pulse * dash_intensity)), 0)
                else:  # ORANGE/RED
                    glow_color = (min(255, int(200 * pulse * dash_intensity)), min(255, int(100 * pulse * dash_intensity)), 0)
                
                # Apply vibrance to dash glow colors
                glow_color = self.apply_vibrance(glow_color)
                
                # Draw glow layers for each dash
                pygame.draw.line(self.screen, glow_color, dash_start, dash_end, int(12 * thickness_multiplier))
                
                middle_color = tuple(min(255, int(c * 1.2)) for c in glow_color)
                pygame.draw.line(self.screen, middle_color, dash_start, dash_end, int(8 * thickness_multiplier))
                
                inner_color = tuple(min(255, int(c * 1.5)) for c in glow_color)
                pygame.draw.line(self.screen, inner_color, dash_start, dash_end, int(5 * thickness_multiplier))
            
            # Draw dash core
            if self.effect_toggles['laser_core_halo']:
                dash_core_color = tuple(min(255, int(c * dash_intensity)) for c in core_color)
                pygame.draw.line(self.screen, dash_core_color, dash_start, dash_end, max(1, int(2 * thickness_multiplier)))
            else:
                dash_base_color = self.apply_vibrance(tuple(min(255, int(c * dash_intensity)) for c in base_color))
                pygame.draw.line(self.screen, dash_base_color, dash_start, dash_end, max(1, int(3 * thickness_multiplier)))
            
            # Add particles to each dash if enabled
            if self.effect_toggles['particle_effects']:
                dash_actual_length = dash_end_distance - dash_start_distance
                if dash_actual_length > 5:
                    # Add 1-2 particles per dash
                    num_particles = max(1, int(dash_actual_length / 8))
                    for p in range(num_particles):
                        particle_t = (p + 0.5) / num_particles
                        particle_distance = dash_start_distance + particle_t * dash_actual_length
                        
                        particle_x = int(start_pos[0] + dx_norm * particle_distance)
                        particle_y = int(start_pos[1] + dy_norm * particle_distance)
                        
                        # Particle intensity can sparkle slightly
                        if self.effect_toggles['animated_properties']:
                            particle_intensity = 0.8 + 0.2 * math.sin(self.time * 0.1 + p * 2 + i)
                        else:
                            particle_intensity = 1.0
                        
                        particle_intensity *= dash_intensity
                        
                        if self.effect_toggles['laser_core_halo']:
                            particle_color = tuple(min(255, int(c * particle_intensity)) for c in core_color)
                        else:
                            particle_color = self.apply_vibrance(tuple(min(255, int(c * particle_intensity)) for c in base_color))
                        
                        pygame.draw.circle(self.screen, particle_color, (particle_x, particle_y), max(1, int(2 * thickness_multiplier * 0.5)))
    
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
    
    def draw_thickness_slider(self):
        # Draw thickness slider track
        pygame.draw.rect(self.screen, GRAY, 
                        (THICKNESS_SLIDER_X, THICKNESS_SLIDER_Y + THICKNESS_SLIDER_HEIGHT//2 - 3, THICKNESS_SLIDER_WIDTH, 6))
        
        # Draw thickness slider handle
        handle_x = THICKNESS_SLIDER_X + self.thickness_value * THICKNESS_SLIDER_WIDTH - THICKNESS_SLIDER_HANDLE_WIDTH // 2
        pygame.draw.rect(self.screen, WHITE, 
                        (handle_x, THICKNESS_SLIDER_Y, THICKNESS_SLIDER_HANDLE_WIDTH, THICKNESS_SLIDER_HEIGHT))
        
        # Draw thickness label and value
        thickness_multiplier = self.get_thickness_multiplier()
        thickness_text = self.small_font.render(f"Laser Thickness: {thickness_multiplier:.1f}x", True, WHITE)
        self.screen.blit(thickness_text, (THICKNESS_SLIDER_X, THICKNESS_SLIDER_Y - 25))
    
    def draw_dash_gap_slider(self):
        # Draw dash gap slider track
        pygame.draw.rect(self.screen, GRAY, 
                        (DASH_GAP_SLIDER_X, DASH_GAP_SLIDER_Y + DASH_GAP_SLIDER_HEIGHT//2 - 3, DASH_GAP_SLIDER_WIDTH, 6))
        
        # Draw dash gap slider handle
        handle_x = DASH_GAP_SLIDER_X + self.dash_gap_value * DASH_GAP_SLIDER_WIDTH - DASH_GAP_SLIDER_HANDLE_WIDTH // 2
        pygame.draw.rect(self.screen, WHITE, 
                        (handle_x, DASH_GAP_SLIDER_Y, DASH_GAP_SLIDER_HANDLE_WIDTH, DASH_GAP_SLIDER_HEIGHT))
        
        # Draw dash gap label and value
        gap_multiplier = self.get_dash_gap_multiplier()
        gap_text = self.small_font.render(f"Dash Gap Size: {gap_multiplier:.1f}x", True, WHITE)
        self.screen.blit(gap_text, (DASH_GAP_SLIDER_X, DASH_GAP_SLIDER_Y - 25))
    
    def draw_dash_speed_slider(self):
        # Draw dash speed slider track
        pygame.draw.rect(self.screen, GRAY, 
                        (DASH_SPEED_SLIDER_X, DASH_SPEED_SLIDER_Y + DASH_SPEED_SLIDER_HEIGHT//2 - 3, DASH_SPEED_SLIDER_WIDTH, 6))
        
        # Draw dash speed slider handle
        handle_x = DASH_SPEED_SLIDER_X + self.dash_speed_value * DASH_SPEED_SLIDER_WIDTH - DASH_SPEED_SLIDER_HANDLE_WIDTH // 2
        pygame.draw.rect(self.screen, WHITE, 
                        (handle_x, DASH_SPEED_SLIDER_Y, DASH_SPEED_SLIDER_HANDLE_WIDTH, DASH_SPEED_SLIDER_HEIGHT))
        
        # Draw dash speed label and value
        speed_multiplier = self.get_dash_speed_multiplier()
        speed_text = self.small_font.render(f"Dash Speed: {speed_multiplier:.1f}x", True, WHITE)
        self.screen.blit(speed_text, (DASH_SPEED_SLIDER_X, DASH_SPEED_SLIDER_Y - 25))
    
    def draw_vibrance_slider(self):
        # Draw vibrance slider track
        pygame.draw.rect(self.screen, GRAY, 
                        (VIBRANCE_SLIDER_X, VIBRANCE_SLIDER_Y + VIBRANCE_SLIDER_HEIGHT//2 - 3, VIBRANCE_SLIDER_WIDTH, 6))
        
        # Draw vibrance slider handle
        handle_x = VIBRANCE_SLIDER_X + self.vibrance_value * VIBRANCE_SLIDER_WIDTH - VIBRANCE_SLIDER_HANDLE_WIDTH // 2
        pygame.draw.rect(self.screen, WHITE, 
                        (handle_x, VIBRANCE_SLIDER_Y, VIBRANCE_SLIDER_HANDLE_WIDTH, VIBRANCE_SLIDER_HEIGHT))
        
        # Draw vibrance label and value
        vibrance_multiplier = self.get_vibrance_multiplier()
        vibrance_text = self.small_font.render(f"Vibrance: {vibrance_multiplier:.1f}x", True, WHITE)
        self.screen.blit(vibrance_text, (VIBRANCE_SLIDER_X, VIBRANCE_SLIDER_Y - 25))
    
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
            intensity = 1.0
        elif current_angle < CRITICAL_ANGLE + 10:
            light_color = YELLOW  # Marginal TIR
            intensity = 0.8
        else:  # Poor TIR - would leak light in real fiber
            light_color = ORANGE
            intensity = 0.6
        
        # Draw the laser beam segments with realistic effects
        cumulative_distance = 0
        for i in range(len(path_points) - 1):
            # Calculate segment length
            segment_length = math.sqrt(
                (path_points[i+1][0] - path_points[i][0])**2 + 
                (path_points[i+1][1] - path_points[i][1])**2
            )
            
            if self.effect_toggles['pulsing_segments']:
                self.draw_pulsing_segments(path_points[i], path_points[i + 1], light_color, 
                                         (255, 255, 255), self.get_thickness_multiplier(), 
                                         0.8 + 0.2 * math.sin(self.time * 0.1) if self.effect_toggles['animated_properties'] else 1.0, 
                                         intensity, cumulative_distance)
            else:
                self.draw_laser_beam(path_points[i], path_points[i + 1], light_color, intensity)
            
            cumulative_distance += segment_length
        
        # Draw enhanced bounce points with energy burst effects
        for i, (bounce_pos, incident_angle) in enumerate(zip(bounce_positions, bounce_angles)):
            # Color code bounce points based on angle of incidence
            if incident_angle < CRITICAL_ANGLE:
                bounce_color = GREEN
            elif incident_angle < CRITICAL_ANGLE + 10:
                bounce_color = YELLOW
            else:
                bounce_color = RED
            
            # Animated bounce effect (only if animated properties are enabled)
            if self.effect_toggles['animated_properties']:
                bounce_pulse = 0.7 + 0.3 * math.sin(self.time * 0.15 + i * 0.5)
            else:
                bounce_pulse = 1.0
            
            # Draw bounce effects based on enabled toggles
            if self.effect_toggles['gradient_glow']:
                # Outer energy burst
                burst_radius = int(12 * bounce_pulse)
                burst_color = self.apply_vibrance(tuple(int(c * 0.3 * bounce_pulse) for c in bounce_color))
                pygame.draw.circle(self.screen, burst_color, (int(bounce_pos[0]), int(bounce_pos[1])), burst_radius)
                
                # Middle energy ring
                ring_radius = int(8 * bounce_pulse)
                ring_color = self.apply_vibrance(tuple(int(c * 0.6 * bounce_pulse) for c in bounce_color))
                pygame.draw.circle(self.screen, ring_color, (int(bounce_pos[0]), int(bounce_pos[1])), ring_radius)
            
            if self.effect_toggles['laser_core_halo']:
                # Bright core
                core_radius = int(4 * bounce_pulse)
                core_color = self.apply_vibrance(tuple(min(255, int(c * bounce_pulse)) for c in bounce_color))
                pygame.draw.circle(self.screen, core_color, (int(bounce_pos[0]), int(bounce_pos[1])), core_radius)
            else:
                # Simple circle
                simple_bounce_color = self.apply_vibrance(bounce_color)
                pygame.draw.circle(self.screen, simple_bounce_color, (int(bounce_pos[0]), int(bounce_pos[1])), 3)
            
            # Draw angle of incidence text near first few bounces
            if i < 3:  # Show only first 3 bounces to avoid clutter
                angle_text = self.small_font.render(f"{incident_angle:.1f}°", True, WHITE)
                text_x = int(bounce_pos[0]) + 15
                text_y = int(bounce_pos[1]) - 25
                self.screen.blit(angle_text, (text_x, text_y))
        
        # Enhanced starting point (laser source)
        start_pos = path_points[0]
        
        if self.effect_toggles['animated_properties']:
            source_pulse = 0.8 + 0.2 * math.sin(self.time * 0.2)
        else:
            source_pulse = 1.0
        
        # Draw source effects based on enabled toggles
        if self.effect_toggles['gradient_glow']:
            # Laser source glow
            source_glow_radius = int(15 * source_pulse)
            source_glow_color = self.apply_vibrance((0, int(100 * source_pulse), 0))
            pygame.draw.circle(self.screen, source_glow_color, (int(start_pos[0]), int(start_pos[1])), source_glow_radius)
        
        if self.effect_toggles['laser_core_halo']:
            # Laser source core
            pygame.draw.circle(self.screen, self.apply_vibrance(WHITE), (int(start_pos[0]), int(start_pos[1])), 8)
            pygame.draw.circle(self.screen, self.apply_vibrance(GREEN), (int(start_pos[0]), int(start_pos[1])), 6)
            pygame.draw.circle(self.screen, self.apply_vibrance((0, 255, 0)), (int(start_pos[0]), int(start_pos[1])), 3)
        else:
            # Simple source dot
            pygame.draw.circle(self.screen, self.apply_vibrance(GREEN), (int(start_pos[0]), int(start_pos[1])), 5)
        
        # Enhanced ending point (laser exit)
        if path_points:
            end_point = path_points[-1]
            
            if self.effect_toggles['animated_properties']:
                exit_pulse = 0.9 + 0.1 * math.sin(self.time * 0.25)
            else:
                exit_pulse = 1.0
            
            # Draw exit effects based on enabled toggles
            if self.effect_toggles['gradient_glow']:
                # Exit glow
                exit_glow_radius = int(12 * exit_pulse)
                exit_glow_color = self.apply_vibrance(tuple(int(c * 0.3 * exit_pulse) for c in light_color))
                pygame.draw.circle(self.screen, exit_glow_color, (int(end_point[0]), int(end_point[1])), exit_glow_radius)
            
            if self.effect_toggles['laser_core_halo']:
                # Exit core
                pygame.draw.circle(self.screen, self.apply_vibrance(WHITE), (int(end_point[0]), int(end_point[1])), 8)
                pygame.draw.circle(self.screen, self.apply_vibrance(light_color), (int(end_point[0]), int(end_point[1])), 6)
            else:
                # Simple exit dot
                pygame.draw.circle(self.screen, self.apply_vibrance(light_color), (int(end_point[0]), int(end_point[1])), 5)
    
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
            "Move angle slider to change light entry angle",
            "Use thickness slider to adjust laser beam width",
            "Click checkboxes to toggle visual effects",
            "GREEN: Excellent TIR | YELLOW: Marginal | ORANGE: Poor",
            "Numbers show angle of incidence at bounce points",
            "F11: Toggle fullscreen | ESC: Exit"
        ]
        
        for i, instruction in enumerate(instructions):
            inst_text = self.small_font.render(instruction, True, LIGHT_GRAY)
            self.screen.blit(inst_text, (10, SCREEN_HEIGHT - 140 + i * 25))
    
    def draw_checkboxes(self):
        """Draw interactive checkboxes for effect toggles"""
        checkbox_labels = [
            ('gradient_glow', 'Gradient/Glow Effect'),
            ('animated_properties', 'Animated Properties'),
            ('laser_core_halo', 'Laser Core & Halo'),
            ('particle_effects', 'Particle Effects'),
            ('pulsing_segments', 'Pulsing Segments'),
            ('solid_with_dashes', '  └ Solid + Dashes')  # Sub-effect with indentation
        ]
        
        # Draw title
        title_text = self.checkbox_font.render("Visual Effects:", True, WHITE)
        self.screen.blit(title_text, (self.checkbox_x, self.checkbox_y - 30))
        
        for i, (effect_key, label) in enumerate(checkbox_labels):
            y_pos = self.checkbox_y + i * self.checkbox_spacing
            
            # Special handling for sub-effect
            is_sub_effect = effect_key == 'solid_with_dashes'
            checkbox_x = self.checkbox_x + (20 if is_sub_effect else 0)  # Indent sub-effect
            
            # Gray out sub-effect if parent effect is disabled
            if is_sub_effect and not self.effect_toggles['pulsing_segments']:
                checkbox_color = GRAY
                label_color = GRAY
                is_enabled = False
            else:
                checkbox_color = WHITE
                label_color = WHITE
                is_enabled = self.effect_toggles[effect_key]
            
            # Draw checkbox border
            checkbox_rect = pygame.Rect(checkbox_x, y_pos, self.checkbox_size, self.checkbox_size)
            pygame.draw.rect(self.screen, checkbox_color, checkbox_rect, 2)
            
            # Fill checkbox if effect is enabled
            if is_enabled:
                # Draw checkmark
                inner_rect = pygame.Rect(checkbox_x + 3, y_pos + 3, 
                                       self.checkbox_size - 6, self.checkbox_size - 6)
                pygame.draw.rect(self.screen, GREEN, inner_rect)
                
                # Draw checkmark symbol
                check_points = [
                    (checkbox_x + 5, y_pos + 10),
                    (checkbox_x + 8, y_pos + 13),
                    (checkbox_x + 15, y_pos + 6)
                ]
                pygame.draw.lines(self.screen, WHITE, False, check_points, 2)
            
            # Draw label
            label_text = self.checkbox_font.render(label, True, label_color)
            label_x = checkbox_x + self.checkbox_size + 10
            self.screen.blit(label_text, (label_x, y_pos - 2))
    
    def check_checkbox_click(self, mouse_x, mouse_y):
        """Check if a checkbox was clicked and toggle the effect"""
        checkbox_labels = [
            'gradient_glow',
            'animated_properties', 
            'laser_core_halo',
            'particle_effects',
            'pulsing_segments',
            'solid_with_dashes'
        ]
        
        for i, effect_key in enumerate(checkbox_labels):
            y_pos = self.checkbox_y + i * self.checkbox_spacing
            
            # Special handling for sub-effect positioning
            checkbox_x = self.checkbox_x + (20 if effect_key == 'solid_with_dashes' else 0)
            checkbox_rect = pygame.Rect(checkbox_x, y_pos, self.checkbox_size, self.checkbox_size)
            
            if checkbox_rect.collidepoint(mouse_x, mouse_y):
                # Special logic for sub-effects
                if effect_key == 'solid_with_dashes':
                    # Only allow toggling if parent effect is enabled
                    if self.effect_toggles['pulsing_segments']:
                        self.effect_toggles[effect_key] = not self.effect_toggles[effect_key]
                elif effect_key == 'pulsing_segments':
                    # If disabling pulsing segments, also disable sub-effects
                    self.effect_toggles[effect_key] = not self.effect_toggles[effect_key]
                    if not self.effect_toggles[effect_key]:
                        self.effect_toggles['solid_with_dashes'] = False
                else:
                    # Normal toggle for other effects
                    self.effect_toggles[effect_key] = not self.effect_toggles[effect_key]
                return True
        
        return False
    
    def run(self):
        while self.running:
            # Update animation time
            self.time += 1
            
            # Update global dash offset for continuous dashed line animation
            if self.effect_toggles['animated_properties'] and self.effect_toggles['pulsing_segments']:
                self.global_dash_offset += 2.5 * self.get_dash_speed_multiplier()  # Speed controlled by slider
            
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
            self.draw_thickness_slider()
            self.draw_dash_gap_slider()
            self.draw_dash_speed_slider()
            self.draw_vibrance_slider()
            self.draw_info(total_distance, bounce_angles)
            self.draw_checkboxes()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS
        
        pygame.quit()
        sys.exit()

# Run the simulation
if __name__ == "__main__":
    simulation = OpticalFiberSimulation()
    simulation.run()