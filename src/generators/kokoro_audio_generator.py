"""
Kokoro TTS audio generator for natural narration.
Uses local ONNX model for high-quality, natural-paced speech synthesis.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


class KokoroAudioGenerator:
    """
    Kokoro TTS wrapper for natural storytelling narration.

    Uses kokoro-onnx for local inference with natural prosody
    (not mechanical time-stretching like cloud TTS services).
    """

    # Model file locations (relative to project root or absolute)
    DEFAULT_MODEL_PATH = "experiments/tts_tests/kokoro-v1.0.onnx"
    DEFAULT_VOICES_PATH = "experiments/tts_tests/voices-v1.0.bin"

    # Recommended voices for narration
    VOICE_PRESETS = {
        "deep_male": "am_onyx",
        "dramatic_male": "am_fenrir",
        "british_male": "bm_george",
        "warm_male": "am_adam",
        "female_narrator": "af_bella",
        "british_female": "bf_emma",
    }

    def __init__(
        self,
        voice: str = "am_onyx",
        speed: float = 0.75,
        model_path: Optional[str] = None,
        voices_path: Optional[str] = None
    ):
        """
        Initialize Kokoro audio generator.

        Args:
            voice: Voice ID (e.g., 'am_onyx' for deep American male)
            speed: Speech speed (0.65=slow dramatic, 0.75=storytelling, 1.0=normal)
            model_path: Path to kokoro-v1.0.onnx model
            voices_path: Path to voices-v1.0.bin file
        """
        self.voice = voice
        self.speed = speed

        # Resolve model paths
        project_root = Path(__file__).parent.parent.parent
        self.model_path = Path(model_path) if model_path else project_root / self.DEFAULT_MODEL_PATH
        self.voices_path = Path(voices_path) if voices_path else project_root / self.DEFAULT_VOICES_PATH

        self._kokoro = None

    def _get_kokoro(self):
        """Lazy load Kokoro model."""
        if self._kokoro is None:
            try:
                from kokoro_onnx import Kokoro
            except ImportError:
                raise ImportError("kokoro-onnx not installed. Run: pip install kokoro-onnx")

            if not self.model_path.exists():
                raise FileNotFoundError(
                    f"Kokoro model not found at {self.model_path}. "
                    "Download from: https://github.com/thewh1teagle/kokoro-onnx/releases"
                )
            if not self.voices_path.exists():
                raise FileNotFoundError(
                    f"Kokoro voices not found at {self.voices_path}. "
                    "Download from: https://github.com/thewh1teagle/kokoro-onnx/releases"
                )

            self._kokoro = Kokoro(str(self.model_path), str(self.voices_path))

        return self._kokoro

    def get_available_voices(self) -> List[str]:
        """Get list of available voice IDs."""
        return self._get_kokoro().get_voices()

    def generate_audio(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        speed: Optional[float] = None
    ) -> float:
        """
        Generate audio from text.

        Args:
            text: Text to synthesize
            output_path: Path to save audio file (.wav or .mp3)
            voice: Override voice ID
            speed: Override speed

        Returns:
            Audio duration in seconds
        """
        import soundfile as sf

        kokoro = self._get_kokoro()
        voice = voice or self.voice
        speed = speed or self.speed

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate audio
        samples, sample_rate = kokoro.create(text, voice=voice, speed=speed)

        # Save as WAV first
        wav_path = output_path.with_suffix('.wav')
        sf.write(str(wav_path), samples, sample_rate)

        # Calculate duration
        duration = len(samples) / sample_rate

        # Convert to MP3 if requested
        if output_path.suffix.lower() == '.mp3':
            subprocess.run(
                ['ffmpeg', '-y', '-i', str(wav_path), '-b:a', '192k', str(output_path)],
                capture_output=True,
                check=True
            )
            wav_path.unlink()  # Remove intermediate WAV

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
        output_dir: Path,
        parallel: bool = False,
        max_workers: int = 4
    ) -> Dict[int, float]:
        """
        Generate audio for all scenes.

        Args:
            scenes: List of scene dicts with 'scene_number' and 'narration'
            output_dir: Directory to save audio files
            parallel: Use parallel generation (faster but uses more memory)
            max_workers: Number of parallel workers

        Returns:
            Dict mapping scene_number to duration in seconds
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        durations = {}

        if parallel:
            # Parallel generation
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for scene in scenes:
                    scene_num = scene.get('scene_number', scenes.index(scene) + 1)
                    output_path = output_dir / f"scene_{scene_num:02d}.wav"
                    future = executor.submit(self.generate_scene_audio, scene, output_path)
                    futures[future] = scene_num

                for future in as_completed(futures):
                    scene_num = futures[future]
                    try:
                        duration = future.result()
                        durations[scene_num] = duration
                        print(f"  Scene {scene_num}: {duration:.1f}s")
                    except Exception as e:
                        print(f"  Scene {scene_num}: ERROR - {e}")
                        durations[scene_num] = 0
        else:
            # Sequential generation
            for scene in scenes:
                scene_num = scene.get('scene_number', scenes.index(scene) + 1)
                output_path = output_dir / f"scene_{scene_num:02d}.wav"

                try:
                    duration = self.generate_scene_audio(scene, output_path)
                    durations[scene_num] = duration
                    print(f"  Scene {scene_num}: {duration:.1f}s")
                except Exception as e:
                    print(f"  Scene {scene_num}: ERROR - {e}")
                    durations[scene_num] = 0

        return durations

    def estimate_duration(self, text: str) -> float:
        """
        Estimate audio duration without generating.
        Based on average speaking rate at given speed.

        Args:
            text: Text to estimate

        Returns:
            Estimated duration in seconds
        """
        # Average speaking rate: ~150 words/min at speed=1.0
        # Adjusted for our speed setting
        words = len(text.split())
        words_per_minute = 150 * self.speed
        return (words / words_per_minute) * 60


if __name__ == "__main__":
    # Test the generator
    generator = KokoroAudioGenerator(voice="am_onyx", speed=0.75)

    print("Available voices:")
    voices = generator.get_available_voices()
    male_voices = [v for v in voices if v.startswith('am_') or v.startswith('bm_')]
    print(f"  Male voices: {', '.join(male_voices[:5])}...")

    test_text = """
    In the ancient city of Baghdad, where the Tigris River flows like a silver ribbon,
    there lived a young merchant named Hassan. His story begins on a moonlit night,
    when destiny would change everything.
    """

    print("\nGenerating test audio...")
    output_path = Path("output/test_kokoro.wav")
    duration = generator.generate_audio(test_text, output_path)
    print(f"Generated: {output_path} ({duration:.1f}s)")
