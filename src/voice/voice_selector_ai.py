#!/usr/bin/env python3
"""
AI-Powered Voice Selector for ElevenLabs
Uses Claude to intelligently select voices based on character descriptions
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env.secrets")

ELEVEN_LABS_KEY = os.getenv("ELEVEN_LABS_KEY")
OPENROUTER_KEY = os.getenv("OPEN_ROUTER_API")
VOICE_CACHE_PATH = Path("/tmp/elevenlabs_voices_cache.json")
CACHE_TTL_HOURS = 24


def fetch_voices_from_api() -> List[Dict]:
    """Fetch all available voices from ElevenLabs API"""
    headers = {"xi-api-key": ELEVEN_LABS_KEY}

    try:
        response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)
        response.raise_for_status()
        data = response.json()
        return data.get("voices", [])
    except Exception as e:
        print(f"Error fetching voices from API: {e}")
        return []


def get_cached_voices() -> Optional[List[Dict]]:
    """Get voices from cache if valid"""
    if not VOICE_CACHE_PATH.exists():
        return None

    try:
        with open(VOICE_CACHE_PATH, 'r') as f:
            cache = json.load(f)

        # Check if cache is still valid
        cache_time = cache.get("timestamp", 0)
        age_hours = (time.time() - cache_time) / 3600

        if age_hours < CACHE_TTL_HOURS:
            return cache.get("voices", [])

        return None
    except Exception as e:
        print(f"Error reading voice cache: {e}")
        return None


def save_voices_to_cache(voices: List[Dict]):
    """Save voices to cache"""
    try:
        cache = {
            "timestamp": time.time(),
            "ttl_hours": CACHE_TTL_HOURS,
            "voices": voices
        }
        with open(VOICE_CACHE_PATH, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Error saving voice cache: {e}")


def get_available_voices() -> List[Dict]:
    """Get voices from cache or API"""
    # Try cache first
    voices = get_cached_voices()
    if voices:
        return voices

    # Fetch from API
    voices = fetch_voices_from_api()
    if voices:
        save_voices_to_cache(voices)

    return voices


def build_ai_prompt(host1_name: str, host1_desc: str,
                    host2_name: str, host2_desc: str,
                    voices: List[Dict]) -> str:
    """Build prompt for AI voice selection"""

    # Format voices for prompt (simplified)
    voices_list = []
    for v in voices:
        labels = v.get("labels", {})
        voice_entry = {
            "voice_id": v["voice_id"],
            "name": v["name"],
            "gender": labels.get("gender", "unknown"),
            "age": labels.get("age", "unknown"),
            "accent": labels.get("accent", "unknown"),
            "description": v.get("description", "")
        }
        voices_list.append(voice_entry)

    voices_json = json.dumps(voices_list, indent=2)

    prompt = f"""You are an expert voice casting director for podcasts. Your task is to select the most appropriate voices for two podcast hosts.

CONTEXT:
- This is a conversational podcast with natural back-and-forth dialogue
- Voice personalities should complement each other
- Consider: tone, energy, accent compatibility, age appropriateness
- The two voices MUST be clearly distinguishable from each other

HOST 1: {host1_name}
Character Description: {host1_desc}

HOST 2: {host2_name}
Character Description: {host2_desc}

AVAILABLE VOICES:
{voices_json}

SELECTION CRITERIA:
1. Match personality and tone to character description
2. Ensure voices are clearly distinguishable (different gender/age/accent preferred)
3. Consider chemistry - voices should work well in conversation
4. Prefer voices with clear, engaging delivery for podcasts

CONSTRAINTS:
- Must select exactly TWO different voice IDs
- Host 1 and Host 2 must have DIFFERENT voices
- Only use voice_ids from the provided list

