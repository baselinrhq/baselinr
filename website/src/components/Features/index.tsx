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
    Svg: require('@site/static/img/undraw_statistical_tests.svg').default,
    title: 'Advanced Statistical Tests',
    description: (
      <>
        Kolmogorov-Smirnov (KS) test, Population Stability Index (PSI), Chi-square,
        Entropy, and more for rigorous drift detection. Type-specific thresholds reduce
        false positives.
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
    Svg: require('@site/static/img/undraw_multi_database.svg').default,
    title: 'Multi-Database Support',
    description: (
      <>
        Works seamlessly with PostgreSQL, Snowflake, SQLite, MySQL, BigQuery, and Redshift.
        Unified API across all supported databases.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_web_dashboard.svg').default,
    title: 'Web Dashboard',
    description: (
      <>
        Lightweight local web dashboard (FastAPI + Next.js) for visualizing profiling runs
        and drift detection. Get insights at a glance.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_cli_api.svg').default,
    title: 'CLI & API',
    description: (
      <>
        Comprehensive command-line interface and powerful querying API for profiling runs,
        drift events, and table history. Perfect for automation and integration.
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
];

const UseCases: FeatureItem[] = [
  {
    Svg: require('@site/static/img/undraw_data_quality_monitoring.svg').default,
    title: 'Data Quality Monitoring',
    description: (
      <>
        Track data quality metrics over time and automatically detect when data quality
        degrades. Set up alerts for critical drift events.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_schema_change.svg').default,
    title: 'Schema Change Detection',
    description: (
      <>
        Automatically detect schema changes in your databases. Get notified when columns
        are added, removed, or modified.
      </>
    ),
  },
  {
    Svg: require('@site/static/img/undraw_statistical_drift_use_case.svg').default,
    title: 'Statistical Drift Detection',
    description: (
      <>
        Identify statistical anomalies in your data using advanced tests. Detect distribution
        shifts, value range changes, and frequency variations.
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
};

function FeaturesSection({title, description, features, showHeader = true, alternateBackground = false, leftAligned = false, extraPadding = false}: FeaturesSectionProps & {showHeader?: boolean; alternateBackground?: boolean; leftAligned?: boolean; extraPadding?: boolean}) {
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
        title="Built for Production"
        description="Every feature is designed to meet the demands of production workloads and enterprise requirements."
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

