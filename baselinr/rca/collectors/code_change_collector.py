"""
Code change/deployment collector for RCA.

Supports multiple git platforms:
- GitHub webhooks
- GitLab webhooks
- Bitbucket webhooks
- Manual registration via API
"""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.engine import Engine

from ..models import CodeDeployment
from ..storage import RCAStorage

logger = logging.getLogger(__name__)


class CodeChangeCollector:
    """Collector for code changes and deployments."""

    def __init__(self, engine: Engine):
        """
        Initialize code change collector.

        Args:
            engine: SQLAlchemy engine for storage
        """
        self.engine = engine
        self.storage = RCAStorage(engine)

    def parse_github_webhook(self, payload: Dict[str, Any]) -> Optional[CodeDeployment]:
        """
        Parse GitHub push webhook payload.

        Args:
            payload: GitHub webhook payload

        Returns:
            CodeDeployment object or None
        """
        try:
            # GitHub push event
            if "commits" not in payload:
                logger.debug("Not a push event, skipping")
                return None

            ref = payload.get("ref", "")
            branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

            # Get commit info
            head_commit = payload.get("head_commit", {}) or {}
            commit_sha = head_commit.get("id") or payload.get("after")
            if not commit_sha:
                logger.warning("No commit SHA found in GitHub webhook")
                return None

            # Extract changed files from commits
            changed_files = set()
            for commit in payload.get("commits", []):
                changed_files.update(commit.get("added", []))
                changed_files.update(commit.get("modified", []))
                changed_files.update(commit.get("removed", []))

            # Determine affected pipelines based on file patterns
            affected_pipelines = self._infer_affected_pipelines(list(changed_files))

            # Determine deployment type
            deployment_type = self._infer_deployment_type(list(changed_files))

            deployment = CodeDeployment(
                deployment_id=f"github_{commit_sha[:8]}_{int(datetime.utcnow().timestamp())}",
                deployed_at=datetime.utcnow(),
                git_commit_sha=commit_sha,
                git_branch=branch,
                changed_files=list(changed_files),
                deployment_type=deployment_type,
                affected_pipelines=affected_pipelines,
                metadata={
                    "repository": payload.get("repository", {}).get("full_name"),
                    "pusher": payload.get("pusher", {}).get("name"),
                    "commit_message": head_commit.get("message"),
                    "commit_url": head_commit.get("url"),
                    "platform": "github",
                },
            )

            return deployment

        except Exception as e:
            logger.error(f"Failed to parse GitHub webhook: {e}")
            return None

    def parse_gitlab_webhook(self, payload: Dict[str, Any]) -> Optional[CodeDeployment]:
        """
        Parse GitLab push webhook payload.

        Args:
            payload: GitLab webhook payload

        Returns:
            CodeDeployment object or None
        """
        try:
            # GitLab push event
            if payload.get("object_kind") != "push":
                logger.debug("Not a push event, skipping")
                return None

            ref = payload.get("ref", "")
            branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

            commit_sha = payload.get("checkout_sha") or payload.get("after")
            if not commit_sha:
                logger.warning("No commit SHA found in GitLab webhook")
                return None

            # Extract changed files from commits
            changed_files = set()
            for commit in payload.get("commits", []):
                changed_files.update(commit.get("added", []))
                changed_files.update(commit.get("modified", []))
                changed_files.update(commit.get("removed", []))

            # Determine affected pipelines
            affected_pipelines = self._infer_affected_pipelines(list(changed_files))

            # Determine deployment type
            deployment_type = self._infer_deployment_type(list(changed_files))

            deployment = CodeDeployment(
                deployment_id=f"gitlab_{commit_sha[:8]}_{int(datetime.utcnow().timestamp())}",
                deployed_at=datetime.utcnow(),
                git_commit_sha=commit_sha,
                git_branch=branch,
                changed_files=list(changed_files),
                deployment_type=deployment_type,
                affected_pipelines=affected_pipelines,
                metadata={
                    "repository": payload.get("project", {}).get("path_with_namespace"),
                    "user_name": payload.get("user_name"),
                    "user_email": payload.get("user_email"),
                    "platform": "gitlab",
                },
            )

            return deployment

        except Exception as e:
            logger.error(f"Failed to parse GitLab webhook: {e}")
            return None

    def parse_bitbucket_webhook(self, payload: Dict[str, Any]) -> Optional[CodeDeployment]:
        """
        Parse Bitbucket push webhook payload.

        Args:
            payload: Bitbucket webhook payload

        Returns:
            CodeDeployment object or None
        """
        try:
            # Bitbucket push event
            push = payload.get("push", {})
            changes = push.get("changes", [])

            if not changes:
                logger.debug("No changes in push event, skipping")
                return None

            # Get first change (most recent)
            change = changes[0]
            new_commit = change.get("new", {})

            commit_sha = new_commit.get("target", {}).get("hash")
            branch = new_commit.get("name")

            # Bitbucket doesn't include file list in webhook, use placeholder
            changed_files: List[str] = []

            deployment = CodeDeployment(
                deployment_id=f"bitbucket_{commit_sha[:8]}_{int(datetime.utcnow().timestamp())}",
                deployed_at=datetime.utcnow(),
                git_commit_sha=commit_sha,
                git_branch=branch,
                changed_files=changed_files,
                deployment_type="code",
                affected_pipelines=[],
                metadata={
                    "repository": payload.get("repository", {}).get("full_name"),
                    "actor": payload.get("actor", {}).get("display_name"),
                    "platform": "bitbucket",
                    "note": "File list not available in Bitbucket webhook",
                },
            )

            return deployment

        except Exception as e:
            logger.error(f"Failed to parse Bitbucket webhook: {e}")
            return None

    def register_deployment(
        self,
        git_commit_sha: str,
        git_branch: str,
        changed_files: List[str],
        deployment_type: str = "code",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CodeDeployment:
        """
        Manually register a deployment.

        Args:
            git_commit_sha: Git commit SHA
            git_branch: Git branch name
            changed_files: List of changed file paths
            deployment_type: Type of deployment (code, schema, config)
            metadata: Additional metadata

        Returns:
            CodeDeployment object
        """
        affected_pipelines = self._infer_affected_pipelines(changed_files)

        deployment = CodeDeployment(
            deployment_id=str(uuid4()),
            deployed_at=datetime.utcnow(),
            git_commit_sha=git_commit_sha,
            git_branch=git_branch,
            changed_files=changed_files,
            deployment_type=deployment_type,
            affected_pipelines=affected_pipelines,
            metadata=metadata or {},
        )

        return deployment

    def _infer_affected_pipelines(self, changed_files: List[str]) -> List[str]:
        """
        Infer which pipelines are affected by file changes.

        Args:
            changed_files: List of changed file paths

        Returns:
            List of affected pipeline names
        """
        affected = set()

        for file_path in changed_files:
            file_lower = file_path.lower()

            # DBT models
            if "models/" in file_lower and file_lower.endswith(".sql"):
                affected.add("dbt")
                # Try to extract model name
                parts = file_path.split("/")
                for i, part in enumerate(parts):
                    if part == "models" and i + 1 < len(parts):
                        model_dir = parts[i + 1]
                        affected.add(f"dbt_{model_dir}")

            # Airflow DAGs
            if "dags/" in file_lower and file_lower.endswith(".py"):
                affected.add("airflow")
                # Try to extract DAG name from filename
                filename = file_path.split("/")[-1].replace(".py", "")
                affected.add(f"airflow_{filename}")

            # Dagster
            if ("dagster" in file_lower or "assets/" in file_lower) and file_lower.endswith(".py"):
                affected.add("dagster")

            # SQL scripts
            if file_lower.endswith(".sql") and "models/" not in file_lower:
                affected.add("sql_scripts")

            # Config files
            if file_lower.endswith((".yml", ".yaml", ".json")):
                if "dbt_project" in file_lower or "profiles" in file_lower:
                    affected.add("dbt")

        return list(affected)

    def _infer_deployment_type(self, changed_files: List[str]) -> str:
        """
        Infer deployment type from changed files.

        Args:
            changed_files: List of changed file paths

        Returns:
            Deployment type: 'code', 'schema', or 'config'
        """
        has_code = False
        has_schema = False
        has_config = False

        for file_path in changed_files:
            file_lower = file_path.lower()

            # Code changes
            if file_lower.endswith((".py", ".sql", ".js", ".ts")):
                has_code = True

            # Schema changes
            if "schema" in file_lower or "migration" in file_lower or file_lower.endswith(".ddl"):
                has_schema = True

            # Config changes
            if file_lower.endswith((".yml", ".yaml", ".json", ".toml", ".ini", ".env")):
                has_config = True

        # Prioritize by impact
        if has_schema:
            return "schema"
        elif has_code:
            return "code"
        elif has_config:
            return "config"
        else:
            return "code"  # Default

    def store_deployment(self, deployment: CodeDeployment) -> None:
        """
        Store deployment to database.

        Args:
            deployment: CodeDeployment to store
        """
        self.storage.write_code_deployment(deployment)
        logger.info(f"Stored deployment: {deployment.deployment_id}")

    def handle_webhook(
        self, payload: Dict[str, Any], platform: str, signature: Optional[str] = None
    ) -> Optional[CodeDeployment]:
        """
        Handle webhook from any supported platform.

        Args:
            payload: Webhook payload
            platform: Platform name ('github', 'gitlab', 'bitbucket')
            signature: Optional webhook signature for verification

        Returns:
            CodeDeployment object or None
        """
        # TODO: Add signature verification for security

        platform_lower = platform.lower()

        if platform_lower == "github":
            deployment = self.parse_github_webhook(payload)
        elif platform_lower == "gitlab":
            deployment = self.parse_gitlab_webhook(payload)
        elif platform_lower == "bitbucket":
            deployment = self.parse_bitbucket_webhook(payload)
        else:
            logger.warning(f"Unsupported platform: {platform}")
            return None

        if deployment:
            self.store_deployment(deployment)

        return deployment

    @staticmethod
    def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
        """
        Verify GitHub webhook signature.

        Args:
            payload: Raw webhook payload bytes
            signature: X-Hub-Signature-256 header value
            secret: Webhook secret

        Returns:
            True if signature is valid
        """
        if not signature.startswith("sha256="):
            return False

        expected_signature = "sha256=" + hashlib.sha256(secret.encode() + payload).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
