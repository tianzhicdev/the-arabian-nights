#!/usr/bin/env python3
"""
Video Editor Flask Server

Provides web UI for fine-grained control over video generation pipeline.
"""

import json
import os
import re
import threading
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Get absolute path to build directory
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent  # /Users/biubiu/projects/the-arabian-nights
BUILD_DIR = PROJECT_ROOT / 'ui' / 'video-editor' / 'build'

app = Flask(__name__, static_folder=str(BUILD_DIR), static_url_path='')
CORS(app)

# Global state for background jobs
current_job = {
    'status': 'idle',  # idle, running, completed, failed
    'progress': 0,
    'total': 0,
    'current_scene': None,
    'message': ''
}


def get_timestamp() -> str:
    """Get current timestamp string for file naming"""
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def parse_timestamp_from_filename(filename: str) -> Optional[str]:
    """Extract timestamp from filename like scene_001_20240129_120530.wav"""
    match = re.search(r'_(\d{8}_\d{6})\.\w+$', filename)
    return match.group(1) if match else None


def scan_output_directory(output_dir: Path) -> Dict[int, Dict[str, Any]]:
    """
    Scan output directory and build file inventory with timestamps.

    Returns:
        Dict mapping scene_id -> {audio: [{path, timestamp}], image: [...], video: [...]}
    """
    inventory = {}

    # Scan audio directory
    audio_dir = output_dir / 'audio'
    if audio_dir.exists():
        for audio_file in audio_dir.glob('scene_*.wav'):
            match = re.match(r'scene_(\d+)', audio_file.stem)
            if match:
                scene_id = int(match.group(1))
                timestamp = parse_timestamp_from_filename(audio_file.name)
                if scene_id not in inventory:
                    inventory[scene_id] = {'audio': [], 'image': [], 'video': []}
                inventory[scene_id]['audio'].append({
                    'path': str(audio_file),
                    'timestamp': timestamp or audio_file.stat().st_mtime,
                    'size': audio_file.stat().st_size
                })

    # Scan images directory
    images_dir = output_dir / 'images'
    if images_dir.exists():
        for image_file in images_dir.glob('scene_*.png'):
            match = re.match(r'scene_(\d+)', image_file.stem)
            if match:
                scene_id = int(match.group(1))
                timestamp = parse_timestamp_from_filename(image_file.name)
                if scene_id not in inventory:
                    inventory[scene_id] = {'audio': [], 'image': [], 'video': []}
                inventory[scene_id]['image'].append({
                    'path': str(image_file),
                    'timestamp': timestamp or image_file.stat().st_mtime,
                    'size': image_file.stat().st_size
                })

    # Scan video directory
    video_dir = output_dir / 'video'
    if video_dir.exists():
        for video_file in video_dir.glob('scene_*.mp4'):
            match = re.match(r'scene_(\d+)', video_file.stem)
            if match:
                scene_id = int(match.group(1))
                timestamp = parse_timestamp_from_filename(video_file.name)
                if scene_id not in inventory:
                    inventory[scene_id] = {'audio': [], 'image': [], 'video': []}
                inventory[scene_id]['video'].append({
                    'path': str(video_file),
                    'timestamp': timestamp or video_file.stat().st_mtime,
                    'size': video_file.stat().st_size
                })

    # Sort by timestamp (latest first)
    for scene_data in inventory.values():
        for file_type in ['audio', 'image', 'video']:
            scene_data[file_type].sort(key=lambda x: x['timestamp'], reverse=True)

    return inventory


@app.route('/api/project/load', methods=['POST'])
def load_project():
    """Load project from scenes.json"""
    data = request.json
    scenes_path = Path(data.get('scenes_json'))
    output_dir = Path(data.get('output_dir'))

    if not scenes_path.exists():
        return jsonify({'error': f'Scenes file not found: {scenes_path}'}), 404

    # Load scenes
    try:
        with open(scenes_path, 'r') as f:
            scenes_data = json.load(f)
    except json.JSONDecodeError as e:
        return jsonify({
            'error': f'Invalid JSON in scenes file: {str(e)}',
            'line': e.lineno,
            'column': e.colno
        }), 400

    # Scan existing files
    file_inventory = scan_output_directory(output_dir)

    # Build response
    scenes_list = []
    for scene in scenes_data['scenes']:
        scene_id = scene['scene_id']
        inventory = file_inventory.get(scene_id, {'audio': [], 'image': [], 'video': []})

        scenes_list.append({
            'scene_id': scene_id,
            'sentences': scene.get('sentences', []),
            'video_description': scene.get('video_description', ''),
            'files': {
                'audio': inventory['audio'],
                'image': inventory['image'],
                'video': inventory['video']
            },
            'has_audio': len(inventory['audio']) > 0,
            'has_image': len(inventory['image']) > 0,
            'has_video': len(inventory['video']) > 0,
            'latest_audio': inventory['audio'][0]['timestamp'] if inventory['audio'] else None,
            'latest_image': inventory['image'][0]['timestamp'] if inventory['image'] else None,
            'latest_video': inventory['video'][0]['timestamp'] if inventory['video'] else None
        })

    return jsonify({
        'episode': scenes_data.get('episode', {}),
        'scenes': scenes_list,
        'total_scenes': len(scenes_list)
    })


@app.route('/api/generate', methods=['POST'])
def start_generation():
    """Start background generation job"""
    global current_job

    if current_job['status'] == 'running':
        return jsonify({'error': 'Generation already running'}), 409

    data = request.json

    # Start background thread
    thread = threading.Thread(target=run_generation_job, args=(data,))
    thread.daemon = True
    thread.start()

    return jsonify({'message': 'Generation started', 'job_id': get_timestamp()})


