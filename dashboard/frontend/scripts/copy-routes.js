/**
 * Copy _routes.json to output directory after Next.js build
 * This ensures Cloudflare Pages can properly route static files
 */

const fs = require('fs');
const path = require('path');

const publicRoutesPath = path.join(__dirname, '..', 'public', '_routes.json');
const outRoutesPath = path.join(__dirname, '..', 'out', '_routes.json');
const outDir = path.join(__dirname, '..', 'out');

try {
  // Check if public/_routes.json exists
  if (!fs.existsSync(publicRoutesPath)) {
    console.warn('Warning: public/_routes.json not found');
    process.exit(0);
  }

  // Ensure out directory exists
  if (!fs.existsSync(outDir)) {
    console.error('Error: out directory does not exist. Run "next build" first.');
    process.exit(1);
  }

  // Copy the file
  fs.copyFileSync(publicRoutesPath, outRoutesPath);
  console.log('✓ Copied _routes.json to out/_routes.json');
} catch (error) {
  console.error('Error copying _routes.json:', error);
  process.exit(1);
}
