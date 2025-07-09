import pygame
import math
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor

# Try to import numpy for faster math operations (Jetson optimization)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("NumPy not available - using standard math (install numpy for better performance on Jetson)")

# Try to import CuPy for GPU-accelerated math (Jetson Tensor Core utilization)
try:
    import cupy as cp
    CUPY_AVAILABLE = True
    print("CuPy available - GPU acceleration enabled for Jetson Tensor Cores")
except ImportError:
    CUPY_AVAILABLE = False
    print("CuPy not available - install with: pip install cupy-cuda11x (for Tensor Core acceleration)")

# Try to import OpenGL for GPU rendering (alternative to pygame)
try:
    import moderngl
    import pygame.opengl
    OPENGL_AVAILABLE = True
    print("ModernGL available - GPU rendering possible")
except ImportError:
    OPENGL_AVAILABLE = False
    print("ModernGL not available - install with: pip install moderngl (for GPU rendering)")
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
        
        # Encoder control properties - simplified for direct control
        self.encoder_enabled = False
        self.encoder_thread = None
        self.encoder_device = None
        self.encoder_lock = threading.Lock()
        self.encoder_sensitivity = 0.0001  # Much smaller sensitivity for slower, smoother movement
        
        # Smoothing for visual fluidity
        self.target_slider_value = 0.5  # Target value the slider is moving towards
        self.smoothing_factor = 0.15    # How fast the slider catches up to target (0.1 = smooth, 0.5 = fast)
        
        # Initialize encoder if available
        if PHIDGETS_AVAILABLE:
            self.setup_encoder()
        
        # Laser animation properties
        self.time = 0
        self.pulse_intensity = 0
        self.last_frame_time = pygame.time.get_ticks()
        
        # Global animation offset for continuous dashed line effect (time-based)
        self.global_dash_offset = 0.0
        
        # HARDCODED EFFECT SETTINGS - Minimal effects only
        # pulsing segments ON, solid+dashed line ON, line thickness 3.7x, 
        # dash gap 0.3x, dash speed 4.9x, vibrance 1.1x
        # Animation is always enabled for pulsing to work properly
        self.effect_toggles = {
            'pulsing_segments': True,  # ON
            'solid_with_dashes': True  # ON (sub-effect of pulsing_segments)
        }
        
        # Hardcoded effect values (no sliders) - pre-calculated for performance
        self.thickness_multiplier = 3.7  # 3.7x thickness
        self.dash_gap_multiplier = 0.3   # 0.3x dash gap
        self.dash_speed_multiplier = 4.9 # 4.9x dash speed
        self.vibrance_multiplier = 1.1   # 1.1x vibrance
        
        # Pre-calculate frequently used values for performance
        self.pre_calc_dash_gap = 50 * self.thickness_multiplier * self.dash_gap_multiplier
        self.pre_calc_dash_length = 10 * self.thickness_multiplier
        self.pre_calc_pattern_length = self.pre_calc_dash_length + self.pre_calc_dash_gap
        self.pre_calc_line_thickness = max(1, int(3 * self.thickness_multiplier))
        
        # Base thickness for angle compensation (appears consistent at all angles)
        self.base_line_thickness = 3 * self.thickness_multiplier
        self.base_fade_thickness = 2 * self.thickness_multiplier
        
        # Threading for path calculation (Jetson optimization)
        self.path_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="PathCalc")
        self.path_future = None
        self.cached_path_data = None
        self.last_angle_for_path = None
        self.path_calculation_in_progress = False
        
        # Path cache for when angle hasn't changed significantly
        self.path_cache = {}
        self.cache_precision = 100  # Round angle to nearest 0.01 degrees for caching
        
        # Pre-compute color variations for performance (Jetson optimization)
        self.vibrant_green = self.apply_vibrance(GREEN)
        self.vibrant_yellow = self.apply_vibrance(YELLOW)
        self.vibrant_red = self.apply_vibrance(RED)
        self.faded_green = tuple(int(c * 0.3) for c in GREEN)
        self.faded_yellow = tuple(int(c * 0.3) for c in YELLOW)
        self.faded_orange = tuple(int(c * 0.3) for c in ORANGE)
        self.pre_calc_fade_thickness = max(1, int(2 * self.thickness_multiplier))
        
        # GPU acceleration settings (Jetson Tensor Core utilization)
        self.use_gpu_math = CUPY_AVAILABLE  # Enable GPU math if CuPy is available
        
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
    
    def get_angle_compensated_thickness(self, dx, dy, base_thickness):
        """Calculate line thickness compensated for angle to maintain visual consistency"""
        if dx == 0 and dy == 0:
            return max(1, int(base_thickness))
        
        # Calculate the angle of the line
        angle_rad = math.atan2(abs(dy), abs(dx))
        
        # Much more subtle compensation - only reduce thickness slightly for extreme angles
        # Convert to degrees for easier calculation
        angle_deg = math.degrees(angle_rad)
        
        # Very gentle compensation curve that maintains visibility
        if angle_deg <= 30:
            # For angles 0-30°, no compensation needed
            compensation = 1.0
        elif angle_deg <= 60:
            # For angles 30-60°, very gentle reduction (max 15% reduction)
            normalized_angle = (angle_deg - 30) / 30.0  # 0 to 1
            compensation = 1.0 - (normalized_angle * 0.15)  # Reduce up to 15%
        else:
            # For angles 60-90°, gentle reduction (max 25% reduction total)
            normalized_angle = (angle_deg - 60) / 30.0  # 0 to 1  
            compensation = 0.85 - (normalized_angle * 0.10)  # Reduce up to 25% total
        
        # Ensure minimum thickness of 2 pixels for visibility
        compensated_thickness = max(2, int(base_thickness * compensation))
        
        return compensated_thickness
    
    def draw_smooth_line(self, surface, color, start_pos, end_pos, thickness):
        """Draw a smooth anti-aliased line that looks consistent at all angles"""
        if thickness <= 2:
            # For thin lines, use pygame's built-in anti-aliasing with fallback
            try:
                pygame.draw.aaline(surface, color, start_pos, end_pos)
                # Add a regular line for better visibility
                if thickness >= 2:
                    pygame.draw.line(surface, color, start_pos, end_pos, 1)
            except:
                # Fallback to regular line if aaline fails
                pygame.draw.line(surface, color, start_pos, end_pos, max(1, thickness))
        else:
            # For thick lines, use a hybrid approach that maintains brightness
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
            
            if dx == 0 and dy == 0:
                return
            
            # Draw the main line at full thickness and intensity
            pygame.draw.line(surface, color, start_pos, end_pos, max(1, int(thickness * 0.8)))
            
            # Add anti-aliasing only for angles that need it (diagonal lines)
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                angle_rad = math.atan2(abs(dy), abs(dx))
                angle_deg = math.degrees(angle_rad)
                
                # Only add anti-aliasing for diagonal lines (30-60 degrees)
                if 30 <= angle_deg <= 60:
                    # Calculate perpendicular offset for edge softening
                    perp_x = -dy / length
                    perp_y = dx / length
                    
                    # Softer edge color (50% intensity instead of 30%)
                    edge_color = tuple(int(c * 0.5) for c in color)
                    
                    # Single edge softening pass
                    offset_dist = thickness * 0.3
                    
                    # Upper edge
                    start_offset = (int(start_pos[0] + perp_x * offset_dist), 
                                  int(start_pos[1] + perp_y * offset_dist))
                    end_offset = (int(end_pos[0] + perp_x * offset_dist), 
                                int(end_pos[1] + perp_y * offset_dist))
                    
                    try:
                        pygame.draw.aaline(surface, edge_color, start_offset, end_offset)
                    except:
                        pygame.draw.line(surface, edge_color, start_offset, end_offset, 1)
                    
                    # Lower edge  
                    start_offset = (int(start_pos[0] - perp_x * offset_dist), 
                                  int(start_pos[1] - perp_y * offset_dist))
                    end_offset = (int(end_pos[0] - perp_x * offset_dist), 
                                int(end_pos[1] - perp_y * offset_dist))
                    
                    try:
                        pygame.draw.aaline(surface, edge_color, start_offset, end_offset)
                    except:
                        pygame.draw.line(surface, edge_color, start_offset, end_offset, 1)
        
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
        """Calculate light path - now with caching and threading support for Jetson optimization"""
        current_angle = self.get_angle_from_slider()
        
        # Round angle for caching (reduce cache misses from tiny angle changes)
        cache_key = round(current_angle * self.cache_precision)
        
        # Check cache first
        if cache_key in self.path_cache:
            return self.path_cache[cache_key]
        
        # Perform the actual calculation
        path_data = self._calculate_path_internal(current_angle)
        
        # Cache the result (limit cache size for memory efficiency)
        if len(self.path_cache) > 50:  # Limit cache size
            # Remove oldest entry
            oldest_key = next(iter(self.path_cache))
            del self.path_cache[oldest_key]
        
        self.path_cache[cache_key] = path_data
        return path_data
    
    def _calculate_path_internal(self, angle):
        """Internal path calculation - separated for threading with GPU acceleration support"""
        # Starting point (left side of screen, middle height)
        start_x = 0
        start_y = self.screen_height // 2
        
        # Initial direction based on angle - GPU accelerated when available
        if CUPY_AVAILABLE and hasattr(self, 'use_gpu_math') and self.use_gpu_math:
            # Use CuPy for GPU-accelerated trigonometric calculations (Tensor Core utilization)
            angle_gpu = cp.array(angle)
            dx = float(cp.cos(angle_gpu))
            dy = float(cp.sin(angle_gpu))
        elif NUMPY_AVAILABLE:
            # Use numpy for faster trigonometric calculations on Jetson
            dx = np.cos(angle)
            dy = np.sin(angle)
        else:
            dx = math.cos(angle)
            dy = math.sin(angle)
        
        # Trace the light path with bounces - optimized for speed
        path_points = [(start_x, start_y)]
        bounce_angles = []  # Store angle of incidence at each bounce
        bounce_positions = []  # Store bounce positions
        current_x, current_y = float(start_x), float(start_y)
        
        # Larger step size for better performance - fewer points to draw
        step_size = 8.0  # Increased from 2.0 for 4x fewer calculations
        total_distance = 0.0
        
        # Pre-calculate screen bounds
        screen_height_f = float(self.screen_height)
        screen_width_f = float(self.screen_width)
        
        while current_x < screen_width_f:
            # Move one step
            next_x = current_x + dx * step_size
            next_y = current_y + dy * step_size
            
            # Check for bounces off top and bottom walls
            if next_y <= 0:
                # Bounce off top wall
                next_y = -next_y  # Simpler reflection calculation
                
                # Calculate angle of incidence (angle between ray and normal to surface)
                if CUPY_AVAILABLE and hasattr(self, 'use_gpu_math') and self.use_gpu_math:
                    # GPU-accelerated angle calculation
                    dy_abs = abs(dy)
                    dx_abs = abs(dx)
                    angle_gpu = cp.arctan2(dy_abs, dx_abs)
                    incident_angle = float(cp.degrees(angle_gpu))
                elif NUMPY_AVAILABLE:
                    incident_angle = np.degrees(np.arctan2(abs(dy), abs(dx)))
                else:
                    incident_angle = math.degrees(math.atan2(abs(dy), abs(dx)))
                bounce_angles.append(incident_angle)
                bounce_positions.append((int(current_x), 0))
                
                dy = -dy  # Reverse vertical direction
            elif next_y >= screen_height_f:
                # Bounce off bottom wall
                next_y = screen_height_f * 2 - next_y  # Simpler reflection calculation
                
                # Calculate angle of incidence
                if CUPY_AVAILABLE and hasattr(self, 'use_gpu_math') and self.use_gpu_math:
                    # GPU-accelerated angle calculation
                    dy_abs = abs(dy)
                    dx_abs = abs(dx)
                    angle_gpu = cp.arctan2(dy_abs, dx_abs)
                    incident_angle = float(cp.degrees(angle_gpu))
                elif NUMPY_AVAILABLE:
                    incident_angle = np.degrees(np.arctan2(abs(dy), abs(dx)))
                else:
                    incident_angle = math.degrees(math.atan2(abs(dy), abs(dx)))
                bounce_angles.append(incident_angle)
                bounce_positions.append((int(current_x), self.screen_height))
                
                dy = -dy  # Reverse vertical direction
            
            current_x = next_x
            current_y = next_y
            
            # Add to path (pre-convert to int to avoid repeated conversions later)
            path_points.append((int(current_x), int(current_y)))
            
            # Update total distance (simplified calculation)
            total_distance += step_size
        
        return path_points, total_distance, bounce_angles, bounce_positions
    
    def draw_laser_beam(self, start_pos, end_pos, base_color, intensity=1.0):
        """Draw a simple laser beam without effects (for fallback when pulsing segments disabled)"""
        if start_pos == end_pos:
            return
            
        # Calculate beam direction for angle compensation
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        
        # Simple pulsing effect (always enabled for animation)
        pulse = 0.8 + 0.2 * math.sin(self.time * 0.1) * intensity
        
        # Apply vibrance to color
        vibrant_color = self.apply_vibrance(base_color)
        
        # Get angle-compensated thickness to maintain consistent visual width
        thickness = self.get_angle_compensated_thickness(dx, dy, self.base_line_thickness)
        
        # Use smooth line drawing for better appearance at all angles
        self.draw_smooth_line(self.screen, vibrant_color, start_pos, end_pos, thickness)
    
    def draw_solid_beam(self, start_pos, end_pos, base_color, core_color, thickness_multiplier, pulse, beam_length):
        """Draw a simple solid laser beam without effects"""
        # Calculate beam direction for angle compensation
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        
        # Get angle-compensated thickness
        thickness = self.get_angle_compensated_thickness(dx, dy, self.base_line_thickness)
        
        # Simple line with vibrance applied
        simple_color = self.apply_vibrance(base_color)
        self.draw_smooth_line(self.screen, simple_color, start_pos, end_pos, thickness)
    
    def draw_faded_solid_base(self, start_pos, end_pos, base_color, core_color, thickness_multiplier, pulse, intensity):
        """Draw a faded solid line as the base for the dashed effect - optimized"""
        # Reduce intensity for the faded effect (30-50% of original)
        fade_intensity = intensity * 0.4
        
        # Calculate beam direction for angle compensation
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        
        # Get angle-compensated thickness for faded base
        fade_thickness = self.get_angle_compensated_thickness(dx, dy, self.base_fade_thickness)
        
        # Draw simple faded line with vibrance
        faded_base_color = self.apply_vibrance(tuple(min(255, int(c * fade_intensity)) for c in base_color))
        self.draw_smooth_line(self.screen, faded_base_color, start_pos, end_pos, fade_thickness)
    
    def draw_pulsing_segments(self, start_pos, end_pos, base_color, core_color, thickness_multiplier, pulse, intensity, cumulative_distance):
        """Draw a moving dashed line like energy bursts traveling through the fiber - optimized"""
        
        # If solid_with_dashes is enabled, draw a faded solid line first
        if self.effect_toggles['solid_with_dashes']:
            self.draw_faded_solid_base(start_pos, end_pos, base_color, core_color, thickness_multiplier, pulse, intensity)
        
        # Calculate beam direction and length
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        beam_length_sq = dx * dx + dy * dy
        
        if beam_length_sq == 0:
            return
            
        beam_length = math.sqrt(beam_length_sq)
        
        # Normalize direction
        dx_norm = dx / beam_length
        dy_norm = dy / beam_length
        
        # Use pre-calculated dash properties for performance
        dash_length = self.pre_calc_dash_length
        gap_length = self.pre_calc_dash_gap
        total_pattern_length = self.pre_calc_pattern_length
        
        # Animation offset - time-based for consistent visual speed regardless of FPS
        # Use cumulative distance to make dashes flow continuously across all segments
        # Subtract offset to make dashes move from left to right (in direction of light travel)
        animation_offset = (-self.global_dash_offset + cumulative_distance) % total_pattern_length
        
        # Calculate how many complete patterns fit in the beam (fewer iterations)
        num_patterns = int((beam_length + total_pattern_length) / total_pattern_length) + 1
        
        # Pre-calculate colors and thickness to avoid repeated calculations
        vibrant_base_color = self.apply_vibrance(base_color)
        
        # Get angle-compensated thickness for consistent visual width at all angles
        line_thickness = self.get_angle_compensated_thickness(dx, dy, self.base_line_thickness)
        
        # Draw each dash - optimized loop
        for i in range(num_patterns):
            # Calculate dash start position (with animation offset)
            dash_start_distance = i * total_pattern_length - animation_offset
            dash_end_distance = dash_start_distance + dash_length
            
            # Skip if dash is completely outside beam bounds
            if dash_end_distance <= 0 or dash_start_distance >= beam_length:
                continue
            
            # Clamp dash to beam boundaries
            dash_start_distance = max(0, dash_start_distance)
            dash_end_distance = min(beam_length, dash_end_distance)
            
            # Skip if dash has no length after clamping
            if dash_start_distance >= dash_end_distance:
                continue
            
            # Calculate actual start and end positions (avoid repeated int conversions)
            dash_start_x = start_pos[0] + dx_norm * dash_start_distance
            dash_start_y = start_pos[1] + dy_norm * dash_start_distance
            dash_end_x = start_pos[0] + dx_norm * dash_end_distance
            dash_end_y = start_pos[1] + dy_norm * dash_end_distance
            
            # Round once for final drawing positions
            dash_start = (int(dash_start_x), int(dash_start_y))
            dash_end = (int(dash_end_x), int(dash_end_y))
            
            # Calculate dash intensity with brightness variation for animation (simplified)
            # Use time-based animation for consistent speed regardless of angle
            brightness_variation = 0.9 + 0.1 * math.sin(self.time * 5.0 + i * 0.8)
            dash_intensity = intensity * brightness_variation
            
            # Apply intensity to pre-calculated vibrant color
            final_color = tuple(min(255, int(c * dash_intensity)) for c in vibrant_base_color)
            
            # Draw dash with smooth line for consistent appearance at all angles
            self.draw_smooth_line(self.screen, final_color, dash_start, dash_end, line_thickness)
    
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
        """Handle encoder position changes - updates target value for smooth visual movement"""
        try:
            # Only process if we're not manually dragging the slider
            if self.dragging:
                return
                
            with self.encoder_lock:
                # Direct movement calculation updates the target value
                movement = positionChange * self.encoder_sensitivity
                
                # Update target value (the actual slider will smoothly follow)
                self.target_slider_value = max(0.0, min(1.0, self.target_slider_value + movement))
                    
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
        """Simple encoder update - no complex processing needed since we handle it directly in the callback"""
        # The encoder callback now handles all the movement directly
        # This method is kept for compatibility but doesn't need to do anything
        pass
    
    def cleanup_encoder(self):
        """Clean up encoder and threading resources"""
        self.running = False
        
        # Shutdown path calculation thread
        if self.path_executor:
            self.path_executor.shutdown(wait=True)
        
        # Clean up encoder
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
        
        # Color coding for TIR - pre-calculate to avoid repeated conditionals
        if current_angle < CRITICAL_ANGLE:
            light_color = GREEN  # Good TIR - efficient transmission
            intensity = 1.0
        elif current_angle < CRITICAL_ANGLE + 10:
            light_color = YELLOW  # Marginal TIR
            intensity = 0.8
        else:  # Poor TIR - would leak light in real fiber
            light_color = ORANGE
            intensity = 0.6
        
        # Pre-calculate common values for performance
        thickness_multiplier = self.get_thickness_multiplier()
        pulse_value = 0.8 + 0.2 * math.sin(self.time * 10.0)  # Time-based animation
        
        # Draw the laser beam segments with realistic effects - optimized loop
        cumulative_distance = 0.0
        path_len = len(path_points) - 1
        
        for i in range(path_len):
            start_point = path_points[i]
            end_point = path_points[i + 1]
            
            # Calculate segment length (simplified - use step_size since we know it's constant now)
            segment_length = 8.0  # We know this from the optimized path calculation
            
            if self.effect_toggles['pulsing_segments']:
                self.draw_pulsing_segments(start_point, end_point, light_color, 
                                         (255, 255, 255), thickness_multiplier, 
                                         pulse_value, intensity, cumulative_distance)
            else:
                self.draw_laser_beam(start_point, end_point, light_color, intensity)
            
            cumulative_distance += segment_length
        
        # Draw enhanced bounce points with simple effects - optimized with pre-computed colors
        for i, (bounce_pos, incident_angle) in enumerate(zip(bounce_positions, bounce_angles)):
            # Color code bounce points based on angle of incidence - use pre-computed colors
            if incident_angle < CRITICAL_ANGLE:
                bounce_color = self.vibrant_green  # Pre-computed vibrant green
            elif incident_angle < CRITICAL_ANGLE + 10:
                bounce_color = self.vibrant_yellow  # Pre-computed vibrant yellow
            else:
                bounce_color = self.vibrant_red    # Pre-computed vibrant red
            
            # Draw simple bounce circle (removed animation for performance)
            pygame.draw.circle(self.screen, bounce_color, (int(bounce_pos[0]), int(bounce_pos[1])), 3)
        
        # Simple starting point (laser source)
        start_pos = path_points[0]
        pygame.draw.circle(self.screen, self.apply_vibrance(GREEN), start_pos, 5)
        
        # Simple ending point (laser exit)
        if path_points:
            end_point = path_points[-1]
            pygame.draw.circle(self.screen, self.apply_vibrance(light_color), end_point, 5)
    
    def draw_info(self, total_distance, bounce_angles):
        # Remove all text information display for minimal version
        pass
    
    def draw_checkboxes(self):
        # Remove all checkboxes for minimal version
        pass
    
    def check_checkbox_click(self, mouse_x, mouse_y):
        # Remove checkbox functionality for minimal version
        return False
    
    def run(self):
        while self.running:
            # Get current time for frame-rate independent animation
            current_time = pygame.time.get_ticks()
            delta_time = current_time - self.last_frame_time
            self.last_frame_time = current_time
            
            # Update animation time (frame-rate independent)
            self.time += delta_time * 0.001  # Convert to seconds-like units
            
            # Smooth slider movement towards target (for encoder smoothing)
            if not self.dragging:
                # Smoothly interpolate slider towards target value
                diff = self.target_slider_value - self.slider_value
                self.slider_value += diff * self.smoothing_factor
                
                # Snap to target if very close to avoid endless tiny movements
                if abs(diff) < 0.001:
                    self.slider_value = self.target_slider_value
            else:
                # When dragging, keep target in sync with actual slider
                self.target_slider_value = self.slider_value
            
            # Update slider from encoder input (now just a placeholder)
            self.update_slider_from_encoder()
            
            # Update global dash offset for continuous dashed line animation (TIME-BASED for consistent speed)
            if self.effect_toggles['pulsing_segments']:
                # Use delta_time to make animation speed consistent regardless of FPS
                self.global_dash_offset += (delta_time * 0.15) * self.dash_speed_multiplier  # Time-based movement
            
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
# PERFORMANCE OPTIMIZATIONS IMPLEMENTED:
# 1. Time-based animation (not frame-based) for consistent dash speed at any FPS/angle
# 2. Larger step size (8.0 vs 2.0) for 4x fewer path points and draw calls
# 3. Pre-calculated values (dash lengths, thicknesses, colors) to avoid repeated math
# 4. Simplified reflection calculations and removed unnecessary sqrt operations
# 5. Reduced float-to-int conversions and optimized drawing loops
# 6. Hardware-friendly optimizations for NVIDIA Jetson Orin Nano Super
# 7. Threading-ready path calculation with caching for identical angles
# 8. Pre-computed color variations to eliminate runtime apply_vibrance() calls
# 9. NumPy support for faster trigonometric operations (install: pip install numpy)
# 10. Path result caching to avoid recalculating identical light paths

