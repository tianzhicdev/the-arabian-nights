# TODO - The Arabian Nights Project

## Audio Quality Improvements

### 1. Try Alternative Audio Generation for Better Voice Quality
**Priority**: High
**Status**: Pending

**Current Issue**:
- Current Chatterbox-generated audio may not have the ideal meditative, low voice quality
- Need professional-sounding narration for audiobook content

**Action Items**:
- [ ] Research ElevenLabs API pricing and quality
  - Consider paid tier for professional voice quality
  - Test sample generation with meditative voice profiles
- [ ] Compare alternatives:
  - [ ] ElevenLabs (most professional, paid)
  - [ ] Azure TTS (good quality, reasonable pricing)
  - [ ] Google Cloud TTS (good alternative)
  - [ ] PlayHT (audiobook-focused)
- [ ] Test with 1-2 scenes from Rip Van Winkle
- [ ] Evaluate voice characteristics:
  - Low, calm, meditative tone
  - Natural pacing for storytelling
  - Emotional range for dramatic moments
- [ ] If quality improvement is significant, regenerate audio for:
  - [ ] Rip Van Winkle (99 scenes)
  - [ ] Man from Underground (128 scenes)
  - [ ] Animal Farm E2-E10 (pending episodes)

**Cost Consideration**: ElevenLabs paid tier may be worth investment for professional audiobook quality

---

## Image Quality Improvements

### 2. Regenerate Low-Quality Images
**Priority**: Medium
**Status**: Pending

**Current Issue**:
- Some GPT-Image-1.5 generated images don't meet quality standards
- Need to identify and regenerate problematic images

**Action Items**:
- [ ] Review all generated images and identify bad ones:
  - [ ] Rip Van Winkle (99 images)
  - [ ] Man from Underground (128 images - in progress)
  - [ ] Animal Farm E2 (50 images)
  - [ ] Animal Farm E3-E10 (when complete)
- [ ] Document specific issues:
  - [ ] Composition problems
  - [ ] Style inconsistencies
  - [ ] Character/object misrepresentation
  - [ ] Poor quality rendering
- [ ] Create list of scenes needing regeneration with improved prompts
- [ ] Consider alternative approaches:
  - [ ] Refine video_description prompts
  - [ ] Add more specific art direction
  - [ ] Use different reference images
  - [ ] Try DALL-E 3 for comparison
- [ ] Regenerate identified bad images
- [ ] Re-assemble affected videos

**Notes**:
- Keep original bad images in a separate folder for reference
- Document what prompt changes led to improvements

---

## Completed Items

### ✅ Rip Van Winkle Upload
- Uploaded to YouTube: https://www.youtube.com/watch?v=RFjv0BTQisU
- Category: Education
- Duration: 18:58
- Status: Public

---

## In Progress

### 🔄 Video Generation Pipeline
- [x] Rip Van Winkle - COMPLETE
- [ ] Man from Underground - Generating (scene 59+)
- [ ] Animal Farm E2 - Generating (scene 42+)
- [ ] Animal Farm E3 - COMPLETE
- [ ] Animal Farm E4 - In Progress
- [ ] Animal Farm E5-E10 - Queued
