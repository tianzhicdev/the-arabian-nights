#!/usr/bin/env python3
"""
Configuration Manager for Podcast Generation System
Handles loading, saving, and validating podcast configurations
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ConfigManager:
    """Manages podcast configuration file"""

    def __init__(self, config_path: str = None):
        """
        Initialize ConfigManager

        Args:
            config_path: Path to config file. Defaults to ../podcasts_config.json
        """
        if config_path is None:
            project_root = Path(__file__).parent.parent
            config_path = project_root / "podcasts_config.json"

        self.config_path = Path(config_path)
        self.config = None

    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # Validate structure
        if 'podcasts' not in self.config:
            raise ValueError("Invalid config: missing 'podcasts' key")

        return self.config

    def save_config(self):
        """Save current configuration to JSON file"""
        if self.config is None:
            raise ValueError("No config loaded")

        # Create backup
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix('.json.backup')
            self.config_path.rename(backup_path)

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # Restore backup on failure
            if self.config_path.with_suffix('.json.backup').exists():
                self.config_path.with_suffix('.json.backup').rename(self.config_path)
            raise e

    def get_podcast(self, podcast_id: str = None, topic: str = None) -> Optional[Dict]:
        """
        Get podcast by ID or topic

        Args:
            podcast_id: Podcast ID to search for
            topic: Topic to search for

        Returns:
            Podcast dict or None if not found
        """
        if self.config is None:
            self.load_config()

        for podcast in self.config['podcasts']:
            if podcast_id and podcast['id'] == podcast_id:
                return podcast
            if topic and podcast['topic'].lower() == topic.lower():
                return podcast

        return None

    def list_podcasts(self) -> List[Dict]:
        """Get list of all podcasts"""
        if self.config is None:
            self.load_config()

        return self.config['podcasts']

    def check_files_exist(self, podcast_id: str) -> Dict[str, bool]:
        """
        Check which files exist for a podcast

        Returns:
            Dict with elevenlabs_ready_exists, mp3_exists
        """
        podcast = self.get_podcast(podcast_id=podcast_id)
        if not podcast:
            raise ValueError(f"Podcast not found: {podcast_id}")

        project_root = Path(__file__).parent.parent

        status = {
            'elevenlabs_ready_exists': False,
            'mp3_exists': False
        }

        # Check ElevenLabs-ready script
        if podcast.get('elevenlabs_ready_filepath'):
            elevenlabs_path = project_root / podcast['elevenlabs_ready_filepath']
            status['elevenlabs_ready_exists'] = elevenlabs_path.exists()

        # Check MP3 files
        if podcast.get('mp3_filepath'):
            mp3_path = project_root / podcast['mp3_filepath']
            status['mp3_exists'] = mp3_path.exists()
        else:
            # Check if any MP3 exists for this podcast ID
            audio_dir = project_root / "audio_output"
            if audio_dir.exists():
                mp3_pattern = f"{podcast_id}_*.mp3"
                mp3_files = list(audio_dir.glob(mp3_pattern))
                status['mp3_exists'] = len(mp3_files) > 0

        return status

    def update_podcast_status(self, podcast_id: str):
        """Update status fields for a podcast based on file existence"""
        status = self.check_files_exist(podcast_id)

        podcast = self.get_podcast(podcast_id=podcast_id)
        if not podcast:
            raise ValueError(f"Podcast not found: {podcast_id}")

        podcast['status'].update(status)

    def update_podcast_filepaths(self, podcast_id: str,
                                 elevenlabs_ready_filepath: str = None,
                                 mp3_filepath: str = None):
        """Update file paths for a podcast"""
        podcast = self.get_podcast(podcast_id=podcast_id)
        if not podcast:
            raise ValueError(f"Podcast not found: {podcast_id}")

        if elevenlabs_ready_filepath:
            podcast['elevenlabs_ready_filepath'] = elevenlabs_ready_filepath
        if mp3_filepath:
            podcast['mp3_filepath'] = mp3_filepath

            # Update metadata
            project_root = Path(__file__).parent.parent
            mp3_full_path = project_root / mp3_filepath
            if mp3_full_path.exists():
                file_size_mb = mp3_full_path.stat().st_size / (1024 * 1024)
                podcast['metadata']['file_size_mb'] = round(file_size_mb, 2)
                podcast['metadata']['generation_date'] = datetime.now().isoformat()

        # Update status
        self.update_podcast_status(podcast_id)

    def add_podcast(self, podcast_data: Dict) -> bool:
        """Add a new podcast to config"""
        if self.config is None:
            self.load_config()

        # Check for duplicate ID
        if self.get_podcast(podcast_id=podcast_data['id']):
            raise ValueError(f"Podcast with ID '{podcast_data['id']}' already exists")

        self.config['podcasts'].append(podcast_data)
        return True

    def add_podcast_to_config(self, podcast_data: Dict) -> bool:
        """Add a new podcast to config and save immediately"""
        self.add_podcast(podcast_data)
        self.save_config()
        return True
