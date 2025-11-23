import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import HomepageFeatures from '@site/src/components/HomepageFeatures';
import Features from '@site/src/components/Features';
import Heading from '@theme/Heading';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/getting-started/QUICKSTART">
            Get Started - 5min ⏱️
          </Link>
          <Link
            className="button button--outline button--secondary button--lg"
            to="/docs/guides/PYTHON_SDK"
            style={{marginLeft: '1rem'}}>
            Python SDK →
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="Modern data profiling and drift detection framework for Python. Automatically detect data quality issues, schema changes, and statistical anomalies.">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
        <Features />
        <section className="margin-vert--xl" style={{
          background: 'var(--ifm-color-primary)',
          textAlign: 'center',
          paddingTop: '4rem',
          paddingBottom: '4rem',
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