def run_generation_job(config: Dict):
    """Run generation job in background"""
    global current_job

    current_job['status'] = 'running'
    current_job['progress'] = 0
    current_job['message'] = 'Starting generation...'

    try:
        from audio_generator import SceneAudioGenerator
        from openai_responses_image_client import OpenAIResponsesImageClient

        output_dir = Path(config.get('output_dir'))
        global_config = config.get('global_config', {})
        audio_ref = Path(global_config.get('audio_ref'))
        art_ref = Path(global_config.get('art_ref'))

        scenes_to_generate = config.get('scenes', [])
        current_job['total'] = len(scenes_to_generate)

        # Initialize generators once
        audio_generator = None
        image_generator = None

        # Check if we need audio generation
        needs_audio = any(s.get('generate_audio') for s in scenes_to_generate)
        if needs_audio:
            current_job['message'] = 'Initializing audio generator...'
            audio_generator = SceneAudioGenerator(
                audio_prompt_path=str(audio_ref),
                device='cpu',
                speed=1.0
            )

        # Check if we need image generation
        needs_image = any(s.get('generate_image') for s in scenes_to_generate)
        if needs_image:
            current_job['message'] = 'Initializing image generator...'
            image_generator = OpenAIResponsesImageClient()

        # Load full scenes data from JSON
        scenes_json_path = Path(config.get('scenes_json'))
        if not scenes_json_path.exists():
            raise FileNotFoundError(f"Scenes file not found: {scenes_json_path}")

        with open(scenes_json_path, 'r') as f:
            scenes_data = json.load(f)

        scenes_by_id = {s['scene_id']: s for s in scenes_data['scenes']}

        # Process each scene
        for i, scene_config in enumerate(scenes_to_generate):
            scene_id = scene_config['scene_id']
            current_job['current_scene'] = scene_id
            current_job['message'] = f"Processing scene {scene_id}"

            # Get full scene data
            scene = scenes_by_id.get(scene_id)
            if not scene:
                print(f"Warning: Scene {scene_id} not found in scenes.json")
                continue

            # Generate audio if requested
            if scene_config.get('generate_audio') and audio_generator:
                current_job['message'] = f"Scene {scene_id}: Generating audio..."
                timestamp = get_timestamp()
                audio_path = output_dir / 'audio' / f"scene_{scene_id:03d}_{timestamp}.wav"
                audio_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    audio_generator.generate_scene_audio(scene, audio_path)
                    print(f"  ✓ Audio generated: {audio_path}")
                except Exception as e:
                    print(f"  ✗ Audio generation failed: {e}")

            # Generate image if requested
            if scene_config.get('generate_image') and image_generator:
                current_job['message'] = f"Scene {scene_id}: Generating image..."
                timestamp = get_timestamp()
                image_path = output_dir / 'images' / f"scene_{scene_id:03d}_{timestamp}.png"
                image_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    # Build prompt from video_description
                    prompt = scene.get('video_description', '')
                    if not prompt:
                        prompt = ' '.join(scene.get('sentences', []))

                    # Generate image
                    image_b64 = image_generator.generate_with_style_reference(
                        prompt=prompt,
                        style_reference_path=str(art_ref),
                        size="1536x1024"
                    )

                    # Save image
                    image_bytes = base64.b64decode(image_b64)
                    with open(image_path, 'wb') as f:
                        f.write(image_bytes)

                    print(f"  ✓ Image generated: {image_path}")
                except Exception as e:
                    print(f"  ✗ Image generation failed: {e}")

            current_job['progress'] = i + 1

        current_job['status'] = 'completed'
        current_job['message'] = 'Generation completed'

    except Exception as e:
        current_job['status'] = 'failed'
        current_job['message'] = str(e)
        import traceback
        traceback.print_exc()


@app.route('/api/generate/status', methods=['GET'])
def get_generation_status():
    """Get current generation job status"""
    return jsonify(current_job)


@app.route('/api/browse', methods=['POST'])
def browse_files():
    """Browse filesystem for file selection"""
    data = request.json
    start_path = data.get('path', str(SCRIPT_DIR.parent))
    file_type = data.get('type', 'all')  # 'all', 'json', 'image', 'audio'

    try:
        path = Path(start_path)
        if not path.exists():
            path = SCRIPT_DIR.parent

        items = []
        if path.is_dir():
            for item in sorted(path.iterdir()):
                if item.name.startswith('.'):
                    continue

                item_type = 'dir' if item.is_dir() else 'file'

                # Filter by file type
                if file_type != 'all' and item_type == 'file':
                    if file_type == 'json' and not item.suffix == '.json':
                        continue
                    elif file_type == 'image' and item.suffix not in ['.png', '.jpg', '.jpeg']:
                        continue
                    elif file_type == 'audio' and item.suffix not in ['.mp3', '.wav']:
                        continue

                items.append({
                    'name': item.name,
                    'path': str(item),
                    'type': item_type,
                    'size': item.stat().st_size if item_type == 'file' else 0
                })

        return jsonify({
            'current_path': str(path),
            'parent_path': str(path.parent) if path.parent != path else None,
            'items': items
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/assemble', methods=['POST'])
def assemble_video():
    """Assemble final video from selected versions"""
    data = request.json

    # TODO: Implement video assembly
    # This will use the video_assembler.py

    return jsonify({'message': 'Assembly started', 'job_id': get_timestamp()})


# Serve React frontend
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve React app"""
    if path != "" and (BUILD_DIR / path).exists():
        return send_from_directory(BUILD_DIR, path)
    else:
        return send_from_directory(BUILD_DIR, 'index.html')


if __name__ == '__main__':
    print("Starting Video Editor Server...")
    print("Access UI at: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)
