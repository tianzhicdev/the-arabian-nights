"""
Explainer Video Pipeline.
Generates educational explainer videos from trending news topics.
"""

import os
import sys
import json
import time
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.clients.xai_client import XAIClient
from src.clients.openrouter_client import OpenRouterClient
from src.clients.openai_client import OpenAIClient
from src.clients.replicate_client import ReplicateClient
from src.clients.pexels_client import PexelsClient
from src.clients.pixabay_client import PixabayClient
from src.generators.explainer_script_generator import ExplainerScriptGenerator
from src.generators.elevenlabs_explainer_audio import ElevenLabsExplainerAudio
from src.generators.edge_audio_generator import EdgeAudioGenerator
from src.generators.kokoro_audio_generator import KokoroAudioGenerator
from src.generators.video_assembler import VideoAssembler


class ExplainerPipeline:
    """
    Main orchestrator for explainer video generation.

    Pipeline steps:
    1. News Discovery (xAI Grok)
    2. Topic Selection (OpenRouter) → PAUSE FOR APPROVAL
    3. Deep Research (xAI Grok)
    4. Script Generation (OpenRouter)
    5. Audio Generation (Kokoro)
    6. Image Generation (DALL-E 3)
    7. Video Assembly
    8. Queue for Upload
    """

    # Image style prefix - PHOTOREALISTIC
    IMAGE_STYLE_PREFIX = (
        "Professional photograph, photorealistic, like a real photo taken by a photographer. "
        "NOT illustration, NOT painting, NOT artistic rendering. "
        "Real photograph of real places, real people, real events, real objects. "
        "High quality documentary or news photography style. "
        "16:9 aspect ratio. "
        "Photo of: "
    )

    def __init__(
        self,
        output_dir: str = "output/explainer",
        upload_queue_dir: str = None,
        voice_id: str = None,
        art_style: str = "editorial",
        image_provider: str = "flux",
        add_branding: bool = True,
        tts_provider: str = "elevenlabs",
        edge_voice: str = "en-US-AriaNeural",
        edge_rate: str = "-10%",
        kokoro_voice: str = "am_adam",
        kokoro_speed: float = 0.75
    ):
        """
        Initialize explainer pipeline.

        Args:
            output_dir: Base directory for output files
            upload_queue_dir: Directory for upload queue (default: ~/upload_queue_main)
            voice_id: ElevenLabs voice ID (defaults to env var ELEVENLABS_VOICE_ID)
            art_style: Art style for images (editorial, flat_vector, watercolor)
            image_provider: Image provider (flux or dalle)
            add_branding: Whether to add intro/outro branding (default True)
            tts_provider: TTS provider ('elevenlabs', 'edge', or 'kokoro')
            edge_voice: Edge TTS voice ID (default: en-US-AriaNeural)
            edge_rate: Edge TTS rate adjustment (default: -10%)
            kokoro_voice: Kokoro voice ID (default: am_adam)
            kokoro_speed: Kokoro speech speed (default: 0.75 for storytelling)
        """
        self.output_dir = Path(output_dir)
        self.upload_queue_dir = Path(upload_queue_dir or os.path.expanduser("~/upload_queue_main"))
        self.image_provider = image_provider
        self.zoom_per_sec = 0.02  # 2% zoom per second
        self.add_branding = add_branding
        self.tts_provider = tts_provider

        # Branding assets (relative to project root)
        project_root = Path(__file__).parent.parent.parent
        self.branding = {
            "logo": project_root / "resources" / "wornhole-logo.png",
            "intro_sound": project_root / "resources" / "sounds" / "woosh1.mp3",
            "bg_music": project_root / "resources" / "sounds" / "loop1.mp3",
            "intro_duration": 2.0,
            "outro_duration": 10.0,
            "fade_duration": 2.0,
            "bg_music_volume": 0.15  # 15% volume for background music
        }

        # Initialize clients
        self.xai = XAIClient()
        self.openrouter = OpenRouterClient()
        self.openai = OpenAIClient()
        if image_provider == "flux":
            self.replicate = ReplicateClient()
        elif image_provider == "pexels":
            self.pexels = PexelsClient()
            self.pixabay = PixabayClient()
        self.script_generator = ExplainerScriptGenerator(self.openrouter, art_style=art_style)

        # TTS provider selection
        if tts_provider == "kokoro":
            self.audio_generator = KokoroAudioGenerator(voice=kokoro_voice, speed=kokoro_speed)
        elif tts_provider == "edge":
            self.audio_generator = EdgeAudioGenerator(voice=edge_voice, rate=edge_rate)
        else:
            self.audio_generator = ElevenLabsExplainerAudio(voice_id=voice_id)

        self.video_assembler = VideoAssembler()

    def _generate_hash(self, content: str, length: int = 8) -> str:
        """Generate short hash for content identification."""
        return hashlib.sha256(content.encode()).hexdigest()[:length]

    def _save_json(self, data: Dict, path: Path):
        """Save data as JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_json(self, path: Path) -> Optional[Dict]:
        """Load JSON file if exists."""
        if path.exists():
            with open(path, 'r') as f:
                return json.load(f)
        return None

    def _save_text(self, text: str, path: Path):
        """Save text to file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(text)

    def _select_best_media_with_llm(
        self,
        narration: str,
        candidates: List[Dict]
    ) -> Optional[Dict]:
        """
        Use LLM to select the most relevant media (video or photo) from candidates.

        Args:
            narration: The scene's narration text
            candidates: List of media metadata dicts with id, type, tags, description

        Returns:
            The selected media dict or None
        """
        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # Build candidate descriptions for LLM
        candidate_text = ""
        for i, media in enumerate(candidates[:15]):  # Limit to 15 candidates
            media_type = media.get("type", "video").upper()
            source = media.get("source", "unknown")
            tags = media.get("tags", [])
            if isinstance(tags, list):
                tags = ", ".join(tags[:10])  # Limit tags
            desc = media.get("description", "")
            candidate_text += f"{i+1}. [{media_type}][{source}] {desc}\n"

        prompt = f"""Select the most relevant media for this narration.

NARRATION: "{narration}"

MEDIA OPTIONS (VIDEO preferred, but PHOTO acceptable if more relevant):
{candidate_text}

PRIORITY: Prefer VIDEO over PHOTO, but choose PHOTO if no video is truly relevant to the narration.

Return ONLY the number (1-{min(len(candidates), 15)}) of the best match. Consider:
- Visual relevance to the narration topic
- Tags/description that match the subject matter
- VIDEO is preferred but irrelevant video is worse than relevant photo

Your answer (just the number):"""

        try:
            messages = [{"role": "user", "content": prompt}]
            result = self.openrouter.chat_completion(messages, temperature=0, max_tokens=10)
            content = result.get("content", "1").strip()

            # Extract number from response
            import re
            match = re.search(r'\d+', content)
            if match:
                idx = int(match.group()) - 1
                if 0 <= idx < len(candidates):
                    return candidates[idx]

            return candidates[0]  # Fallback to first
        except Exception as e:
            print(f"    LLM selection failed: {e}, using first candidate")
            return candidates[0]

    def step1_discover_news(self, category: Optional[str] = None, count: int = 8) -> List[Dict]:
        """
        Step 1: Discover trending news topics.

        Args:
            category: Optional category hint (geopolitics, tech, economics)
            count: Number of topics to fetch

        Returns:
            List of topic dicts
        """
        print("\n" + "=" * 60)
        print("Step 1: Discovering Trending News")
        print("=" * 60)

        topics = self.xai.search_news(category=category, count=count)

        print(f"\nFound {len(topics)} topics:")
        for i, topic in enumerate(topics, 1):
            print(f"  {i}. {topic.get('title', 'Unknown')}")

        return topics

    def step2_select_topic(self, topics: List[Dict]) -> Dict:
        """
        Step 2: Select best topic for explainer video.

        Args:
            topics: List of topic dicts from step 1

        Returns:
            Selection dict with topic details and reasoning
        """
        print("\n" + "=" * 60)
        print("Step 2: Selecting Best Topic")
        print("=" * 60)

        selection = self.script_generator.select_topic(topics)

        print(f"\nSelected: {selection.get('selected_topic', 'Unknown')}")
        print(f"Angle: {selection.get('suggested_angle', 'N/A')}")
        print(f"Reasoning: {selection.get('reasoning', 'N/A')}")

        return selection

    def step3_research_topic(self, topic: str, angle: str) -> str:
        """
        Step 3: Deep research on selected topic.

        Args:
            topic: Selected topic title
            angle: Suggested angle for the video

        Returns:
            Research notes as markdown text
        """
        print("\n" + "=" * 60)
        print("Step 3: Researching Topic")
        print("=" * 60)

        research = self.xai.research_topic(topic, context=angle)

        print(f"\nResearch complete: {len(research)} characters")
        print(f"Preview: {research[:200]}...")

        return research

    def step4_generate_script(
        self,
        research: str,
        topic: str,
        angle: str,
        news_hook: str = "",
        target_minutes: int = 8
    ) -> Dict:
        """
        Step 4: Generate video script with scenes.

        Args:
            research: Research notes from step 3
            topic: Topic title
            angle: Educational angle
            news_hook: Recent news event to open with
            target_minutes: Target video length

        Returns:
            Script dict with scenes
        """
        print("\n" + "=" * 60)
        print("Step 4: Generating Script")
        print("=" * 60)

        script = self.script_generator.generate_script(
            research_notes=research,
            topic_title=topic,
            angle=angle,
            news_hook=news_hook,
            target_minutes=target_minutes
        )

        script = self.script_generator.validate_script(script)
        total_duration = self.script_generator.estimate_total_duration(script)

        print(f"\nScript generated:")
        print(f"  Title: {script.get('title', 'Unknown')}")
        print(f"  Scenes: {len(script.get('scenes', []))}")
        print(f"  Estimated duration: {total_duration // 60}m {total_duration % 60}s")

        return script

    def step5_generate_audio(self, script: Dict, output_dir: Path) -> Dict[int, float]:
        """
        Step 5: Generate audio for all scenes.

        Args:
            script: Script dict with scenes
            output_dir: Directory for audio files

        Returns:
            Dict mapping scene_number to duration
        """
        print("\n" + "=" * 60)
        tts_names = {"kokoro": "Kokoro", "edge": "Edge TTS", "elevenlabs": "ElevenLabs"}
        tts_name = tts_names.get(self.tts_provider, "ElevenLabs")
        print(f"Step 5: Generating Audio ({tts_name})")
        print("=" * 60)

        audio_dir = output_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)

        durations = self.audio_generator.generate_all_scenes(
            script.get("scenes", []),
            audio_dir
        )

        total_duration = sum(durations.values())
        print(f"\nAudio complete: {len(durations)} scenes, {total_duration:.1f}s total")

        return durations

    def step6_generate_images(self, script: Dict, output_dir: Path, audio_durations: Dict[int, float] = None) -> Dict:
        """
        Step 6: Get media (videos or images) for all scenes.

        Priority for pexels mode: Pexels video → Pixabay video → Pexels photo → Pixabay photo

        Args:
            script: Script dict with scenes
            output_dir: Directory for image files

        Returns:
            Dict mapping scene_number to image path
        """
        provider_names = {"pexels": "Pexels", "flux": "Flux", "dalle": "DALL-E 3"}
        provider_name = provider_names.get(self.image_provider, self.image_provider)
        print("\n" + "=" * 60)
        print(f"Step 6: Getting Images ({provider_name})")
        print("=" * 60)

        image_dir = output_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)

        images = {}
        scenes = script.get("scenes", [])

        # Reset used IDs for new video
        if self.image_provider == "pexels":
            self.pexels.reset_used_ids()
            self.pixabay.reset_used_ids()

        # Default audio durations if not provided
        if audio_durations is None:
            audio_durations = {}

        for scene in scenes:
            scene_num = scene.get("scene_number", 0)

            image_path = image_dir / f"scene_{scene_num:02d}.png"

            # Skip if already generated
            if image_path.exists():
                print(f"  Scene {scene_num}: Already exists, skipping")
                images[scene_num] = image_path
                continue

            try:
                if self.image_provider == "pexels":
                    # Get keyword and narration from script
                    keyword = scene.get("image_keyword", "") or scene.get("scene_image_description", "nature")
                    narration = scene.get("narration", "")
                    expected_duration = audio_durations.get(scene_num, 5)

                    print(f"  Scene {scene_num}: Searching '{keyword}'...")
                    media = None
                    media_type = None

                    # Collect ALL media candidates (videos + photos from both providers)
                    candidates = []

                    # Get videos from Pexels
                    pexels_videos = self.pexels.search_videos_with_metadata(
                        query=keyword,
                        per_page=5,
                        min_duration=int(expected_duration)
                    )
                    candidates.extend(pexels_videos)

                    # Get videos from Pixabay
                    pixabay_videos = self.pixabay.search_videos_with_metadata(
                        query=keyword,
                        per_page=5,
                        min_duration=int(expected_duration)
                    )
                    candidates.extend(pixabay_videos)

                    # Get photos from Pexels
                    pexels_photos = self.pexels.search_photos_with_metadata(
                        query=keyword,
                        per_page=5
                    )
                    candidates.extend(pexels_photos)

                    # Get photos from Pixabay
                    pixabay_photos = self.pixabay.search_photos_with_metadata(
                        query=keyword,
                        per_page=5
                    )
                    candidates.extend(pixabay_photos)

                    # Use LLM to select the best media (video preferred, photo if more relevant)
                    if candidates:
                        video_count = len([c for c in candidates if c.get("type") == "video"])
                        photo_count = len([c for c in candidates if c.get("type") == "photo"])
                        print(f"    Found {video_count} videos + {photo_count} photos, asking LLM...")
                        selected = self._select_best_media_with_llm(narration, candidates)

                        if selected:
                            selected_type = selected.get("type", "video")

                            if selected_type == "video":
                                # Download video
                                video_path = image_dir / f"scene_{scene_num:02d}.mp4"
                                response = requests.get(selected["url"], timeout=120)
                                response.raise_for_status()
                                with open(video_path, 'wb') as f:
                                    f.write(response.content)

                                # Mark as used
                                if selected["source"] == "pexels":
                                    self.pexels.used_video_ids.add(selected["id"])
                                else:
                                    self.pixabay.used_video_ids.add(selected["id"])

                                media = video_path
                                media_type = "video"
                                tags_preview = selected.get("tags", [])[:3] if selected.get("tags") else []
                                print(f"  Scene {scene_num}: {selected['source']} VIDEO (ID: {selected['id']}, tags: {tags_preview})")

                            else:
                                # Download and resize photo
                                if selected["source"] == "pexels":
                                    # For Pexels, need to create a photo dict compatible with download_and_resize
                                    photo_dict = {"src": {"large2x": selected["url"], "large": selected["url"]}, "id": selected["id"]}
                                    self.pexels.download_and_resize(photo_dict, image_path, 1280, 720)
                                    self.pexels.used_photo_ids.add(selected["id"])
                                else:
                                    # For Pixabay
                                    photo_dict = {"url": selected["url"], "id": selected["id"]}
                                    self.pixabay.download_and_resize_photo(photo_dict, image_path, 1280, 720)
                                    self.pixabay.used_photo_ids.add(selected["id"])

                                media = image_path
                                media_type = "photo"
                                tags_preview = selected.get("tags", [])[:3] if selected.get("tags") else []
                                print(f"  Scene {scene_num}: {selected['source']} PHOTO (ID: {selected['id']}, tags: {tags_preview})")

                    if media:
                        images[scene_num] = {"path": media, "type": media_type}
                    else:
                        print(f"  Scene {scene_num}: No media found for '{keyword}'")

                elif self.image_provider == "flux":
                    image_desc = scene.get("scene_image_description", "")
                    prompt = self.IMAGE_STYLE_PREFIX + image_desc
                    print(f"  Scene {scene_num}: Generating...")

                    image_url = self.replicate.generate_image(
                        prompt=prompt,
                        aspect_ratio="16:9",
                        output_format="png"
                    )

                    response = requests.get(image_url, timeout=60)
                    response.raise_for_status()
                    with open(image_path, 'wb') as f:
                        f.write(response.content)

                    images[scene_num] = image_path
                    print(f"  Scene {scene_num}: Done")

                else:  # dalle
                    image_desc = scene.get("scene_image_description", "")
                    prompt = self.IMAGE_STYLE_PREFIX + image_desc
                    print(f"  Scene {scene_num}: Generating...")

                    image_url = self.openai.generate_image(
                        prompt=prompt,
                        model="dall-e-3",
                        size="1792x1024",
                        quality="standard"
                    )

                    response = requests.get(image_url, timeout=60)
                    response.raise_for_status()
                    with open(image_path, 'wb') as f:
                        f.write(response.content)

                    images[scene_num] = image_path
                    print(f"  Scene {scene_num}: Done")

                # Small delay to avoid rate limiting
                time.sleep(0.5)

            except Exception as e:
                print(f"  Scene {scene_num}: ERROR - {e}")

        print(f"\nImages complete: {len(images)} found")
        return images

    def step7_assemble_videos(
        self,
        script: Dict,
        audio_durations: Dict[int, float],
        images: Dict[int, Path],
        output_dir: Path
    ) -> Path:
        """
        Step 7: Assemble scene videos and concatenate.

        Args:
            script: Script dict
            audio_durations: Scene durations from step 5
            images: Image paths from step 6
            output_dir: Output directory

        Returns:
            Path to final video
        """
        print("\n" + "=" * 60)
        print("Step 7: Assembling Videos")
        print("=" * 60)

        scene_dir = output_dir / "scenes"
        scene_dir.mkdir(parents=True, exist_ok=True)

        audio_dir = output_dir / "audio"
        scene_videos = []

        scenes = script.get("scenes", [])

        for scene in scenes:
            scene_num = scene.get("scene_number", 0)

            # Try mp3 first (ElevenLabs), then wav (Kokoro fallback)
            audio_path = audio_dir / f"scene_{scene_num:02d}.mp3"
            if not audio_path.exists():
                audio_path = audio_dir / f"scene_{scene_num:02d}.wav"

            # Get media info (can be dict with path/type or just Path for backward compat)
            media_info = images.get(scene_num)
            if isinstance(media_info, dict):
                media_path = media_info.get("path")
                media_type = media_info.get("type", "photo")
            else:
                media_path = media_info
                media_type = "photo"

            video_path = scene_dir / f"scene_{scene_num:02d}.mp4"

            if not audio_path.exists():
                print(f"  Scene {scene_num}: Missing audio, skipping")
                continue

            if not media_path or not Path(media_path).exists():
                print(f"  Scene {scene_num}: Missing media, skipping")
                continue

            if video_path.exists():
                print(f"  Scene {scene_num}: Already assembled")
                scene_videos.append(video_path)
                continue

            print(f"  Scene {scene_num}: Assembling ({media_type})...")

            try:
                if media_type == "video":
                    # Trim video and overlay audio
                    self.video_assembler.create_video_with_audio(
                        video_path=media_path,
                        audio_path=audio_path,
                        output_path=video_path
                    )
                else:
                    # Photo with Ken Burns zoom
                    self.video_assembler.create_slide_video(
                        image_path=media_path,
                        audio_path=audio_path,
                        output_path=video_path,
                        zoom_per_sec=self.zoom_per_sec
                    )
                scene_videos.append(video_path)
            except Exception as e:
                print(f"  Scene {scene_num}: ERROR - {e}")

        # Concatenate all scenes
        print("\nConcatenating scenes...")
        final_video = output_dir / "final_video.mp4"

        if len(scene_videos) > 0:
            self.video_assembler.concatenate_videos(
                video_paths=sorted(scene_videos),
                output_path=final_video
            )
            print(f"Final video: {final_video}")
        else:
            print("ERROR: No scene videos to concatenate")

        return final_video

    def step7b_add_branding(self, video_path: Path, output_dir: Path) -> Path:
        """
        Step 7b: Add intro/outro branding to the video.

        Args:
            video_path: Path to the assembled video
            output_dir: Output directory

        Returns:
            Path to branded video
        """
        print("\n" + "=" * 60)
        print("Step 7b: Adding Branding (Intro/Outro)")
        print("=" * 60)

        if not video_path.exists():
            print("ERROR: Input video does not exist")
            return video_path

        # Check branding assets
        for key in ["logo", "intro_sound", "bg_music"]:
            if not self.branding[key].exists():
                print(f"WARNING: Missing {key}: {self.branding[key]}")
                return video_path

        branded_video = output_dir / "branded_video.mp4"

        try:
            self.video_assembler.add_branding(
                main_video_path=video_path,
                output_path=branded_video,
                logo_path=self.branding["logo"],
                intro_sound_path=self.branding["intro_sound"],
                bg_music_path=self.branding["bg_music"],
                intro_duration=self.branding["intro_duration"],
                outro_duration=self.branding["outro_duration"],
                fade_duration=self.branding["fade_duration"],
                bg_music_volume=self.branding["bg_music_volume"]
            )
            print(f"Branded video: {branded_video}")
            return branded_video
        except Exception as e:
            print(f"ERROR adding branding: {e}")
            return video_path

    def step8_queue_for_upload(self, video_path: Path, script: Dict, topic_hash: str):
        """
        Step 8: Queue video for YouTube upload.

        Args:
            video_path: Path to final video
            script: Script dict for metadata
            topic_hash: Hash identifier for the topic
        """
        print("\n" + "=" * 60)
        print("Step 8: Queueing for Upload")
        print("=" * 60)

        if not video_path.exists():
            print("ERROR: Video file does not exist")
            return

        # Create queue directory
        queue_dir = self.upload_queue_dir / f"explainer_{topic_hash}"
        queue_dir.mkdir(parents=True, exist_ok=True)

        # Copy video
        import shutil
        dest_video = queue_dir / video_path.name
        if not dest_video.exists():
            shutil.copy2(video_path, dest_video)

        # Create metadata
        metadata = {
            "title": script.get("title", "Explainer Video"),
            "description": script.get("description", "Educational explainer video."),
            "tags": script.get("tags", ["explainer", "education"]),
            "category_id": "27",  # Education
            "privacy_status": "private",
            "uploaded": False,
            "creation_timestamp": time.time(),
            "topic_hash": topic_hash,
            "video_filename": video_path.name
        }

        metadata_path = queue_dir / "metadata.json"
        self._save_json(metadata, metadata_path)

        print(f"Queued: {queue_dir}")
        print(f"Upload via: scripts/upload_next_episode.sh")

    def run(
        self,
        category: Optional[str] = None,
        target_minutes: int = 8,
        auto_approve: bool = False
    ) -> Path:
        """
        Run the full explainer pipeline.

        Args:
            category: Optional news category to search
            target_minutes: Target video length
            auto_approve: Skip topic approval step

        Returns:
            Path to final video
        """
        print("\n" + "=" * 60)
        print("EXPLAINER VIDEO PIPELINE")
        print("=" * 60)
        print(f"Category: {category or 'all'}")
        print(f"Target: {target_minutes} minutes")
        print("=" * 60)

        # Step 1: Discover news
        topics = self.step1_discover_news(category=category)

        if not topics:
            print("ERROR: No topics found")
            return None

        # Step 2: Select topic
        selection = self.step2_select_topic(topics)

        topic_title = selection.get("selected_topic", topics[0].get("title", "Unknown"))
        topic_angle = selection.get("educational_angle", selection.get("suggested_angle", "general overview"))
        news_hook = selection.get("news_hook", "")
        topic_hash = self._generate_hash(topic_title)

        # Create output directory
        output_dir = self.output_dir / topic_hash
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save intermediate outputs
        self._save_json(topics, output_dir / "01_news_topics.json")
        self._save_json(selection, output_dir / "02_selected_topic.json")

        # APPROVAL CHECKPOINT
        if not auto_approve:
            print("\n" + "=" * 60)
            print("APPROVAL REQUIRED")
            print("=" * 60)
            print(f"\nSelected topic: {topic_title}")
            print(f"Angle: {topic_angle}")
            print(f"\nTo proceed, run again with the topic hash:")
            print(f"  python -m src.pipelines.explainer_pipeline --continue {topic_hash}")
            print(f"\nOr approve automatically:")
            print(f"  python -m src.pipelines.explainer_pipeline --auto-approve")
            print(f"\nOutput directory: {output_dir}")
            return output_dir

        # Step 3: Research
        research = self.step3_research_topic(topic_title, topic_angle)
        self._save_text(research, output_dir / "03_research_notes.md")

        # Step 4: Generate script
        script = self.step4_generate_script(research, topic_title, topic_angle, news_hook, target_minutes)
        self._save_json(script, output_dir / "04_script.json")

        # Step 5: Generate audio
        durations = self.step5_generate_audio(script, output_dir)

        # Step 6: Get media (videos/images)
        media = self.step6_generate_images(script, output_dir, durations)

        # Step 7: Assemble videos
        final_video = self.step7_assemble_videos(script, durations, media, output_dir)

        # Step 7b: Add branding (intro/outro)
        if self.add_branding:
            final_video = self.step7b_add_branding(final_video, output_dir)

        # Step 8: Queue for upload
        self.step8_queue_for_upload(final_video, script, topic_hash)

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Output: {output_dir}")
        print(f"Video: {final_video}")

        return final_video

    def continue_from_approval(self, topic_hash: str, target_minutes: int = 8) -> Path:
        """
        Continue pipeline from approval checkpoint.

        Args:
            topic_hash: Hash from previous run
            target_minutes: Target video length

        Returns:
            Path to final video
        """
        output_dir = self.output_dir / topic_hash

        if not output_dir.exists():
            print(f"ERROR: Output directory not found: {output_dir}")
            return None

        # Load saved data
        selection = self._load_json(output_dir / "02_selected_topic.json")

        if not selection:
            print("ERROR: No selection data found")
            return None

        topic_title = selection.get("selected_topic", "Unknown")
        topic_angle = selection.get("educational_angle", selection.get("suggested_angle", "general overview"))
        news_hook = selection.get("news_hook", "")

        print("\n" + "=" * 60)
        print(f"Continuing: {topic_title}")
        print("=" * 60)

        # Check if research exists
        research_path = output_dir / "03_research_notes.md"
        if research_path.exists():
            with open(research_path, 'r') as f:
                research = f.read()
            print("Using existing research...")
        else:
            research = self.step3_research_topic(topic_title, topic_angle)
            self._save_text(research, research_path)

        # Check if script exists
        script_path = output_dir / "04_script.json"
        if script_path.exists():
            script = self._load_json(script_path)
            print("Using existing script...")
        else:
            script = self.step4_generate_script(research, topic_title, topic_angle, news_hook, target_minutes)
            self._save_json(script, script_path)

        # Generate audio
        durations = self.step5_generate_audio(script, output_dir)

        # Get media (videos/images)
        media = self.step6_generate_images(script, output_dir, durations)

        # Assemble videos
        final_video = self.step7_assemble_videos(script, durations, media, output_dir)

        # Add branding (intro/outro)
        if self.add_branding:
            final_video = self.step7b_add_branding(final_video, output_dir)

        # Queue for upload
        self.step8_queue_for_upload(final_video, script, topic_hash)

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Output: {output_dir}")
        print(f"Video: {final_video}")

        return final_video


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Explainer Video Pipeline")
    parser.add_argument("--category", "-c", help="News category (geopolitics, tech, economics)")
    parser.add_argument("--minutes", "-m", type=int, default=8, help="Target video length in minutes")
    parser.add_argument("--auto-approve", "-a", action="store_true", help="Skip topic approval")
    parser.add_argument("--continue", "-k", dest="continue_hash", help="Continue from topic hash")
    parser.add_argument("--voice-id", help="ElevenLabs voice ID")
    parser.add_argument("--art-style", default="photo", help="Art style (photo, editorial, flat_vector, watercolor)")
    parser.add_argument("--image-provider", default="pexels", choices=["pexels", "flux", "dalle"], help="Image provider (pexels, flux, or dalle)")

    args = parser.parse_args()

    # Load environment
    from dotenv import load_dotenv
    load_dotenv('.env.secrets')

    pipeline = ExplainerPipeline(
        voice_id=args.voice_id,
        art_style=args.art_style,
        image_provider=args.image_provider
    )

    if args.continue_hash:
        pipeline.continue_from_approval(args.continue_hash, args.minutes)
    else:
        pipeline.run(
            category=args.category,
            target_minutes=args.minutes,
            auto_approve=args.auto_approve
        )


if __name__ == "__main__":
    main()
