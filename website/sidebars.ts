import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

/**
 * Sidebar configuration for Baselinr documentation.
 * 
 * This explicitly defines the sidebar structure to ensure all guides
 * and documentation are accessible on the website.
 */
const sidebars: SidebarsConfig = {
  docsSidebar: [
    // Getting Started
    {
      type: 'category',
      label: 'Getting Started',
      items: [
        'getting-started/QUICKSTART',
        'getting-started/INSTALL',
      ],
    },
    
    // Core Guides
    {
      type: 'category',
      label: 'Guides',
      items: [
        // Automated Setup & Smart Selection
        {
          type: 'category',
          label: 'Automated Setup',
          items: [
            'guides/SMART_SELECTION_QUICKSTART',
            'guides/SMART_TABLE_SELECTION',
            'guides/COLUMN_RECOMMENDATION',
          ],
        },
        
        // Data Quality
        {
          type: 'category',
          label: 'Data Quality',
          items: [
            'guides/DATA_VALIDATION',
            'guides/DRIFT_DETECTION',
            'guides/STATISTICAL_DRIFT_DETECTION',
            'guides/ANOMALY_DETECTION',
            'guides/EXPECTATION_LEARNING',
            'guides/SCHEMA_CHANGE_DETECTION',
          ],
        },
        
        // Root Cause & Lineage
        {
          type: 'category',
          label: 'Root Cause & Lineage',
          items: [
            'guides/ROOT_CAUSE_ANALYSIS',
            'guides/DATA_LINEAGE',
            'lineage-visualization',
          ],
        },
        
        // AI & Chat
        {
          type: 'category',
          label: 'AI Chat Assistant',
          items: [
            'chat/GETTING_STARTED',
            'chat/EXAMPLES',
            'chat/TOOLS',
            'chat/ADVANCED',
          ],
        },
        
        // LLM Configuration
        {
          type: 'category',
          label: 'LLM Configuration',
          items: [
            'llm/CONFIGURATION',
            'llm/PROVIDERS',
            'llm/PROMPTS',
          ],
        },
        
        // Profiling
        {
          type: 'category',
          label: 'Profiling',
          items: [
            'guides/PROFILING_ENRICHMENT',
            'guides/COLUMN_LEVEL_CONFIGS',
            'guides/PARTITION_SAMPLING',
            'guides/INCREMENTAL_PROFILING',
            'guides/PARALLELISM_AND_BATCHING',
          ],
        },
        
        // Integrations
        {
          type: 'category',
          label: 'Integrations',
          items: [
            'guides/DBT_INTEGRATION',
            'guides/DAGSTER_INTEGRATION',
            'guides/AIRFLOW_INTEGRATION',
            'guides/AIRFLOW_QUICKSTART',
          ],
        },
        
        // Python SDK
        'guides/PYTHON_SDK',
        
        // Operations
        {
          type: 'category',
          label: 'Operations',
          items: [
            'guides/SLACK_ALERTS',
            'guides/SLACK_ALERTS_QUICKSTART',
            'guides/PROMETHEUS_METRICS',
            'guides/RETRY_AND_RECOVERY',
            'guides/RETRY_QUICK_START',
          ],
        },
      ],
    },
    
    // Dashboard
    {
      type: 'category',
      label: 'Dashboard',
      items: [
        'dashboard/QUICKSTART',
        'dashboard/README',
        {
          type: 'link',
          label: '🔄 Try Quality Studio Demo',
          href: 'https://demo.baselinr.io',
        },
        'dashboard/ARCHITECTURE',
        'dashboard/DASHBOARD_INTEGRATION',
        'dashboard/SETUP_COMPLETE',
        {
          type: 'category',
          label: 'Backend',
          items: [
            'dashboard/backend/README',
            'dashboard/backend/DAGSTER',
          ],
        },
        {
          type: 'category',
          label: 'Frontend',
          items: [
            'dashboard/frontend/README',
          ],
        },
      ],
    },
    
    // Schemas & CLI
    {
      type: 'category',
      label: 'Schemas & CLI',
      items: [
        'schemas/QUERY_EXAMPLES',
        'schemas/STATUS_COMMAND',
        'schemas/UI_COMMAND',
        'schemas/SCHEMA_REFERENCE',
        'schemas/MIGRATION_GUIDE',
      ],
    },
    
    // Architecture
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/PROJECT_OVERVIEW',
        'architecture/EVENTS_AND_HOOKS',
        'architecture/ANOMALY_DETECTION',
        'architecture/EXPECTATION_LEARNING',
      ],
    },
    
    // Development
    {
      type: 'category',
      label: 'Development',
      items: [
        'development/DEVELOPMENT',
        'development/GIT_HOOKS',
        'development/DBT_TESTING',
      ],
    },
    
    // Docker
    {
      type: 'category',
      label: 'Docker',
      items: [
        'docker/README_METRICS',
        'docker/README_DBT',
      ],
    },
  ],
};

export default sidebars;
