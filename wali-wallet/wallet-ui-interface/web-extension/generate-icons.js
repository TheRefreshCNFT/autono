const fs = require('fs');
const path = require('path');

// Simple SVG-based icon generator
// Creates wAli walrus icons in PNG format using data URIs and canvas

const createWaliIcon = async (size) => {
  const canvas = require('canvas');
  const Canvas = canvas.createCanvas(size, size);
  const ctx = Canvas.getContext('2d');

  // Background - wAli blue
  ctx.fillStyle = '#4A90E2';
  ctx.fillRect(0, 0, size, size);

  // Draw a simple walrus silhouette
  ctx.fillStyle = '#FFFFFF';
  
  // Scale factors based on size
  const scale = size / 128;
  
  // Walrus head (ellipse)
  ctx.beginPath();
  ctx.ellipse(size/2, size/2, 35*scale, 30*scale, 0, 0, Math.PI * 2);
  ctx.fill();

  // Walrus tusks (two white triangles)
  ctx.beginPath();
  ctx.moveTo(size/2 - 12*scale, size/2 + 15*scale);
  ctx.lineTo(size/2 - 8*scale, size/2 + 30*scale);
  ctx.lineTo(size/2 - 4*scale, size/2 + 15*scale);
  ctx.fill();

  ctx.beginPath();
  ctx.moveTo(size/2 + 12*scale, size/2 + 15*scale);
  ctx.lineTo(size/2 + 8*scale, size/2 + 30*scale);
  ctx.lineTo(size/2 + 4*scale, size/2 + 15*scale);
  ctx.fill();

  // Eyes
  ctx.fillStyle = '#2C3E50';
  ctx.beginPath();
  ctx.arc(size/2 - 10*scale, size/2 - 5*scale, 3*scale, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(size/2 + 10*scale, size/2 - 5*scale, 3*scale, 0, Math.PI * 2);
  ctx.fill();

  // Nose
  ctx.beginPath();
  ctx.arc(size/2, size/2 + 8*scale, 4*scale, 0, Math.PI * 2);
  ctx.fill();

  // Whisker dots (simplified)
  const whiskerDots = [
    [size/2 - 25*scale, size/2 + 5*scale],
    [size/2 - 30*scale, size/2 + 2*scale],
    [size/2 + 25*scale, size/2 + 5*scale],
    [size/2 + 30*scale, size/2 + 2*scale],
  ];
  
  ctx.fillStyle = '#34495E';
  whiskerDots.forEach(([x, y]) => {
    ctx.beginPath();
    ctx.arc(x, y, 1.5*scale, 0, Math.PI * 2);
    ctx.fill();
  });

  return Canvas.toBuffer('image/png');
};

const generateIcons = async () => {
  const sizes = [16, 48, 128];
  const outputDir = path.join(__dirname, 'public', 'assets');

  // Create output directory
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  console.log('🦭 Generating wAli icons...\n');

  for (const size of sizes) {
    const buffer = await createWaliIcon(size);
    const filename = `icon-${size}.png`;
    const filepath = path.join(outputDir, filename);
    
    fs.writeFileSync(filepath, buffer);
    console.log(`✅ Created ${filename} (${size}x${size})`);
  }

  console.log('\n🎉 All icons generated successfully!');
  console.log(`📁 Location: ${outputDir}`);
};

// Check if canvas package is available
try {
  require.resolve('canvas');
  generateIcons().catch(console.error);
} catch (e) {
  console.error('❌ Error: canvas package not found.');
  console.error('Please install it with: npm install canvas');
  process.exit(1);
}
