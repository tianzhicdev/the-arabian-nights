# Code Quality Improvement - Action Items

## Critical Issues to Fix Immediately

### 1. Input Validation (P0)
- [ ] Add path existence checks in `create_static_video_with_waveform()` before ffmpeg
- [ ] Validate `static_background` exists in `generate_static_videos()` before loop
- [ ] Check `args.text` and `args.scenes` files exist at pipeline start
- [ ] Validate output directory is writable at initialization

**Files affected:** pipeline_manager.py, video_assembler.py

### 2. Exception Handling (P0)
- [ ] Fix bare `except:` in audio_backend.py line 100 → `except (json.JSONDecodeError, ValueError)`
- [ ] Add try/except for subprocess.run() with check=True in pipeline_manager.py:296
- [ ] Add try/except for json.load() in pipeline_manager.py:157
- [ ] Handle FFprobe failures with proper error context in video_assembler.py:180-184, 232-237
- [ ] Validate float conversion from ffprobe output

**Files affected:** audio_backend.py, pipeline_manager.py, video_assembler.py

### 3. Dependency Validation (P0)
- [ ] Add `verify_dependencies()` function to check ffmpeg/ffprobe installed
- [ ] Call in main before pipeline starts
- [ ] Provide helpful error message with installation instructions

**Files affected:** main entry point

---

## High Priority Issues (Fix This Sprint)

### 4. Code Deduplication (P1)
- [ ] Extract FFprobe command to utility function: `utils/ffmpeg_utils.py:get_audio_duration()`
  - Replace 5 instances in video_assembler.py and audio_generator.py
- [ ] Extract `determine_video_chunks()` to module function in video_generator.py
  - Remove from both SceneVideoGenerator and ParallelVideoGenerator
- [ ] Extract `_build_video_prompt()` to module function in video_generator.py
  - Share between both generator classes
- [ ] Create `run_ffmpeg_command()` wrapper to handle error reporting consistently

**Files affected:** video_assembler.py, audio_generator.py, video_generator.py

### 5. Logging Implementation (P1)
- [ ] Configure logging module in main
- [ ] Replace all `print()` statements with `logger.info()`, `logger.debug()`, `logger.error()`
- [ ] Add file and console handlers with timestamps
- [ ] Remove hardcoded print formatting (separator lines, etc.)

**Files affected:** All modules

**Script template:**
```python
import logging

logger = logging.getLogger(__name__)

# In main:
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/pipeline.log'),
        logging.StreamHandler()
    ]
)
```

### 6. Configuration Management (P1)
- [ ] Create `VideoEncodeConfig` dataclass in video_assembler.py
  - Extract hardcoded FFmpeg parameters: preset, crf, audio_bitrate, resolution
  - Create presets: high_quality(), fast_preview(), streaming()
- [ ] Implement waveform_style parameter usage in `create_static_video_with_waveform()`
  - Accept waveform_size, waveform_color, waveform_mode parameters
- [ ] Create `APIConfig` dataclass in video_generator.py
  - Move hardcoded max_concurrent (153), timeout (424), retry count (372)

**Files affected:** video_assembler.py, video_generator.py

### 7. Type Safety (P1)
- [ ] Add return type hints to all methods in pipeline_manager.py
- [ ] Add parameter type hints to all methods in pipeline_manager.py
- [ ] Create TypedDict for Scene structure
- [ ] Create TypedDict for ScenesData structure
- [ ] Add `Optional[]` type hints for optional parameters

**Files affected:** pipeline_manager.py, audio_generator.py, video_generator.py

---

## Medium Priority Issues (Next Sprint)

### 8. Static Mode Validation (P2)
- [ ] Ensure consistent error handling across all generate_*_videos methods
- [ ] Log warnings when skipping scenes due to missing files
- [ ] Add progress bar for static video generation using tqdm

**Files affected:** pipeline_manager.py

