#!/usr/bin/env python3
"""
End-to-End Video Generation Pipeline
Converts text to video with AI-generated scenes and narration.

Usage:
    python3 scripts/generate_video_end_to_end.py \
        --content source.txt \
        --audio-reference resources/voices/maurice-meditate.mp3 \
        --art-style "19th century Russian realism" \
        --narrator-style "deliberate, intimate, building dread" \
        --length 5m

    # Regenerate single scene:
    python3 scripts/generate_video_end_to_end.py \
        --content source.txt \
        ... (same args) \
        --rerun-scene 8
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env.secrets'
if env_path.exists():
    load_dotenv(env_path)

# Import our modules
from src.generators.scene_generator import SceneGenerator
from audio_generator import ParallelAudioGenerator, SceneAudioGenerator
from src.generators.video_generator import ParallelVideoGenerator
from src.generators.video_assembler import VideoAssembler
from src.utils.slug_utils import generate_slug, create_output_filename
from src.clients.openai_client import OpenAIClient
from src.clients.openrouter_client import OpenRouterClient
from src.utils.checkpoint_manager import CheckpointManager
from pydub import AudioSegment
import asyncio
import subprocess


def parse_length(length_str: str) -> float:
    """Parse length string like '5m', '30s', '2.5m' to minutes"""
    length_str = length_str.lower().strip()

    if length_str.endswith('m'):
        return float(length_str[:-1])
    elif length_str.endswith('s'):
        return float(length_str[:-1]) / 60.0
    else:
        try:
            return float(length_str)  # Assume minutes
        except ValueError:
            raise ValueError(f"Invalid length format: {length_str}. Use '5m' or '30s'")


def get_duration(file_path: Path) -> float:
    """Get duration of audio/video file using ffprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(file_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ffprobe failed: {result.stderr}")

    return float(result.stdout.strip())


def generate_final_report(scenes, output_dir: Path, slug: str):
    """Generate detailed scene-by-scene report"""
    print("\n" + "=" * 80)
    print("FINAL SCENE REPORT")
    print("=" * 80)

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("SCENE-BY-SCENE BREAKDOWN")
    report_lines.append("=" * 80 + "\n")

    audio_dir = output_dir / 'raw_audio'
    video_dir = output_dir / 'raw_videos'
    scene_dir = output_dir / 'scene_videos'  # Combined A/V per scene

    for scene in scenes:
        scene_id = scene['scene_id']

        report_lines.append(f"SCENE {scene_id}")
        report_lines.append("-" * 40)

        # Sentences
        report_lines.append(f"Sentences: {len(scene['sentences'])}")
        for i, sentence in enumerate(scene['sentences'], 1):
            report_lines.append(f"  {i}. {sentence}")

        # Audio info
        audio_path = audio_dir / f"scene_{scene_id:03d}.wav"
        if audio_path.exists():
            audio_duration = get_duration(audio_path)
            report_lines.append(f"\nAudio: {audio_path.name}")
            report_lines.append(f"  Duration: {audio_duration:.3f}s")

        # Video info
        video_path = video_dir / f"scene_{scene_id:03d}_final.mp4"
        if video_path.exists():
            video_duration = get_duration(video_path)
            report_lines.append(f"\nVideo: {video_path.name}")
            report_lines.append(f"  Duration: {video_duration:.3f}s")

        # Combined scene info
        scene_video_path = scene_dir / f"scene_{scene_id:03d}.mp4"
        if scene_video_path.exists():
            combined_duration = get_duration(scene_video_path)
            report_lines.append(f"\nCombined Scene Video: {scene_video_path.name}")
            report_lines.append(f"  Duration: {combined_duration:.3f}s")

        # Sync check
        if audio_path.exists() and video_path.exists():
            diff = video_duration - audio_duration
            if abs(diff) > 0.05:
                report_lines.append(f"\n  ⚠️  SYNC WARNING: Video {diff:+.3f}s off from audio")
            else:
                report_lines.append(f"\n  ✓ SYNCED: Within 50ms tolerance")

        report_lines.append("\n")

    # Save report
    report_path = output_dir / 'scene_report.txt'
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))

    # Print to console
    for line in report_lines:
        print(line)

    print(f"\n✓ Report saved: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="End-to-end video generation from text",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Input source (mutually exclusive)
    parser.add_argument("--scenes", help="Path to pre-generated scenes JSON file")
    parser.add_argument("--content", help="Path to text file to generate scenes from")
    parser.add_argument("--audio-reference", help="Path to voice cloning reference audio")
    parser.add_argument("--art-style", help="Visual art style description")
    parser.add_argument("--narrator-style", help="Audio narration style")
    parser.add_argument("--length", help="Target length (e.g., '5m', '30s')")

    # Optional arguments
    parser.add_argument("--episode-title", help="Episode title (auto-generated if not provided)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Device for audio generation")
    parser.add_argument("--speed", type=float, default=1.0, help="Audio speed multiplier")
    parser.add_argument("--sora-model", default="sora-2", choices=["sora-2", "sora-2-pro"], help="Sora model")
    parser.add_argument("--scene-model", default="anthropic/claude-sonnet-4.5", help="LLM for scene generation")

    # Optimization arguments
    parser.add_argument("--audio-workers", type=int, default=4, help="Number of parallel audio workers (default: 4)")
    parser.add_argument("--video-concurrent", type=int, default=5, help="Max concurrent video API calls (default: 5)")
    parser.add_argument("--max-retries", type=int, default=5, help="Max retries for API failures (default: 5)")

    # Rerun single scene
    parser.add_argument("--rerun-scene", type=int, help="Regenerate only this scene number (1-based)")

    args = parser.parse_args()

    # Validate mutually exclusive argument groups
    has_scenes = args.scenes is not None
    has_content_mode = args.content is not None

    if has_scenes and has_content_mode:
        parser.error(
            "❌ ERROR: --scenes and --content are mutually exclusive.\n"
            "\n"
            "Choose ONE of:\n"
            "  1. Generate from text:  --content + --audio-reference + --art-style + --narrator-style + --length\n"
            "  2. Use existing scenes: --scenes\n"
            "\n"
            "The --scenes file should contain scenes generated from a previous --content run."
        )

    if not has_scenes and not has_content_mode:
        parser.error(
            "❌ ERROR: Missing required input.\n"
            "\n"
            "Choose ONE of:\n"
            "  1. Generate from text:  --content + --audio-reference + --art-style + --narrator-style + --length\n"
            "  2. Use existing scenes: --scenes\n"
        )

    # Validate content mode has all required parameters
    if has_content_mode:
        missing = []
        if not args.audio_reference:
            missing.append("--audio-reference")
        if not args.art_style:
            missing.append("--art-style")
        if not args.narrator_style:
            missing.append("--narrator-style")
        if not args.length:
            missing.append("--length")

        if missing:
            parser.error(
                f"❌ ERROR: When using --content, you must also provide: {', '.join(missing)}\n"
                "\n"
                "Required for content mode: --content --audio-reference --art-style --narrator-style --length"
            )

    # Validate --rerun-scene requires checkpoint (will be checked later when loading checkpoint)
    if args.rerun_scene:
        if has_scenes:
            parser.error(
                "❌ ERROR: --rerun-scene cannot be used with --scenes.\n"
                "\n"
                "--rerun-scene regenerates a specific scene from a previous --content run.\n"
                "It requires the checkpoint file created during that run."
            )

    # Parse length
    target_length_minutes = parse_length(args.length) if args.length else None

    # Load content
    print("=" * 80)
    print("END-TO-END VIDEO GENERATION PIPELINE")
    print("=" * 80)

    content_path = Path(args.content)
    if not content_path.exists():
        raise FileNotFoundError(f"Content file not found: {args.content}")

    with open(content_path, 'r', encoding='utf-8') as f:
        text_content = f.read()

    print(f"Content:       {args.content} ({len(text_content)} chars)")
    print(f"Audio Ref:     {args.audio_reference}")
    print(f"Art Style:     {args.art_style}")
    print(f"Narrator:      {args.narrator_style}")
    print(f"Target Length: {target_length_minutes:.1f} minutes")
    print(f"Scene Model:   {args.scene_model}")
    print(f"Sora Model:    {args.sora_model}")
    if args.rerun_scene:
        print(f"🔄 RERUN MODE: Regenerating scene {args.rerun_scene} only")
    print("=" * 80)
    print()

    # Track timing
    start_time = time.time()
    timings = {}

    # ========================================================================
    # STAGE 0: Generate Scenes from Text (or load existing)
    # ========================================================================
    print("=" * 80)
    print("STAGE 0: Scene Generation from Text")
    print("=" * 80)

    stage_start = time.time()

    # Check if we're in rerun mode and can load existing scenes
    if args.rerun_scene:
        # Try to find existing output directory
        if args.episode_title:
            slug = generate_slug(args.episode_title)
        else:
            # Try to find most recent output dir
            output_base = Path('output')
            if output_base.exists():
                dirs = [d for d in output_base.iterdir() if d.is_dir()]
                if dirs:
                    slug = max(dirs, key=lambda d: d.stat().st_mtime).name
                else:
                    raise ValueError("No existing output found for --rerun-scene. Run full pipeline first.")
            else:
                raise ValueError("No existing output found for --rerun-scene. Run full pipeline first.")

        output_dir = Path('output') / slug
        scenes_json_path = output_dir / 'scenes.json'

        if not scenes_json_path.exists():
            raise FileNotFoundError(f"Scenes file not found: {scenes_json_path}. Run full pipeline first.")

        with open(scenes_json_path, 'r') as f:
            scenes_data = json.load(f)

        print(f"✓ Loaded existing scenes from: {scenes_json_path}")
        print(f"✓ Episode: {scenes_data['episode']['title']}")
        print(f"✓ Total scenes: {len(scenes_data['scenes'])}")
        print(f"  Time: 0.0s (loaded from cache)")
        timings['scene_generation'] = 0.0
    else:
        # Generate new scenes
        scene_gen = SceneGenerator(model=args.scene_model)
        scenes_data = scene_gen.generate_scenes_from_text(
            text=text_content,
            art_style=args.art_style,
            narrator_style=args.narrator_style,
            target_length_minutes=target_length_minutes,
            episode_title=args.episode_title
        )

        timings['scene_generation'] = time.time() - stage_start

        print(f"\n✓ Generated {len(scenes_data['scenes'])} scenes")
        print(f"✓ Episode: {scenes_data['episode']['title']}")
        print(f"  Time: {timings['scene_generation']:.1f}s")

        # Create output directory
        slug = generate_slug(scenes_data['episode']['title'])
        output_dir = Path('output') / slug
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save scenes JSON
        scenes_json_path = output_dir / 'scenes.json'
        with open(scenes_json_path, 'w') as f:
            json.dump(scenes_data, f, indent=2)
        print(f"✓ Saved scenes: {scenes_json_path}")

    episode = scenes_data['episode']
    scenes = scenes_data['scenes']

    # Initialize checkpoint manager
    checkpoint_mgr = CheckpointManager(output_dir)
    checkpoint = checkpoint_mgr.load_or_create(slug=slug)
    checkpoint['scenes_data'] = scenes_data
    checkpoint_mgr.initialize_stage(checkpoint, 'audio_generation', len(scenes))
    checkpoint_mgr.initialize_stage(checkpoint, 'video_generation', len(scenes))
    checkpoint_mgr.mark_stage_completed(checkpoint, 'scene_generation')

    # ========================================================================
    # STAGE 1: Audio Generation (Parallel or Single Scene)
    # ========================================================================
    print("\n" + "=" * 80)
    print("STAGE 1: Audio Generation")
    print("=" * 80)

    stage_start = time.time()

    audio_dir = output_dir / 'raw_audio'

    if args.rerun_scene:
        # Regenerate single scene audio
        scene_to_regen = next((s for s in scenes if s['scene_id'] == args.rerun_scene), None)
        if not scene_to_regen:
            raise ValueError(f"Scene {args.rerun_scene} not found. Valid range: 1-{len(scenes)}")

        print(f"\n🔄 Regenerating audio for scene {args.rerun_scene} only...")
        print(f"Progress: 1/1 scenes")

        audio_gen = SceneAudioGenerator(
            args.audio_reference,
            device=args.device,
            speed=args.speed
        )

        audio_path = audio_dir / f"scene_{args.rerun_scene:03d}.wav"
        duration = audio_gen.generate_scene_audio(scene_to_regen, audio_path)
        scene_to_regen['actual_duration'] = duration

        # Update checkpoint
        checkpoint_mgr.mark_scene_completed(checkpoint, 'audio_generation', args.rerun_scene)

    else:
        # Generate all scene audio in parallel
        print(f"\nGenerating audio for {len(scenes)} scenes (parallel)...")
        print(f"  Workers: {args.audio_workers}")

        audio_gen = ParallelAudioGenerator(
            args.audio_reference,
            device=args.device,
            speed=args.speed,
            max_workers=args.audio_workers
        )

        # Generate audio in parallel
        durations = audio_gen.generate_all_scenes(scenes, audio_dir, checkpoint_mgr)

        # Update scenes with durations
        for scene in scenes:
            scene['actual_duration'] = durations[scene['scene_id']]

        checkpoint_mgr.mark_stage_completed(checkpoint, 'audio_generation')

    timings['audio_generation'] = time.time() - stage_start
    print(f"  Time: {timings['audio_generation']:.1f}s")

    # ========================================================================
    # STAGE 2: Video Generation (Parallel or Single Scene)
    # ========================================================================
    print("\n" + "=" * 80)
    print("STAGE 2: Video Generation")
    print("=" * 80)

    stage_start = time.time()

    video_dir = output_dir / 'raw_videos'
    openai_client = OpenAIClient()
    assembler = VideoAssembler()

    video_gen = ParallelVideoGenerator(
        openai_client,
        model=args.sora_model,
        max_concurrent=args.video_concurrent
    )

    if args.rerun_scene:
        # Regenerate single scene video
        scene_to_regen = next((s for s in scenes if s['scene_id'] == args.rerun_scene), None)

        print(f"\n🔄 Regenerating video for scene {args.rerun_scene} only...")
        print(f"Progress: 1/1 scenes")

        # Run async video generation for single scene
        async def generate_single_video_async():
            return await video_gen._generate_single_scene_async(
                scene_to_regen,
                episode['context'],
                episode['art_style'],
                video_dir,
                assembler,
                checkpoint_mgr
            )

        asyncio.run(generate_single_video_async())

    else:
        # Generate all videos
        print(f"\nGenerating videos for {len(scenes)} scenes...")
        print(f"  Max concurrent: {args.video_concurrent}")

        # Run async video generation
        async def generate_videos_async():
            return await video_gen.generate_all_scenes(
                scenes,
                episode['context'],
                episode['art_style'],
                video_dir,
                assembler,
                checkpoint_mgr
            )

        trimmed_video_paths = asyncio.run(generate_videos_async())

        checkpoint_mgr.mark_stage_completed(checkpoint, 'video_generation')

    timings['video_generation'] = time.time() - stage_start
    print(f"  Time: {timings['video_generation']:.1f}s")

    # ========================================================================
    # STAGE 3: Final Assembly (Combine A/V per scene, then stitch)
    # ========================================================================
    print("\n" + "=" * 80)
    print("STAGE 3: Final Assembly")
    print("=" * 80)

    stage_start = time.time()

    scene_dir = output_dir / 'scene_videos'
    scene_dir.mkdir(exist_ok=True)

    # Step 1: Combine audio + video for EACH scene
    print("\nStep 1: Combining audio + video per scene...")
    print(f"Progress: 0/{len(scenes)} scenes combined")

    combined_scene_paths = []
    for i, scene in enumerate(scenes, 1):
        scene_id = scene['scene_id']

        audio_path = audio_dir / f"scene_{scene_id:03d}.wav"
        video_path = video_dir / f"scene_{scene_id:03d}_final.mp4"
        scene_video_path = scene_dir / f"scene_{scene_id:03d}.mp4"

        if not audio_path.exists() or not video_path.exists():
            print(f"  ⚠️  Scene {scene_id}: Missing audio or video, skipping")
            continue

        # Combine this scene's audio + video
        assembler.add_audio_to_video(video_path, audio_path, scene_video_path)
        combined_scene_paths.append(scene_video_path)

        print(f"Progress: {i}/{len(scenes)} scenes combined", end='\r')

    print(f"\n✓ Combined {len(combined_scene_paths)} scene videos")

    # Step 2: Concatenate all scene videos into final video
    print("\nStep 2: Concatenating all scene videos...")
    final_video_filename = create_output_filename(slug, "final_video.mp4")
    final_video_path = output_dir / final_video_filename
    assembler.concatenate_videos(combined_scene_paths, final_video_path)

    timings['final_assembly'] = time.time() - stage_start
    timings['total'] = time.time() - start_time

    # ========================================================================
    # Save Metadata
    # ========================================================================
    total_duration = get_duration(final_video_path)

    metadata = {
        "slug": slug,
        "created_at": datetime.now().isoformat(),
        "parameters": {
            "content_file": str(content_path),
            "audio_reference": args.audio_reference,
            "art_style": args.art_style,
            "narrator_style": args.narrator_style,
            "target_length": args.length,
            "device": args.device,
            "speed": args.speed,
            "sora_model": args.sora_model,
            "scene_model": args.scene_model,
            "rerun_scene": args.rerun_scene
        },
        "episode": {
            "title": episode['title'],
            "context": episode['context'],
            "scenes_count": len(scenes)
        },
        "output": {
            "total_duration": total_duration,
            "final_video": final_video_filename
        },
        "timing": timings
    }

    metadata_path = output_dir / 'metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    # ========================================================================
    # Generate Final Report
    # ========================================================================
    generate_final_report(scenes, output_dir, slug)

    # ========================================================================
    # SUCCESS!
    # ========================================================================
    print("\n" + "=" * 80)
    print("SUCCESS! Video Generation Complete")
    print("=" * 80)
    print(f"Episode:      {episode['title']}")
    print(f"Scenes:       {len(scenes)}")
    print(f"Duration:     {total_duration:.1f}s ({total_duration/60:.1f}m)")
    print(f"Output Dir:   {output_dir}")
    print(f"Final Video:  {final_video_path}")
    print(f"\nTiming:")
    print(f"  Scene Generation: {timings['scene_generation']:.1f}s")
    print(f"  Audio Generation: {timings['audio_generation']:.1f}s ({timings['audio_generation']/60:.1f}m)")
    print(f"  Video Generation: {timings['video_generation']:.1f}s ({timings['video_generation']/60:.1f}m)")
    print(f"  Final Assembly:   {timings['final_assembly']:.1f}s")
    print(f"  Total:            {timings['total']:.1f}s ({timings['total']/60:.1f}m)")
    print("=" * 80)


if __name__ == "__main__":
    main()
