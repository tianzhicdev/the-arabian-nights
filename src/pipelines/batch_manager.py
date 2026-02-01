"""
Batch Manager - Resumable batch processing with progress tracking

Features:
- Process multiple stories with automatic resume
- Track batch progress (7/20 complete)
- Handle API errors gracefully (retry with backoff)
- Graceful shutdown (CTRL+C)
- Skip completed stories instantly
- Save batch state for resume
"""

import json
import signal
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import subprocess


class BatchProgress:
    """Tracks progress of batch processing."""

    def __init__(self, batch_file: Path):
        self.batch_file = batch_file
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load batch state or create new."""
        if self.batch_file.exists():
            with open(self.batch_file, 'r') as f:
                return json.load(f)

        return {
            'version': '1.0',
            'started_at': datetime.now().isoformat(),
            'jobs': {},  # job_id -> status
            'stats': {
                'completed': 0,
                'failed': 0,
                'skipped': 0,
                'total': 0
            }
        }

    def _save_state(self):
        """Save batch state to disk."""
        self.state['updated_at'] = datetime.now().isoformat()
        with open(self.batch_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def mark_started(self, job_id: str, metadata: Dict):
        """Mark job as started."""
        self.state['jobs'][job_id] = {
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'metadata': metadata
        }
        self._save_state()

    def mark_completed(self, job_id: str, cost: float = 0.0):
        """Mark job as completed."""
        if job_id in self.state['jobs']:
            self.state['jobs'][job_id]['status'] = 'completed'
            self.state['jobs'][job_id]['completed_at'] = datetime.now().isoformat()
            self.state['jobs'][job_id]['cost'] = cost

        self.state['stats']['completed'] += 1
        self._save_state()

    def mark_failed(self, job_id: str, error: str):
        """Mark job as failed."""
        if job_id in self.state['jobs']:
            self.state['jobs'][job_id]['status'] = 'failed'
            self.state['jobs'][job_id]['failed_at'] = datetime.now().isoformat()
            self.state['jobs'][job_id]['error'] = error

        self.state['stats']['failed'] += 1
        self._save_state()

    def mark_skipped(self, job_id: str, reason: str = "Already complete"):
        """Mark job as skipped (cached)."""
        if job_id not in self.state['jobs']:
            self.state['jobs'][job_id] = {}

        self.state['jobs'][job_id]['status'] = 'skipped'
        self.state['jobs'][job_id]['reason'] = reason
        self.state['stats']['skipped'] += 1
        self._save_state()

    def is_completed(self, job_id: str) -> bool:
        """Check if job is already completed."""
        return self.state['jobs'].get(job_id, {}).get('status') == 'completed'

    def get_status(self, job_id: str) -> Optional[str]:
        """Get job status."""
        return self.state['jobs'].get(job_id, {}).get('status')

    def get_summary(self) -> str:
        """Get human-readable summary."""
        stats = self.state['stats']
        total = stats['total']
        completed = stats['completed']
        failed = stats['failed']
        skipped = stats['skipped']

        lines = []
        lines.append("=" * 80)
        lines.append("BATCH PROGRESS")
        lines.append("=" * 80)
        lines.append(f"Total Jobs: {total}")
        lines.append(f"Completed:  {completed}/{total} ({completed/total*100 if total > 0 else 0:.1f}%)")
        lines.append(f"Skipped:    {skipped}/{total} (cached)")
        lines.append(f"Failed:     {failed}/{total}")
        lines.append("=" * 80)

        return "\n".join(lines)


class BatchManager:
    """
    Manages batch processing with resumability.

    Features:
    - Automatic resume from interruption
    - API error handling with retry
    - Graceful shutdown on CTRL+C
    - Progress tracking
    - Skip completed jobs instantly
    """

    def __init__(self, batch_name: str, jobs: List[Dict[str, Any]]):
        """
        Initialize batch manager.

        Args:
            batch_name: Name of the batch (e.g., "gutenberg_stories")
            jobs: List of job dicts with 'id', 'command', 'output_dir', 'metadata'
        """
        self.batch_name = batch_name
        self.jobs = jobs
        self.progress_file = Path(f'batch_progress_{batch_name}.json')
        self.progress = BatchProgress(self.progress_file)
        self.progress.state['stats']['total'] = len(jobs)

        # Track if we should stop (CTRL+C)
        self.should_stop = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown on CTRL+C."""
        def signal_handler(signum, frame):
            print("\n\n⚠️  Interrupt received! Finishing current job and stopping...")
            print("    (Press CTRL+C again to force quit)")
            self.should_stop = True

            # Second CTRL+C = force quit
            signal.signal(signal.SIGINT, lambda s, f: sys.exit(1))

        signal.signal(signal.SIGINT, signal_handler)

    def _check_job_complete_fast(self, output_dir: Path) -> bool:
        """
        Fast check if job is complete by looking for final video.

        This is a quick check before running the full pipeline.
        If final video exists, we assume job is complete.

        Args:
            output_dir: Job output directory

        Returns:
            True if job appears complete
        """
        # Check for final video (assembly output)
        video_files = list(output_dir.glob('*_slides.mp4'))
        if not video_files:
            video_files = list(output_dir.glob('*_video.mp4'))
        if not video_files:
            video_files = list(output_dir.glob('*_static.mp4'))

        return len(video_files) > 0

    def run_job_with_retry(self, job: Dict, max_retries: int = 3) -> bool:
        """
        Run a single job with retry on API errors.

        Args:
            job: Job dictionary
            max_retries: Maximum retry attempts

        Returns:
            True if successful, False if failed
        """
        job_id = job['id']
        command = job['command']
        output_dir = Path(job['output_dir'])

        for attempt in range(1, max_retries + 1):
            try:
                print(f"\n{'=' * 80}")
                print(f"Running: {job_id}")
                if attempt > 1:
                    print(f"Attempt {attempt}/{max_retries} (retrying after error)")
                print(f"{'=' * 80}\n")

                # Mark as started
                self.progress.mark_started(job_id, job.get('metadata', {}))

                # Run command
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True
                )

                # Check result
                if result.returncode == 0:
                    self.progress.mark_completed(job_id, cost=0.0)
                    print(f"\n✓ Completed: {job_id}")
                    return True
                else:
                    # Check if it's a retryable error
                    error_output = result.stderr.lower()

                    # API errors that can be retried
                    retryable_errors = [
                        '429',  # Rate limit
                        'rate limit',
                        'timeout',
                        'connection',
                        'temporarily unavailable',
                        '503',  # Service unavailable
                        '500'   # Internal server error (sometimes transient)
                    ]

                    is_retryable = any(err in error_output for err in retryable_errors)

                    if is_retryable and attempt < max_retries:
                        wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                        print(f"\n⚠️  Retryable error detected. Waiting {wait_time}s before retry...")
                        print(f"   Error: {result.stderr[:200]}")
                        time.sleep(wait_time)
                        continue
                    else:
                        # Not retryable or out of retries
                        error_msg = result.stderr[:500]
                        self.progress.mark_failed(job_id, error_msg)
                        print(f"\n✗ Failed: {job_id}")
                        print(f"   Error: {error_msg}")
                        return False

            except Exception as e:
                error_msg = str(e)
                self.progress.mark_failed(job_id, error_msg)
                print(f"\n✗ Exception in {job_id}: {error_msg}")
                return False

        # All retries exhausted
        return False

    def run_batch(self, skip_completed: bool = True):
        """
        Run entire batch with resume capability.

        Args:
            skip_completed: If True, skip jobs marked as completed in progress file
        """
        print("\n" + "=" * 80)
        print(f"BATCH: {self.batch_name}")
        print(f"Total Jobs: {len(self.jobs)}")
        print("=" * 80)

        # Check if this is a resume
        completed_count = self.progress.state['stats']['completed']
        if completed_count > 0:
            print(f"\n📥 RESUMING BATCH (found {completed_count} completed jobs)")
            print(f"   Progress file: {self.progress_file}")
            print()

        start_time = datetime.now()
        processed = 0
        skipped = 0

        for i, job in enumerate(self.jobs, 1):
            job_id = job['id']
            output_dir = Path(job['output_dir'])

            # Check if should stop
            if self.should_stop:
                print(f"\n⚠️  Stopping after job {i-1}/{len(self.jobs)}")
                print(f"   Resume by running this script again")
                break

            print(f"\n[{i}/{len(self.jobs)}] {job_id}")

            # Fast check: Is it already completed?
            if skip_completed and self.progress.is_completed(job_id):
                print(f"  ✓ Already completed (from previous run)")
                skipped += 1
                continue

            # Quick check: Does final output exist?
            if self._check_job_complete_fast(output_dir):
                print(f"  ✓ Final video found, skipping")
                self.progress.mark_skipped(job_id, "Final video exists")
                skipped += 1
                continue

            # Run the job
            success = self.run_job_with_retry(job, max_retries=3)
            processed += 1

            # Show progress
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / processed if processed > 0 else 0
            remaining_jobs = len(self.jobs) - i
            est_remaining = avg_time * remaining_jobs

            print(f"\n   Progress: {i}/{len(self.jobs)} jobs")
            print(f"   Processed: {processed}, Skipped: {skipped}")
            print(f"   Est. remaining: {est_remaining/60:.1f} minutes")

        # Final summary
        print("\n\n" + self.progress.get_summary())

        elapsed_total = (datetime.now() - start_time).total_seconds()
        print(f"\nTotal time: {elapsed_total/60:.1f} minutes")
        print(f"Progress saved to: {self.progress_file}")
        print("\nTo resume if interrupted, just run this script again!")
        print()


