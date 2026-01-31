#!/usr/bin/env python3
"""
Audio Generation for Scenes using Chatterbox.
Includes parallel processing support for speedup.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from audio_backend import ChatterboxBackend


class SceneAudioGenerator:
    """Generate audio for scenes using Chatterbox"""

    def __init__(self, audio_prompt_path: str, device: str = 'cpu', speed: float = 1.0):
        self.backend = ChatterboxBackend(
            audio_prompt_path=audio_prompt_path,
            device=device,
            exaggeration=0.7,
            speed=speed
        )

    def generate_scene_audio(self, scene: Dict, output_path: Path) -> float:
        """
        Generate audio for a single scene.

        Returns:
            Duration in seconds
        """
        # Format as dialogues for backend (speaker, text)
        dialogues = []

        # Add all sentences for the scene
        for sentence in scene['sentences']:
            dialogues.append(('Narrator', sentence))

        # Add pause at end if specified
        if scene.get('pause_after', 0) > 0:
            dialogues.append(('Narrator', f"[pause-{scene['pause_after']}]"))

        print(f"\nGenerating audio for Scene {scene['scene_id']}...")
        audio_bytes = self.backend.generate_chunk(dialogues, 1, 1)

        # Save audio
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

        # Measure duration using ffprobe
        duration = self._get_audio_duration(output_path)
        print(f"  ✓ Scene {scene['scene_id']}: {duration:.2f}s → {output_path.name}")

        return duration

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration using ffprobe"""
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                str(audio_path)
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception(f"ffprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        return float(data['format']['duration'])


class ParallelAudioGenerator:
    """
    Parallel audio generation using process pool for 4-8x speedup.

    Uses ProcessPoolExecutor to generate audio for multiple scenes simultaneously.
    """

    def __init__(
        self,
        audio_prompt_path: str,
        device: str = 'cpu',
        speed: float = 1.0,
        max_workers: Optional[int] = None
    ):
        """
        Initialize parallel audio generator.

        Args:
            audio_prompt_path: Path to reference audio file for Chatterbox
            device: Device to use ('cpu' or 'cuda')
            speed: Speech speed multiplier
            max_workers: Number of worker processes (default: min(cpu_count(), 8))
        """
        self.audio_prompt_path = audio_prompt_path
        self.device = device
        self.speed = speed
        self.max_workers = max_workers or min(cpu_count(), 8)

    def generate_all_scenes(
        self,
        scenes: List[Dict],
        audio_dir: Path,
        checkpoint_mgr=None
    ) -> Dict[int, float]:
        """
        Generate audio for all scenes in parallel.

        Args:
            scenes: List of scene dictionaries
            audio_dir: Directory to save audio files
            checkpoint_mgr: Optional CheckpointManager for tracking progress

        Returns:
            Dict mapping scene_id -> duration
        """
        audio_dir.mkdir(parents=True, exist_ok=True)

        # Determine which scenes to process
        if checkpoint_mgr:
            # Load checkpoint to get current state
            checkpoint = checkpoint_mgr.load_or_create()
            pending_scenes = checkpoint_mgr.get_pending_scenes(checkpoint, 'audio_generation')

            if not pending_scenes:
                print("✓ All audio already generated, loading durations...")
                return self._load_existing_durations(scenes, audio_dir)

            scenes_to_process = [s for s in scenes if s['scene_id'] in pending_scenes]
            print(f"\nGenerating audio for {len(scenes_to_process)} scenes (parallel)...")
        else:
            scenes_to_process = scenes
            print(f"\nGenerating audio for {len(scenes)} scenes (parallel)...")

        print(f"  Workers: {self.max_workers}")

        durations = {}

        # Create work items
        work_items = [
            (scene, audio_dir / f"scene_{scene['scene_id']:03d}.wav")
            for scene in scenes_to_process
        ]

        # Process in parallel
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(
                    _generate_single_scene_worker,
                    scene,
                    output_path,
                    self.audio_prompt_path,
                    self.device,
                    self.speed
                ): scene['scene_id']
                for scene, output_path in work_items
            }

            # Progress bar if tqdm is available
            try:
                from tqdm import tqdm
                progress_bar = tqdm(total=len(futures), desc="Audio Generation", unit="scene")
            except ImportError:
                progress_bar = None
                print(f"  Processing {len(futures)} scenes...")

            # Collect results as they complete
            for future in as_completed(futures):
                scene_id = futures[future]

                try:
                    duration = future.result()
                    durations[scene_id] = duration

                    # Update checkpoint if available
                    if checkpoint_mgr:
                        checkpoint_mgr.mark_scene_completed(checkpoint, 'audio_generation', scene_id)

                    if progress_bar:
                        progress_bar.update(1)
                        progress_bar.set_postfix({'scene': scene_id, 'duration': f'{duration:.1f}s'})
                    else:
                        print(f"  ✓ Scene {scene_id}: {duration:.2f}s")

                except Exception as e:
                    print(f"\n❌ Scene {scene_id} failed: {e}")

                    if checkpoint_mgr:
                        checkpoint_mgr.mark_scene_failed(checkpoint, 'audio_generation', scene_id)

                    if progress_bar:
                        progress_bar.update(1)

                    raise

            if progress_bar:
                progress_bar.close()

        # Load any existing durations we didn't regenerate
        if checkpoint_mgr:
            existing_durations = self._load_existing_durations(scenes, audio_dir)
            durations.update(existing_durations)

        print(f"✓ Generated {len(durations)} audio files")
        return durations

    def _load_existing_durations(self, scenes: List[Dict], audio_dir: Path) -> Dict[int, float]:
        """Load durations of existing audio files"""
        durations = {}

        for scene in scenes:
            audio_path = audio_dir / f"scene_{scene['scene_id']:03d}.wav"
            if audio_path.exists():
                try:
                    duration = _get_audio_duration_static(audio_path)
                    durations[scene['scene_id']] = duration
                except Exception as e:
                    print(f"⚠️  Could not read duration for Scene {scene['scene_id']}: {e}")

        return durations


def _generate_single_scene_worker(
    scene: Dict,
    output_path: Path,
    audio_prompt_path: str,
    device: str,
    speed: float
) -> float:
    """
    Worker function for parallel execution.

    Must be a top-level function for multiprocessing to pickle it.
    """
    # Import inside worker to avoid pickling issues
    from audio_backend import ChatterboxBackend

    backend = ChatterboxBackend(
        audio_prompt_path=audio_prompt_path,
        device=device,
        exaggeration=0.7,
        speed=speed
    )

    # Generate audio
    dialogues = []
    for sentence in scene['sentences']:
        dialogues.append(('Narrator', sentence))

    if scene.get('pause_after', 0) > 0:
        dialogues.append(('Narrator', f"[pause-{scene['pause_after']}]"))

    audio_bytes = backend.generate_chunk(dialogues, 1, 1)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(audio_bytes)

    # Measure duration
    duration = _get_audio_duration_static(output_path)

    return duration


def _get_audio_duration_static(audio_path: Path) -> float:
    """Static function to get audio duration (for use in worker processes)"""
    result = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json',
         '-show_format', str(audio_path)],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        raise Exception(f"ffprobe failed: {result.stderr}")

    data = json.loads(result.stdout)
    return float(data['format']['duration'])
