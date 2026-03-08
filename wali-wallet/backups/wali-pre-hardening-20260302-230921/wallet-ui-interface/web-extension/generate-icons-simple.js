const fs = require('fs');
const path = require('path');

// Simple PNG generator using pure Node.js
// Creates minimal valid PNG files with wAli branding

function createPNG(width, height, color) {
  const { createCanvas } = require('canvas');
  
  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext('2d');
  
  // Background gradient
  const gradient = ctx.createRadialGradient(width/2, height/2, 0, width/2, height/2, width/2);
  gradient.addColorStop(0, '#5BA3F5');
  gradient.addColorStop(1, '#4A90E2');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);
  
  // Draw "W" for wAli in white
  ctx.fillStyle = 'white';
  ctx.font = `bold ${Math.floor(height * 0.6)}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('W', width/2, height/2);
  
  return canvas.toBuffer('image/png');
}

// Fallback: Create a simple colored PNG without canvas
function createSimplePNG(width, height) {
  // This creates a minimal valid PNG file
  const PNG = require('pngjs').PNG;
  const png = new PNG({ width, height });
  
  // wAli blue color
  const r = 74, g = 144, b = 226;
  
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (width * y + x) << 2;
      
      // Create gradient effect
      const centerX = width / 2;
      const centerY = height / 2;
      const distance = Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));
      const maxDist = Math.sqrt(centerX * centerX + centerY * centerY);
      const brightness = 1 - (distance / maxDist) * 0.2;
      
      png.data[idx] = Math.floor(r * brightness);
      png.data[idx + 1] = Math.floor(g * brightness);
      png.data[idx + 2] = Math.floor(b * brightness);
      png.data[idx + 3] = 255; // alpha
      
      // Add white "W" in center (very simple)
      const relX = (x - centerX) / width;
      const relY = (y - centerY) / height;
      
      if (Math.abs(relY) < 0.25 && Math.abs(relX) < 0.3) {
        // Simple W shape
        const leftV = Math.abs(relX + 0.15) < 0.04 && relY > -0.25;
        const rightV = Math.abs(relX - 0.15) < 0.04 && relY > -0.25;
        const middleV = Math.abs(relX) < 0.04 && relY < 0.1 && relY > -0.05;
        
        if (leftV || rightV || middleV) {
          png.data[idx] = 255;
          png.data[idx + 1] = 255;
          png.data[idx + 2] = 255;
        }
      }
    }
  }
  
  return PNG.sync.write(png);
}

async function generateIcons() {
  const sizes = [16, 48, 128];
  const outputDir = path.join(__dirname, 'public', 'assets');

  // Create output directory
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  console.log('🦭 Generating wAli icons...\n');

  let useCanvas = true;
  try {
    require.resolve('canvas');
  } catch {
    useCanvas = false;
    try {
      require.resolve('pngjs');
    } catch {
      console.error('Installing pngjs...');
      require('child_process').execSync('npm install pngjs', { stdio: 'inherit' });
    }
  }

  for (const size of sizes) {
    let buffer;
    
    try {
      if (useCanvas) {
        buffer = createPNG(size, size);
      } else {
        buffer = createSimplePNG(size, size);
      }
      
      const filename = `icon-${size}.png`;
      const filepath = path.join(outputDir, filename);
      
      fs.writeFileSync(filepath, buffer);
      console.log(`✅ Created ${filename} (${size}x${size})`);
    } catch (error) {
      console.error(`❌ Error creating ${size}x${size} icon:`, error.message);
    }
  }

  console.log('\n🎉 All icons generated!');
  console.log(`📁 Location: ${outputDir}`);
}

generateIcons().catch(console.error);
