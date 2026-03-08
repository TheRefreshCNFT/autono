#!/usr/bin/env node

/**
 * Convert SVG walrus logo to PNG icons
 * Uses Puppeteer to render SVG and screenshot at different sizes
 */

const fs = require('fs');
const path = require('path');

// Try to use puppeteer if available, otherwise use a simpler approach
let usePuppeteer = false;
try {
  require.resolve('puppeteer');
  usePuppeteer = true;
} catch (e) {
  console.log('Puppeteer not found, trying alternative method...');
}

if (usePuppeteer) {
  convertWithPuppeteer();
} else {
  convertWithSharp();
}

async function convertWithSharp() {
  try {
    const sharp = require('sharp');
    const svgPath = path.join(__dirname, '../assets/wali-logo.svg');
    const outputDir = path.join(__dirname, 'public/assets');
    
    // Ensure output directory exists
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    const svgBuffer = fs.readFileSync(svgPath);
    const sizes = [16, 48, 128];
    
    console.log('Converting SVG to PNG icons with sharp...');
    
    for (const size of sizes) {
      const outputPath = path.join(outputDir, `icon-${size}.png`);
      await sharp(svgBuffer)
        .resize(size, size)
        .png()
        .toFile(outputPath);
      console.log(`✓ Created ${size}x${size} icon: ${outputPath}`);
    }
    
    console.log('\n🦭 All walrus icons created successfully!');
  } catch (error) {
    console.error('Sharp method failed:', error.message);
    console.log('\nTrying browser-based conversion...');
    convertWithBrowser();
  }
}

async function convertWithPuppeteer() {
  const puppeteer = require('puppeteer');
  const svgPath = path.join(__dirname, '../assets/wali-logo.svg');
  const outputDir = path.join(__dirname, 'public/assets');
  
  // Ensure output directory exists
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  const svgContent = fs.readFileSync(svgPath, 'utf8');
  const sizes = [16, 48, 128];
  
  console.log('Converting SVG to PNG icons with Puppeteer...');
  
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  
  for (const size of sizes) {
    await page.setViewport({ width: size, height: size });
    await page.setContent(`
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            body { margin: 0; padding: 0; width: ${size}px; height: ${size}px; }
            svg { width: 100%; height: 100%; }
          </style>
        </head>
        <body>${svgContent}</body>
      </html>
    `);
    
    const outputPath = path.join(outputDir, `icon-${size}.png`);
    await page.screenshot({ path: outputPath, omitBackground: false });
    console.log(`✓ Created ${size}x${size} icon: ${outputPath}`);
  }
  
  await browser.close();
  console.log('\n🦭 All walrus icons created successfully!');
}

function convertWithBrowser() {
  console.log('\n📝 Manual conversion needed:');
  console.log('Please run this HTML file in a browser and save the canvas images:\n');
  
  const svgPath = path.join(__dirname, '../assets/wali-logo.svg');
  const svgContent = fs.readFileSync(svgPath, 'utf8');
  
  const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <title>SVG to PNG Converter</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 20px; }
    .icon-container { display: inline-block; margin: 20px; text-align: center; }
    canvas { border: 1px solid #ddd; display: block; margin: 10px auto; }
    button { padding: 10px 20px; margin: 5px; cursor: pointer; }
  </style>
</head>
<body>
  <h1>🦭 wAli Walrus Logo Converter</h1>
  <p>Click the download buttons to save each icon:</p>
  
  <div class="icon-container">
    <h3>16x16 (Toolbar)</h3>
    <canvas id="canvas-16" width="16" height="16"></canvas>
    <button onclick="download(16)">Download 16x16</button>
  </div>
  
  <div class="icon-container">
    <h3>48x48 (Extension)</h3>
    <canvas id="canvas-48" width="48" height="48"></canvas>
    <button onclick="download(48)">Download 48x48</button>
  </div>
  
  <div class="icon-container">
    <h3>128x128 (Store)</h3>
    <canvas id="canvas-128" width="128" height="128"></canvas>
    <button onclick="download(128)">Download 128x128</button>
  </div>
  
  <script>
    const svgContent = \`${svgContent}\`;
    const sizes = [16, 48, 128];
    
    function renderSVG(size) {
      const canvas = document.getElementById('canvas-' + size);
      const ctx = canvas.getContext('2d');
      const img = new Image();
      const blob = new Blob([svgContent], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);
      
      img.onload = function() {
        ctx.drawImage(img, 0, 0, size, size);
        URL.revokeObjectURL(url);
      };
      
      img.src = url;
    }
    
    function download(size) {
      const canvas = document.getElementById('canvas-' + size);
      canvas.toBlob(function(blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'icon-' + size + '.png';
        a.click();
        URL.revokeObjectURL(url);
      });
    }
    
    // Render all sizes on load
    sizes.forEach(size => renderSVG(size));
  </script>
</body>
</html>
`;
  
  const htmlPath = path.join(__dirname, 'convert-icons.html');
  fs.writeFileSync(htmlPath, htmlContent);
  console.log(`Created: ${htmlPath}`);
  console.log('Open this file in your browser and click the download buttons.');
}
