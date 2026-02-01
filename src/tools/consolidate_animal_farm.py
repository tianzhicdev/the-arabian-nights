#!/usr/bin/env python3
"""
Consolidate consistent_objects across Animal Farm episodes.
Reads all episode JSON files, merges consistent_objects, and writes consolidated versions.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set

def read_episode(filepath: Path) -> Dict:
    """Read and parse an episode JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def extract_consistent_objects(episode: Dict) -> Dict:
    """Extract consistent_objects from an episode."""
    return episode.get('episode', {}).get('consistent_objects', {})

def merge_consistent_objects(episodes_data: List[Dict]) -> Dict:
    """
    Merge consistent_objects from all episodes.
    Handles conflicts by preferring more detailed descriptions.
    """
    merged = {}
    conflicts = defaultdict(list)

    # Collect all objects
    for ep_num, ep_data in enumerate(episodes_data, 1):
        objects = extract_consistent_objects(ep_data)
        for key, obj in objects.items():
            if key not in merged:
                merged[key] = obj
                conflicts[key].append((ep_num, obj))
            else:
                # Check if descriptions differ
                if merged[key]['description'] != obj['description']:
                    conflicts[key].append((ep_num, obj))
                    # Prefer longer, more detailed description
                    if len(obj['description']) > len(merged[key]['description']):
                        merged[key] = obj

    # Report conflicts
    print("\n=== Consistent Objects Consolidation ===")
    print(f"Total unique objects: {len(merged)}")

    conflicting = {k: v for k, v in conflicts.items() if len(v) > 1}
    if conflicting:
        print(f"\nObjects with variations across episodes: {len(conflicting)}")
        for key, variants in conflicting.items():
            print(f"\n  {key}:")
            for ep_num, obj in variants:
                print(f"    Episode {ep_num}: {obj['description'][:80]}...")

    return merged

def normalize_scene_references(episode: Dict, consolidated_objects: Dict) -> List[str]:
    """
    Validate and normalize scene references to consistent_objects.
    Returns list of errors found.
    """
    errors = []
    all_valid_keys = set(consolidated_objects.keys())

    for scene in episode.get('scenes', []):
        scene_id = scene.get('scene_id')
        refs = scene.get('consistent_objects', [])

        # Normalize barn references
        normalized_refs = []
        for ref in refs:
            if ref in ['big_barn', 'the_barn']:
                normalized_refs.append('the_barn')
            else:
                normalized_refs.append(ref)

        # Check for invalid references
        invalid = [ref for ref in normalized_refs if ref not in all_valid_keys]
        if invalid:
            errors.append(f"Scene {scene_id}: Invalid objects {invalid}")

        # Update scene with normalized references
        scene['consistent_objects'] = normalized_refs

    return errors

def create_json_schema() -> Dict:
    """Create JSON schema for episode validation."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Animal Farm Episode",
        "type": "object",
        "required": ["episode", "scenes"],
        "properties": {
            "episode": {
                "type": "object",
                "required": ["title", "context", "art_style", "narrator_style", "consistent_objects"],
                "properties": {
                    "title": {"type": "string"},
                    "context": {"type": "string"},
                    "art_style": {"type": "string"},
                    "narrator_style": {"type": "string"},
                    "consistent_objects": {
                        "type": "object",
                        "patternProperties": {
                            "^[a-z_]+$": {
                                "type": "object",
                                "required": ["name", "description"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            },
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["scene_id", "sentences", "pause_after", "video_description", "camera_style", "consistent_objects"],
                    "properties": {
                        "scene_id": {"type": "integer"},
                        "sentences": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "pause_after": {"type": "number"},
                        "video_description": {"type": "string"},
                        "camera_style": {"type": "string"},
                        "consistent_objects": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            }
        }
    }

def main():
    base_dir = Path(__file__).parent.parent
    stories_dir = base_dir / 'resources' / 'stories' / 'gutenberg'

    # Find all Animal Farm episode files
    episode_files = sorted(stories_dir.glob('animal_farm_e*.json'))
    if not episode_files:
        print("No Animal Farm episode files found!")
        return 1

    print(f"Found {len(episode_files)} episode files")

    # Read all episodes
    episodes_data = []
    for filepath in episode_files:
        try:
            data = read_episode(filepath)
            episodes_data.append((filepath, data))
            print(f"  ✓ {filepath.name}")
        except Exception as e:
            print(f"  ✗ {filepath.name}: {e}")
            return 1

    # Merge consistent objects
    consolidated_objects = merge_consistent_objects([data for _, data in episodes_data])

    # Normalize barn references to 'the_barn'
    if 'big_barn' in consolidated_objects and 'the_barn' not in consolidated_objects:
        consolidated_objects['the_barn'] = consolidated_objects.pop('big_barn')
        consolidated_objects['the_barn']['name'] = 'The Barn'
    elif 'big_barn' in consolidated_objects and 'the_barn' in consolidated_objects:
        # Prefer the_barn, remove big_barn
        del consolidated_objects['big_barn']

    print(f"\n=== Final Consolidated Objects ===")
    for key in sorted(consolidated_objects.keys()):
        print(f"  {key}: {consolidated_objects[key]['name']}")

    # Write consolidated files and validate
    print("\n=== Writing Consolidated Files ===")
    all_errors = []

    for filepath, data in episodes_data:
        # Update consistent_objects
        data['episode']['consistent_objects'] = consolidated_objects

        # Normalize scene references
        errors = normalize_scene_references(data, consolidated_objects)
        if errors:
            all_errors.extend([f"{filepath.name}: {e}" for e in errors])

        # Write consolidated file
        output_path = filepath.parent / f"{filepath.stem}-consolidated.json"
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"  ✓ {output_path.name}")

    # Write schema
    schema_path = stories_dir / 'animal_farm_schema.json'
    with open(schema_path, 'w') as f:
        json.dump(create_json_schema(), f, indent=2)
    print(f"\n  ✓ Schema: {schema_path.name}")

    # Report validation errors
    if all_errors:
        print("\n=== Validation Errors ===")
        for error in all_errors:
            print(f"  ✗ {error}")
        return 1
    else:
        print("\n✅ All files consolidated and validated successfully!")
        return 0

if __name__ == '__main__':
    sys.exit(main())
