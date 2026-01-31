"""
Cache Manager - Intelligent caching and incremental builds

Tracks input changes and skips expensive operations when possible.
Uses content-based hashing to detect changes.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List


class CacheManager:
    """Manages caching and incremental builds for the video pipeline."""

    def __init__(self, output_dir: Path):
        """
        Initialize cache manager.

        Args:
            output_dir: Path to output directory
        """
        self.output_dir = Path(output_dir)
        self.manifest_path = self.output_dir / 'cache_manifest.json'
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        """Load existing manifest or create new one."""
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r') as f:
                return json.load(f)

        return {
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'inputs': {},
            'stages': {},
            'costs': {
                'total': 0.0,
                'by_stage': {}
            }
        }

    def _save_manifest(self):
        """Save manifest to disk."""
        self.manifest['updated_at'] = datetime.now().isoformat()
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)

    def _hash_file(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        if not Path(file_path).exists():
            return "file_not_found"

        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()[:12]  # First 12 chars for brevity

    def _hash_string(self, text: str) -> str:
        """
        Calculate SHA256 hash of string.

        Args:
            text: String to hash

        Returns:
            Hex digest of string hash
        """
        return hashlib.sha256(text.encode()).hexdigest()[:12]

    def _hash_params(self, params: Dict[str, Any]) -> str:
        """
        Calculate hash of parameters dictionary.

        Args:
            params: Dictionary of parameters

        Returns:
            Hash of sorted JSON representation
        """
        # Sort keys for consistent hashing
        json_str = json.dumps(params, sort_keys=True)
        return self._hash_string(json_str)

    def register_input_file(self, name: str, file_path: Optional[str]) -> str:
        """
        Register an input file and calculate its hash.

        Args:
            name: Name of the input (e.g., 'text_file', 'art_reference')
            file_path: Path to input file (can be None)

        Returns:
            Hash of the file
        """
        if file_path is None:
            hash_value = "not_provided"
        else:
            hash_value = self._hash_file(file_path)

        # Store in manifest
        self.manifest['inputs'][name] = {
            'path': str(file_path) if file_path else None,
            'hash': hash_value,
            'updated_at': datetime.now().isoformat()
        }

        return hash_value

    def register_params(self, stage: str, params: Dict[str, Any]) -> str:
        """
        Register stage parameters.

        Args:
            stage: Stage name (e.g., 'scene_generation')
            params: Dictionary of parameters

        Returns:
            Hash of parameters
        """
        param_hash = self._hash_params(params)

        if stage not in self.manifest['stages']:
            self.manifest['stages'][stage] = {}

        self.manifest['stages'][stage]['params'] = params
        self.manifest['stages'][stage]['param_hash'] = param_hash

        return param_hash

    def check_stage_cache(self, stage: str, output_files: List[str]) -> bool:
        """
        Check if stage can be skipped (cached).

        Args:
            stage: Stage name
            output_files: List of expected output files

        Returns:
            True if stage can be skipped, False otherwise
        """
        # Check if stage exists in manifest
        if stage not in self.manifest['stages']:
            return False

        stage_data = self.manifest['stages'][stage]

        # Check if all output files exist
        for file_path in output_files:
            if not Path(file_path).exists():
                return False

        # Check if stage completed successfully
        if stage_data.get('status') != 'completed':
            return False

        return True

    def mark_stage_start(self, stage: str, params: Dict[str, Any]):
        """
        Mark stage as started.

        Args:
            stage: Stage name
            params: Stage parameters
        """
        param_hash = self.register_params(stage, params)

        if stage not in self.manifest['stages']:
            self.manifest['stages'][stage] = {}

        self.manifest['stages'][stage]['status'] = 'running'
        self.manifest['stages'][stage]['started_at'] = datetime.now().isoformat()
        self.manifest['stages'][stage]['param_hash'] = param_hash

        self._save_manifest()

    def mark_stage_complete(self, stage: str,
                          output_files: List[str],
                          cost: float = 0.0,
                          metadata: Optional[Dict] = None):
        """
        Mark stage as completed.

        Args:
            stage: Stage name
            output_files: List of output files produced
            cost: Estimated cost of this stage
            metadata: Additional metadata to store
        """
        if stage not in self.manifest['stages']:
            self.manifest['stages'][stage] = {}

        # Calculate output hashes
        output_hashes = {}
        for file_path in output_files:
            if Path(file_path).exists():
                output_hashes[file_path] = self._hash_file(file_path)

        self.manifest['stages'][stage]['status'] = 'completed'
        self.manifest['stages'][stage]['completed_at'] = datetime.now().isoformat()
        self.manifest['stages'][stage]['output_files'] = output_files
        self.manifest['stages'][stage]['output_hashes'] = output_hashes
        self.manifest['stages'][stage]['cost'] = cost

        if metadata:
            self.manifest['stages'][stage]['metadata'] = metadata

        # Update total cost
        self.manifest['costs']['total'] += cost
        self.manifest['costs']['by_stage'][stage] = \
            self.manifest['costs']['by_stage'].get(stage, 0.0) + cost

        self._save_manifest()

    def mark_stage_failed(self, stage: str, error: str):
        """
        Mark stage as failed.

        Args:
            stage: Stage name
            error: Error message
        """
        if stage not in self.manifest['stages']:
            self.manifest['stages'][stage] = {}

        self.manifest['stages'][stage]['status'] = 'failed'
        self.manifest['stages'][stage]['failed_at'] = datetime.now().isoformat()
        self.manifest['stages'][stage]['error'] = error

        self._save_manifest()

    def invalidate_stage(self, stage: str, reason: str):
        """
        Invalidate a stage (force rerun).

        Args:
            stage: Stage name
            reason: Reason for invalidation
        """
        if stage in self.manifest['stages']:
            self.manifest['stages'][stage]['status'] = 'invalidated'
            self.manifest['stages'][stage]['invalidation_reason'] = reason
            self.manifest['stages'][stage]['invalidated_at'] = datetime.now().isoformat()

        self._save_manifest()

    def get_stage_status(self, stage: str) -> Optional[str]:
        """
        Get status of a stage.

        Args:
            stage: Stage name

        Returns:
            Status string or None if stage not found
        """
        if stage not in self.manifest['stages']:
            return None

        return self.manifest['stages'][stage].get('status')

    def get_total_cost(self) -> float:
        """Get total cost of all operations."""
        return self.manifest['costs']['total']

    def get_stage_cost(self, stage: str) -> float:
        """Get cost of a specific stage."""
        return self.manifest['costs']['by_stage'].get(stage, 0.0)

    def has_input_changed(self, name: str, current_path: Optional[str]) -> bool:
        """
        Check if an input file has changed.

        Args:
            name: Input name
            current_path: Current file path

        Returns:
            True if changed, False otherwise
        """
        if name not in self.manifest['inputs']:
            return True  # New input

        old_hash = self.manifest['inputs'][name]['hash']

        if current_path is None:
            new_hash = "not_provided"
        else:
            new_hash = self._hash_file(current_path)

        return old_hash != new_hash

    def has_params_changed(self, stage: str, current_params: Dict[str, Any]) -> bool:
        """
        Check if stage parameters have changed.

        Args:
            stage: Stage name
            current_params: Current parameters

        Returns:
            True if changed, False otherwise
        """
        if stage not in self.manifest['stages']:
            return True  # New stage

        old_hash = self.manifest['stages'][stage].get('param_hash')
        new_hash = self._hash_params(current_params)

        return old_hash != new_hash

    def generate_status_report(self, stages: List[str]) -> str:
        """
        Generate a human-readable status report.

        Args:
            stages: List of stage names in order

        Returns:
            Formatted status report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("CACHE STATUS REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Input status
        lines.append("Input Files:")
        for name, data in self.manifest['inputs'].items():
            status = "✓" if data['hash'] != "file_not_found" else "✗"
            lines.append(f"  {status} {name:20s} hash: {data['hash']}")
        lines.append("")

        # Stage status
        lines.append("Stages:")
        status_symbols = {
            'completed': '✓',
            'running': '⟳',
            'failed': '✗',
            'invalidated': '⚠',
            None: '⊗'
        }

        for stage in stages:
            status = self.get_stage_status(stage)
            symbol = status_symbols.get(status, '?')

            stage_data = self.manifest['stages'].get(stage, {})
            cost = stage_data.get('cost', 0.0)
            cost_str = f"${cost:.2f}" if cost > 0 else "-"

            lines.append(f"  [{symbol}] {stage:25s} {cost_str:>8s}  {status or 'pending'}")

        lines.append("")
        lines.append(f"Total Cost: ${self.get_total_cost():.2f}")
        lines.append("=" * 80)

        return "\n".join(lines)
