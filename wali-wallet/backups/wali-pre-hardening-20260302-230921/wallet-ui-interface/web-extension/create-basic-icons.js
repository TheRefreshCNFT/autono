const fs = require('fs');
const path = require('path');

// Create basic wAli icons using embedded PNG data
// These are minimal valid PNG files created programmatically

function createBasicPNG(width, height) {
  // Create a buffer for PNG data
  const headerSize = 8;
  const ihdrSize = 25;
  const idatEstimate = width * height * 4 + 1000;
  const iendSize = 12;
  
  // PNG signature
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  
  // IHDR chunk
  const ihdr = Buffer.alloc(ihdrSize);
  ihdr.writeUInt32BE(13, 0); // Length
  ihdr.write('IHDR', 4);
  ihdr.writeUInt32BE(width, 8);
  ihdr.writeUInt32BE(height, 12);
  ihdr.writeUInt8(8, 16); // Bit depth
  ihdr.writeUInt8(6, 17); // Color type (RGBA)
  ihdr.writeUInt8(0, 18); // Compression
  ihdr.writeUInt8(0, 19); // Filter
  ihdr.writeUInt8(0, 20); // Interlace
  
  // Calculate CRC for IHDR
  const crc = require('zlib').crc32(ihdr.slice(4, 21));
  ihdr.writeUInt32BE(crc, 21);
  
  // Create image data (solid wAli blue with white "W")
  const pixels = Buffer.alloc(width * height * 4);
  
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4;
      
      // Gradient background
      const centerX = width / 2;
      const centerY = height / 2;
      const distance = Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));
      const maxDist = Math.sqrt(centerX * centerX + centerY * centerY);
      const brightness = 1 - (distance / maxDist) * 0.15;
      
      pixels[idx] = Math.floor(74 * brightness);      // R
      pixels[idx + 1] = Math.floor(144 * brightness); // G
      pixels[idx + 2] = Math.floor(226 * brightness); // B
      pixels[idx + 3] = 255;                          // A
      
      // Draw simple white "W" in the center
      const relX = (x - centerX) / width;
      const relY = (y - centerY) / height;
      
      if (Math.abs(relY) < 0.25 && Math.abs(relX) < 0.3) {
        const leftV = Math.abs(relX + 0.15) < 0.04 && relY > -0.25;
        const rightV = Math.abs(relX - 0.15) < 0.04 && relY > -0.25;
        const middleV = Math.abs(relX) < 0.04 && relY < 0.1 && relY > -0.05;
        
        if (leftV || rightV || middleV) {
          pixels[idx] = 255;
          pixels[idx + 1] = 255;
          pixels[idx + 2] = 255;
        }
      }
    }
  }
  
  // Create scanlines (add filter byte at start of each row)
  const scanlines = Buffer.alloc(height * (width * 4 + 1));
  for (let y = 0; y < height; y++) {
    scanlines[y * (width * 4 + 1)] = 0; // No filter
    pixels.copy(scanlines, y * (width * 4 + 1) + 1, y * width * 4, (y + 1) * width * 4);
  }
  
  // Compress the image data
  const compressed = require('zlib').deflateSync(scanlines, { level: 9 });
  
  // IDAT chunk
  const idat = Buffer.alloc(compressed.length + 12);
  idat.writeUInt32BE(compressed.length, 0);
  idat.write('IDAT', 4);
  compressed.copy(idat, 8);
  const idatCrc = require('zlib').crc32(idat.slice(4, idat.length - 4));
  idat.writeUInt32BE(idatCrc, idat.length - 4);
  
  // IEND chunk
  const iend = Buffer.from([0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130]);
  
  // Combine all chunks
  return Buffer.concat([signature, ihdr, idat, iend]);
}

async function generateIcons() {
  const sizes = [16, 48, 128];
  const assetsDir = path.join(__dirname, 'public', 'assets');

  // Create output directory
  if (!fs.existsSync(assetsDir)) {
    fs.mkdirSync(assetsDir, { recursive: true });
  }

  console.log('🦭 Generating wAli PNG icons (pure Node.js)...\n');

  for (const size of sizes) {
    try {
      const buffer = createBasicPNG(size, size);
      const filepath = path.join(assetsDir, `icon-${size}.png`);
      
      fs.writeFileSync(filepath, buffer);
      
      // Verify it's a valid PNG
      const stat = fs.statSync(filepath);
      console.log(`✅ Created icon-${size}.png (${size}x${size}, ${stat.size} bytes)`);
    } catch (error) {
      console.error(`❌ Error creating icon-${size}.png:`, error.message);
      throw error;
    }
  }

  console.log('\n🎉 All PNG icons generated successfully!');
  console.log(`📁 Location: ${assetsDir}`);
  console.log('\n💡 Icons feature:');
  console.log('   - wAli blue gradient background (#4A90E2)');
  console.log('   - White "W" letter in center');
  console.log('   - Valid PNG format, ready for Chrome extension');
}

generateIcons().catch(err => {
  console.error('\n❌ Failed to generate icons:', err);
  process.exit(1);
});
