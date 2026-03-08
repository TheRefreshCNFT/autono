const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

async function convertSVGtoPNG() {
  const assetsDir = path.join(__dirname, 'public', 'assets');
  const sizes = [16, 48, 128];

  console.log('🦭 Converting SVG icons to PNG...\n');

  for (const size of sizes) {
    const svgPath = path.join(assetsDir, `icon-${size}.svg`);
    const pngPath = path.join(assetsDir, `icon-${size}.png`);

    if (!fs.existsSync(svgPath)) {
      console.log(`⚠️  ${svgPath} not found, skipping...`);
      continue;
    }

    try {
      await sharp(svgPath)
        .resize(size, size, {
          fit: 'contain',
          background: { r: 74, g: 144, b: 226, alpha: 1 }
        })
        .png()
        .toFile(pngPath);

      console.log(`✅ Created icon-${size}.png`);
    } catch (error) {
      console.error(`❌ Error converting icon-${size}.svg:`, error.message);
    }
  }

  console.log('\n🎉 PNG conversion complete!');
  console.log(`📁 Location: ${assetsDir}`);
}

convertSVGtoPNG().catch(console.error);
