#!/usr/bin/env python3
"""
Video Generation for Scenes using Sora API.
Includes async parallel processing for 5-10x speedup.
"""

from pathlib import Path
from typing import List, Dict, Optional
import requests
import asyncio
import aiohttp
import subprocess
from asyncio import Semaphore
from openai_client import OpenAIClient


class SceneVideoGenerator:
    """Generate videos for scenes using Sora"""

    def __init__(self, openai_client: OpenAIClient, model: str = 'sora-2'):
        self.client = openai_client
        self.model = model

    def determine_video_chunks(self, duration: float) -> List[int]:
        """
        Determine optimal video chunk sizes for a given duration.
        Sora supports: 4s, 8s, 12s

        Strategy: Generate slightly longer videos, then trim to exact duration
        """
        if duration <= 4:
            return [4]
        elif duration <= 8:
            return [8]
        elif duration <= 12:
            return [12]
        else:
            # For longer durations, break into chunks
            chunks = []
            remaining = duration

            while remaining > 0:
                if remaining > 12:
                    chunks.append(12)
                    remaining -= 12
                elif remaining > 8:
                    chunks.append(12)  # Use 12s, will trim
                    remaining = 0
                elif remaining > 4:
                    chunks.append(8)  # Use 8s, will trim
                    remaining = 0
                else:
                    chunks.append(4)  # Use 4s, will trim
                    remaining = 0

            return chunks

    def generate_scene_videos(
        self,
        scene: Dict,
        duration: float,
        episode_context: str,
        art_style: str,
        output_dir: Path
    ) -> List[Path]:
        """
        Generate video(s) for a scene.

        Returns:
            List of video file paths (untrimmed)
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine chunks needed
        chunks = self.determine_video_chunks(duration)
        print(f"\nScene {scene['scene_id']} ({duration:.2f}s):")
        print(f"  Video strategy: {' + '.join(f'{c}s' for c in chunks)} = {sum(chunks)}s (will trim to {duration:.2f}s)")

        # Build prompt
        prompt = self._build_video_prompt(scene, episode_context, art_style)

        video_paths = []
        for i, chunk_duration in enumerate(chunks, 1):
            print(f"\n  Generating video {i}/{len(chunks)} ({chunk_duration}s)...")
            print(f"    Prompt: {prompt[:100]}...")

            try:
                # Generate video
                video_url = self.client.generate_video(
                    prompt=prompt,
                    model=self.model,
                    seconds=chunk_duration,
                    size="1280x720"
                )

                # Download video
                video_path = output_dir / f"scene_{scene['scene_id']:03d}_part_{i}_{chunk_duration}s.mp4"
                print(f"    Downloading video...")

                headers = {
                    "Authorization": f"Bearer {self.client.api_key}"
                }
                response = requests.get(video_url, headers=headers, timeout=300)
                response.raise_for_status()

                with open(video_path, 'wb') as f:
                    f.write(response.content)

                video_paths.append(video_path)
                print(f"    ✓ Saved: {video_path.name}")

            except Exception as e:
                print(f"    ✗ Error: {e}")
                raise

        return video_paths

    def _build_video_prompt(self, scene: Dict, episode_context: str, art_style: str, consistent_objects: dict = None) -> str:
        """Build detailed video prompt for Sora"""
        video_desc = scene['video_description']
        camera_style = scene.get('camera_style', 'cinematic, smooth')

        # Build character block if consistent objects are provided
        character_block = ""
        if consistent_objects:
            character_block = "CHARACTERS/OBJECTS IN SCENE: "
            char_descs = [f"{obj_data['name']} ({obj_data['description']})"
                         for obj_data in consistent_objects.values()]
            character_block += "; ".join(char_descs) + ". "

        prompt = (
            f"{character_block}"
            f"{video_desc}. "
            f"Camera: {camera_style}. "
            f"Style: {art_style}. "
            f"Context: {episode_context}"
        )

        return prompt[:500]  # Sora prompt limit


class ParallelVideoGenerator:
    """
    Async video generation with rate limiting for 5-10x speedup.

    Generates videos for multiple scenes in parallel while respecting API rate limits.
    Includes nested parallelism for chunks within scenes.
    """

    def __init__(
        self,
        openai_client: OpenAIClient,
        model: str = 'sora-2',
        max_concurrent: int = 5
    ):
        """
        Initialize parallel video generator.

        Args:
            openai_client: OpenAI client instance
            model: Sora model to use
            max_concurrent: Maximum concurrent API calls (rate limit)
        """
        self.client = openai_client
        self.model = model
        self.max_concurrent = max_concurrent
        self.semaphore = Semaphore(max_concurrent)  # Initialize semaphore

    def determine_video_chunks(self, duration: float) -> List[int]:
        """
        Determine optimal video chunk sizes for a given duration.
        Sora supports: 4s, 8s, 12s
        """
        if duration <= 4:
            return [4]
        elif duration <= 8:
            return [8]
        elif duration <= 12:
            return [12]
        else:
            chunks = []
            remaining = duration

            while remaining > 0:
                if remaining > 12:
                    chunks.append(12)
                    remaining -= 12
                elif remaining > 8:
                    chunks.append(12)
                    remaining = 0
                elif remaining > 4:
                    chunks.append(8)
                    remaining = 0
                else:
                    chunks.append(4)
                    remaining = 0

            return chunks

    async def generate_all_scenes(
        self,
        scenes: List[Dict],
        episode_context: str,
        art_style: str,
        video_dir: Path,
        assembler,  # VideoAssembler instance
        checkpoint_mgr=None,
        episode_objects: dict = None
    ) -> List[Path]:
        """
        Generate videos for all scenes in parallel with rate limiting.

        Args:
            scenes: List of scene dictionaries (with actual_duration set)
            episode_context: Episode context for prompts
            art_style: Art style description
            video_dir: Directory to save videos
            assembler: VideoAssembler instance for concat/trim
            checkpoint_mgr: Optional CheckpointManager
            episode_objects: Dict of consistent objects for character consistency

        Returns:
            List of final trimmed video paths
        """
        video_dir.mkdir(parents=True, exist_ok=True)

        # Determine which scenes to process
        if checkpoint_mgr:
            checkpoint = checkpoint_mgr.load_or_create()
            pending_scenes = checkpoint_mgr.get_pending_scenes(checkpoint, 'video_generation')

            if not pending_scenes:
                print("✓ All videos already generated, loading paths...")
                videos = self._load_existing_videos(scenes, video_dir)
                return [videos[s['scene_id']] for s in scenes if s['scene_id'] in videos]

            scenes_to_process = [s for s in scenes if s['scene_id'] in pending_scenes]
            print(f"\nGenerating videos for {len(scenes_to_process)} scenes (parallel)...")
        else:
            scenes_to_process = scenes
            print(f"\nGenerating videos for {len(scenes)} scenes (parallel)...")

        print(f"  Max concurrent: {self.max_concurrent}")

        # Create tasks for all scenes
        tasks = [
            self._generate_single_scene_async(
                scene, episode_context, art_style, video_dir,
                assembler, checkpoint_mgr, episode_objects
            )
            for scene in scenes_to_process
        ]

        # Run all tasks in parallel (use return_exceptions to prevent one failure from crashing all)
        print(f"  Processing {len(tasks)} scenes in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Load existing videos for scenes we didn't regenerate
        if checkpoint_mgr:
            all_videos = self._load_existing_videos(scenes, video_dir)
            # Filter out exceptions and extract successful results
            new_videos = {
                r['scene_id']: r['path']
                for r in results
                if r and not isinstance(r, Exception)
            }
            all_videos.update(new_videos)
            return [all_videos[s['scene_id']] for s in scenes if s['scene_id'] in all_videos]

        # Filter out exceptions and return successful results
        return [r['path'] for r in results if r and not isinstance(r, Exception)]

    async def _generate_single_scene_async(
        self,
        scene: Dict,
        episode_context: str,
        art_style: str,
        video_dir: Path,
        assembler,
        checkpoint_mgr,
        episode_objects: dict = None
    ) -> Optional[Dict]:
        """Generate video for a single scene with rate limiting"""

        async with self.semaphore:  # Rate limiting
            scene_id = scene['scene_id']
            duration = scene['actual_duration']

            try:
                # Get scene-specific consistent objects
                scene_object_ids = scene.get('consistent_objects', [])
                scene_objects = {}
                if episode_objects:
                    scene_objects = {obj_id: episode_objects[obj_id]
                                    for obj_id in scene_object_ids
                                    if obj_id in episode_objects}

                # Determine chunks
                chunks = self.determine_video_chunks(duration)

                print(f"\nScene {scene_id} ({duration:.2f}s):")
                print(f"  Strategy: {' + '.join(f'{c}s' for c in chunks)}")

                # Generate chunks in parallel (within scene)
                chunk_tasks = [
                    self._generate_chunk_async(
                        scene, chunk_duration, i, len(chunks),
                        episode_context, art_style, video_dir, scene_objects
                    )
                    for i, chunk_duration in enumerate(chunks, 1)
                ]

                # Use return_exceptions to prevent one chunk failure from crashing others
                results = await asyncio.gather(*chunk_tasks, return_exceptions=True)

                # Check if any chunk failed
                raw_videos = []
                for i, result in enumerate(results, 1):
                    if isinstance(result, Exception):
                        raise Exception(f"Chunk {i}/{len(chunks)} failed: {result}")
                    raw_videos.append(result)

                # Concatenate if needed (sync FFmpeg)
                if len(raw_videos) > 1:
                    concat_path = video_dir / f"scene_{scene_id:03d}_concat.mp4"
                    await asyncio.to_thread(
                        assembler.concatenate_videos,
                        raw_videos,
                        concat_path
                    )
                    video_to_trim = concat_path
                else:
                    video_to_trim = raw_videos[0]

                # Trim to exact duration (sync FFmpeg)
                trimmed_path = video_dir / f"scene_{scene_id:03d}_video.mp4"
                await asyncio.to_thread(
                    assembler.trim_video,
                    video_to_trim,
                    duration,
                    trimmed_path
                )

                # Update checkpoint
                if checkpoint_mgr:
                    checkpoint = checkpoint_mgr.load_or_create()
                    checkpoint_mgr.mark_scene_completed(checkpoint, 'video_generation', scene_id)

                print(f"  ✓ Scene {scene_id} completed: {trimmed_path.name}")

                return {'scene_id': scene_id, 'path': trimmed_path}

            except Exception as e:
                print(f"\n❌ Scene {scene_id} failed: {e}")

                if checkpoint_mgr:
                    checkpoint = checkpoint_mgr.load_or_create()
                    checkpoint_mgr.mark_scene_failed(checkpoint, 'video_generation', scene_id)

                raise

    async def _generate_chunk_async(
        self,
        scene: Dict,
        chunk_duration: int,
        chunk_num: int,
        total_chunks: int,
        episode_context: str,
        art_style: str,
        video_dir: Path,
        consistent_objects: dict = None,
        max_retries: int = 3
    ) -> Path:
        """Generate a single video chunk asynchronously with retry on moderation failures"""

        print(f"  [{chunk_num}/{total_chunks}] Generating {chunk_duration}s...")

        # Build prompt
        prompt = self._build_video_prompt(scene, episode_context, art_style, consistent_objects)

        # Retry loop for moderation failures
        for attempt in range(max_retries):
            try:
                # Get input reference if available (only use for first chunk)
                input_ref = None
                if chunk_num == 1 and 'input_reference' in scene:
                    input_ref = scene['input_reference']

                # Generate video (use sync client in thread pool)
                video_url = await asyncio.to_thread(
                    self.client.generate_video,
                    prompt=prompt,
                    model=self.model,
                    seconds=chunk_duration,
                    size="1280x720",
                    input_reference=input_ref
                )
                break  # Success, exit retry loop

            except Exception as e:
                error_str = str(e)

                # Check if this is a moderation error
                if 'moderation_blocked' in error_str or 'moderation' in error_str.lower():
                    if attempt < max_retries - 1:
                        print(f"    ⚠️  Moderation block (attempt {attempt + 1}/{max_retries}), retrying with simplified prompt...")
                        # Simplify prompt - remove potentially sensitive content, make more abstract
                        prompt = self._simplify_prompt_for_moderation(prompt)
                        await asyncio.sleep(2)  # Brief delay before retry
                        continue
                    else:
                        print(f"    ❌ Moderation block after {max_retries} attempts, skipping scene")
                        raise Exception(f"Moderation blocked after {max_retries} attempts")
                else:
                    # Not a moderation error, re-raise immediately
                    raise

        # Download video
        video_path = video_dir / f"scene_{scene['scene_id']:03d}_part_{chunk_num}_{chunk_duration}s.mp4"

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {self.client.api_key}"}

            async with session.get(video_url, headers=headers, timeout=aiohttp.ClientTimeout(total=600)) as response:
                response.raise_for_status()

                video_path.parent.mkdir(parents=True, exist_ok=True)
                with open(video_path, 'wb') as f:
                    f.write(await response.read())

        print(f"  ✓ [{chunk_num}/{total_chunks}] Saved {video_path.name}")
        return video_path

    def _build_video_prompt(self, scene: Dict, episode_context: str, art_style: str, consistent_objects: dict = None) -> str:
        """Build detailed video prompt for Sora"""
        video_desc = scene['video_description']
        camera_style = scene.get('camera_style', 'cinematic, smooth')

        # Build character block if consistent objects are provided
        character_block = ""
        if consistent_objects:
            character_block = "CHARACTERS/OBJECTS IN SCENE: "
            char_descs = [f"{obj_data['name']} ({obj_data['description']})"
                         for obj_data in consistent_objects.values()]
            character_block += "; ".join(char_descs) + ". "

        prompt = (
            f"{character_block}"
            f"{video_desc}. "
            f"Camera: {camera_style}. "
            f"Style: {art_style}. "
            f"Context: {episode_context}"
        )

        return prompt[:500]

    def _simplify_prompt_for_moderation(self, prompt: str) -> str:
        """Simplify prompt to avoid moderation blocks"""
        # Remove potentially sensitive words and make more abstract
        sensitive_words = [
            'blood', 'weapon', 'violence', 'kill', 'death', 'fight', 'attack',
            'harm', 'hurt', 'pain', 'suffer', 'destroy', 'shatter', 'break',
            'struggle', 'danger', 'threat', 'fear', 'terror', 'horror'
        ]

        simplified = prompt
        for word in sensitive_words:
            # Replace with more abstract alternatives
            simplified = simplified.replace(word, 'movement')
            simplified = simplified.replace(word.capitalize(), 'Movement')

        # Make it more abstract and artistic
        simplified = simplified.replace('breaking', 'transforming')
        simplified = simplified.replace('falling', 'descending')
        simplified = simplified.replace('crash', 'impact')
        simplified = simplified.replace('hitting', 'touching')

        # Add emphasis on artistic style
        if 'abstract' not in simplified.lower():
            simplified = f"Abstract artistic interpretation. {simplified}"

        return simplified[:500]

    def _load_existing_videos(self, scenes: List[Dict], video_dir: Path) -> Dict[int, Path]:
        """Load paths of existing video files"""
        videos = {}

        for scene in scenes:
            video_path = video_dir / f"scene_{scene['scene_id']:03d}_video.mp4"
            if video_path.exists():
                videos[scene['scene_id']] = video_path

        return videos
