# Baselinr Website Deployment Guide

Guide for deploying the Baselinr documentation website to Cloudflare Pages.

## Overview

The Baselinr website is built with Docusaurus and deployed to Cloudflare Pages for fast, global CDN distribution.

**Production URL**: https://baselinr.io

## Quick Deploy

### Option 1: Git Integration (Recommended)

Cloudflare Pages will automatically build and deploy on every push to your repository.

1. **Connect repository in Cloudflare Dashboard**:
   - Go to https://dash.cloudflare.com
   - Navigate to Workers & Pages → Create application → Pages → Connect to Git
   - Select your repository and branch

2. **Configure build settings**:
   - **Root directory**: `website`
   - **Build command**: `npm ci && npm run build`
   - **Build output directory**: `build`
   - **Node version**: 20.x (or latest LTS)

3. **Deploy!** Cloudflare will automatically build and deploy on every push.

### Option 2: Manual Deployment

```bash
cd website
npm ci
npm run build
wrangler pages deploy build --project-name=baselinr-website
```

## Cloudflare Pages Dashboard Settings

### Build Settings

- **Root directory**: `website`
- **Build command**: `npm ci && npm run build`
- **Build output directory**: `build`
- **Node version**: 20 (configure in Build settings → Environment variables)

### Environment Variables

No environment variables needed for standard Docusaurus deployment.

### Custom Domain

To use a custom domain (e.g., `baselinr.io`):

1. Go to your Pages project → **Custom domains**
2. Add your domain
3. Cloudflare will automatically provision SSL
4. Update DNS records as instructed

### Build Watch Paths (Optional)

To only trigger builds when website code or documentation changes:

```
website/**
docs/**
```

**Important**: Include `docs/**` because the Docusaurus config sources documentation from `../docs`. Changes to documentation files will affect the website build.

This will prevent builds on changes to other parts of the repository (e.g., dashboard code, Python backend).

## Local Development

```bash
cd website
npm install
npm start
```

Visit http://localhost:3000

## Build Commands

- **Development**: `npm start` - Start dev server
- **Build**: `npm run build` - Build static site to `build/` directory
- **Serve**: `npm run serve` - Serve built site locally
- **Type check**: `npm run typecheck` - Run TypeScript checks

## Project Structure

```
website/
├── blog/                    # Blog posts (if enabled)
├── docs/                    # Documentation content (linked from ../docs)
├── src/
│   ├── components/          # React components
│   ├── css/                 # Custom styles
│   └── pages/               # Custom pages (homepage, etc.)
├── static/                  # Static assets (images, etc.)
├── docusaurus.config.ts     # Docusaurus configuration
├── sidebars.ts              # Documentation sidebar structure
├── package.json
└── wrangler.toml            # Cloudflare Pages config (for local dev)
```

## Troubleshooting

### Build fails with "Cannot find module"

Ensure `node_modules` are installed:
```bash
cd website
npm ci
```

### Build output directory incorrect

Verify Docusaurus builds to `build/` directory (default). Check `docusaurus.config.ts` doesn't override `outDir`.

### Custom domain not working

1. Check domain status in Cloudflare Pages dashboard
2. Verify DNS records point to Cloudflare
3. Wait 5-15 minutes for SSL certificate provisioning
4. Ensure domain is added to your Cloudflare account

### Build takes too long

- Use build watch paths to only build on website changes
- Enable build caching in Cloudflare Pages settings
- Consider using `.nvmrc` to specify Node version

## CI/CD Integration

Cloudflare Pages automatically builds on git push when connected via Git integration. No additional CI/CD setup needed.

For advanced workflows, you can use GitHub Actions with `cloudflare/pages-action`:

```yaml
- name: Deploy to Cloudflare Pages
  uses: cloudflare/pages-action@v1
  with:
    apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
    projectName: baselinr-website
    directory: website/build
```

## Related Documentation

- [Docusaurus Deployment Guide](https://docusaurus.io/docs/deployment)
- [Cloudflare Pages Docs](https://developers.cloudflare.com/pages/)
- [Dashboard Demo Deployment](../dashboard/frontend/DEPLOYMENT.md)


