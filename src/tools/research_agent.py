#!/usr/bin/env python3
"""
Research Agent - Uses Perplexity Sonar Pro via OpenRouter for factual research
"""

import os
from pathlib import Path
from openai import OpenAI
from typing import Dict
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env.secrets")


class PerplexityResearchAgent:
    """Research agent using Perplexity Sonar Pro via OpenRouter"""

    def __init__(self):
        # Try both OPEN_ROUTER_API_KEY and OPEN_ROUTER_API
        self.api_key = os.getenv("OPEN_ROUTER_API_KEY") or os.getenv("OPEN_ROUTER_API")
        if not self.api_key:
            raise ValueError("OPEN_ROUTER_API_KEY or OPEN_ROUTER_API not found in environment")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = "perplexity/sonar-pro"

    def research_hosts_and_topic(self, host1: str, host2: str, topic: str) -> Dict[str, str]:
        """
        Research both hosts and the topic using Perplexity

        Args:
            host1: First host's name
            host2: Second host's name
            topic: Episode topic/theme

        Returns:
            Dictionary with research findings
        """
        print(f"  Researching {host1}...")
        host1_bio = self._research_query(
            f"Detailed biography of {host1}: key life events, major achievements, "
            f"core beliefs, famous quotes, historical significance, personality traits"
        )

        print(f"  Researching {host2}...")
        host2_bio = self._research_query(
            f"Detailed biography of {host2}: key life events, major achievements, "
            f"core beliefs, famous quotes, historical significance, personality traits"
        )

        print(f"  Researching topic: {topic}...")
        topic_context = self._research_query(
            f"Historical and intellectual context for {topic}: key themes, "
            f"major debates, lasting impact, important events"
        )

        print(f"  Researching relationship...")
        relationship = self._research_query(
            f"Historical relationship and interactions between {host1} and {host2}: "
            f"did they meet? what did they think of each other? how did their ideas relate?"
        )

        return {
            'host_1_bio': host1_bio,
            'host_2_bio': host2_bio,
            'topic_context': topic_context,
            'relationship': relationship
        }

    def _research_query(self, query: str) -> str:
        """Execute a single research query"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": query
                }],
                max_tokens=2000
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"    Warning: Research query failed: {e}")
            return f"[Research unavailable for: {query}]"
