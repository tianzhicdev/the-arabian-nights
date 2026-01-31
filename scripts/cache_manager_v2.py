"""
Cache Manager V2 - Deterministic caching with output validation

Key improvements:
1. Deterministic output path calculation from input hashes
2. Automatic output discovery (no manual file lists)
3. Output validation against input fingerprint
4. Stage fingerprint stored in outputs
"""

import json
import hashlib
import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Set


class StageFingerprint:
    """
    Represents the unique fingerprint of a stage's inputs and parameters.

    This is what determines if we can use cached results:
    - If fingerprint matches → use cache
    - If fingerprint differs → regenerate
    """

    def __init__(self, stage_name: str, inputs: Dict[str, str], params: Dict[str, Any]):
        """
        Initialize fingerprint.

        Args:
            stage_name: Name of the stage
            inputs: Dictionary of input names to file hashes
            params: Dictionary of parameters
        """
        self.stage_name = stage_name
        self.inputs = inputs
        self.params = params
        self.hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """Calculate deterministic hash of inputs and params."""
        # Sort everything for deterministic hashing
        data = {
            'stage': self.stage_name,
            'inputs': dict(sorted(self.inputs.items())),
            'params': dict(sorted(self.params.items()))
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]  # 16 chars

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'stage_name': self.stage_name,
            'inputs': self.inputs,
            'params': self.params,
            'hash': self.hash
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'StageFingerprint':
        """Create from dictionary."""
        return cls(data['stage_name'], data['inputs'], data['params'])

    def __eq__(self, other) -> bool:
        """Check if two fingerprints are equal."""
        if not isinstance(other, StageFingerprint):
            return False
        return self.hash == other.hash

    def __str__(self) -> str:
        return f"{self.stage_name}:{self.hash[:8]}"


