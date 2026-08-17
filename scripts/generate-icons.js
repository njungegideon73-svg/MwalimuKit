/**
 * Generate Android app icons from the logo SVG.
 *
 * Usage: node scripts/generate-icons.js
 *
 * Requires: npm install sharp (dev dependency)
 */
const fs = require('fs');
const path = require('path');

const SIZES = {
  'mipmap-mdpi': 72,
  'mipmap-hdpi': 96,
  'mipmap-xhdpi': 144,
  'mipmap-xxhdpi': 192,
  'mipmap-xxxhdpi': 512,
};

async function main() {
  let sharp;
  try {
    sharp = require('sharp');
  } catch {
    console.error('Install sharp first: npm install sharp');
    process.exit(1);
  }

  const svgPath = path.resolve(__dirname, '../assets/mwalimukit-logo.svg');
  const svg = fs.readFileSync(svgPath);

  const androidRes = path.resolve(__dirname, '../web/android/app/src/main/res');

  for (const [folder, size] of Object.entries(SIZES)) {
    const dir = path.join(androidRes, folder);
    fs.mkdirSync(dir, { recursive: true });

    await sharp(svg)
      .resize(size, size)
      .png()
      .toFile(path.join(dir, 'ic_launcher.png'));

    await sharp(svg)
      .resize(size, size)
      .png()
      .toFile(path.join(dir, 'ic_launcher_round.png'));

    console.log(`Generated ${folder} (${size}x${size})`);
  }

  // Adaptive icon foreground (512px)
  const adaptiveDir = path.join(androidRes, 'mipmap-xxxhdpi');
  await sharp(svg)
    .resize(432, 432)
    .png()
    .toFile(path.join(adaptiveDir, 'ic_launcher_foreground.png'));

  // Splash screen icon (centered on green bg)
  const splashDir = path.join(androidRes, 'drawable');
  fs.mkdirSync(splashDir, { recursive: true });
  await sharp({
    create: { width: 288, height: 288, channels: 4, background: { r: 14, g: 124, b: 102, alpha: 1 } },
  })
    .png()
    .composite([{ input: path.join(adaptiveDir, 'ic_launcher_foreground.png'), gravity: 'center' }])
    .toFile(path.join(splashDir, 'splash.png'));

  console.log('All icons generated.');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