### 9. Async Error Handling (P2)
- [ ] Log exceptions caught by `return_exceptions=True` in gather() calls
- [ ] Add context about which scene failed in exception messages
- [ ] Handle timeout exceptions explicitly instead of letting them propagate

**Files affected:** video_generator.py

### 10. Progress Reporting (P2)
- [ ] Replace manual progress tracking with tqdm
- [ ] Implement consistent progress output format across all modules
- [ ] Add ETA estimates for long operations

**Files affected:** pipeline_manager.py, audio_generator.py, video_generator.py

### 11. Error Message Quality (P2)
- [ ] Enhance error messages with context about which file/scene failed
- [ ] Include relevant file paths in error messages
- [ ] Truncate long FFmpeg stderr to first 500 chars for readability
- [ ] Add operation context (e.g., "Failed to generate image for scene_001")

**Files affected:** All modules

---

## Low Priority Issues (Nice to Have)

### 12. Code Organization (P3)
- [ ] Extract scene processing loop pattern to reusable function
- [ ] Create FFmpeg command builders to reduce string concatenation
- [ ] Move command definitions to constants or config objects
- [ ] Create validation utilities module

### 13. Testing (P3)
- [ ] Add unit tests for path validation functions
- [ ] Add tests for error handling in subprocess calls
- [ ] Mock FFmpeg commands in tests
- [ ] Test config objects with different preset combinations

### 14. Documentation (P3)
- [ ] Add docstrings to all public methods
- [ ] Document scene dictionary structure
- [ ] Document configuration options
- [ ] Add examples of error handling patterns

### 15. Refactoring (P3)
- [ ] Create base class for video processing stages
- [ ] Use composition over inheritance for shared logic
- [ ] Extract pipeline orchestration from PipelineManager
- [ ] Create pipeline stage interfaces

---

## Implementation Order (Recommended)

### Week 1
1. Critical exception handling fixes (P0)
2. Input validation (P0)
3. Dependency checking (P0)

### Week 2
4. Logging implementation (P1)
5. Code deduplication - FFprobe extraction (P1)
6. Type hints (P1)

### Week 3
7. Configuration classes (P1)
8. Code deduplication - remaining items (P1)
9. Static mode validation (P2)

### Week 4
10. Async error handling improvements (P2)
11. Progress reporting (P2)
12. Error message enhancements (P2)

---

## Estimated Impact

| Issue Category | Count | Severity | Impact |
|---|---|---|---|
| Critical Errors | 6 | CRITICAL | Pipeline crashes, data loss |
| Unhandled Exceptions | 11 | HIGH | Confusing error messages |
| Code Duplication | 5 | HIGH | Maintenance burden |
| Missing Logging | 56+ | HIGH | Debugging difficulty |
| Config Magic Numbers | 4 | HIGH | Inflexible, hard to test |
| Type Safety | 5 | HIGH | IDE/linting issues |

**Total Issues:** 53
**Estimated Fix Time:** 3-4 weeks
**Estimated Test Time:** 1-2 weeks
**Total Effort:** 4-6 weeks

---

## Quick Wins (Can do in 1-2 days)

1. Add try/except for json.load() - 30 mins
2. Fix bare except in audio_backend.py - 15 mins
3. Add dependency checking - 1 hour
4. Configure basic logging - 2 hours
5. Extract FFprobe utility function - 2 hours

**Total: ~6 hours of focused work**

---

## Risk Mitigation

Before making changes:
1. Create feature branch: `git checkout -b refactor/code-quality`
2. Run existing tests to establish baseline
3. Make changes incrementally (one issue category at a time)
4. Add tests for new validation/error handling
5. Test error paths explicitly
6. Review with team before merging

---

## Questions for Team

1. Should single scene failure stop entire pipeline or continue with partial results?
2. What quality preset should be default for video encoding?
3. How many concurrent API requests should be allowed by default?
4. Should we add retry logic for failed scenes?
5. How verbose should logging be by default (INFO vs DEBUG)?

