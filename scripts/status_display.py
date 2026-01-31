"""
Status Display - Rich status reporting for pipeline operations

Provides detailed visual feedback on:
- Input changes
- Stage completion status
- Cost estimates
- Time estimates
- Cache hits/misses
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import sys


@dataclass
class StageInfo:
    """Information about a pipeline stage."""
    name: str
    display_name: str
    status: str  # 'pending', 'cached', 'running', 'completed', 'failed', 'skipped'
    time_estimate: float  # seconds
    cost_estimate: float  # dollars
    actual_time: Optional[float] = None
    actual_cost: Optional[float] = None
    output_count: Optional[int] = None
    cache_reason: Optional[str] = None


class StatusDisplay:
    """Manages status display for pipeline operations."""

    # Status symbols
    SYMBOLS = {
        'pending': '⊗',
        'cached': '✓',
        'running': '⟳',
        'completed': '✓',
        'failed': '✗',
        'skipped': '→',
        'invalidated': '⚠'
    }

    # Color codes (optional, can be disabled for plain output)
    COLORS = {
        'pending': '\033[90m',    # Gray
        'cached': '\033[32m',     # Green
        'running': '\033[33m',    # Yellow
        'completed': '\033[32m',  # Green
        'failed': '\033[31m',     # Red
        'skipped': '\033[36m',    # Cyan
        'reset': '\033[0m'
    }

    def __init__(self, use_colors: bool = True):
        """
        Initialize status display.

        Args:
            use_colors: Whether to use ANSI colors
        """
        self.use_colors = use_colors and sys.stdout.isatty()
        self.stages: List[StageInfo] = []

    def _color(self, text: str, color_name: str) -> str:
        """
        Apply color to text.

        Args:
            text: Text to colorize
            color_name: Color name

        Returns:
            Colorized text if colors enabled, otherwise plain text
        """
        if not self.use_colors:
            return text

        color = self.COLORS.get(color_name, '')
        reset = self.COLORS['reset']
        return f"{color}{text}{reset}"

    def add_stage(self, stage_info: StageInfo):
        """Add a stage to track."""
        self.stages.append(stage_info)

    def print_header(self, output_dir: str, title: Optional[str] = None):
        """
        Print header section.

        Args:
            output_dir: Output directory path
            title: Optional title
        """
        print("=" * 80)
        print(f"PIPELINE STATUS: {output_dir}")
        if title:
            print(f"Title: {title}")
        print("=" * 80)
        print()

    def print_input_changes(self, changes: Dict[str, Dict[str, Any]]):
        """
        Print input change summary.

        Args:
            changes: Dictionary of input changes
                    {name: {'changed': bool, 'old_hash': str, 'new_hash': str, 'path': str}}
        """
        if not changes:
            return

        print("Input Changes:")

        for name, info in changes.items():
            changed = info.get('changed', False)
            path = info.get('path', 'N/A')

            if changed:
                symbol = self._color("✗", "failed")
                old_hash = info.get('old_hash') or 'N/A'
                new_hash = info.get('new_hash') or 'N/A'
                # Only slice if not N/A
                old_hash = old_hash[:8] if old_hash != 'N/A' else old_hash
                new_hash = new_hash[:8] if new_hash != 'N/A' else new_hash
                reason = self._color("CHANGED", "running")
                details = f"({old_hash} → {new_hash})"
            else:
                symbol = self._color("✓", "cached")
                hash_val = info.get('new_hash') or 'N/A'
                hash_val = hash_val[:8] if hash_val != 'N/A' else hash_val
                reason = self._color("unchanged", "cached")
                details = f"(hash: {hash_val})"

            print(f"  {symbol} {name:20s} {reason} {details}")

        print()

    def print_stage_summary(self, verbose: bool = False):
        """
        Print stage status summary.

        Args:
            verbose: Whether to show detailed information
        """
        print("Stage Status:")

        total_time = 0.0
        total_cost = 0.0
        cached_count = 0

        for stage in self.stages:
            symbol = self.SYMBOLS.get(stage.status, '?')
            symbol = self._color(symbol, stage.status)

            # Format status
            status_str = stage.status.upper()
            if stage.status == 'cached':
                status_str = self._color("CACHED", "cached")
                cached_count += 1
            elif stage.status == 'completed':
                status_str = self._color("COMPLETE", "completed")
            elif stage.status == 'running':
                status_str = self._color("RUNNING", "running")
            elif stage.status == 'failed':
                status_str = self._color("FAILED", "failed")
            elif stage.status == 'pending':
                status_str = self._color("PENDING", "pending")

            # Format time
            if stage.actual_time is not None:
                time_str = f"{stage.actual_time:.1f}s"
                total_time += stage.actual_time
            elif stage.time_estimate > 0:
                time_str = f"~{stage.time_estimate:.0f}s"
                if stage.status not in ['cached', 'skipped']:
                    total_time += stage.time_estimate
            else:
                time_str = "-"

            # Format cost
            if stage.actual_cost is not None:
                cost_str = f"${stage.actual_cost:.2f}"
                total_cost += stage.actual_cost
            elif stage.cost_estimate > 0:
                cost_str = f"~${stage.cost_estimate:.2f}"
                if stage.status not in ['cached', 'skipped']:
                    total_cost += stage.cost_estimate
            else:
                cost_str = "-"

            # Format output count
            output_str = ""
            if stage.output_count is not None:
                output_str = f"{stage.output_count} outputs"
            elif stage.status in ['completed', 'cached']:
                output_str = "✓"

            # Print stage line
            print(f"  [{symbol}] {stage.display_name:30s} {time_str:>8s} {cost_str:>10s}  {status_str}")

            # Print cache reason if verbose
            if verbose and stage.cache_reason and stage.status == 'cached':
                print(f"      └─ {stage.cache_reason}")

        print()
        print(f"Estimated Total Time: {total_time:.0f}s ({timedelta(seconds=int(total_time))})")
        print(f"Estimated Total Cost: ${total_cost:.2f}")
        if cached_count > 0:
            print(f"Cache Hits: {cached_count}/{len(self.stages)} stages")
        print()

    def print_warnings(self, warnings: List[str]):
        """
        Print warnings.

        Args:
            warnings: List of warning messages
        """
        if not warnings:
            return

        print(self._color("Warnings:", "running"))
        for warning in warnings:
            print(f"  ⚠  {warning}")
        print()

    def print_recommendations(self, recommendations: List[str]):
        """
        Print recommendations.

        Args:
            recommendations: List of recommendation messages
        """
        if not recommendations:
            return

        print("Recommendations:")
        for rec in recommendations:
            print(f"  💡 {rec}")
        print()

    def print_footer(self, action: str = "continue"):
        """
        Print footer with action prompt.

        Args:
            action: Action to take ('continue', 'abort', 'complete')
        """
        print("=" * 80)

        if action == "continue":
            print("Ready to proceed? Pipeline will skip cached stages.")
        elif action == "abort":
            print(self._color("Pipeline aborted.", "failed"))
        elif action == "complete":
            print(self._color("✓ Pipeline completed successfully!", "completed"))

        print("=" * 80)
        print()

    def print_compact_summary(self):
        """Print a compact one-line summary."""
        completed = sum(1 for s in self.stages if s.status == 'completed')
        cached = sum(1 for s in self.stages if s.status == 'cached')
        failed = sum(1 for s in self.stages if s.status == 'failed')
        running = sum(1 for s in self.stages if s.status == 'running')
        pending = sum(1 for s in self.stages if s.status == 'pending')

        parts = []
        if completed > 0:
            parts.append(self._color(f"{completed} completed", "completed"))
        if cached > 0:
            parts.append(self._color(f"{cached} cached", "cached"))
        if running > 0:
            parts.append(self._color(f"{running} running", "running"))
        if pending > 0:
            parts.append(self._color(f"{pending} pending", "pending"))
        if failed > 0:
            parts.append(self._color(f"{failed} failed", "failed"))

        summary = " | ".join(parts)
        print(f"[{summary}]")


def estimate_stage_cost(stage: str, scene_count: int, mode: str) -> float:
    """
    Estimate cost for a stage.

    Args:
        stage: Stage name
        scene_count: Number of scenes
        mode: Pipeline mode ('static', 'slides', 'video')

    Returns:
        Estimated cost in dollars
    """
    costs = {
        'scene_generation': 0.02,  # Per request (Claude Sonnet)
        'audio_generation': 0.0,   # Free (local Chatterbox)
        'image_generation': 0.15 * scene_count,  # Per image (GPT-Image)
        'video_generation_slides': 0.0,  # Free (FFmpeg)
        'video_generation_sora': 15.0 * scene_count,  # Per video (Sora)
        'assembly': 0.0  # Free (FFmpeg)
    }

    # Adjust video generation cost based on mode
    if stage == 'video_generation':
        if mode == 'video':
            return costs['video_generation_sora']
        else:
            return costs['video_generation_slides']

    return costs.get(stage, 0.0)


def estimate_stage_time(stage: str, scene_count: int, mode: str, workers: int = 1) -> float:
    """
    Estimate time for a stage.

    Args:
        stage: Stage name
        scene_count: Number of scenes
        mode: Pipeline mode
        workers: Number of parallel workers

    Returns:
        Estimated time in seconds
    """
    times = {
        'scene_generation': 10.0,
        'audio_generation': 20.0 * scene_count / workers,
        'image_generation': 8.0 * scene_count,
        'video_generation_slides': 2.0 * scene_count,
        'video_generation_sora': 90.0 * scene_count,
        'assembly': 5.0
    }

    if stage == 'video_generation':
        if mode == 'video':
            return times['video_generation_sora']
        else:
            return times['video_generation_slides']

    return times.get(stage, 0.0)
