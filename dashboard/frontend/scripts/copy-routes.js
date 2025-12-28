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

  // Ensure demo_data files are copied (Next.js should copy from public/, but if not, do it manually)
  const publicDemoDataDir = path.join(__dirname, '..', 'public', 'demo_data');
  const outDemoDataDir = path.join(outDir, 'demo_data');
  
  if (!fs.existsSync(outDemoDataDir)) {
    // Next.js didn't copy them, try to copy from public/ if they exist
    if (fs.existsSync(publicDemoDataDir)) {
      console.log('⚠ Next.js did not copy demo_data files, copying manually...');
      fs.mkdirSync(outDemoDataDir, { recursive: true });
      
      const files = fs.readdirSync(publicDemoDataDir);
      let copiedCount = 0;
      for (const file of files) {
        if (file.endsWith('.json')) {
          const srcPath = path.join(publicDemoDataDir, file);
          const destPath = path.join(outDemoDataDir, file);
          fs.copyFileSync(srcPath, destPath);
          copiedCount++;
        }
      }
      console.log(`✓ Copied ${copiedCount} demo_data files to out/demo_data/`);
    } else {
      console.warn('⚠ Warning: public/demo_data/ directory not found. Demo data files may not be accessible.');
      console.warn('  Note: These files may be gitignored. Ensure they are committed or generated during build.');
    }
  } else {
    // Files were already copied by Next.js
    const files = fs.readdirSync(outDemoDataDir);
    console.log(`✓ Found ${files.length} demo_data files in out/demo_data/`);
    if (files.length > 0) {
      console.log(`  Files: ${files.slice(0, 5).join(', ')}${files.length > 5 ? '...' : ''}`);
    }
  }

  // Copy functions directory to out/functions for Cloudflare Pages
  const functionsDir = path.join(__dirname, '..', 'functions');
  const outFunctionsDir = path.join(outDir, 'functions');
  
  if (fs.existsSync(functionsDir)) {
    console.log('Copying functions directory to out/functions...');
    
    // Recursive copy function
    function copyRecursive(src, dest) {
      const exists = fs.existsSync(src);
      const stats = exists && fs.statSync(src);
      const isDirectory = exists && stats.isDirectory();
      
      if (isDirectory) {
        if (!fs.existsSync(dest)) {
          fs.mkdirSync(dest, { recursive: true });
        }
        fs.readdirSync(src).forEach(childItemName => {
          copyRecursive(
            path.join(src, childItemName),
            path.join(dest, childItemName)
          );
        });
      } else {
        fs.copyFileSync(src, dest);
      }
    }
    
    // Remove existing functions directory if it exists
    if (fs.existsSync(outFunctionsDir)) {
      fs.rmSync(outFunctionsDir, { recursive: true, force: true });
    }
    
    copyRecursive(functionsDir, outFunctionsDir);
    console.log('✓ Copied functions directory to out/functions/');
  } else {
    console.warn('⚠ Warning: functions/ directory not found. Cloudflare Pages Functions may not work.');
  }
} catch (error) {
  console.error('Error generating _routes.json:', error);
  process.exit(1);
}
