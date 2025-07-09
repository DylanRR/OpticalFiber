import pygame
import math
import sys
import threading
import time
from collections import deque
try:
    from Phidget22.Phidget import Phidget
    from Phidget22.Devices.Encoder import Encoder as PhidgetEncoder
    PHIDGETS_AVAILABLE = True
except ImportError:
    print("Phidget22 library not available. Encoder control will be disabled.")
    PHIDGETS_AVAILABLE = False
    # Create dummy class to prevent errors
    class PhidgetEncoder:
        def setDeviceSerialNumber(self, serial): pass
        def setOnPositionChangeHandler(self, handler): pass
        def openWaitForAttachment(self, timeout): pass
        def close(self): pass

# Initialize Pygame
pygame.init()

# Get screen dimensions for single ultra-wide monitor
info = pygame.display.Info()
# Use the actual screen dimensions (single ultra-wide monitor)
SCREEN_WIDTH = info.current_w
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

# Slider dimensions - only angle slider
SLIDER_HEIGHT = 60
SLIDER_Y = SCREEN_HEIGHT - SLIDER_HEIGHT - 20
SLIDER_X = 50
SLIDER_WIDTH = SCREEN_WIDTH - 100
SLIDER_HANDLE_WIDTH = 20

class OpticalFiberSimulation:
    def __init__(self):
        # Create fullscreen display for single ultra-wide monitor
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption("Optical Fiber Light Path Simulation - Ultra-Wide Monitor")
        
        # Get actual screen dimensions after setting fullscreen
        self.screen_width = self.screen.get_width()
        self.screen_height = self.screen.get_height()
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Slider properties - only angle slider
        self.slider_value = 0.5  # 0.0 to 1.0 (center position)
        self.dragging = False
        
        # Encoder control properties
        self.encoder_enabled = False
        self.encoder_thread = None
        self.encoder_device = None
        self.encoder_position_history = deque(maxlen=3)  # Store more position changes for better smoothing
        self.encoder_lock = threading.Lock()
        self.encoder_slider_speed = 0.00002  # Much smaller step size for smoother, less sensitive movement
        self.encoder_accumulator = 0.0  # Accumulate small movements before applying
        self.encoder_threshold = 1  # Require more encoder ticks before moving slider
        self.last_encoder_update = time.time()
        
        # Initialize encoder if available
        if PHIDGETS_AVAILABLE:
            self.setup_encoder()
        
        # Laser animation properties
        self.time = 0
        self.pulse_intensity = 0
        
        # Global animation offset for continuous dashed line effect
        self.global_dash_offset = 0
        
        # HARDCODED EFFECT SETTINGS - No UI controls needed
        # pulsing segments ON, solid+dashed line ON, line thickness 3.7x, 
        # dash gap 0.3x, dash speed 4.9x, vibrance 1.1x
        self.effect_toggles = {
            'gradient_glow': True,
            'animated_properties': True,
            'laser_core_halo': True,
            'particle_effects': True,
            'pulsing_segments': True,  # ON
            'solid_with_dashes': True  # ON (sub-effect of pulsing_segments)
        }
        
        # Hardcoded effect values (no sliders)
        self.thickness_multiplier = 3.7  # 3.7x thickness
        self.dash_gap_multiplier = 0.3   # 0.3x dash gap
        self.dash_speed_multiplier = 4.9 # 4.9x dash speed
        self.vibrance_multiplier = 1.1   # 1.1x vibrance
        
        # Update slider positions based on actual screen size
        self.slider_y = self.screen_height - 80
        self.slider_x = 50
        self.slider_width = self.screen_width - 100
        
    def get_thickness_multiplier(self):
        """Return hardcoded thickness multiplier (3.7x)"""
        return self.thickness_multiplier
    
    def get_dash_gap_multiplier(self):
        """Return hardcoded dash gap multiplier (0.3x)"""
        return self.dash_gap_multiplier
    
    def get_dash_speed_multiplier(self):
        """Return hardcoded dash speed multiplier (4.9x)"""
        return self.dash_speed_multiplier
    
    def get_vibrance_multiplier(self):
        """Return hardcoded vibrance multiplier (1.1x)"""
        return self.vibrance_multiplier
    
    def apply_vibrance(self, color):
        """Apply hardcoded vibrance multiplier to a color tuple"""
        return tuple(min(255, int(c * self.vibrance_multiplier)) for c in color)
        
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
                    
                    # Check if clicking on angle slider only
                    if (self.slider_y <= mouse_y <= self.slider_y + 60 and
                        self.slider_x <= mouse_x <= self.slider_x + self.slider_width):
                        self.dragging = True
                        self.update_slider(mouse_x)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    mouse_x, mouse_y = event.pos
                    # Only update if mouse is still in reasonable range
                    if 0 <= mouse_x <= self.screen_width:
                        self.update_slider(mouse_x)
    
    def update_slider(self, mouse_x):
        # Calculate slider value based on mouse position with safety bounds
        try:
            relative_x = mouse_x - self.slider_x
            self.slider_value = max(0.0, min(1.0, relative_x / self.slider_width))
        except (ZeroDivisionError, TypeError):
            # Fallback to center position if calculation fails
            self.slider_value = 0.5
    
    def get_angle_from_slider(self):
        # Convert slider value to angle (-87 to +87 degrees)
        max_angle = 87  # degrees
        angle_degrees = (self.slider_value - 0.5) * 2 * max_angle
        return math.radians(angle_degrees)
    
    def calculate_light_path(self):
        # Starting point (left side of screen, middle height)
        start_x = 0
        start_y = self.screen_height // 2
        
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
        
        while current_x < self.screen_width:
            # Move one step
            next_x = current_x + dx * step_size
            next_y = current_y + dy * step_size
            
            # Check for bounces off top and bottom walls
            if next_y <= 0:
                # Bounce off top wall
                next_y = 0 + (0 - next_y)
                
                # Calculate angle of incidence (angle between ray and normal to surface)
                incident_angle = math.degrees(math.atan2(abs(dy), abs(dx)))
                bounce_angles.append(incident_angle)
                bounce_positions.append((current_x, 0))
                
                dy = -dy  # Reverse vertical direction
            elif next_y >= self.screen_height:
                # Bounce off bottom wall
                next_y = self.screen_height - (next_y - self.screen_height)
                
                # Calculate angle of incidence
                incident_angle = math.degrees(math.atan2(abs(dy), abs(dx)))
                bounce_angles.append(incident_angle)
                bounce_positions.append((current_x, self.screen_height))
                
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
    
    def setup_encoder(self):
        """Initialize the Phidget encoder for slider control"""
        if not PHIDGETS_AVAILABLE:
            print("Phidgets library not available - encoder control disabled")
            return
            
        try:
            self.encoder_device = PhidgetEncoder()
            
            # Try without setting serial number first (will connect to any available encoder)
            # Uncomment the line below and set the correct serial number if you have multiple encoders
            # self.encoder_device.setDeviceSerialNumber(689556)
            
            self.encoder_device.setOnPositionChangeHandler(self.on_encoder_position_change)
            
            # Start encoder thread
            self.encoder_thread = threading.Thread(target=self.encoder_thread_worker, daemon=True)
            self.encoder_thread.start()
            
            print("Encoder setup initiated...")
        except Exception as e:
            print(f"Failed to setup encoder: {e}")
            self.encoder_enabled = False
            self.encoder_device = None
    
    def on_encoder_position_change(self, encoder, positionChange, timeChange, indexTriggered):
        """Handle encoder position changes with accumulation for less sensitive control"""
        try:
            current_time = time.time()
            
            # Accumulate position changes instead of storing individual events
            with self.encoder_lock:
                self.encoder_accumulator += positionChange
                
                # Store position change for direction smoothing
                self.encoder_position_history.append({
                    'change': positionChange,
                    'time': current_time,
                    'timeChange': timeChange
                })
                
                # Reduced debug output - only show significant changes
                #if abs(self.encoder_accumulator) > 2:  # Only print when accumulator is building up
                #    print(f"Encoder accumulator: {self.encoder_accumulator:.1f}, latest change: {positionChange}")
                    
        except Exception as e:
            print(f"Error in encoder position change handler: {e}")
    
    def encoder_thread_worker(self):
        """Worker thread for encoder operations"""
        if not PHIDGETS_AVAILABLE or not self.encoder_device:
            return
            
        try:
            print("Attempting to connect to encoder...")
            # Open and wait for attachment
            self.encoder_device.openWaitForAttachment(5000)
            self.encoder_enabled = True
            
            # Print encoder information
            print(f"Encoder connected successfully!")
            # Note: Some encoder methods may not be available depending on the device/library version
            try:
                # Attempt to get device details if available
                serial_num = getattr(self.encoder_device, 'getDeviceSerialNumber', lambda: 'Unknown')()
                position = getattr(self.encoder_device, 'getPosition', lambda: 'Unknown')()
                print(f"Encoder serial number: {serial_num}")
                print(f"Encoder position: {position}")
            except Exception as detail_error:
                print(f"Could not read encoder details: {detail_error}")
            
            # Keep the thread alive while the simulation is running
            while self.running:
                time.sleep(0.1)  # Small sleep to prevent excessive CPU usage
                
        except Exception as e:
            print(f"Encoder thread error: {e}")
            self.encoder_enabled = False
        finally:
            if self.encoder_device:
                try:
                    self.encoder_device.close()
                except:
                    pass
    
    def update_slider_from_encoder(self):
        """Update slider position based on encoder input with accumulation and threshold for smooth, less sensitive control"""
        if not self.encoder_enabled:
            return
        
        current_time = time.time()
        
        # Only process encoder updates if we're not manually dragging the slider
        if self.dragging:
            return
        
        # Debounce - only update every 50ms for smoother movement
        if current_time - self.last_encoder_update < 0.05:
            return
        
        with self.encoder_lock:
            # Check if accumulated movement exceeds threshold
            if abs(self.encoder_accumulator) >= self.encoder_threshold:
                # Determine direction and calculate movement
                if self.encoder_accumulator > 0:
                    direction = 1
                elif self.encoder_accumulator < 0:
                    direction = -1
                else:
                    return
                
                # Calculate how many "steps" to take based on accumulated value
                accumulated_steps = int(abs(self.encoder_accumulator) / self.encoder_threshold)
                
                # Apply movement with reduced sensitivity
                movement = accumulated_steps * direction * self.encoder_slider_speed
                old_value = self.slider_value
                
                # Use helper method to apply movement
                self.apply_encoder_movement(movement)
                
                # Reduce accumulator by the amount we used
                used_accumulator = accumulated_steps * self.encoder_threshold * direction
                self.encoder_accumulator -= used_accumulator
                
                # Clear old history to prevent buildup
                current_time = time.time()
                self.encoder_position_history = [
                    entry for entry in self.encoder_position_history
                    if current_time - entry['time'] < 0.1  # Keep only very recent history
                ]
                
                self.last_encoder_update = current_time
                
                # Debug output for significant movements only
                #if abs(movement) > 0.001:  # Only print when making noticeable movement
                #    print(f"Slider moved: {old_value:.3f} -> {self.slider_value:.3f} (steps: {accumulated_steps}, remaining accum: {self.encoder_accumulator:.1f})")
    
    def cleanup_encoder(self):
        """Clean up encoder resources"""
        self.running = False
        if self.encoder_device and self.encoder_enabled:
            try:
                self.encoder_device.close()
            except:
                pass
        if self.encoder_thread and self.encoder_thread.is_alive():
            self.encoder_thread.join(timeout=1.0)

    def draw_slider(self):
        # Draw slider track
        pygame.draw.rect(self.screen, GRAY, 
                        (self.slider_x, self.slider_y + 30 - 5, self.slider_width, 10))
        
        # Draw slider handle
        handle_x = self.slider_x + self.slider_value * self.slider_width - 10
        pygame.draw.rect(self.screen, WHITE, 
                        (handle_x, self.slider_y, 20, 60))
    
    def draw_fiber(self):
        # No longer drawing fiber walls - laser extends to full screen edges
        pass
    
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
        # Remove all text information display for minimal version
        pass
    
    def draw_checkboxes(self):
        # Remove all checkboxes for minimal version
        pass
    
    def check_checkbox_click(self, mouse_x, mouse_y):
        # Remove checkbox functionality for minimal version
        return False
    
    def apply_encoder_movement(self, movement):
        """Apply encoder movement to slider with bounds checking"""
        if movement > 0:
            self.slider_value = min(1.0, self.slider_value + abs(movement))
        elif movement < 0:
            self.slider_value = max(0.0, self.slider_value - abs(movement))
    
    def run(self):
        while self.running:
            # Update animation time
            self.time += 1
            
            # Update slider from encoder input
            self.update_slider_from_encoder()
            
            # Update global dash offset for continuous dashed line animation (hardcoded speed 4.9x)
            if self.effect_toggles['animated_properties'] and self.effect_toggles['pulsing_segments']:
                self.global_dash_offset += 2.5 * self.dash_speed_multiplier  # Using hardcoded speed
            
            self.handle_events()
            
            # Calculate light path
            path_points, total_distance, bounce_angles, bounce_positions = self.calculate_light_path()
            self.current_path = path_points  # Store for bounce calculation
            
            # Clear screen
            self.screen.fill(BLACK)
            
            # Draw everything - minimal version with only laser and angle slider
            self.draw_fiber()
            self.draw_light_path(path_points, total_distance, bounce_angles, bounce_positions)
            self.draw_slider()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS
        
        # Cleanup encoder resources
        self.cleanup_encoder()
        
        pygame.quit()
        sys.exit()

# Run the simulation
if __name__ == "__main__":
    simulation = OpticalFiberSimulation()
    simulation.run()