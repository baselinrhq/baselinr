import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Automated Setup',
    Svg: require('@site/static/img/undraw_docusaurus_profiling.svg').default,
    description: (
      <>
        Zero-touch configuration—automatically recommends tables and columns to monitor,
        suggests data quality checks, and can auto-apply configurations. Or configure
        everything manually with full control—your choice.
      </>
    ),
  },
  {
    title: 'Comprehensive Monitoring',
    Svg: require('@site/static/img/undraw_docusaurus_drift.svg').default,
    description: (
      <>
        Profile your data, detect schema and statistical drift, identify anomalies,
        validate data quality rules, and perform root cause analysis—all in one platform.
      </>
    ),
  },
  {
    title: 'Developer-First',
    Svg: require('@site/static/img/undraw_docusaurus_python.svg').default,
    description: (
      <>
        Built for data engineers who want transparency and control. CLI-first with Python SDK,
        YAML/JSON configuration, and native integrations with dbt, Dagster, and Airflow.
      </>
    ),
  },
];

function Feature({title, Svg, description}: FeatureItem) {
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

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
