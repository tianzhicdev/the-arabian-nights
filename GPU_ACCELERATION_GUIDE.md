# GPU Acceleration Guide - Speed Up Scene Generation

## Current Pipeline Analysis

Let's analyze where GPU can help in your workflow:

```
Your Current Pipeline:
┌─────────────────────────────────────────────────────────┐
│ 1. Scene Generation (OpenRouter API)      │ Remote GPU │
│ 2. Image Generation (GPT-Image API)       │ Remote GPU │
│ 3. Audio Generation (Chatterbox TTS)      │ CPU/Local  │ ⚠️ Can GPU accelerate
│ 4. Video Assembly (FFmpeg)                │ CPU/Local  │ ⚠️ Can GPU accelerate
│ 5. Format Conversion (FFmpeg)             │ CPU/Local  │ ⚠️ Can GPU accelerate
└─────────────────────────────────────────────────────────┘
```

**Currently using GPU:** Steps 1-2 (via APIs, running on their servers)
**Can add GPU acceleration:** Steps 3-5 (local processing)

---

## Option 1: Cloud GPU (Recommended - Fastest Setup)

### Why Cloud GPU?

✅ **Cheapest to start** - No hardware purchase
✅ **Flexible** - Pay per hour
✅ **Powerful** - Access to A100, H100 GPUs
✅ **Fast setup** - Running in 5 minutes

### Best Cloud GPU Services

#### A. RunPod (Best Value)
**Cost:** $0.34/hour (RTX 4090) to $1.89/hour (A100)

**Setup:**
```bash
# 1. Go to runpod.io
# 2. Create account
# 3. Deploy pod with PyTorch template
# 4. Upload your scripts via Jupyter
# 5. Run generation pipeline
```

**When to use:**
- Batch processing (run 10 episodes, then stop)
- Testing different models
- Don't want to buy hardware

#### B. Vast.ai (Cheapest)
**Cost:** $0.15-0.50/hour (RTX 3090/4090)

**Pros:**
- Cheapest rates
- Spot instances

**Cons:**
- Can be interrupted
- Variable availability

#### C. Lambda Labs
**Cost:** $0.50/hour (A10) to $1.10/hour (A100)

**Pros:**
- Reliable
- Good for long-running jobs

---

## Option 2: Local GPU (Best Long-Term)

### Mac Studio (If You Have Apple Silicon)

**Your Mac:** Likely M1/M2/M3 chip with unified memory

**Already has GPU!** The Neural Engine can accelerate:
- ✅ TTS (Chatterbox can use Metal)
- ✅ FFmpeg (with VideoToolbox)
- ⚠️ Local image generation (limited by memory)

**Optimize for Mac:**

```bash
# Use Metal acceleration for FFmpeg
ffmpeg -hwaccel videotoolbox \
  -i input.mp4 \
  -c:v h264_videotoolbox \
  output.mp4
```

**Limitations:**
- Can't run large image models (Stable Diffusion XL)
- Better for video encoding than image generation

---

### NVIDIA GPU for Mac (eGPU - Not Recommended)

**Cost:** $500-1500 (eGPU enclosure + GPU)

**Pros:**
- Adds real GPU to Mac

**Cons:**
- ❌ Apple dropped eGPU support in Apple Silicon
- ❌ Only works with Intel Macs
- ❌ Expensive
- ❌ Thunderbolt bandwidth limits

**Verdict:** Don't do this

---

### Build/Buy Windows PC with GPU (Best for Heavy Use)

**Recommended Build:**

```
Budget Build ($1,200):
- CPU: AMD Ryzen 5 7600 ($200)
- GPU: RTX 4060 Ti 16GB ($500)
- RAM: 32GB DDR5 ($100)
- SSD: 1TB NVMe ($80)
- PSU: 650W ($80)
- Case: $70
- Motherboard: $170

Mid-Range ($2,000):
- CPU: AMD Ryzen 7 7700X ($300)
- GPU: RTX 4070 Ti ($800)
- RAM: 64GB DDR5 ($200)
- SSD: 2TB NVMe ($150)
- PSU: 750W ($100)
- Case: $80
- Motherboard: $200

High-End ($4,000):
- CPU: AMD Ryzen 9 7950X ($550)
- GPU: RTX 4090 ($1,800)
- RAM: 128GB DDR5 ($500)
- SSD: 4TB NVMe ($300)
- PSU: 1000W ($180)
- Case: $150
- Motherboard: $300
```

