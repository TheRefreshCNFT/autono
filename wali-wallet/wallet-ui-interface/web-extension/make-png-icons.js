const fs = require('fs');
const path = require('path');

// Create simple PNG files using raw PNG format
// This creates valid PNG files without external dependencies

function createPNG(width, height, drawFn) {
  const { PNG } = require('pngjs');
  const png = new PNG({ width, height });
  
  // Fill with wAli blue background
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (width * y + x) << 2;
      
      // Radial gradient background
      const centerX = width / 2;
      const centerY = height / 2;
      const distance = Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));
      const maxDist = Math.sqrt(centerX * centerX + centerY * centerY);
      const brightness = 1 - (distance / maxDist) * 0.15;
      
      png.data[idx] = Math.floor(74 * brightness);      // R
      png.data[idx + 1] = Math.floor(144 * brightness); // G
      png.data[idx + 2] = Math.floor(226 * brightness); // B
      png.data[idx + 3] = 255;                          // A
    }
  }
  
  // Draw walrus icon
  if (drawFn) {
    drawFn(png, width, height);
  }
  
  return PNG.sync.write(png);
}

function drawWalrus(png, width, height) {
  const scale = width / 128;
  const centerX = width / 2;
  const centerY = height / 2;
  
  // Helper to draw filled circle
  const fillCircle = (cx, cy, radius, r, g, b, a = 255) => {
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const dx = x - cx;
        const dy = y - cy;
        if (dx * dx + dy * dy <= radius * radius) {
          const idx = (width * y + x) << 2;
          png.data[idx] = r;
          png.data[idx + 1] = g;
          png.data[idx + 2] = b;
          png.data[idx + 3] = a;
        }
      }
    }
  };
  
  // Helper to draw filled ellipse
  const fillEllipse = (cx, cy, rx, ry, r, g, b, a = 255) => {
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const dx = (x - cx) / rx;
        const dy = (y - cy) / ry;
        if (dx * dx + dy * dy <= 1) {
          const idx = (width * y + x) << 2;
          png.data[idx] = r;
          png.data[idx + 1] = g;
          png.data[idx + 2] = b;
          png.data[idx + 3] = a;
        }
      }
    }
  };
  
  // Helper to draw filled rectangle
  const fillRect = (x, y, w, h, r, g, b, a = 255) => {
    for (let py = Math.max(0, y); py < Math.min(height, y + h); py++) {
      for (let px = Math.max(0, x); px < Math.min(width, x + w); px++) {
        const idx = (width * py + px) << 2;
        png.data[idx] = r;
        png.data[idx + 1] = g;
        png.data[idx + 2] = b;
        png.data[idx + 3] = a;
      }
    }
  };
  
  // Draw walrus head (white ellipse)
  fillEllipse(centerX, centerY, 35 * scale, 30 * scale, 255, 255, 255, 230);
  
  // Draw eyes (dark circles)
  fillCircle(centerX - 10 * scale, centerY - 5 * scale, 3 * scale, 44, 62, 80);
  fillCircle(centerX + 10 * scale, centerY - 5 * scale, 3 * scale, 44, 62, 80);
  
  // Draw nose (dark circle)
  fillCircle(centerX, centerY + 8 * scale, 4 * scale, 44, 62, 80);
  
  // Draw tusks (white rectangles)
  fillRect(
    Math.floor(centerX - 12 * scale),
    Math.floor(centerY + 15 * scale),
    Math.floor(4 * scale),
    Math.floor(15 * scale),
    255, 255, 255, 240
  );
  fillRect(
    Math.floor(centerX + 8 * scale),
    Math.floor(centerY + 15 * scale),
    Math.floor(4 * scale),
    Math.floor(15 * scale),
    255, 255, 255, 240
  );
  
  // Draw whisker dots
  if (width >= 32) {
    fillCircle(centerX - 25 * scale, centerY + 5 * scale, 1.5 * scale, 52, 73, 94, 180);
    fillCircle(centerX - 30 * scale, centerY + 2 * scale, 1.2 * scale, 52, 73, 94, 180);
    fillCircle(centerX + 25 * scale, centerY + 5 * scale, 1.5 * scale, 52, 73, 94, 180);
    fillCircle(centerX + 30 * scale, centerY + 2 * scale, 1.2 * scale, 52, 73, 94, 180);
  }
}

async function generateIcons() {
  const sizes = [16, 48, 128];
  const assetsDir = path.join(__dirname, 'public', 'assets');

  // Create output directory
  if (!fs.existsSync(assetsDir)) {
    fs.mkdirSync(assetsDir, { recursive: true });
  }

  console.log('🦭 Generating wAli PNG icons...\n');

  try {
    require.resolve('pngjs');
  } catch {
    console.log('Installing pngjs...');
    require('child_process').execSync('npm install pngjs', { stdio: 'inherit', cwd: __dirname });
  }

  for (const size of sizes) {
    try {
      const buffer = createPNG(size, size, drawWalrus);
      const filepath = path.join(assetsDir, `icon-${size}.png`);
      
      fs.writeFileSync(filepath, buffer);
      console.log(`✅ Created icon-${size}.png (${size}x${size})`);
    } catch (error) {
      console.error(`❌ Error creating icon-${size}.png:`, error.message);
      throw error;
    }
  }

  console.log('\n🎉 All PNG icons generated successfully!');
  console.log(`📁 Location: ${assetsDir}`);
}

generateIcons().catch(err => {
  console.error('\n❌ Failed to generate icons:', err);
  process.exit(1);
});
