"""
ODCS Contracts service for Baselinr Dashboard.

Handles contract loading, validation, and management operations.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Add parent directory to path to import baselinr
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

logger = logging.getLogger(__name__)


class ContractsService:
    """
    Service for managing ODCS data contracts.
    
    Handles loading contracts from disk, validation, and CRUD operations.
    """

    def __init__(self, contracts_dir: Optional[str] = None):
        """
        Initialize contracts service.
        
        Args:
            contracts_dir: Path to contracts directory (optional)
        """
        self._contracts_dir = contracts_dir
        self._contracts_cache: List[Dict[str, Any]] = []
        self._last_load_time: Optional[float] = None

    def set_contracts_dir(self, contracts_dir: str) -> None:
        """Set the contracts directory and clear cache."""
        self._contracts_dir = contracts_dir
        self._contracts_cache = []
        self._last_load_time = None

    def list_contracts(self) -> List[Dict[str, Any]]:
        """
        List all contracts as summaries.
        
        Returns:
            List of contract summary dictionaries
        """
        contracts = self._load_all_contracts()
        summaries = []
        
        for contract in contracts:
            summary = self._contract_to_summary(contract)
            summaries.append(summary)
        
        return summaries

    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific contract by ID.
        
        Args:
            contract_id: Contract ID or dataset name
            
        Returns:
            Contract dictionary or None if not found
        """
        contracts = self._load_all_contracts()
        
        for contract in contracts:
            # Match by contract ID
            if contract.get("id") == contract_id:
                return contract
            
            # Match by dataset name
            datasets = contract.get("dataset", [])
            if datasets:
                for ds in datasets:
                    if ds.get("name") == contract_id or ds.get("table") == contract_id:
                        return contract
                    if ds.get("physicalName") == contract_id:
                        return contract
        
        return None

    def validate_contracts(self, strict: bool = False) -> Dict[str, Any]:
        """
        Validate all loaded contracts.
        
        Args:
            strict: If True, treat warnings as errors
            
        Returns:
            Validation result dictionary
        """
        try:
            from baselinr.contracts import ODCSValidator, ODCSContract
        except ImportError:
            # Fall back to basic validation if baselinr not available
            return self._basic_validation()
        
        contracts = self._load_all_contracts()
        validator = ODCSValidator(strict=strict)
        
        result = {
            "valid": True,
            "contracts_checked": 0,
            "errors": [],
            "warnings": [],
        }
        
        for contract_data in contracts:
            result["contracts_checked"] += 1
            
            try:
                contract = ODCSContract(**contract_data)
                validation_result = validator.validate_full(contract)
                
                contract_name = contract_data.get("id") or "unnamed"
                
                if not validation_result.valid:
                    result["valid"] = False
                
                for error in validation_result.errors:
                    result["errors"].append({
                        "contract": contract_name,
                        "message": str(error),
                    })
                
                for warning in validation_result.warnings:
                    result["warnings"].append({
                        "contract": contract_name,
                        "message": str(warning),
                    })
            except Exception as e:
                result["valid"] = False
                result["errors"].append({
                    "contract": contract_data.get("id", "unknown"),
                    "message": f"Parse error: {str(e)}",
                })
        
        return result

    def get_validation_rules(
        self, contract_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get validation rules from contracts.
        
        Args:
            contract_id: Optional filter by contract ID
            
        Returns:
            List of validation rule dictionaries
        """
        try:
            from baselinr.contracts import ODCSAdapter, ODCSContract
        except ImportError:
            # Fall back to basic extraction
            return self._basic_rule_extraction(contract_id)
        
        contracts = self._load_all_contracts()
        adapter = ODCSAdapter()
        rules = []
        
        for contract_data in contracts:
            # Filter by contract ID if specified
            if contract_id and contract_data.get("id") != contract_id:
                continue
            
            try:
                contract = ODCSContract(**contract_data)
                contract_rules = adapter.to_validation_rules(contract)
                
                for rule in contract_rules:
                    rules.append({
                        "type": rule.type,
                        "table": rule.table,
                        "column": rule.column,
                        "severity": rule.severity,
                        "dimension": rule.dimension,
                        "description": rule.description,
                        "contract_id": rule.contract_id,
                    })
            except Exception as e:
                logger.warning(f"Failed to extract rules from contract: {e}")
        
        return rules

    def create_contract(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new contract.
        
        Args:
            contract: Contract dictionary
            
        Returns:
            Created contract dictionary
        """
        if not self._contracts_dir:
            raise ValueError("Contracts directory not configured")
        
        contracts_path = Path(self._contracts_dir)
        contracts_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from ID or create one
        contract_id = contract.get("id")
        if not contract_id:
            # Generate from dataset name
            datasets = contract.get("dataset", [])
            if datasets and datasets[0].get("name"):
                contract_id = datasets[0]["name"]
            else:
                import uuid
                contract_id = f"contract-{uuid.uuid4().hex[:8]}"
            contract["id"] = contract_id
        
        filename = f"{contract_id}.odcs.yaml"
        filepath = contracts_path / filename
        
        if filepath.exists():
            raise ValueError(f"Contract already exists: {contract_id}")
        
        # Write to file
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(contract, f, default_flow_style=False, sort_keys=False)
        
        # Clear cache
        self._contracts_cache = []
        
        return contract

    def update_contract(
        self, contract_id: str, contract: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing contract.
        
        Args:
            contract_id: Contract ID
            contract: Updated contract dictionary
            
        Returns:
            Updated contract dictionary
        """
        if not self._contracts_dir:
            raise ValueError("Contracts directory not configured")
        
        # Find existing contract file
        filepath = self._find_contract_file(contract_id)
        if not filepath:
            raise ValueError(f"Contract not found: {contract_id}")
        
        # Preserve the ID
        contract["id"] = contract_id
        
        # Write updated contract
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(contract, f, default_flow_style=False, sort_keys=False)
        
        # Clear cache
        self._contracts_cache = []
        
        return contract

    def delete_contract(self, contract_id: str) -> bool:
        """
        Delete a contract.
        
        Args:
            contract_id: Contract ID
            
        Returns:
            True if deleted
        """
        if not self._contracts_dir:
            raise ValueError("Contracts directory not configured")
        
        filepath = self._find_contract_file(contract_id)
        if not filepath:
            raise ValueError(f"Contract not found: {contract_id}")
        
        os.remove(filepath)
        
        # Clear cache
        self._contracts_cache = []
        
        return True

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _load_all_contracts(self) -> List[Dict[str, Any]]:
        """Load all contracts from disk."""
        if self._contracts_cache:
            return self._contracts_cache
        
        if not self._contracts_dir:
            return []
        
        contracts_path = Path(self._contracts_dir)
        if not contracts_path.exists():
            return []
        
        contracts = []
        patterns = ["*.odcs.yaml", "*.odcs.yml"]
        
        for pattern in patterns:
            for filepath in contracts_path.rglob(pattern):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        contract = yaml.safe_load(f)
                    if contract:
                        # Store source file for later updates
                        contract["_source_file"] = str(filepath)
                        contracts.append(contract)
                except Exception as e:
                    logger.warning(f"Failed to load contract {filepath}: {e}")
        
        self._contracts_cache = contracts
        return contracts

    def _contract_to_summary(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a contract to a summary dictionary."""
        info = contract.get("info", {})
        datasets = contract.get("dataset", [])
        quality = contract.get("quality", [])
        servicelevels = contract.get("servicelevels", [])
        stakeholders = contract.get("stakeholders", [])
        
        # Count quality rules including dataset-level
        total_quality_rules = len(quality)
        for ds in datasets:
            total_quality_rules += len(ds.get("quality", []))
            for col in ds.get("columns", []):
                total_quality_rules += len(col.get("quality", []))
        
        dataset_names = []
        for ds in datasets:
            name = ds.get("name") or ds.get("table")
            if name:
                dataset_names.append(name)
        
        return {
            "id": contract.get("id"),
            "title": info.get("title") if info else None,
            "status": contract.get("status"),
            "owner": info.get("owner") if info else None,
            "domain": info.get("domain") if info else None,
            "datasets": dataset_names,
            "quality_rules_count": total_quality_rules,
            "service_levels_count": len(servicelevels),
            "stakeholders_count": len(stakeholders),
        }

    def _find_contract_file(self, contract_id: str) -> Optional[Path]:
        """Find the file path for a contract."""
        contracts = self._load_all_contracts()
        
        for contract in contracts:
            if contract.get("id") == contract_id:
                source_file = contract.get("_source_file")
                if source_file:
                    return Path(source_file)
        
        return None

    def _basic_validation(self) -> Dict[str, Any]:
        """Basic validation without baselinr imports."""
        contracts = self._load_all_contracts()
        
        result = {
            "valid": True,
            "contracts_checked": 0,
            "errors": [],
            "warnings": [],
        }
        
        for contract in contracts:
            result["contracts_checked"] += 1
            contract_name = contract.get("id", "unnamed")
            
            # Check required fields
            if contract.get("kind") != "DataContract":
                result["errors"].append({
                    "contract": contract_name,
                    "message": "kind must be 'DataContract'",
                })
                result["valid"] = False
            
            if not contract.get("apiVersion"):
                result["warnings"].append({
                    "contract": contract_name,
                    "message": "Missing apiVersion",
                })
            
            if not contract.get("dataset"):
                result["warnings"].append({
                    "contract": contract_name,
                    "message": "No datasets defined",
                })
        
        return result

    def _basic_rule_extraction(
        self, contract_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Basic rule extraction without baselinr imports."""
        contracts = self._load_all_contracts()
        rules = []
        
        for contract in contracts:
            if contract_id and contract.get("id") != contract_id:
                continue
            
            cid = contract.get("id")
            
            # Contract-level quality rules
            for quality in contract.get("quality", []):
                rules.append({
                    "type": quality.get("rule") or quality.get("type", "check"),
                    "table": self._get_default_table(contract),
                    "column": quality.get("column"),
                    "severity": quality.get("severity", "error"),
                    "dimension": quality.get("dimension"),
                    "description": quality.get("description"),
                    "contract_id": cid,
                })
            
            # Dataset-level rules
            for ds in contract.get("dataset", []):
                table_name = ds.get("physicalName") or ds.get("name") or ds.get("table", "")
                
                for quality in ds.get("quality", []):
                    rules.append({
                        "type": quality.get("rule") or quality.get("type", "check"),
                        "table": table_name,
                        "column": quality.get("column"),
                        "severity": quality.get("severity", "error"),
                        "dimension": quality.get("dimension"),
                        "description": quality.get("description"),
                        "contract_id": cid,
                    })
        
        return rules

    def _get_default_table(self, contract: Dict[str, Any]) -> str:
        """Get default table name from contract."""
        datasets = contract.get("dataset", [])
        if datasets:
            ds = datasets[0]
            return ds.get("physicalName") or ds.get("name") or ds.get("table", "")
        return contract.get("datasetName", "")

