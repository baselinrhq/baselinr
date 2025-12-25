/**
 * Generate _routes.json in output directory after Next.js build
 * This ensures Cloudflare Pages can properly route static files
 */

const fs = require('fs');
const path = require('path');

const outRoutesPath = path.join(__dirname, '..', 'out', '_routes.json');
const outDir = path.join(__dirname, '..', 'out');

try {
  // Ensure out directory exists
  if (!fs.existsSync(outDir)) {
    console.error('Error: out directory does not exist. Run "next build" first.');
    process.exit(1);
  }

  // Generate _routes.json directly
  const routesConfig = {
    version: 1,
    include: ['/*'],
    exclude: ['/demo_data/*']
  };

  fs.writeFileSync(outRoutesPath, JSON.stringify(routesConfig, null, 2));
  console.log('✓ Generated _routes.json in out/_routes.json');
} catch (error) {
  console.error('Error generating _routes.json:', error);
  process.exit(1);
}