def create_jobs_from_bash_script(script_path: Path) -> List[Dict]:
    """
    Parse bash script to extract jobs.

    Args:
        script_path: Path to bash script

    Returns:
        List of job dictionaries
    """
    jobs = []

    with open(script_path, 'r') as f:
        lines = f.readlines()

    current_command = []
    current_comment = None

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Extract comment (job name)
        if line.startswith('# Story'):
            current_comment = line[2:].strip()  # Remove "# "
            continue

        # Skip other comments
        if line.startswith('#'):
            continue

        # Build command (multi-line with backslashes)
        if line.startswith('python'):
            current_command = [line.rstrip('\\').strip()]
        elif current_command and not line.startswith('python'):
            current_command.append(line.rstrip('\\').strip())

            # End of command (no trailing backslash)
            if not line.endswith('\\'):
                # Parse command
                full_command = ' '.join(current_command)

                # Extract output dir
                import re
                match = re.search(r'--output-dir\s+(\S+)', full_command)
                if match:
                    output_dir = match.group(1)
                    job_id = Path(output_dir).name

                    jobs.append({
                        'id': job_id,
                        'command': full_command,
                        'output_dir': output_dir,
                        'metadata': {
                            'description': current_comment
                        }
                    })

                # Reset
                current_command = []
                current_comment = None

    return jobs


if __name__ == '__main__':
    # Example: Run gutenberg batch
    import sys

    if len(sys.argv) > 1:
        script_path = Path(sys.argv[1])
    else:
        script_path = Path('../run_gutenberg_videos.sh')

    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        sys.exit(1)

    print(f"Parsing batch script: {script_path}")

    # Parse jobs
    jobs = create_jobs_from_bash_script(script_path)
    print(f"Found {len(jobs)} jobs")

    # Run batch
    batch = BatchManager('gutenberg_stories', jobs)
    batch.run_batch(skip_completed=True)
