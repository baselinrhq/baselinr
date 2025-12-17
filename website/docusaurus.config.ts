import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const config: Config = {
  title: 'Baselinr',
  tagline: 'Open-source data quality and observability platform for SQL data warehouses',
  favicon: 'img/favicon.svg',

  // Future flags, see https://docusaurus.io/docs/api/docusaurus-config#future
  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
  },

  // Set the production url of your site here
  url: 'https://baselinr.io',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'baselinrhq', // Usually your GitHub org/user name.
  projectName: 'baselinr', // Usually your repo name.

  onBrokenLinks: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: '../docs',
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/baselinrhq/baselinr/tree/main/docs/',
          routeBasePath: 'docs',
        },
        blog: false, // Disable blog for now
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/baselinr-social-card.jpg',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Baselinr',
      logo: {
        alt: 'Baselinr Logo',
        src: 'img/favicon.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          href: 'https://demo.baselinr.io',
          label: 'Try Demo',
          position: 'right',
        },
        {
          href: 'https://github.com/baselinrhq/baselinr',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {
              label: 'Getting Started',
              to: '/docs/getting-started/QUICKSTART',
            },
            {
              label: 'Python SDK',
              to: '/docs/guides/PYTHON_SDK',
            },
            {
              label: 'API Reference',
              to: '/docs/reference/API_REFERENCE',
            },
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/baselinrhq/baselinr',
            },
            {
              label: 'Issues',
              href: 'https://github.com/baselinrhq/baselinr/issues',
            },
          ],
        },
        {
          title: 'Resources',
          items: [
            {
              label: 'Quality Studio Demo',
              href: 'https://demo.baselinr.io',
            },
            {
              label: 'Configuration Reference',
              to: '/docs/reference/CONFIG_REFERENCE',
            },
            {
              label: 'Best Practices',
              to: '/docs/guides/BEST_PRACTICES',
            },
            {
              label: 'Troubleshooting',
              to: '/docs/guides/TROUBLESHOOTING',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Baselinr. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'yaml', 'json', 'python', 'sql'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