Respond ONLY with valid JSON (no markdown, no code blocks):
{{
  "host1_voice_id": "exact_voice_id_from_list",
  "host1_reasoning": "Brief explanation of why this voice fits",
  "host2_voice_id": "exact_voice_id_from_list",
  "host2_reasoning": "Brief explanation of why this voice fits"
}}"""

    return prompt


def call_claude_api(prompt: str, model: str = "anthropic/claude-sonnet-4.5") -> Optional[Dict]:
    """Call Claude via OpenRouter for voice selection"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/anthropics/the-arabian-nights",
        "X-Title": "Arabian Nights Podcast Generator"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # Parse JSON from response
        # Handle markdown code blocks if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)

    except requests.exceptions.HTTPError as e:
        print(f"Error calling Claude API: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response body: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        return None


def validate_ai_response(response: Dict, voices: List[Dict]) -> bool:
    """Validate AI response has valid structure and voice IDs"""

    required_keys = ["host1_voice_id", "host1_reasoning", "host2_voice_id", "host2_reasoning"]
    if not all(key in response for key in required_keys):
        return False

    # Check voice IDs exist
    voice_ids = {v["voice_id"] for v in voices}
    if response["host1_voice_id"] not in voice_ids:
        return False
    if response["host2_voice_id"] not in voice_ids:
        return False

    # Check voices are different
    if response["host1_voice_id"] == response["host2_voice_id"]:
        return False

    return True


def rule_based_fallback(host1_desc: str, host2_desc: str,
                        voices: List[Dict]) -> Dict:
    """Fallback to rule-based selection if AI fails"""

    from voice_selector import filter_voices

    # Simple heuristics from descriptions
    def extract_criteria(desc: str):
        desc_lower = desc.lower()
        gender = None
        age = None

        if "male" in desc_lower and "female" not in desc_lower:
            gender = "male"
        elif "female" in desc_lower:
            gender = "female"

        if "young" in desc_lower:
            age = "young"
        elif "middle" in desc_lower or "middle-aged" in desc_lower:
            age = "middle_aged"
        elif "old" in desc_lower:
            age = "old"

        return gender, age

    # Get criteria for both hosts
    h1_gender, h1_age = extract_criteria(host1_desc)
    h2_gender, h2_age = extract_criteria(host2_desc)

    # Filter for host 1
    h1_voices = filter_voices(voices, gender=h1_gender, age=h1_age)
    if not h1_voices:
        h1_voices = voices

    import random
    host1_voice = random.choice(h1_voices)

    # Filter for host 2 (exclude host 1)
    h2_voices = filter_voices(voices, gender=h2_gender, age=h2_age)
    h2_voices = [v for v in h2_voices if v["voice_id"] != host1_voice["voice_id"]]
    if not h2_voices:
        h2_voices = [v for v in voices if v["voice_id"] != host1_voice["voice_id"]]

    host2_voice = random.choice(h2_voices)

    return {
        "host1_voice_id": host1_voice["voice_id"],
        "host1_reasoning": f"Rule-based selection: {h1_gender or 'any'} gender, {h1_age or 'any'} age",
        "host2_voice_id": host2_voice["voice_id"],
        "host2_reasoning": f"Rule-based selection: {h2_gender or 'any'} gender, {h2_age or 'any'} age"
    }


def get_voice_info(voice_id: str, voices: List[Dict]) -> Dict:
    """Get voice name and details by ID"""
    for v in voices:
        if v["voice_id"] == voice_id:
            return {
                "name": v["name"],
                "gender": v.get("labels", {}).get("gender", "unknown"),
                "age": v.get("labels", {}).get("age", "unknown"),
                "accent": v.get("labels", {}).get("accent", "unknown")
            }
    return {"name": "Unknown", "gender": "unknown", "age": "unknown", "accent": "unknown"}


def select_voices_for_episode(
    host1_name: str,
    host1_description: str,
    host2_name: str,
    host2_description: str,
    host1_voice_override: Optional[str] = None,
    host2_voice_override: Optional[str] = None,
    model: str = "anthropic/claude-sonnet-4.5"
) -> Dict[str, str]:
    """
    Main function: Select voices with AI or use overrides

    Returns:
    {
        "host1_voice_id": "...",
        "host1_voice_name": "...",
        "host1_reasoning": "...",
        "host2_voice_id": "...",
        "host2_voice_name": "...",
        "host2_reasoning": "..."
    }
    """

    print("\n" + "="*70)
    print("VOICE SELECTION")
    print("="*70 + "\n")

    # Get available voices
    voices = get_available_voices()
    if not voices:
        raise Exception("Failed to fetch available voices")

    print(f"Loaded {len(voices)} available voices from ElevenLabs\n")

    result = {}

    # Host 1
    if host1_voice_override:
        print(f"Host 1: {host1_name}")
        print(f"  ✓ Manual override provided")
        result["host1_voice_id"] = host1_voice_override
        result["host1_reasoning"] = "Manual voice ID override"
        voice_info = get_voice_info(host1_voice_override, voices)
        result["host1_voice_name"] = voice_info["name"]
        print(f"  Voice: {voice_info['name']}")
        print(f"  Voice ID: {host1_voice_override}\n")

    # Host 2
    if host2_voice_override:
        print(f"Host 2: {host2_name}")
        print(f"  ✓ Manual override provided")
        result["host2_voice_id"] = host2_voice_override
        result["host2_reasoning"] = "Manual voice ID override"
        voice_info = get_voice_info(host2_voice_override, voices)
        result["host2_voice_name"] = voice_info["name"]
        print(f"  Voice: {voice_info['name']}")
        print(f"  Voice ID: {host2_voice_override}\n")

    # If both overridden, return early
    if host1_voice_override and host2_voice_override:
        print("="*70 + "\n")
        return result

    # Need AI selection for at least one host
    print("Using AI-powered voice selection...")

    # Build prompt
    prompt = build_ai_prompt(host1_name, host1_description,
                            host2_name, host2_description, voices)

    # Call AI
    ai_response = call_claude_api(prompt, model=model)

    # Validate response
    if ai_response and validate_ai_response(ai_response, voices):
        print("✓ AI selection successful\n")

        # Use AI selections for non-overridden hosts
        if not host1_voice_override:
            result["host1_voice_id"] = ai_response["host1_voice_id"]
            result["host1_reasoning"] = ai_response["host1_reasoning"]
            voice_info = get_voice_info(ai_response["host1_voice_id"], voices)
            result["host1_voice_name"] = voice_info["name"]

            print(f"Host 1: {host1_name}")
            print(f"  Description: {host1_description}")
            print(f"  ✓ Selected: {voice_info['name']}")
            print(f"  Voice ID: {ai_response['host1_voice_id']}")
            print(f"  Reasoning: {ai_response['host1_reasoning']}\n")

        if not host2_voice_override:
            result["host2_voice_id"] = ai_response["host2_voice_id"]
            result["host2_reasoning"] = ai_response["host2_reasoning"]
            voice_info = get_voice_info(ai_response["host2_voice_id"], voices)
            result["host2_voice_name"] = voice_info["name"]

            print(f"Host 2: {host2_name}")
            print(f"  Description: {host2_description}")
            print(f"  ✓ Selected: {voice_info['name']}")
            print(f"  Voice ID: {ai_response['host2_voice_id']}")
            print(f"  Reasoning: {ai_response['host2_reasoning']}\n")

    else:
        # Fallback to rule-based
        print("⚠ AI selection failed, using rule-based fallback\n")
        fallback = rule_based_fallback(host1_description, host2_description, voices)

        if not host1_voice_override:
            result["host1_voice_id"] = fallback["host1_voice_id"]
            result["host1_reasoning"] = fallback["host1_reasoning"]
            voice_info = get_voice_info(fallback["host1_voice_id"], voices)
            result["host1_voice_name"] = voice_info["name"]

            print(f"Host 1: {host1_name}")
            print(f"  ✓ Selected: {voice_info['name']}")
            print(f"  Voice ID: {fallback['host1_voice_id']}\n")

        if not host2_voice_override:
            result["host2_voice_id"] = fallback["host2_voice_id"]
            result["host2_reasoning"] = fallback["host2_reasoning"]
            voice_info = get_voice_info(fallback["host2_voice_id"], voices)
            result["host2_voice_name"] = voice_info["name"]

            print(f"Host 2: {host2_name}")
            print(f"  ✓ Selected: {voice_info['name']}")
            print(f"  Voice ID: {fallback['host2_voice_id']}\n")

    print("="*70 + "\n")
    return result


if __name__ == "__main__":
    # Test the selector
    result = select_voices_for_episode(
        host1_name="Jesus",
        host1_description="warm, laughing, relatable, early 30s vibe, iced coffee energy",
        host2_name="Buddha",
        host2_description="calm, peaceful, quiet wisdom, green tea energy, old wise male"
    )

    print("Result:")
    print(json.dumps(result, indent=2))
