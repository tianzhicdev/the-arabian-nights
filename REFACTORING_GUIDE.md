# Refactoring Guide for Video Generation Pipeline

## Overview

This document provides guidance for refactoring the video generation pipeline based on the comprehensive codebase analysis.

## Current State Assessment

**Status:** Production-Ready ✅
- Core functionality: Fully working
- Performance: Well optimized (4-5x faster with parallelization)
- Reliability: Stable with checkpoint/resume system

**Ready for Refactoring:** Yes
- Architecture is clear and understandable
- Code is mostly well-organized
- Opportunity for improvement without disrupting core functionality

---

## Refactoring Priorities

### Phase 1: Foundation (High Impact, Low Risk) - Week 1

#### 1.1 Logging System
**Current:** Uses `print()` everywhere  
**Problem:** Hard to debug production issues, no log levels, unclear what's important  
**Solution:** Replace all `print()` with Python `logging` module

**Implementation:**
```python
# Create: scripts/logger.py
import logging

def setup_logger(name, log_file=None, level=logging.INFO):
    """Setup logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console)
    
    # File handler (optional)
    if log_file:
        file_h = logging.FileHandler(log_file)
        file_h.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_h)
    
    return logger
```

**Changes Required:**
- Replace `print(...)` with `logger.info(...)`
- Use `logger.warning()` for warnings
- Use `logger.error()` for errors
- Use `logger.debug()` for detailed info
- Add `--log-level` CLI argument

**Effort:** 2-3 hours  
**Impact:** High (debugging, monitoring)

---

#### 1.2 Configuration File Support
**Current:** All parameters via CLI arguments  
**Problem:** Long command lines, hard to manage multiple configurations  
**Solution:** Add YAML config file support with CLI override

**Implementation:**
```python
# Create: scripts/config.py
import yaml
from dataclasses import dataclass
from pathlib import Path

@dataclass
class GenerationConfig:
    """Pipeline configuration"""
    content: str
    audio_reference: str
    art_style: str
    narrator_style: str
    length: str
    episode_title: Optional[str] = None
    device: str = "cpu"
    speed: float = 1.0
    sora_model: str = "sora-2"
    scene_model: str = "anthropic/claude-sonnet-4.5"
    audio_workers: int = 4
    video_concurrent: int = 5
    max_retries: int = 5
    
    @classmethod
    def from_yaml(cls, path: str) -> 'GenerationConfig':
        """Load config from YAML file"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, path: str):
        """Save config to YAML file"""
        with open(path, 'w') as f:
            yaml.dump(asdict(self), f)

# Usage:
# Config file: pipeline.yaml
# content: Anansi.txt
# audio_reference: resources/voices/sample.mp3
# art_style: "watercolor storybook"
# narrator_style: "warm, curious"
# length: 5m

config = GenerationConfig.from_yaml("pipeline.yaml")
```

**Changes Required:**
- Create `GenerationConfig` dataclass
- Update CLI to accept `--config` argument
- CLI args override config file values
- Update `generate_video_end_to_end.py` to use new config

**Effort:** 2-3 hours  
**Impact:** High (usability, maintainability)

---

### Phase 2: Architecture Improvements (Medium Risk) - Week 2

#### 2.1 Dependency Injection
**Current:** Classes create their own dependencies (tight coupling)  
**Problem:** Hard to test, difficult to swap implementations  
**Solution:** Pass dependencies to constructors

**Before:**
```python
class ParallelAudioGenerator:
    def __init__(self, audio_prompt_path, device, speed, max_workers):
        self.backend = ChatterboxBackend(...)  # Tightly coupled
```

**After:**
```python
class ParallelAudioGenerator:
    def __init__(self, audio_backend, max_workers):
        self.backend = audio_backend  # Dependency injected
```

**Changes Required:**
- Create factory classes for creating clients and backends
- Pass dependencies to stage classes
- Update main orchestrator to wire up dependencies
- Create dependency container for initialization

**Effort:** 4-6 hours  
**Impact:** Medium (testability, flexibility)

---

#### 2.2 Unified Async Architecture
**Current:** Audio uses ProcessPoolExecutor, video uses asyncio  
**Problem:** Mixed patterns, harder to reason about, potential scaling issues  
**Solution:** Use async/await for both

**Before:**
```python
# Audio: ProcessPoolExecutor
with ProcessPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(worker, scene) for scene in scenes]
    
# Video: asyncio
async def generate_all_scenes(...):
    tasks = [_generate_scene_async(scene) for scene in scenes]
    await asyncio.gather(*tasks)
```

**After:**
```python
# Both: async/await
async def generate_audio_all_scenes(...):
    semaphore = asyncio.Semaphore(max_workers)
    tasks = [_generate_scene_audio_async(scene, semaphore) for scene in scenes]
    return await asyncio.gather(*tasks)

async def generate_video_all_scenes(...):
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = [_generate_scene_video_async(scene, semaphore) for scene in scenes]
    return await asyncio.gather(*tasks)
```

