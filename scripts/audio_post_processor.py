#!/usr/bin/env python3
"""
Audio Post-Processing for TTS Output

Improves audio quality through:
1. DeepFilterNet - Neural network noise suppression (best quality)
2. noisereduce - Spectral gating noise reduction
3. FFmpeg filters - EQ, compression, normalization

Usage:
    python scripts/audio_post_processor.py input.mp3 -o output.mp3 --method deepfilter
    python scripts/audio_post_processor.py input.mp3 --method all  # Apply all enhancements
"""

import argparse
import subprocess
import tempfile
import shutil
from pathlib import Path
import sys


def check_dependencies():
    """Check which post-processing tools are available."""
    available = {}

    # Check ffmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        available['ffmpeg'] = True
    except:
        available['ffmpeg'] = False

    # Check DeepFilterNet
    try:
        import importlib
        importlib.import_module('df')
        available['deepfilter'] = True
    except:
        available['deepfilter'] = False

    # Check noisereduce
    try:
        import noisereduce
        available['noisereduce'] = True
    except:
        available['noisereduce'] = False

    return available


def convert_to_wav(input_path: Path, output_path: Path, sample_rate: int = 48000) -> bool:
    """Convert audio to WAV format at specified sample rate."""
    cmd = [
        'ffmpeg', '-y', '-i', str(input_path),
        '-ar', str(sample_rate),
        '-ac', '1',  # mono
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def convert_to_mp3(input_path: Path, output_path: Path, quality: int = 2) -> bool:
    """Convert WAV to high-quality MP3."""
    cmd = [
        'ffmpeg', '-y', '-i', str(input_path),
        '-codec:a', 'libmp3lame',
        '-qscale:a', str(quality),
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def apply_deepfilter(input_path: Path, output_path: Path) -> bool:
    """
    Apply DeepFilterNet neural network noise suppression.
    Best quality but requires deepfilternet package.

    Install: pip install deepfilternet
    """
    try:
        from df.enhance import enhance, init_df, load_audio, save_audio
        from df import config

        print("  Loading DeepFilterNet model...")
        model, df_state, _ = init_df()

        print("  Loading audio...")
        audio, _ = load_audio(str(input_path), sr=df_state.sr())

        print("  Enhancing audio...")
        enhanced = enhance(model, df_state, audio)

        print("  Saving enhanced audio...")
        save_audio(str(output_path), enhanced, df_state.sr())

        return True
    except ImportError:
        print("  ERROR: DeepFilterNet not installed. Run: pip install deepfilternet")
        return False
    except Exception as e:
        print(f"  ERROR: DeepFilterNet failed: {e}")
        return False


def apply_noisereduce(input_path: Path, output_path: Path,
                      stationary: bool = True, prop_decrease: float = 0.75) -> bool:
    """
    Apply spectral gating noise reduction.

    Install: pip install noisereduce

    Args:
        stationary: Use stationary (True) or non-stationary (False) algorithm
        prop_decrease: Proportion to reduce noise by (0-1)
    """
    try:
        import noisereduce as nr
        import numpy as np
        import scipy.io.wavfile as wav

        print("  Loading audio...")
        rate, data = wav.read(str(input_path))

        # Convert to float
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            data = data.astype(np.float32) / 2147483648.0

        print(f"  Applying {'stationary' if stationary else 'non-stationary'} noise reduction...")

        if stationary:
            reduced = nr.reduce_noise(
                y=data,
                sr=rate,
                stationary=True,
                prop_decrease=prop_decrease,
                n_fft=512,
                n_std_thresh_stationary=1.5,
            )
        else:
            reduced = nr.reduce_noise(
                y=data,
                sr=rate,
                stationary=False,
                prop_decrease=prop_decrease,
                time_constant_s=2.0,
                freq_mask_smooth_hz=500,
            )

        # Convert back to int16
        reduced = np.clip(reduced * 32768, -32768, 32767).astype(np.int16)

        print("  Saving reduced audio...")
        wav.write(str(output_path), rate, reduced)

        return True
    except ImportError:
        print("  ERROR: noisereduce not installed. Run: pip install noisereduce")
        return False
    except Exception as e:
        print(f"  ERROR: noisereduce failed: {e}")
        return False


def apply_ffmpeg_enhance(input_path: Path, output_path: Path,
                         method: str = 'full') -> bool:
    """
    Apply FFmpeg audio enhancement filters.

    Methods:
        - 'denoise': afftdn FFT-based denoiser
        - 'voice': highpass/lowpass for voice frequency isolation
        - 'gate': noise gate to silence quiet parts
        - 'normalize': loudnorm for consistent volume
        - 'compress': dynamic range compression
        - 'full': all of the above combined
    """

    filters = {
        'denoise': 'afftdn=nf=-25:nr=12:nt=w',
        'voice': 'highpass=f=80,lowpass=f=8000',
        'gate': 'agate=threshold=0.01:attack=20:release=200:ratio=2',
        'normalize': 'loudnorm=I=-16:TP=-1.5:LRA=11',
        'compress': 'acompressor=threshold=-20dB:ratio=4:attack=5:release=50',
    }

    if method == 'full':
        # Optimal order: denoise -> voice EQ -> gate -> compress -> normalize
        filter_chain = ','.join([
            filters['denoise'],
            filters['voice'],
            filters['gate'],
            filters['compress'],
            filters['normalize'],
        ])
    elif method in filters:
        filter_chain = filters[method]
    else:
        print(f"  ERROR: Unknown method '{method}'")
        return False

    print(f"  Applying FFmpeg filters: {method}")
    cmd = [
        'ffmpeg', '-y', '-i', str(input_path),
        '-af', filter_chain,
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: FFmpeg failed: {result.stderr}")
        return False

    return True


def apply_all_enhancements(input_path: Path, output_path: Path,
                           available: dict) -> bool:
    """Apply the best available enhancement pipeline."""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        current = input_path
        stage = 0

        # Stage 1: DeepFilterNet (best neural denoising)
        if available.get('deepfilter'):
            stage += 1
            next_file = tmpdir / f"stage{stage}_deepfilter.wav"
            print(f"\n[Stage {stage}] DeepFilterNet neural denoising...")

            # Convert to 48kHz WAV for DeepFilterNet
            wav_input = tmpdir / "input_48k.wav"
            convert_to_wav(current, wav_input, sample_rate=48000)

            if apply_deepfilter(wav_input, next_file):
                current = next_file
            else:
                print("  Skipping DeepFilterNet stage")

        # Stage 2: noisereduce (spectral gating for residual noise)
        if available.get('noisereduce'):
            stage += 1
            next_file = tmpdir / f"stage{stage}_noisereduce.wav"
            print(f"\n[Stage {stage}] Spectral gating noise reduction...")

            # Ensure WAV format
            if current.suffix != '.wav':
                wav_input = tmpdir / "input_nr.wav"
                convert_to_wav(current, wav_input, sample_rate=24000)
                current = wav_input

            if apply_noisereduce(current, next_file, stationary=True, prop_decrease=0.5):
                current = next_file
            else:
                print("  Skipping noisereduce stage")

        # Stage 3: FFmpeg enhancement (EQ, compression, normalization)
        if available.get('ffmpeg'):
            stage += 1
            next_file = tmpdir / f"stage{stage}_ffmpeg.wav"
            print(f"\n[Stage {stage}] FFmpeg enhancement (EQ, compression, normalize)...")

            if apply_ffmpeg_enhance(current, next_file, method='full'):
                current = next_file
            else:
                print("  Skipping FFmpeg stage")

        # Final: Convert to output format
        print(f"\n[Final] Converting to output format...")
        if output_path.suffix.lower() == '.mp3':
            return convert_to_mp3(current, output_path, quality=2)
        else:
            shutil.copy(current, output_path)
            return True


def get_audio_info(path: Path) -> dict:
    """Get audio file information."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration,size:stream=sample_rate,channels',
        '-of', 'json', str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        import json
        return json.loads(result.stdout)
    return {}


def main():
    parser = argparse.ArgumentParser(
        description='Post-process TTS audio for improved quality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Methods:
  deepfilter   Neural network noise suppression (best quality, requires deepfilternet)
  noisereduce  Spectral gating noise reduction (requires noisereduce)
  ffmpeg       FFmpeg filters (denoise, voice EQ, compress, normalize)
  all          Apply all available enhancements in optimal order

FFmpeg sub-methods (use with --ffmpeg-method):
  denoise      FFT-based denoiser (afftdn)
  voice        Voice frequency isolation (80Hz-8kHz)
  gate         Noise gate for silence
  normalize    Loudness normalization
  compress     Dynamic range compression
  full         All FFmpeg filters combined (default)

Examples:
  %(prog)s input.mp3 -o output.mp3 --method deepfilter
  %(prog)s input.mp3 -o output.mp3 --method ffmpeg --ffmpeg-method denoise
  %(prog)s input.mp3 -o output.mp3 --method all
        """
    )

    parser.add_argument('input', type=Path, nargs='?', help='Input audio file')
    parser.add_argument('-o', '--output', type=Path, help='Output audio file')
    parser.add_argument('--method', choices=['deepfilter', 'noisereduce', 'ffmpeg', 'all'],
                        default='all', help='Enhancement method (default: all)')
    parser.add_argument('--ffmpeg-method', default='full',
                        choices=['denoise', 'voice', 'gate', 'normalize', 'compress', 'full'],
                        help='FFmpeg filter method (default: full)')
    parser.add_argument('--noise-reduce-strength', type=float, default=0.75,
                        help='Noise reduction strength 0-1 (default: 0.75)')
    parser.add_argument('--check-deps', action='store_true',
                        help='Check available dependencies and exit')

    args = parser.parse_args()

    # Check dependencies
    available = check_dependencies()

    if args.check_deps:
        print("Available post-processing tools:")
        print(f"  FFmpeg:        {'YES' if available['ffmpeg'] else 'NO'}")
        print(f"  DeepFilterNet: {'YES' if available['deepfilter'] else 'NO (pip install deepfilternet)'}")
        print(f"  noisereduce:   {'YES' if available['noisereduce'] else 'NO (pip install noisereduce)'}")
        return 0

    if not args.input:
        parser.error("input file is required")

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}")
        return 1

    # Set output path
    if args.output:
        output_path = args.output
    else:
        output_path = args.input.with_stem(args.input.stem + '_enhanced')

    print("=" * 60)
    print("Audio Post-Processor")
    print("=" * 60)
    print(f"Input:  {args.input}")
    print(f"Output: {output_path}")
    print(f"Method: {args.method}")
    print()

    # Get input info
    info = get_audio_info(args.input)
    if info:
        fmt = info.get('format', {})
        duration = float(fmt.get('duration', 0))
        size_mb = int(fmt.get('size', 0)) / 1024 / 1024
        print(f"Input duration: {duration:.1f}s ({duration/60:.1f} min)")
        print(f"Input size: {size_mb:.2f} MB")

    print()

    success = False

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        if args.method == 'all':
            success = apply_all_enhancements(args.input, output_path, available)

        elif args.method == 'deepfilter':
            if not available['deepfilter']:
                print("ERROR: DeepFilterNet not available. Install: pip install deepfilternet")
                return 1

            # Convert to 48kHz WAV
            wav_input = tmpdir / "input_48k.wav"
            wav_output = tmpdir / "output_48k.wav"
            convert_to_wav(args.input, wav_input, sample_rate=48000)

            if apply_deepfilter(wav_input, wav_output):
                success = convert_to_mp3(wav_output, output_path) if output_path.suffix == '.mp3' else shutil.copy(wav_output, output_path)
                success = True

        elif args.method == 'noisereduce':
            if not available['noisereduce']:
                print("ERROR: noisereduce not available. Install: pip install noisereduce")
                return 1

            wav_input = tmpdir / "input.wav"
            wav_output = tmpdir / "output.wav"
            convert_to_wav(args.input, wav_input, sample_rate=24000)

            if apply_noisereduce(wav_input, wav_output, prop_decrease=args.noise_reduce_strength):
                if output_path.suffix == '.mp3':
                    success = convert_to_mp3(wav_output, output_path)
                else:
                    shutil.copy(wav_output, output_path)
                    success = True

        elif args.method == 'ffmpeg':
            if not available['ffmpeg']:
                print("ERROR: FFmpeg not available")
                return 1
            success = apply_ffmpeg_enhance(args.input, output_path, method=args.ffmpeg_method)

    print()
    print("=" * 60)

    if success and output_path.exists():
        info = get_audio_info(output_path)
        if info:
            fmt = info.get('format', {})
            duration = float(fmt.get('duration', 0))
            size_mb = int(fmt.get('size', 0)) / 1024 / 1024
            print(f"SUCCESS: {output_path}")
            print(f"Output duration: {duration:.1f}s ({duration/60:.1f} min)")
            print(f"Output size: {size_mb:.2f} MB")
        return 0
    else:
        print("FAILED: Post-processing did not complete successfully")
        return 1


if __name__ == '__main__':
    sys.exit(main())
