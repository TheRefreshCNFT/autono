#!/usr/bin/env python3
"""
Convert SVG walrus logo to PNG icons for Chrome extension
Uses cairosvg or Pillow + reportlab, with fallbacks
"""

import sys
import os
from pathlib import Path

def convert_with_cairosvg(svg_path, output_dir, sizes):
    """Use cairosvg (best quality)"""
    try:
        import cairosvg
        print("Using cairosvg for conversion...")
        
        for size in sizes:
            output_path = os.path.join(output_dir, f'icon-{size}.png')
            cairosvg.svg2png(
                url=svg_path,
                write_to=output_path,
                output_width=size,
                output_height=size
            )
            print(f"✓ Created {size}×{size} icon: {output_path}")
        return True
    except ImportError:
        print("cairosvg not available")
        return False
    except Exception as e:
        print(f"cairosvg failed: {e}")
        return False

def convert_with_pillow(svg_path, output_dir, sizes):
    """Use Pillow with svglib"""
    try:
        from PIL import Image
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
        
        print("Using Pillow + svglib for conversion...")
        
        for size in sizes:
            # Convert SVG to ReportLab drawing
            drawing = svg2rlg(svg_path)
            
            # Scale the drawing
            scale = size / 200.0  # Original SVG is 200x200
            drawing.width = size
            drawing.height = size
            drawing.scale(scale, scale)
            
            # Render to PNG
            output_path = os.path.join(output_dir, f'icon-{size}.png')
            renderPM.drawToFile(drawing, output_path, fmt='PNG')
            print(f"✓ Created {size}×{size} icon: {output_path}")
        return True
    except ImportError as e:
        print(f"Pillow/svglib not available: {e}")
        return False
    except Exception as e:
        print(f"Pillow method failed: {e}")
        return False

def install_dependencies():
    """Try to install required dependencies"""
    import subprocess
    
    print("\nAttempting to install cairosvg...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cairosvg'])
        return True
    except:
        print("Failed to install cairosvg")
        
    print("\nAttempting to install pillow svglib reportlab...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pillow', 'svglib', 'reportlab'])
        return True
    except:
        print("Failed to install pillow dependencies")
        
    return False

def main():
    # Paths
    script_dir = Path(__file__).parent
    svg_path = script_dir.parent / 'assets' / 'wali-logo.svg'
    output_dir = script_dir / 'public' / 'assets'
    
    # Ensure paths exist
    if not svg_path.exists():
        print(f"Error: SVG file not found: {svg_path}")
        return 1
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sizes to generate
    sizes = [16, 48, 128]
    
    print(f"Converting {svg_path} to PNG icons...")
    print(f"Output directory: {output_dir}\n")
    
    # Try cairosvg first (best quality)
    if convert_with_cairosvg(str(svg_path), str(output_dir), sizes):
        print("\n🦭 All walrus icons created successfully with cairosvg!")
        return 0
    
    # Try Pillow + svglib
    if convert_with_pillow(str(svg_path), str(output_dir), sizes):
        print("\n🦭 All walrus icons created successfully with Pillow!")
        return 0
    
    # If nothing worked, try installing dependencies
    print("\n❌ No SVG converters available.")
    response = input("Would you like to try installing dependencies? (y/n): ")
    
    if response.lower().startswith('y'):
        if install_dependencies():
            print("\nRetrying conversion...")
            if convert_with_cairosvg(str(svg_path), str(output_dir), sizes):
                print("\n🦭 All walrus icons created successfully!")
                return 0
            if convert_with_pillow(str(svg_path), str(output_dir), sizes):
                print("\n🦭 All walrus icons created successfully!")
                return 0
    
    print("\n❌ Conversion failed. Please install cairosvg or pillow+svglib manually:")
    print("  pip install cairosvg")
    print("  OR")
    print("  pip install pillow svglib reportlab")
    return 1

if __name__ == '__main__':
    sys.exit(main())
