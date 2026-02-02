"""
ElevenLabs audio generator wrapper for explainer videos.
Adapts the existing ElevenLabs generator for explainer script format.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from src.generators.elevenlabs_audio_generator import ElevenLabsSceneGenerator


class ElevenLabsExplainerAudio:
    """
    ElevenLabs TTS wrapper for explainer video narration.

    Uses the existing ElevenLabsSceneGenerator but adapts the scene format.
    """

    def __init__(
        self,
        voice_id: str = None,
        api_key: str = None,
        model_id: str = "eleven_turbo_v2_5"
    ):
        """
        Initialize ElevenLabs audio generator.

        Args:
            voice_id: ElevenLabs voice ID (defaults to ELEVENLABS_VOICE_ID env var)
            api_key: ElevenLabs API key (defaults to ELEVEN_LABS_KEY env var)
            model_id: Model ID (eleven_turbo_v2_5 for speed, eleven_v3 for emotion tags)
        """
        self.voice_id = voice_id or os.getenv('ELEVENLABS_VOICE_ID') or 'pNInz6obpgDQGcFmaJgB'  # Default: Adam
        self.api_key = api_key or os.getenv('ELEVEN_LABS_KEY')

        if not self.api_key:
            raise ValueError("ElevenLabs API key not provided. Set ELEVEN_LABS_KEY environment variable.")

        self.model_id = model_id
        self._generator = None

    def _get_generator(self) -> ElevenLabsSceneGenerator:
        """Lazy load the generator."""
        if self._generator is None:
            self._generator = ElevenLabsSceneGenerator(
                voice_id=self.voice_id,
                api_key=self.api_key,
                model_id=self.model_id
            )
        return self._generator

    def generate_audio(self, text: str, output_path: Path) -> float:
        """
        Generate audio from text.

        Args:
            text: Text to synthesize
            output_path: Path to save audio file (.mp3)

        Returns:
            Audio duration in seconds
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Adapt to ElevenLabsSceneGenerator format
        scene = {
            'scene_id': 0,
            'sentences': [text],
            'pause_after': 0
        }

        generator = self._get_generator()
        return generator.generate_scene_audio(scene, output_path)

    def generate_scene_audio(self, scene: Dict, output_path: Path) -> float:
        """
        Generate audio for a single scene.

        Args:
            scene: Scene dict with 'narration' or 'text' key
            output_path: Path to save audio file

        Returns:
            Audio duration in seconds
        """
        text = scene.get('narration') or scene.get('text', '')
        if not text:
            raise ValueError("Scene has no narration or text")

        scene_num = scene.get('scene_number', 0)

        # Adapt to ElevenLabsSceneGenerator format
        adapted_scene = {
            'scene_id': scene_num,
            'sentences': [text],
            'pause_after': 0
        }

        generator = self._get_generator()
        return generator.generate_scene_audio(adapted_scene, output_path)

    def generate_all_scenes(
        self,
        scenes: List[Dict],
        output_dir: Path
    ) -> Dict[int, float]:
        """
        Generate audio for all scenes.

        Args:
            scenes: List of scene dicts with 'scene_number' and 'narration'
            output_dir: Directory to save audio files

        Returns:
            Dict mapping scene_number to duration in seconds
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        durations = {}

        for scene in scenes:
            scene_num = scene.get('scene_number', scenes.index(scene) + 1)
            output_path = output_dir / f"scene_{scene_num:02d}.mp3"

            # Skip if already exists
            if output_path.exists() and output_path.stat().st_size > 0:
                import subprocess
                result = subprocess.run(
                    ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                     '-of', 'default=noprint_wrappers=1:nokey=1', str(output_path)],
                    capture_output=True, text=True
                )
                duration = float(result.stdout.strip()) if result.stdout.strip() else 0
                durations[scene_num] = duration
                print(f"  Scene {scene_num}: {duration:.1f}s (exists)")
                continue

            try:
                duration = self.generate_scene_audio(scene, output_path)
                durations[scene_num] = duration
                print(f"  Scene {scene_num}: {duration:.1f}s")
            except Exception as e:
                print(f"  Scene {scene_num}: ERROR - {e}")
                durations[scene_num] = 0

        return durations


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv('.env.secrets')

    generator = ElevenLabsExplainerAudio()

    test_text = """
    In the ancient city of Baghdad, where the Tigris River flows like a silver ribbon,
    there lived a young merchant named Hassan. His story begins on a moonlit night.
    """

    print("Testing ElevenLabs explainer audio...")
    output = Path("output/test_elevenlabs.mp3")
    duration = generator.generate_audio(test_text, output)
    print(f"Generated: {output} ({duration:.1f}s)")