**Changes Required:**
- Refactor audio generation to use asyncio
- Make main orchestrator async
- Update ChatterboxBackend interface if needed
- Test with CPU-bound audio tasks (may need asyncio.to_thread)

**Effort:** 6-8 hours  
**Impact:** High (consistency, potential performance)

---

#### 2.3 Abstract Stage Pattern
**Current:** Each stage is independent, no common interface  
**Problem:** Difficult to extend, test, or modify behavior  
**Solution:** Create abstract Stage base class

**Implementation:**
```python
# Create: scripts/pipeline/stage.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any
import asyncio

class PipelineStage(ABC):
    """Abstract base for pipeline stages"""
    
    def __init__(self, name: str, checkpoint_mgr=None, logger=None):
        self.name = name
        self.checkpoint_mgr = checkpoint_mgr
        self.logger = logger or logging.getLogger(self.name)
    
    @abstractmethod
    async def execute(self, input_data: Dict) -> Dict:
        """Execute the stage"""
        pass
    
    @abstractmethod
    def get_pending_items(self) -> List[int]:
        """Get list of items needing processing"""
        pass
    
    def log(self, msg, level='info'):
        """Log stage message"""
        getattr(self.logger, level)(f"[{self.name}] {msg}")

# Implementations
class SceneGenerationStage(PipelineStage):
    async def execute(self, input_data: Dict) -> Dict:
        # Implementation
        pass

class AudioGenerationStage(PipelineStage):
    async def execute(self, input_data: Dict) -> Dict:
        # Implementation
        pass
```

**Usage:**
```python
# Main orchestrator becomes simpler
stages = [
    SceneGenerationStage(),
    AudioGenerationStage(max_workers=4),
    VideoGenerationStage(max_concurrent=5),
    AssemblyStage()
]

for stage in stages:
    if stage.name not in checkpoint['completed_stages']:
        result = await stage.execute(result)
        checkpoint.mark_completed(stage.name)
```

**Changes Required:**
- Create abstract Stage class
- Refactor each stage to inherit from it
- Update main orchestrator to use stage interface
- Add stage registry for easier management

**Effort:** 8-10 hours  
**Impact:** Medium-High (extensibility, testability, maintainability)

---

### Phase 3: New Features (Week 3)

#### 3.1 Static Background/Podcast Mode
**Current:** NOT IMPLEMENTED  
**Problem:** Can't generate audio-only or static background content  
**Solution:** Add mode option, skip video generation, generate static images instead

**Implementation:**
```python
@dataclass
class GenerationConfig:
    # ... existing fields ...
    mode: str = "video"  # "video", "audio-only", "static-background"
    background_style: Optional[str] = None  # For static mode

# In main pipeline
if config.mode == "audio-only":
    # Skip video generation
    # Skip assembly
    output_path = save_audio_as_podcast()
    
elif config.mode == "static-background":
    # Generate static images per scene instead of video
    # Use DALL-E or Flux instead of Sora
    image_paths = await generate_static_images(scenes)
    # Create video from static images + audio
    video_paths = assemble_static_with_audio(image_paths, audio_paths)
    
elif config.mode == "video":
    # Current behavior
    video_paths = await generate_videos(scenes)
```

**New Modules Needed:**
- `scripts/image_generator.py` - Static image generation
- `scripts/static_assembler.py` - Create video from static images

**Changes Required:**
- Add mode field to config
- Create image generation interface (similar to video generator)
- Implement DALL-E or Flux image client
- Update assembly logic for static mode
- Update output structure for different modes

**Effort:** 12-16 hours  
**Impact:** High (new capability)

---

#### 3.2 Cost Tracking System
**Current:** NOT IMPLEMENTED  
**Problem:** Can't track spending on APIs  
**Solution:** Track API calls and calculate costs

**Implementation:**
```python
# Create: scripts/cost_tracker.py
@dataclass
class APICall:
    service: str  # "openai", "openrouter", etc.
    operation: str  # "video_generation", "scene_generation", etc.
    input_tokens: int = 0
    output_tokens: int = 0
    duration_seconds: float = 0
    cost_usd: float = 0

class CostTracker:
    """Track API costs across pipeline"""
    
    PRICING = {
        "openrouter": {
            "anthropic/claude-sonnet-4.5": {
                "input": 3.0 / 1_000_000,  # per token
                "output": 15.0 / 1_000_000
            }
        },
        "openai": {
            "sora-2": 0.08,  # per 1000 video frames
            "dall-e-3": 0.08  # per image
        }
    }
    
    def track_openrouter_call(self, model, input_tokens, output_tokens):
        """Track OpenRouter API call"""
        pricing = self.PRICING["openrouter"][model]
        cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
        self.calls.append(APICall(
            service="openrouter",
            operation="scene_generation",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost
        ))
    
    def get_summary(self) -> Dict:
        """Get cost summary"""
        total_cost = sum(call.cost_usd for call in self.calls)
        by_service = defaultdict(float)
        by_operation = defaultdict(float)
        for call in self.calls:
            by_service[call.service] += call.cost_usd
            by_operation[call.operation] += call.cost_usd
        return {
            "total_cost_usd": total_cost,
            "by_service": dict(by_service),
            "by_operation": dict(by_operation),
            "num_calls": len(self.calls)
        }
```

