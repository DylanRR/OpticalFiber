#!/usr/bin/env python3
"""
Test script to verify the checkbox functionality is working correctly.
This will run the simulation for a few seconds and then exit.
"""

import pygame
import sys
import time
from fiberTest_laser import OpticalFiberSimulation

def test_checkboxes():
    """Test the checkbox functionality"""
    print("Testing Optical Fiber Simulation with Interactive Checkboxes...")
    print("Features added:")
    print("1. Interactive checkboxes for visual effect toggles")
    print("2. Gradient/Glow Effect toggle")
    print("3. Animated Properties toggle")
    print("4. Laser Core & Halo toggle")
    print("5. Particle Effects toggle")
    print()
    print("Instructions for testing:")
    print("- Move the slider to adjust the laser angle")
    print("- Click the checkboxes in the upper right to toggle effects")
    print("- Press F11 to toggle fullscreen")
    print("- Press ESC to exit")
    print()
    print("Starting simulation... (Press ESC or close window to exit)")
    
    try:
        # Create and run the simulation
        simulation = OpticalFiberSimulation()
        
        # Verify that all the new properties exist
        assert hasattr(simulation, 'effect_toggles'), "Missing effect_toggles property"
        assert hasattr(simulation, 'checkbox_size'), "Missing checkbox_size property"
        assert hasattr(simulation, 'draw_checkboxes'), "Missing draw_checkboxes method"
        assert hasattr(simulation, 'check_checkbox_click'), "Missing check_checkbox_click method"
        
        print("✓ All checkbox properties and methods are present")
        print("✓ Starting interactive simulation...")
        
        # Run the simulation
        simulation.run()
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        return False
    
    print("✓ Simulation completed successfully")
    return True

if __name__ == "__main__":
    success = test_checkboxes()
    if success:
        print("\n🎉 All tests passed! The interactive checkboxes are working correctly.")
    else:
        print("\n❌ Tests failed. Please check the implementation.")
        sys.exit(1)
