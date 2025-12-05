import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import Features from '@site/src/components/Features';

import styles from './index.module.css';

export default function FeaturesPage(): ReactNode {
  return (
    <Layout
      title="Features"
      description="Comprehensive data quality and observability features. Automated setup, profiling, drift detection, anomaly detection, validation, root cause analysis, and AI-powered investigation.">
      <header className={clsx('hero hero--primary', styles.heroBanner)}>
        <div className="container">
          <Heading as="h1" className="hero__title">
            Powerful Features for Data Quality
          </Heading>
          <p className="hero__subtitle">
            Everything you need for data quality and observability in your SQL data warehouses.
            From automated setup to AI-powered root cause analysis, Baselinr has you covered.
          </p>
          <div className={styles.buttons}>
            <Link
              className="button button--secondary button--lg"
              to="/docs/getting-started/QUICKSTART">
              Get Started
            </Link>
            <Link
              className="button button--outline button--secondary button--lg"
              to="/docs/getting-started/QUICKSTART"
              style={{marginLeft: '1rem'}}>
              View Documentation
            </Link>
          </div>
        </div>
      </header>

      <main>
        <Features />
        <section className="margin-vert--xl padding-vert--xl" style={{
          background: 'var(--ifm-color-primary)',
          borderRadius: '8px',
          textAlign: 'center',
        }}>
          <div className="container">
            <Heading as="h2">Ready to Get Started?</Heading>
            <p className="margin-bottom--lg">
              Join developers building better data quality monitoring with Baselinr.
            </p>
            <div className={styles.buttons}>
              <Link
                className="button button--secondary button--lg"
                to="/docs/getting-started/QUICKSTART">
                View Full Documentation
              </Link>
              <Link
                className="button button--outline button--secondary button--lg"
                href="https://github.com/baselinrhq/baselinr"
                style={{marginLeft: '1rem'}}>
                View on GitHub
              </Link>
            </div>
          </div>
        </section>
      </main>
    </Layout>
  );
}