**ROI Calculation:**

If using RunPod at $0.50/hour:
- 10 hours/week = $20/week = $1,040/year
- Budget PC pays for itself in ~14 months
- High-end PC pays for itself in ~46 months

**When to buy:**
- Processing 20+ hours per week
- Want full control
- Privacy concerns with cloud

---

## Option 3: Hybrid Approach (Recommended)

**Best Strategy:**

1. **Keep using APIs for:**
   - Scene text generation (OpenRouter)
   - Image generation (GPT-Image)
   - **Why:** Already fast, no setup needed

2. **Add GPU for local processing:**
   - Video encoding (FFmpeg with GPU)
   - Audio generation (Chatterbox with GPU)
   - Format conversion
   - **Why:** Speed up bottlenecks

3. **Use cloud GPU for:**
   - Batch processing
   - Testing new models
   - Overflow capacity
   - **Why:** Flexible, no upfront cost

---

## What Actually Benefits from GPU?

### 1. Image Generation ⭐⭐⭐

**Current:** GPT-Image API (~8s per image, $0.15)
**With Local GPU:** Stable Diffusion (~2-5s per image, free)

**GPU Requirements:**
- Minimum: RTX 3060 12GB
- Recommended: RTX 4070 Ti 12GB or RTX 4060 Ti 16GB
- Best: RTX 4090 24GB

**Speed Comparison:**
```
Animal Farm Episode (63 scenes):
API (GPT-Image): 63 × 8s = 504s (8.4 min) - $9.45
Local GPU (RTX 4090): 63 × 2s = 126s (2.1 min) - $0.00

Savings: 75% faster, $9.45 saved per episode
```

### 2. Video Encoding ⭐⭐

**Current:** CPU FFmpeg (slow)
**With GPU:** NVENC (NVIDIA encoder)

**Speed Improvement:**
```
CPU: 63 videos × 20s = 1,260s (21 min)
GPU: 63 videos × 5s = 315s (5.25 min)

Savings: 75% faster
```

### 3. Audio Generation ⭐

**Current:** Chatterbox on CPU
**With GPU:** Chatterbox with CUDA

**Speed Improvement:**
```
CPU: 63 scenes × 3s = 189s (3.15 min)
GPU: 63 scenes × 1s = 63s (1 min)

Savings: 67% faster
```

### 4. Scene Text Generation (Already GPU via API)

You're already using OpenRouter which runs on remote GPUs. No benefit to adding local GPU for this.

---

## Practical Recommendations

### If You Process < 5 Episodes/Week
**Use:** Current API approach + cloud GPU for batch jobs
**Cost:** ~$50/month
**Why:** Not worth buying hardware

### If You Process 5-20 Episodes/Week
**Use:** Budget/Mid-range PC with RTX 4060 Ti 16GB
**Cost:** $1,200 upfront + electricity
**ROI:** 6-12 months
**Why:** Heavy enough use to justify purchase

### If You Process 20+ Episodes/Week
**Use:** High-end PC with RTX 4090
**Cost:** $4,000 upfront
**ROI:** 12-18 months
**Why:** Maximum speed, full control

### If You Want to Try First
**Use:** RunPod for 1 month ($50-100)
**Why:** Test GPU acceleration before buying hardware

---

## How to Add GPU to Your Pipeline

### Step 1: Switch to Local Image Generation

**Install Stable Diffusion:**

```bash
# Clone ComfyUI (easiest interface)
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI

# Install dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# Download model
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors \
  -P models/checkpoints/
```

**Update your image generation:**

```python
# Old: Using GPT-Image API
from openai import OpenAI
image_url = client.images.generate(...)

# New: Using local Stable Diffusion
from diffusers import StableDiffusionXLPipeline
import torch

pipe = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16,
    variant="fp16"
).to("cuda")

image = pipe(prompt=scene_description).images[0]
image.save(f"output/images/scene_{i}.png")
```