class CacheManagerV2:
    """
    Improved cache manager with deterministic validation.

    Key improvements:
    1. Automatic output discovery (scan directories)
    2. Fingerprint-based validation (stored with outputs)
    3. No manual file list maintenance
    4. Robust cache hit/miss detection
    """

    def __init__(self, output_dir: Path):
        """
        Initialize cache manager.

        Args:
            output_dir: Path to output directory
        """
        self.output_dir = Path(output_dir)
        self.manifest_path = self.output_dir / 'cache_manifest_v2.json'
        self.manifest = self._load_manifest()

        # Track input file hashes
        self.input_hashes: Dict[str, str] = {}

    def _load_manifest(self) -> Dict[str, Any]:
        """Load existing manifest or create new one."""
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r') as f:
                return json.load(f)

        return {
            'version': '2.0',
            'created_at': datetime.now().isoformat(),
            'stages': {},  # stage_name -> stage data
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
        """Calculate SHA256 hash of file."""
        if not Path(file_path).exists():
            return "missing"

        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]  # 16 chars

    def register_input_file(self, name: str, file_path: Optional[str]) -> str:
        """
        Register an input file and return its hash.

        Args:
            name: Input name (e.g., 'text_file')
            file_path: Path to file (can be None)

        Returns:
            File hash
        """
        if file_path is None:
            hash_value = "not_provided"
        else:
            hash_value = self._hash_file(file_path)

        self.input_hashes[name] = hash_value
        return hash_value

    def create_stage_fingerprint(self,
                                stage_name: str,
                                input_deps: List[str],
                                params: Dict[str, Any]) -> StageFingerprint:
        """
        Create fingerprint for a stage.

        Args:
            stage_name: Name of the stage
            input_deps: List of input names this stage depends on
            params: Stage parameters

        Returns:
            Stage fingerprint
        """
        # Get hashes for dependent inputs
        inputs = {name: self.input_hashes.get(name, 'unknown')
                 for name in input_deps}

        return StageFingerprint(stage_name, inputs, params)

    def check_stage_cached(self,
                          output_dir: Path,
                          fingerprint: StageFingerprint,
                          expected_patterns: Optional[List[str]] = None) -> bool:
        """
        Check if stage can use cached results.

        This is the KEY method - it determines cache hit/miss.

        Algorithm:
        1. Look for fingerprint file in output directory
        2. If found, load and compare fingerprints
        3. If match, verify output files exist
        4. If all good → CACHE HIT
        5. Otherwise → CACHE MISS

        Args:
            output_dir: Directory where stage outputs are stored
            fingerprint: Current stage fingerprint
            expected_patterns: Optional glob patterns for outputs (for validation)

        Returns:
            True if cache hit, False if cache miss
        """
        fingerprint_file = output_dir / '.fingerprint.json'

        # No fingerprint file → never run
        if not fingerprint_file.exists():
            return False

        # Load stored fingerprint
        try:
            with open(fingerprint_file, 'r') as f:
                stored_data = json.load(f)
                stored_fingerprint = StageFingerprint.from_dict(stored_data)
        except Exception as e:
            print(f"  ⚠ Warning: Could not load fingerprint: {e}")
            return False

        # Compare fingerprints
        if fingerprint != stored_fingerprint:
            # Fingerprint mismatch - inputs or params changed
            return False

        # Fingerprint matches - verify outputs exist
        if expected_patterns:
            for pattern in expected_patterns:
                files = list(output_dir.glob(pattern))
                if not files:
                    print(f"  ⚠ Warning: Expected output not found: {pattern}")
                    return False
        else:
            # Just check that directory has some files (besides .fingerprint.json)
            output_files = [f for f in output_dir.iterdir()
                          if f.name != '.fingerprint.json']
            if not output_files:
                return False

        # All checks passed → CACHE HIT
        return True

    def mark_stage_complete(self,
                          output_dir: Path,
                          fingerprint: StageFingerprint,
                          cost: float = 0.0,
                          metadata: Optional[Dict] = None):
        """
        Mark stage as complete and save fingerprint.

        This writes the .fingerprint.json file to the output directory,
        which is used to detect cache hits on subsequent runs.

        Args:
            output_dir: Directory where outputs were written
            fingerprint: Stage fingerprint
            cost: Cost of this stage
            metadata: Additional metadata
        """
        # Save fingerprint to output directory
        fingerprint_file = output_dir / '.fingerprint.json'
        with open(fingerprint_file, 'w') as f:
            json.dump(fingerprint.to_dict(), f, indent=2)

        # Update manifest
        stage_name = fingerprint.stage_name
        if stage_name not in self.manifest['stages']:
            self.manifest['stages'][stage_name] = {}

        self.manifest['stages'][stage_name]['status'] = 'completed'
        self.manifest['stages'][stage_name]['fingerprint'] = fingerprint.to_dict()
        self.manifest['stages'][stage_name]['output_dir'] = str(output_dir)
        self.manifest['stages'][stage_name]['cost'] = cost
        self.manifest['stages'][stage_name]['completed_at'] = datetime.now().isoformat()

        if metadata:
            self.manifest['stages'][stage_name]['metadata'] = metadata

        # Update costs
        self.manifest['costs']['total'] += cost
        self.manifest['costs']['by_stage'][stage_name] = \
            self.manifest['costs']['by_stage'].get(stage_name, 0.0) + cost

        self._save_manifest()

    def get_stage_output_dir(self, base_dir: Path, stage_name: str) -> Path:
        """
        Get output directory for a stage.

        Args:
            base_dir: Base output directory
            stage_name: Stage name

        Returns:
            Path to stage output directory
        """
        # Map stage names to subdirectories
        dir_map = {
            'scene_generation': base_dir,  # Root level
            'audio_generation': base_dir / 'audio',
            'image_generation': base_dir / 'images',
            'video_generation': base_dir / 'video',
        }

        output_dir = dir_map.get(stage_name, base_dir / stage_name)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def discover_stage_outputs(self, output_dir: Path) -> List[Path]:
        """
        Discover all output files in a stage directory.

        Args:
            output_dir: Stage output directory

        Returns:
            List of output file paths
        """
        outputs = []
        for path in output_dir.iterdir():
            if path.name == '.fingerprint.json':
                continue  # Skip fingerprint file
            if path.is_file():
                outputs.append(path)
        return outputs

    def get_cache_summary(self) -> Dict[str, Any]:
        """Get summary of cache state."""
        return {
            'total_cost': self.manifest['costs']['total'],
            'stages': {
                name: {
                    'status': data.get('status'),
                    'cost': data.get('cost', 0.0),
                    'fingerprint': data.get('fingerprint', {}).get('hash', 'N/A')
                }
                for name, data in self.manifest['stages'].items()
            }
        }

    def explain_cache_miss(self,
                          stored_fingerprint: Optional[StageFingerprint],
                          current_fingerprint: StageFingerprint) -> str:
        """
        Explain why there was a cache miss.

        Args:
            stored_fingerprint: Previously stored fingerprint (if any)
            current_fingerprint: Current fingerprint

        Returns:
            Human-readable explanation
        """
        if stored_fingerprint is None:
            return "No previous run found"

        # Compare inputs
        input_changes = []
        for name, current_hash in current_fingerprint.inputs.items():
            old_hash = stored_fingerprint.inputs.get(name)
            if old_hash != current_hash:
                input_changes.append(f"{name} ({old_hash[:8] if old_hash else 'N/A'} → {current_hash[:8]})")

        # Compare params
        param_changes = []
        for key, current_val in current_fingerprint.params.items():
            old_val = stored_fingerprint.params.get(key)
            if old_val != current_val:
                param_changes.append(f"{key} ({old_val} → {current_val})")

        reasons = []
        if input_changes:
            reasons.append(f"Input changes: {', '.join(input_changes)}")
        if param_changes:
            reasons.append(f"Parameter changes: {', '.join(param_changes)}")

        return "; ".join(reasons) if reasons else "Unknown reason"


# Helper function for easy integration
def check_and_skip_if_cached(cache: CacheManagerV2,
                            stage_name: str,
                            output_dir: Path,
                            input_deps: List[str],
                            params: Dict[str, Any],
                            expected_patterns: Optional[List[str]] = None) -> bool:
    """
    Helper function to check cache and skip if possible.

    Usage in pipeline:
        if check_and_skip_if_cached(cache, 'audio_generation', audio_dir,
                                    ['scenes_file'], {'workers': 1}):
            print("✓ Using cached audio")
            return  # Skip generation

        # Otherwise run generation...

    Returns:
        True if cached (should skip), False if need to run
    """
    fingerprint = cache.create_stage_fingerprint(stage_name, input_deps, params)

    if cache.check_stage_cached(output_dir, fingerprint, expected_patterns):
        print(f"✓ Using cached {stage_name} (fingerprint: {fingerprint.hash[:8]})")
        return True

    # Check if there was a previous run
    fingerprint_file = output_dir / '.fingerprint.json'
    if fingerprint_file.exists():
        try:
            with open(fingerprint_file, 'r') as f:
                stored_data = json.load(f)
                stored_fp = StageFingerprint.from_dict(stored_data)
            reason = cache.explain_cache_miss(stored_fp, fingerprint)
            print(f"⚠ Cache miss for {stage_name}: {reason}")
        except:
            print(f"⚠ Cache miss for {stage_name}: Could not read previous fingerprint")
    else:
        print(f"⚠ No cache for {stage_name}: First run")

    return False
