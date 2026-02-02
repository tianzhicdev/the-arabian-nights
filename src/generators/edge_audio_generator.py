"""
Edge-TTS audio generator for narration.
Uses Microsoft Edge TTS for high-quality speech synthesis.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class EdgeAudioGenerator:
    """
    Edge-TTS wrapper for storytelling narration.

    Uses Microsoft's neural TTS voices with rate control.
    """

    # Recommended voices for narration
    VOICE_PRESETS = {
        "male_warm": "en-US-GuyNeural",
        "female_natural": "en-US-AriaNeural",
        "british_male": "en-GB-RyanNeural",
        "storyteller": "en-US-GuyNeural",
    }

    def __init__(
        self,
        voice: str = "en-US-GuyNeural",
        rate: str = "-30%"
    ):
        """
        Initialize Edge-TTS audio generator.

        Args:
            voice: Voice ID (e.g., 'en-US-GuyNeural')
            rate: Speech rate adjustment (e.g., '-30%' for slower)
        """
        self.voice = voice
        self.rate = rate

    async def _generate_async(self, text: str, output_path: Path) -> float:
        """Generate audio asynchronously."""
        import edge_tts

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate
        )
        await communicate.save(str(output_path))

        # Get duration
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(output_path)],
            capture_output=True, text=True
        )
        return float(result.stdout.strip()) if result.stdout.strip() else 0

    def generate_audio(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        rate: Optional[str] = None
    ) -> float:
        """
        Generate audio from text.

        Args:
            text: Text to synthesize
            output_path: Path to save audio file (.mp3)
            voice: Override voice ID
            rate: Override rate

        Returns:
            Audio duration in seconds
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Temporarily override settings if provided
        orig_voice, orig_rate = self.voice, self.rate
        if voice:
            self.voice = voice
        if rate:
            self.rate = rate

        try:
            duration = asyncio.run(self._generate_async(text, output_path))
        finally:
            self.voice, self.rate = orig_voice, orig_rate

        return duration

    def generate_scene_audio(
        self,
        scene: Dict,
        output_path: Path
    ) -> float:
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

        return self.generate_audio(text, output_path)

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

            try:
                duration = self.generate_scene_audio(scene, output_path)
                durations[scene_num] = duration
                print(f"  Scene {scene_num}: {duration:.1f}s")
            except Exception as e:
                print(f"  Scene {scene_num}: ERROR - {e}")
                durations[scene_num] = 0

        return durations


if __name__ == "__main__":
    generator = EdgeAudioGenerator(voice="en-US-GuyNeural", rate="-30%")

    test_text = """
    In the ancient city of Baghdad, where the Tigris River flows like a silver ribbon,
    there lived a young merchant named Hassan.
    """

    print("Testing Edge-TTS generator...")
    output = Path("output/test_edge.mp3")
    duration = generator.generate_audio(test_text, output)
    print(f"Generated: {output} ({duration:.1f}s)")
