#!/usr/bin/env python3
"""
Checkpoint Manager for Video Generation Pipeline.
Enables resume capability and tracks progress across all stages.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class CheckpointManager:
    """Manage pipeline checkpoints for resume capability"""

    def __init__(self, output_dir: Path):
        """
        Initialize checkpoint manager.

        Args:
            output_dir: Output directory where checkpoint will be saved
        """
        self.output_dir = Path(output_dir)
        self.checkpoint_path = self.output_dir / 'checkpoint.json'

    def load_or_create(self, slug: Optional[str] = None) -> Dict:
        """
        Load existing checkpoint or create new one.

        Args:
            slug: Slug for new checkpoint (required if creating new)

        Returns:
            Checkpoint dictionary
        """
        if self.checkpoint_path.exists():
            print(f"✓ Found existing checkpoint, resuming from {self.checkpoint_path}")
            with open(self.checkpoint_path) as f:
                checkpoint = json.load(f)
            print(f"  Stage: {checkpoint.get('stage', 'unknown')}")
            print(f"  Last updated: {checkpoint.get('last_updated', 'unknown')}")
            return checkpoint
        else:
            print(f"✓ Creating new checkpoint at {self.checkpoint_path}")
            return self._create_new(slug)

    def _create_new(self, slug: Optional[str] = None) -> Dict:
        """Create a new checkpoint structure"""
        now = datetime.now().isoformat()

        checkpoint = {
            "version": "1.0",
            "slug": slug or "unknown",
            "created_at": now,
            "last_updated": now,

            "stage": "scene_generation",
            "completed_stages": [],

            "scenes_data": None,

            "audio_generation": {
                "completed_scenes": [],
                "failed_scenes": [],
                "in_progress": [],
                "total": 0
            },

            "video_generation": {
                "completed_scenes": [],
                "failed_scenes": [],
                "in_progress": [],
                "retry_count": {},
                "total": 0
            },

            "files": {
                "audio": {},
                "video": {}
            }
        }

        # Save initial checkpoint
        self.save(checkpoint)
        return checkpoint

    def save(self, checkpoint: Dict):
        """
        Save checkpoint atomically.

        Uses temp file + atomic rename to prevent corruption.
        """
        checkpoint['last_updated'] = datetime.now().isoformat()

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        temp_path = self.checkpoint_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)

        # Atomic rename
        temp_path.replace(self.checkpoint_path)

    def mark_scene_completed(self, checkpoint: Dict, stage: str, scene_id: int):
        """
        Mark a scene as completed for a stage.

        Args:
            checkpoint: Checkpoint dictionary to update
            stage: Stage name ('audio_generation' or 'video_generation')
            scene_id: Scene ID that was completed
        """
        stage_data = checkpoint[stage]

        # Remove from failed and in_progress if present
        if scene_id in stage_data['failed_scenes']:
            stage_data['failed_scenes'].remove(scene_id)
        if scene_id in stage_data['in_progress']:
            stage_data['in_progress'].remove(scene_id)

        # Add to completed if not already there
        if scene_id not in stage_data['completed_scenes']:
            stage_data['completed_scenes'].append(scene_id)
            stage_data['completed_scenes'].sort()

        # Save after each completion for safety
        self.save(checkpoint)

    def mark_scene_failed(self, checkpoint: Dict, stage: str, scene_id: int):
        """
        Mark a scene as failed.

        Args:
            checkpoint: Checkpoint dictionary to update
            stage: Stage name ('audio_generation' or 'video_generation')
            scene_id: Scene ID that failed
        """
        stage_data = checkpoint[stage]

        # Remove from in_progress
        if scene_id in stage_data['in_progress']:
            stage_data['in_progress'].remove(scene_id)

        # Add to failed if not already there
        if scene_id not in stage_data['failed_scenes']:
            stage_data['failed_scenes'].append(scene_id)
            stage_data['failed_scenes'].sort()

        # Increment retry count
        if 'retry_count' in stage_data:
            retry_count = stage_data['retry_count']
            retry_count[str(scene_id)] = retry_count.get(str(scene_id), 0) + 1

        self.save(checkpoint)

    def mark_scene_in_progress(self, checkpoint: Dict, stage: str, scene_id: int):
        """
        Mark a scene as in progress.

        Args:
            checkpoint: Checkpoint dictionary to update
            stage: Stage name ('audio_generation' or 'video_generation')
            scene_id: Scene ID being processed
        """
        stage_data = checkpoint[stage]

        # Add to in_progress if not already there
        if scene_id not in stage_data['in_progress']:
            stage_data['in_progress'].append(scene_id)
            stage_data['in_progress'].sort()

        self.save(checkpoint)

    def get_pending_scenes(self, checkpoint: Dict, stage: str) -> List[int]:
        """
        Get list of scene IDs that need processing for a stage.

        Args:
            checkpoint: Checkpoint dictionary
            stage: Stage name ('audio_generation' or 'video_generation')

        Returns:
            List of scene IDs that are not completed
        """
        stage_data = checkpoint[stage]
        total = stage_data['total']
        completed = set(stage_data['completed_scenes'])

        # All scene IDs from 1 to total
        all_scenes = set(range(1, total + 1))

        # Pending = all - completed
        pending = sorted(list(all_scenes - completed))

        return pending

    def should_retry(self, checkpoint: Dict, stage: str, scene_id: int, max_retries: int = 3) -> bool:
        """
        Check if we should retry a failed scene.

        Args:
            checkpoint: Checkpoint dictionary
            stage: Stage name ('audio_generation' or 'video_generation')
            scene_id: Scene ID to check
            max_retries: Maximum number of retries allowed

        Returns:
            True if we should retry, False if exceeded max retries
        """
        stage_data = checkpoint[stage]

        if 'retry_count' not in stage_data:
            return True

        retry_count = stage_data['retry_count'].get(str(scene_id), 0)
        return retry_count < max_retries

    def initialize_stage(self, checkpoint: Dict, stage: str, total_scenes: int):
        """
        Initialize a stage with the total number of scenes.

        Args:
            checkpoint: Checkpoint dictionary to update
            stage: Stage name ('audio_generation' or 'video_generation')
            total_scenes: Total number of scenes to process
        """
        checkpoint[stage]['total'] = total_scenes
        self.save(checkpoint)

    def mark_stage_completed(self, checkpoint: Dict, stage_name: str):
        """
        Mark an entire stage as completed.

        Args:
            checkpoint: Checkpoint dictionary to update
            stage_name: Stage name to mark as completed
        """
        if stage_name not in checkpoint['completed_stages']:
            checkpoint['completed_stages'].append(stage_name)

        # Update current stage to next stage
        stage_order = ['scene_generation', 'audio_generation', 'video_generation', 'assembly']
        current_idx = stage_order.index(stage_name)
        if current_idx < len(stage_order) - 1:
            checkpoint['stage'] = stage_order[current_idx + 1]
        else:
            checkpoint['stage'] = 'completed'

        self.save(checkpoint)

    def get_progress_summary(self, checkpoint: Dict) -> str:
        """
        Get a human-readable progress summary.

        Args:
            checkpoint: Checkpoint dictionary

        Returns:
            Progress summary string
        """
        lines = []
        lines.append(f"Checkpoint: {checkpoint['slug']}")
        lines.append(f"Current stage: {checkpoint['stage']}")
        lines.append(f"Completed stages: {', '.join(checkpoint['completed_stages']) or 'None'}")

        for stage in ['audio_generation', 'video_generation']:
            stage_data = checkpoint[stage]
            total = stage_data['total']
            completed = len(stage_data['completed_scenes'])
            failed = len(stage_data['failed_scenes'])
            in_progress = len(stage_data['in_progress'])

            if total > 0:
                lines.append(f"\n{stage.replace('_', ' ').title()}:")
                lines.append(f"  Completed: {completed}/{total}")
                lines.append(f"  Failed: {failed}")
                lines.append(f"  In Progress: {in_progress}")
                lines.append(f"  Progress: {completed/total*100:.1f}%")

        return "\n".join(lines)


if __name__ == "__main__":
    # Test checkpoint manager
    import tempfile
    import shutil

    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Testing in: {temp_dir}")

    try:
        # Create new checkpoint
        mgr = CheckpointManager(temp_dir)
        checkpoint = mgr.load_or_create(slug="test-video")

        # Initialize stage
        mgr.initialize_stage(checkpoint, 'audio_generation', 5)

        # Mark some scenes as completed
        mgr.mark_scene_completed(checkpoint, 'audio_generation', 1)
        mgr.mark_scene_completed(checkpoint, 'audio_generation', 2)
        mgr.mark_scene_completed(checkpoint, 'audio_generation', 3)

        # Mark one as failed
        mgr.mark_scene_failed(checkpoint, 'audio_generation', 4)

        # Get pending scenes
        pending = mgr.get_pending_scenes(checkpoint, 'audio_generation')
        print(f"\nPending scenes: {pending}")

        # Check retry
        should_retry_4 = mgr.should_retry(checkpoint, 'audio_generation', 4)
        print(f"Should retry scene 4: {should_retry_4}")

        # Progress summary
        print(f"\n{mgr.get_progress_summary(checkpoint)}")

        # Test resume
        mgr2 = CheckpointManager(temp_dir)
        checkpoint2 = mgr2.load_or_create()
        print(f"\nResumed checkpoint has {len(checkpoint2['audio_generation']['completed_scenes'])} completed scenes")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)
        print(f"\n✓ Cleaned up {temp_dir}")
