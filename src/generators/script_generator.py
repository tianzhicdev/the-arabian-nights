#!/usr/bin/env python3
"""
Script Generator for Podcast Generation System
Uses xAI Grok API to generate podcast dialogue scripts with structured output
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Tuple, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Try to import openai for xAI API
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

# Load environment variables from project root
project_root_env = Path(__file__).parent.parent
load_dotenv(project_root_env / ".env.secrets")


class DialogueSegment(BaseModel):
    """Single dialogue segment"""
    speaker: str = Field(description="The name of the speaker")
    text: str = Field(description="The dialogue text spoken by this speaker")


class PodcastDialogue(BaseModel):
    """Complete podcast dialogue structure"""
    dialogues: List[DialogueSegment] = Field(
        description="List of dialogue segments in the podcast"
    )


class ScriptGenerator:
    """Generates podcast scripts using OpenRouter (Claude Sonnet 4.5) with structured outputs"""

    def __init__(self, model: str = None):
        """
        Initialize ScriptGenerator with OpenRouter API or Ollama

        Args:
            model: Model identifier. If starts with "ollama:", uses local Ollama server
        """
        self.project_root = Path(__file__).parent.parent
        self.client = None
        self.is_ollama = False

        if not OPENAI_AVAILABLE:
            print("Warning: openai package not installed. Script generation will be skipped.")
            print("Install with: pip install openai")
            return

        # Check if using Ollama
        if model and model.startswith("ollama:"):
            self.is_ollama = True
            try:
                self.client = OpenAI(
                    api_key="ollama",  # Ollama doesn't need real API key
                    base_url="http://localhost:11434/v1"
                )
                print("✓ Ollama local client initialized")
            except Exception as e:
                print(f"Warning: Failed to initialize Ollama client: {e}")
                print("Make sure Ollama is running: ollama serve")
                self.client = None
        else:
            # Use OpenRouter API from environment
            self.api_key = os.getenv("OPEN_ROUTER_API")
            if not self.api_key:
                print("Warning: OPEN_ROUTER_API not found in .env.secrets")
                return

            # Initialize OpenRouter client (OpenAI-compatible)
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://openrouter.ai/api/v1"
                )
                print("✓ OpenRouter API client initialized")
            except Exception as e:
                print(f"Warning: Failed to initialize OpenRouter client: {e}")
                self.client = None

    def check_script_exists(self, podcast_config: Dict) -> bool:
        """
        Check if ElevenLabs-ready script exists for this podcast

        Returns:
            True if script exists, False otherwise

        Raises:
            ValueError: If elevenlabs_ready_filepath is set but file doesn't exist
        """
        if podcast_config.get('elevenlabs_ready_filepath'):
            elevenlabs_path = self.project_root / podcast_config['elevenlabs_ready_filepath']
            if not elevenlabs_path.exists():
                raise ValueError(
                    f"Config specifies elevenlabs_ready_filepath but file doesn't exist: {elevenlabs_path}"
                )
            return True
        return False

    def build_prompt(self, podcast_config: Dict, test_mode: bool = False) -> str:
        """
        Build LLM prompt for script generation
        """
        topic = podcast_config['topic']
        host_1 = podcast_config['host_1']
        host_2 = podcast_config['host_2']
        editor_notes = podcast_config['editor_notes']

        length_instruction = "8-10 dialogue exchanges" if test_mode else "approximately 3500-4000 words (about 20-25 minutes when spoken)"

        prompt = f"""You are writing a script for "Wormhole Fireside" - a podcast where historical figures discuss great topics across time.

            THIS EPISODE:
            - Topic: "{topic}"
            - Speaker 1: {host_1['name']} - {host_1['editor_notes']}
            - Speaker 2: {host_2['name']} - {host_2['editor_notes']}
            - Core tension: {editor_notes}

            WHAT MAKES A GREAT EPISODE:

            1. SUBSTANCE OVER FORMAT
            - Each speaker must reference SPECIFIC events from their actual life that connect to the topic's themes
            - They should quote or paraphrase actual passages from the topic being discussed
            - The conversation should teach the listener something real about both the topic AND the speakers' lives
            - Include concrete details: dates, places, names, specific decisions they made

            2. EMOTIONAL ARC (not random emotions)
            Structure the conversation roughly as:
            - Opening: Establish the tension between their worldviews
            - Early conflict: They challenge each other, may get heated
            - Deepening: One or both reveal something vulnerable or admit uncertainty  
            - Surprise: At least one moment where a speaker says something the other didn't expect
            - Resolution: Not agreement, but mutual respect earned through honest exchange

            3. MAKE IT PERSONAL
            - {host_1['name']} should connect the topic to their own failures, regrets, or hard-won lessons
            - {host_2['name']} should do the same
            - The best moments come when abstract philosophy meets concrete lived experience
            - Example: Don't just discuss "the nature of power" - discuss the specific moment when one of them HAD power and what they did with it

            4. AUTHENTIC VOICES
            - {host_1['name']} should sound like {host_1['name']} - their known speaking style, concerns, vocabulary
            - {host_2['name']} should sound like {host_2['name']}
            - They can be witty, sharp, even cutting - but never generic "podcast host" voice
            - Let them interrupt each other when passionate
            - Let there be uncomfortable silences after hard truths

            5. DIALOGUE TECHNIQUES
            - Mix short punchy exchanges (1-2 sentences) with longer explanations
            - Use the format: "Name: [emotion/action] Dialogue"
            - Emotional tags: [sighs], [laughs], [quietly], [heated], [surprised], [bitter laugh], [long pause], [firmly], [softening], [admitting], [defensive], [interrupting]
            - Don't overuse tags - maybe 30-40% of lines have them
            - Some lines should just be raw dialogue with no tag

            6. STRUCTURAL ELEMENTS
            - One speaker opens with a small talk with the guest while mentioning each other's name or establishes their identity in any way;
            - Include at least one moment where they find unexpected common ground
            - Include at least one moment of genuine disagreement that doesn't get resolved
            - End with something memorable - a final exchange that captures the episode's essence

            LENGTH: {length_instruction}

            FORMAT: Output ONLY the dialogue, starting immediately with the first speaker. No titles, headers, or stage directions outside the dialogue.

            Example of GOOD opening (don't copy, just note the style):
            "{host_1['name']}: [direct] Your topic has been used to justify things you would have hated. How does that feel?

            {host_2['name']}: [pause, then quietly] How does it feel to be misunderstood for centuries? [slight laugh] You tell me - they've done the same to you."

            Example of BAD opening (avoid this):
            "{host_1['name']}: Welcome to our discussion! Today we'll be exploring the fascinating themes in this important work.

            {host_2['name']}: Thank you for having me! I'm excited to share my perspective on these ideas."

            NOW GENERATE THE COMPLETE DIALOGUE:"""

        return prompt

    def generate_script(self, podcast_config: Dict, test_mode: bool = False) -> str:
        """
        Generate podcast script using OpenRouter (Claude Sonnet 4.5) with structured output

        Args:
            podcast_config: Podcast configuration dict
            test_mode: If True, generate shorter script for testing

        Returns:
            elevenlabs_ready_script (single string)
        """
        if not self.client:
            raise RuntimeError(
                "Cannot generate script: OpenRouter API client not available. "
                "Either install openai package or provide OPEN_ROUTER_API in .env.secrets"
            )

        print(f"\n=== Generating Script for {podcast_config['topic']} ===")
        print(f"Host 1: {podcast_config['host_1']['name']}")
        print(f"Host 2: {podcast_config['host_2']['name']}")

        if test_mode:
            print("TEST MODE: Generating 8 dialogue exchanges")

        prompt = self.build_prompt(podcast_config, test_mode)

        print("\nCalling OpenRouter (Claude Sonnet 4.5) with structured output...")
        try:
            # Use structured output with response_format
            completion = self.client.beta.chat.completions.parse(
                model="anthropic/claude-sonnet-4.5",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a skilled podcast script writer who creates engaging historical dialogues between famous figures."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format=PodcastDialogue,
                temperature=0.8,
                max_tokens=4000 if test_mode else 8000
            )

            # Extract structured data
            dialogue_data = completion.choices[0].message.parsed

            print(f"✓ Script generated successfully ({len(dialogue_data.dialogues)} exchanges)")

            # Create ElevenLabs-ready script from structured data
            elevenlabs_ready_script = self._format_elevenlabs(dialogue_data.dialogues)

            return elevenlabs_ready_script

        except Exception as e:
            print(f"✗ Error generating script: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _format_elevenlabs(self, dialogues: List[DialogueSegment]) -> str:
        """
        Format dialogues for ElevenLabs TTS (simple format)

        Args:
            dialogues: List of DialogueSegment objects

        Returns:
            Formatted ElevenLabs-ready script
        """
        lines = []
        for segment in dialogues:
            lines.append(f"{segment.speaker}: {segment.text}")

        return "\n".join(lines)

    def generate_script_from_prompt(self, system_prompt: str, topic: str,
                                   host1_name: str, host2_name: str,
                                   duration_minutes: int = 15,
                                   model: str = "anthropic/claude-sonnet-4.5") -> str:
        """
        Generate podcast script from a custom system prompt

        This method is used by generate_episode.py which builds its own prompts
        using the two-layer system (podcast-level + episode-level + research)

        Args:
            system_prompt: Complete system prompt with all instructions
            topic: Episode topic (for logging)
            host1_name: First host name (for logging)
            host2_name: Second host name (for logging)
            duration_minutes: Target duration in minutes (for max_tokens calculation)
            model: Model to use for generation
                   - OpenRouter: "anthropic/claude-sonnet-4.5", "gpt-4", etc.
                   - Ollama: "ollama:dolphin-mistral", "ollama:nous-hermes2", etc.

        Returns:
            ElevenLabs-ready script as plain text
        """
        if not self.client:
            raise RuntimeError(
                "Cannot generate script: API client not available. "
                "Check OPEN_ROUTER_API key or Ollama server status."
            )

        # Extract actual model name for Ollama
        api_model = model.replace("ollama:", "") if model.startswith("ollama:") else model

        # Calculate max_tokens based on duration
        # Rough ratios: 150 words/min, 1 word ≈ 1.3 tokens for dialogue
        # For structured output, need extra tokens for JSON schema
        # For regular output, need buffer for emotion tags and formatting
        target_words = duration_minutes * 150
        if not self.is_ollama:
            # Structured output needs 3x buffer for JSON overhead
            max_tokens = int(target_words * 1.3 * 3)
        else:
            # Regular completion needs 1.5x buffer
            max_tokens = int(target_words * 1.3 * 1.5)

        print(f"  Calling {model}...")
        print(f"  Target: {target_words} words, Max tokens: {max_tokens}")

        try:
            # Try structured output for OpenRouter (not supported by Ollama)
            if not self.is_ollama:
                try:
                    # Use structured output for cleaner results
                    response = self.client.beta.chat.completions.parse(
                        model=api_model,
                        messages=[
                            {
                                "role": "user",
                                "content": system_prompt
                            }
                        ],
                        response_format=PodcastDialogue,
                        temperature=0.8,
                        max_tokens=max_tokens
                    )

                    # Extract structured data
                    dialogue_data = response.choices[0].message.parsed

                    # Format for ElevenLabs
                    script = self._format_elevenlabs(dialogue_data.dialogues)

                    word_count = len(script.split())
                    print(f"  ✓ Generated {word_count} words (structured output)")

                    return script

                except Exception as struct_error:
                    # Fall back to regular completion if structured output fails
                    print(f"  ⚠ Structured output failed, using regular completion: {struct_error}")

            # Regular completion (for Ollama or fallback)
            response = self.client.chat.completions.create(
                model=api_model,
                messages=[
                    {
                        "role": "user",
                        "content": system_prompt
                    }
                ],
                temperature=0.8,
                max_tokens=max_tokens
            )

            script = response.choices[0].message.content

            word_count = len(script.split())
            print(f"  ✓ Generated {word_count} words")

            return script

        except Exception as e:
            if self.is_ollama:
                print(f"  ✗ Ollama Error: {e}")
                print(f"  Make sure '{api_model}' is pulled: ollama pull {api_model}")
            else:
                print(f"  ✗ Error: {e}")
            raise

    def save_script(self, podcast_config: Dict, elevenlabs_script: str) -> str:
        """
        Save ElevenLabs-ready script to resources directory

        Args:
            podcast_config: Podcast configuration dict
            elevenlabs_script: ElevenLabs-ready script content

        Returns:
            elevenlabs_ready_filepath - relative path
        """
        podcast_id = podcast_config['id']

        # Create directory structure using podcast ID
        resources_dir = self.project_root / "resources" / podcast_id
        resources_dir.mkdir(parents=True, exist_ok=True)

        # Define file path using podcast ID
        elevenlabs_filename = f"{podcast_id}_elevenlabs_ready.txt"
        elevenlabs_path = resources_dir / elevenlabs_filename

        # Save file
        print(f"\nSaving script to resources/{podcast_id}/")

        with open(elevenlabs_path, 'w', encoding='utf-8') as f:
            f.write(elevenlabs_script)
        print(f"  ✓ {elevenlabs_filename}")

        # Return relative path
        elevenlabs_filepath = f"resources/{podcast_id}/{elevenlabs_filename}"

        return elevenlabs_filepath
