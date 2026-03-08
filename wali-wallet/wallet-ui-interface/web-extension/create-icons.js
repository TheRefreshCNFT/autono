const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

// Create wAli icons using SVG and ImageMagick or by embedding simple PNG data
async function createIconsWithSVG() {
  const outputDir = path.join(__dirname, 'public', 'assets');
  
  // Create output directory
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  console.log('🦭 Creating wAli icons...\n');

  // Create SVG template
  const createSVG = (size) => `<?xml version="1.0" encoding="UTF-8"?>
<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <defs>
    <radialGradient id="bg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#5BA3F5;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#4A90E2;stop-opacity:1" />
    </radialGradient>
  </defs>
  <rect width="${size}" height="${size}" fill="url(#bg)" rx="${size * 0.15}"/>
  
  <!-- Walrus face -->
  <g transform="translate(${size/2}, ${size/2})">
    <!-- Head -->
    <ellipse cx="0" cy="0" rx="${size * 0.28}" ry="${size * 0.24}" fill="white" opacity="0.9"/>
    
    <!-- Eyes -->
    <circle cx="${-size * 0.08}" cy="${-size * 0.05}" r="${size * 0.025}" fill="#2C3E50"/>
    <circle cx="${size * 0.08}" cy="${-size * 0.05}" r="${size * 0.025}" fill="#2C3E50"/>
    
    <!-- Nose -->
    <circle cx="0" cy="${size * 0.06}" r="${size * 0.03}" fill="#34495E"/>
    
    <!-- Tusks -->
    <rect x="${-size * 0.1}" y="${size * 0.12}" width="${size * 0.03}" height="${size * 0.12}" fill="white" opacity="0.95"/>
    <rect x="${size * 0.07}" y="${size * 0.12}" width="${size * 0.03}" height="${size * 0.12}" fill="white" opacity="0.95"/>
    
    <!-- Whisker dots -->
    <circle cx="${-size * 0.2}" cy="${size * 0.04}" r="${size * 0.015}" fill="#34495E" opacity="0.7"/>
    <circle cx="${-size * 0.24}" cy="${size * 0.02}" r="${size * 0.012}" fill="#34495E" opacity="0.7"/>
    <circle cx="${size * 0.2}" cy="${size * 0.04}" r="${size * 0.015}" fill="#34495E" opacity="0.7"/>
    <circle cx="${size * 0.24}" cy="${size * 0.02}" r="${size * 0.012}" fill="#34495E" opacity="0.7"/>
  </g>
</svg>`;

  const sizes = [16, 48, 128];

  for (const size of sizes) {
    const svgContent = createSVG(size);
    const svgPath = path.join(outputDir, `icon-${size}.svg`);
    const pngPath = path.join(outputDir, `icon-${size}.png`);
    
    // Save SVG
    fs.writeFileSync(svgPath, svgContent);
    console.log(`✅ Created icon-${size}.svg`);
    
    // Try to convert to PNG using various methods
    let converted = false;
    
    // Method 1: Try ImageMagick
    try {
      await execAsync(`magick "${svgPath}" "${pngPath}"`);
      converted = true;
      console.log(`✅ Converted to icon-${size}.png (ImageMagick)`);
    } catch (e) {
      // ImageMagick not available
    }
    
    // Method 2: Try Inkscape
    if (!converted) {
      try {
        await execAsync(`inkscape "${svgPath}" --export-filename="${pngPath}" --export-width=${size} --export-height=${size}`);
        converted = true;
        console.log(`✅ Converted to icon-${size}.png (Inkscape)`);
      } catch (e) {
        // Inkscape not available
      }
    }
    
    // Method 3: Keep SVG if no converter available
    if (!converted) {
      console.log(`⚠️  Keeping SVG format (no PNG converter found)`);
      console.log(`   Install ImageMagick or use online converter`);
    }
  }

  console.log('\n📁 Icons saved to:', outputDir);
  console.log('\n💡 Note: Chrome extensions work with PNG files.');
  console.log('   If you only have SVG files, convert them using:');
  console.log('   - ImageMagick: magick icon.svg icon.png');
  console.log('   - Online: https://convertio.co/svg-png/');
  console.log('   - Or use: npx sharp-cli -i icon.svg -o icon.png');
}

createIconsWithSVG().catch(console.error);