**Speed:** 2-5 seconds per image (vs 8s with API)
**Cost:** $0 (vs $0.15 per image)

### Step 2: Add GPU-Accelerated FFmpeg

**Install FFmpeg with NVENC:**

```bash
# On Ubuntu/RunPod
sudo apt install ffmpeg

# Verify NVENC support
ffmpeg -encoders | grep nvenc
```

**Update video assembly:**

```python
# Old: CPU encoding
cmd = ['ffmpeg', '-i', 'input.mp4', '-c:v', 'libx264', 'output.mp4']

# New: GPU encoding
cmd = [
    'ffmpeg',
    '-hwaccel', 'cuda',
    '-i', 'input.mp4',
    '-c:v', 'h264_nvenc',  # Use NVIDIA encoder
    '-preset', 'p4',       # Fast preset
    '-b:v', '5M',
    'output.mp4'
]
```

**Speed:** 4-5x faster than CPU

### Step 3: GPU-Accelerate Chatterbox TTS

**Check if Chatterbox supports GPU:**

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
```

**Update TTS to use GPU:**

```python
# Load model on GPU
tts = Chatterbox(device="cuda")  # Instead of "cpu"

# Generate audio
audio = tts.generate(text, voice_id="sam")
```

---

## Cost Comparison: Full Episode

### Current Setup (APIs)
```
63 scenes:
- Scene generation: $0.02 × 63 = $1.26
- Images: $0.15 × 63 = $9.45
- Audio: Free (local CPU)
- Video: Free (local CPU)

Total: $10.71 per episode
Time: ~30 minutes
```

### With Local GPU (RTX 4090)
```
63 scenes:
- Scene generation: $0.02 × 63 = $1.26 (keep API)
- Images: $0.00 (local GPU)
- Audio: Free (local GPU, faster)
- Video: Free (local GPU, faster)

Total: $1.26 per episode
Time: ~10 minutes

Savings: $9.45 per episode + 67% faster
```

**ROI for RTX 4090 build ($4,000):**
- Savings: $9.45 per episode
- If 10 episodes/week: $94.50/week saved
- Payback: 42 weeks (~10 months)

---

## Quick Start: Test with RunPod

### 1. Sign up for RunPod
https://runpod.io

### 2. Deploy GPU Pod
```
Template: PyTorch 2.0
GPU: RTX 4090 ($0.34/hour)
Storage: 50GB
```

### 3. Upload Your Scripts
```bash
# Via Jupyter notebook interface
# Upload: scripts/, requirements.txt
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
pip install torch torchvision diffusers accelerate
```

### 5. Run Full Pipeline with GPU
```bash
# Scene generation (still uses API)
# Image generation (now uses local GPU)
# Audio + video (now GPU accelerated)

python generate_video.py \
  --text story.txt \
  --use-local-gpu \
  --output output/test_gpu
```

### 6. Monitor Cost
RunPod dashboard shows real-time cost

**Expected for 1 episode:**
- Time: ~10 minutes
- Cost: $0.34 × (10/60) = $0.06

**Compare to API cost:** $10.71 - $0.06 = **$10.65 saved per episode!**

---

## Summary

### Fastest Setup (Today)
✅ **Use RunPod** - $0.34/hour, running in 5 minutes

### Best Long-Term (Heavy Use)
✅ **Build PC with RTX 4060 Ti 16GB** - $1,200, pays for itself in 6-12 months

### Best Hybrid
✅ **Keep APIs for generation** + **GPU for video/audio** - Best of both worlds

### Don't Do
❌ eGPU for Mac
❌ Buy GPU if processing < 5 episodes/week
❌ Use cloud GPU for long-running (24/7) jobs

---

## Next Steps

1. **Try RunPod for 1 week** ($25-50)
2. **Measure actual speed improvement**
3. **Calculate your ROI** based on episodes/week
4. **Decide:** Cloud vs Local GPU

Want me to help set up RunPod or local GPU acceleration?
