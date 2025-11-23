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
    title: 'Automated Data Profiling',
    Svg: require('@site/static/img/undraw_docusaurus_profiling.svg').default,
    description: (
      <>
        Automatically profile your data sources and detect data quality issues,
        schema changes, and statistical anomalies with minimal configuration.
      </>
    ),
  },
  {
    title: 'Drift Detection',
    Svg: require('@site/static/img/undraw_docusaurus_drift.svg').default,
    description: (
      <>
        Continuously monitor your data for statistical drift and changes over time.
        Get alerted when data quality degrades or unexpected patterns emerge.
      </>
    ),
  },
  {
    title: 'Python-First',
    Svg: require('@site/static/img/undraw_docusaurus_python.svg').default,
    description: (
      <>
        Built for Python data teams. Easy integration with SQLAlchemy
        and popular data orchestration tools like Dagster and dbt.
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