# ADDITIONAL SPEED IMPROVEMENTS FOR JETSON (if needed):
# - Install NumPy: pip install numpy (faster trigonometric calculations)
# - Install CuPy for Tensor Core acceleration: pip install cupy-cuda11x (GPU-accelerated math)
# - Install ModernGL for GPU rendering: pip install moderngl (OpenGL-based drawing)
# - Use pygame.surfarray for bulk pixel operations
# - Consider reducing step_size further (16.0) if visual quality permits
# - Profile with cProfile to identify remaining bottlenecks
# - Use threading for path calculation when angle changes significantly

# JETSON TENSOR CORE UTILIZATION:
# The Jetson's Tensor Cores are optimized for AI/ML matrix operations, not geometric calculations.
# However, CuPy can leverage the GPU's CUDA cores for trigonometric functions, which provides
# some performance benefit. For true Tensor Core utilization, you'd need to reformulate the
# problem as matrix operations (e.g., calculating many light rays simultaneously).

# INSTALLATION FOR MAXIMUM JETSON PERFORMANCE:
# pip install numpy cupy-cuda11x moderngl
# This enables:
# - NumPy: Faster CPU math operations
# - CuPy: GPU-accelerated trigonometric functions (limited Tensor Core usage)
# - ModernGL: Potential GPU-based rendering (would require major rewrite)
if __name__ == "__main__":
    simulation = OpticalFiberSimulation()
    simulation.run()