**Changes Required:**
- Create CostTracker class
- Track all API calls in respective clients
- Update metadata to include costs
- Display cost summary at end of pipeline

**Effort:** 4-6 hours  
**Impact:** Medium (monitoring, budgeting)

---

## Implementation Roadmap

### Week 1: Foundation
```
Monday:    Logging system (2-3 hrs) + Testing (1 hr)
Tuesday:   Config file support (2-3 hrs) + Testing (1 hr)
Wednesday: Integration testing (2-3 hrs) + Documentation (1 hr)
Thursday:  Buffer / Additional improvements
Friday:    Review and cleanup
```

### Week 2: Architecture
```
Monday:    Dependency injection setup (2 hrs) + Stage abstraction (4 hrs)
Tuesday:   Refactor stages (6-8 hrs)
Wednesday: Testing and integration (4 hrs)
Thursday:  AsyncIO unification (6-8 hrs)
Friday:    Testing, buffer, cleanup
```

### Week 3: Features
```
Monday:    Static mode design + image generation (4 hrs)
Tuesday:   Image generation implementation (4-6 hrs)
Wednesday: Static mode integration (4 hrs)
Thursday:  Cost tracking system (4 hrs)
Friday:    Testing, documentation, cleanup
```

---

## Testing Strategy

### Unit Tests
```python
# tests/test_config.py
def test_config_from_yaml():
    config = GenerationConfig.from_yaml("test_config.yaml")
    assert config.length == "5m"

# tests/test_checkpoint.py
def test_checkpoint_resume():
    mgr = CheckpointManager(tmp_dir)
    cp1 = mgr.load_or_create("test")
    mgr.mark_scene_completed(cp1, "audio_generation", 1)
    
    cp2 = mgr.load_or_create("test")
    assert 1 in cp2["audio_generation"]["completed_scenes"]
```

### Integration Tests
```python
# tests/test_pipeline_integration.py
@pytest.mark.asyncio
async def test_end_to_end_short():
    """Test full pipeline with minimal data"""
    config = GenerationConfig(
        content="short_test.txt",
        length="30s",
        # ... other params ...
    )
    result = await run_pipeline(config)
    assert result["final_video_path"].exists()
```

---

## Backward Compatibility

All changes should maintain backward compatibility:

1. **CLI Arguments:** Keep existing args, add new ones as optional
2. **Output Structure:** Don't change existing output paths
3. **Checkpoint Format:** Version the checkpoint schema
4. **API Clients:** Don't change public method signatures

---

## Performance Considerations

### Async AudioGenerator
- Use `asyncio.to_thread()` for CPU-bound Chatterbox calls
- Semaphore limits to avoid context switch overhead
- **Expected impact:** Similar performance, more consistent patterns

### Unified Architecture
- Reduces context switching overhead
- Easier to implement backpressure
- **Expected impact:** 5-10% performance improvement

### Dependency Injection
- No performance impact
- May enable better memory management
- **Expected impact:** Neutral

---

## Success Criteria

### Phase 1
- All print statements moved to logging
- Config file loading works
- CLI args override config values
- All existing tests still pass

### Phase 2
- All stages inherit from PipelineStage
- Audio and video use unified async pattern
- Dependency injection implemented
- 100% backward compatible

### Phase 3
- Static mode fully functional
- Cost tracking implemented and tested
- Documentation complete
- All tests passing

---

## Risk Mitigation

**High-Risk Areas:**
1. Async audio generation (CPU-bound) - Use `asyncio.to_thread()`
2. Checkpoint format changes - Add versioning
3. API client changes - Extensive testing

**Mitigation Strategies:**
- Create feature branches for each phase
- Maintain original scripts during transition
- Comprehensive test coverage before removing old code
- Gradual migration (e.g., support both old and new config formats)

---

## Effort Estimation

| Phase | Component | Hours | Effort |
|---|---|---|---|
| 1 | Logging | 3 | Easy |
| 1 | Config | 3 | Easy |
| 2 | Dependency Injection | 5 | Medium |
| 2 | Abstract Stage | 9 | Medium |
| 2 | Async Unification | 7 | Medium |
| 3 | Static Mode | 15 | Hard |
| 3 | Cost Tracking | 5 | Easy |
| **Total** | | **47** | **~1 week** |

---

## Next Steps

1. **Read CODEBASE_ANALYSIS.md** - Full technical details
2. **Start with Phase 1** - Logging and config are low-risk, high-impact
3. **Create feature branches** - One per component
4. **Write tests first** - TDD approach for refactoring
5. **Review and integrate** - PR-based workflow

---

End of Refactoring Guide
