import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: ReactNode;
};

const CoreFeatures: FeatureItem[] = [
  {
    Svg: require('@site/static/img/undraw_docusaurus_profiling.svg').default,
    title: 'Automated Profiling',
    description: (
      <>
        Continuously profile your data warehouse with column-level metrics, distributions,
        and schema tracking. Intelligent table discovery reduces configuration overhead.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_docusaurus_drift.svg').default,
    title: 'Drift Detection',
    description: (
      <>
        Detect schema and statistical drift using multiple strategies with type-specific
        thresholds. Advanced statistical tests (KS, PSI, Chi-square) for rigorous detection.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_anomaly_detection.svg').default,
    title: 'Anomaly Detection',
    description: (
      <>
        Automatically detect outliers and seasonal anomalies using learned expectations
        with multiple detection methods (IQR, MAD, EWMA, trend/seasonality, regime shift).
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_data_quality_monitoring.svg').default,
    title: 'Data Validation',
    description: (
      <>
        Rule-based data quality validation with built-in validators for format, range, enum,
        null checks, uniqueness, and referential integrity. Custom validators supported.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_statistical_tests.svg').default,
    title: 'Root Cause Analysis',
    description: (
      <>
        Automatically correlate anomalies with pipeline runs, code changes, and upstream data
        issues using temporal correlation, lineage analysis, and pattern matching.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_multi_database.svg').default,
    title: 'Multi-Database Support',
    description: (
      <>
        Works seamlessly with PostgreSQL, Snowflake, SQLite, MySQL, BigQuery, and Redshift.
        Unified API across all supported databases.
      </>
    ),
  },
];

const ProductionFeatures: FeatureItem[] = [
  {
    Svg: require('@site/static/img/undraw_expectation_learning.svg').default,
    title: 'Expectation Learning',
    description: (
      <>
        Automatically learns expected metric ranges from historical profiling data,
        including control limits, distributions, and categorical frequencies for proactive
        anomaly detection.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_web_dashboard.svg').default,
    title: 'Web Dashboard & AI Chat',
    description: (
      <>
        Interactive web dashboard for visualizing profiling runs and drift detection.
        AI-powered chat interface for natural language data quality investigation.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_cli_api.svg').default,
    title: 'CLI & Python SDK',
    description: (
      <>
        Comprehensive command-line interface and powerful Python SDK for programmatic access.
        Perfect for automation, integration, and custom workflows.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_event_alerts.svg').default,
    title: 'Event & Alert Hooks',
    description: (
      <>
        Pluggable event system for real-time alerts and notifications on drift, schema
        changes, anomalies, and profiling lifecycle events. Integrate with Slack, email,
        or custom systems.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_partition_profiling.svg').default,
    title: 'Partition-Aware Profiling',
    description: (
      <>
        Intelligent partition handling with strategies for latest, recent_n, or sample
        partitions. Optimize profiling for large partitioned datasets.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_docusaurus_tree.svg').default,
    title: 'Data Lineage',
    description: (
      <>
        Multi-source lineage extraction from dbt, Dagster, SQL parsing, and query history.
        Visual lineage graphs with interactive exploration and drift impact analysis.
      </>
    ),
  },
];

const UseCases: FeatureItem[] = [
  {
    Svg: require('@site/static/img/undraw_data_quality_monitoring.svg').default,
    title: 'Automated Data Quality Setup',
    description: (
      <>
        Turn on comprehensive data quality monitoring with minimal effort. System automatically
        recommends tables and columns, suggests checks, and can auto-apply configurations.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_schema_change.svg').default,
    title: 'Root Cause Investigation',
    description: (
      <>
        When anomalies occur, automatically correlate with pipeline runs, code changes, and
        upstream data issues to identify root causes. AI-powered chat for interactive investigation.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_statistical_drift_use_case.svg').default,
    title: 'Pipeline Integration',
    description: (
      <>
        Integrate with Airflow, Dagster, and dbt to validate data quality in your pipelines.
        Fail builds when critical issues are detected. Native orchestration support.
      </>
    ),
  },
];

function Feature({Svg, title, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

function FeatureLeftAligned({Svg, title, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4', styles.featureBox)} style={{flex: '1 1 0'}}>
      <div className={styles.featureBoxHeader}>
        <Svg className={styles.featureSvg} role="img" />
        <Heading as="h3" className={styles.featureTitle}>{title}</Heading>
      </div>
      <div className={styles.featureDescription}>
        <p>{description}</p>
      </div>
    </div>
  );
}

type FeaturesSectionProps = {
  title: string;
  description: string;
  features: FeatureItem[];
  showHeader?: boolean;
  alternateBackground?: boolean;
  leftAligned?: boolean;
  extraPadding?: boolean;
};

function FeaturesSection({title, description, features, showHeader = true, alternateBackground = false, leftAligned = false, extraPadding = false}: FeaturesSectionProps) {
  return (
    <section 
      className={clsx(styles.features, alternateBackground && styles.featuresAlternate, extraPadding && styles.featuresExtraPadding)}>
      <div className="container">
        {showHeader && (
          <>
            <Heading as="h2" className="text--center margin-bottom--sm">
              {title}
            </Heading>
            <p className="text--center margin-bottom--lg padding-horiz--md">
              {description}
            </p>
          </>
        )}
        <div className={clsx('row', styles.featuresRow)}>
          {features.map((props, idx) => (
            leftAligned ? (
              <FeatureLeftAligned key={idx} {...props} />
            ) : (
              <Feature key={idx} {...props} />
            )
          ))}
        </div>
      </div>
    </section>
  );
}

export default function Features(): ReactNode {
  return (
    <>
      <FeaturesSection
        title=""
        description=""
        features={CoreFeatures}
        showHeader={false}
        alternateBackground={true}
      />
      <FeaturesSection
        title="Production-Ready Features"
        description="Every feature is designed to meet the demands of production workloads with enterprise-grade capabilities."
        features={ProductionFeatures}
        leftAligned={true}
        extraPadding={true}
      />
      <FeaturesSection
        title="Use Cases"
        description="See how teams are using Baselinr to solve real-world data quality challenges."
        features={UseCases}
        alternateBackground={true}
      />
    </>
  );
}

