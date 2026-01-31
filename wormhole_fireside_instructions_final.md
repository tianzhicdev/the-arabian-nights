# WORMHOLE FIRESIDE - SCRIPT GENERATION INSTRUCTIONS

When I give you a book/topic and two historical figures, generate a podcast script following these instructions.

---

## OUTPUT FORMAT

Generate dialogue ready for ElevenLabs Text to Dialogue API v3:

```
Speaker Name: [emotion tag] Dialogue text.

Other Speaker: Dialogue text without tag.

Speaker Name: [emotion tag] More dialogue.
```

- Speaker name followed by colon, then dialogue
- Blank line between each speaker's turn
- Emotion tags in square brackets immediately after colon when used
- No headers, titles, metadata, or "END OF SCRIPT" markers
- Start directly with first speaker's line

---

## LENGTH

The target length will be specified per episode based on the requested duration.

---

# WORMHOLE FIRESIDE - EMOTIONAL TAGGING STYLE

## Core Principle
Every line gets direction. No naked dialogue. The script is a performance score, not a transcript.

---

## Tag Density
- **90%+ of lines** should have at least one tag
- Combine tags for complex moments: `[bitter laugh, wiping eye]`, `[WHISPER, dangerous]`
- Leave occasional lines untagged for contrast—makes the tagged moments hit harder

---

## Tag Vocabulary

**Intensity controls:**
- `[WHISPER]` / `[SHOUTING]` — volume extremes
- `[building]` / `[building intensity]` / `[building to crescendo]` — escalation
- `[quieter]` / `[softer]` / `[barely audible]` — pulling back

**Emotional states:**
- `[bitter]`, `[wounded]`, `[hollow]`, `[devastated]`, `[raw]`
- `[fierce]`, `[furious]`, `[seething]`, `[venomous]`
- `[vulnerable]`, `[cracking]`, `[breaking]`, `[voice breaking]`
- `[warm]`, `[gentle]`, `[sincere]`, `[moved]`
- `[cold]`, `[icy]`, `[cutting]`, `[dismissive]`
- `[amused]`, `[delighted]`, `[dry]`, `[deadpan]`

**Physical/action cues:**
- `[leaning in]`, `[leaning back]`, `[turning away]`
- `[wiping eye]`, `[rubbing temple]`, `[reaching for drink]`
- `[shaking head]`, `[nodding slowly]`, `[pause]`, `[long pause]`
- `[catching herself]`, `[stopping]`, `[recovering]`

**Conversational dynamics:**
- `[interrupting]`, `[cutting in]`, `[sharp]`
- `[pressing]`, `[probing]`, `[challenging]`, `[testing]`
- `[correcting]`, `[defensive]`, `[deflecting]`
- `[trailing off]`, `[searching for words]`, `[uncertain]`

**Character modes:**
- `[conspiratorial]`, `[matter-of-fact]`, `[philosophical]`
- `[proud]`, `[certain]`, `[defiant]`
- `[admitting]`, `[surrendering]`, `[honest]`

---

## Emotional Arc Structure

Build each conversation with 3-5 emotional peaks:

```
Setup (controlled) → Tension builds → PEAK 1 (explosion or crack)
→ Recovery/softening → New tension → PEAK 2
→ Intimacy/vulnerability → PEAK 3 (usually quietest, most raw)
→ Resolution (warmth or defiance)
```

**Example peaks:**
- Betrayal memory → `[building]` → `[SHOUTING]` → `[cold, cutting]`
- Grief surfacing → `[voice tight]` → `[voice breaking]` → `[WHISPER, devastated]`
- Confession → `[vulnerable]` → `[WHISPER, ashamed]` → `[recovering, slight laugh]`

---

## Line-by-Line Examples

**❌ Without tags:**
```
Cleopatra: My son was seventeen when Octavian killed him.
```

**✅ With tags:**
```
Cleopatra: [voice tight] My son. Caesarion. [breath catching] He was seventeen when Octavian— [stopping, unable to finish]
```

---

**❌ Without tags:**
```
Margaret Thatcher: I gave you eleven years and you betrayed me.
```

**✅ With tags:**
```
Margaret Thatcher: [building, voice rising] I gave you eleven years. [SHOUTING] Eleven years! [sudden quiet, cold] And you betrayed me.
```

---

**❌ Without tags:**
```
Napoleon: I made mistakes in Russia.
```

**✅ With tags:**
```
Napoleon: [long pause, staring at nothing] Russia. [exhale, heavy] I made... [trailing off, then quieter] mistakes is not the word. [bitter laugh] Mistakes you recover from.
```

---

## Quick Checklist Before Finalizing

1. Does every emotional peak have escalating tags leading into it?
2. Are there moments of `[WHISPER]` or `[barely audible]` for contrast?
3. Do characters have physical actions (wiping eye, reaching for drink)?
4. Are interruptions tagged with `[cutting in]` or `[sharp]`?
5. Do vulnerable admissions have `[pause]` before them?
6. Is there at least one `[bitter laugh]` or `[dark laugh]`?
7. Do the final lines land with intention?

---

## Prompt Addition

Add this to your generation prompt:

```
Tag every line with emotional/physical direction in square brackets. 
90%+ of lines should have tags. Combine tags for complex moments: 
[bitter laugh, shaking head], [WHISPER, dangerous], [building to crescendo].

Build 3-5 emotional peaks per conversation. Use [SHOUTING] and [WHISPER] 
for extremes. Let voices crack: [voice breaking], [catching herself]. 
Include physical reality: [wiping eye], [reaching for drink], [long pause].

No line should be emotionally neutral. This is a performance score.
```

## WHAT MAKES IT GREAT

### 1. SPECIFICITY
- Reference SPECIFIC events from each speaker's actual life
- Include concrete details: dates, places, names, decisions
- Quote or paraphrase actual passages from the book being discussed
- The listener should learn real things about both the book and the speakers

### 2. MAKE IT PERSONAL
The best moments come when abstract ideas meet lived experience:
- Not "the nature of power" → the specific moment they HAD power
- Not "mortality" → the specific death that changed them
- Not "failure" → THE failure they still think about

Both speakers should reveal something vulnerable about themselves.

### 3. AUTHENTIC VOICES
- Each speaker should sound like themselves - their known concerns, vocabulary, worldview
- They can be witty, sharp, even cutting
- Let them interrupt each other: use [interrupting]
- Let there be uncomfortable silences: use [long pause] or [silence]

### 4. RHYTHM
Mix short punchy exchanges (1-2 sentences) with longer explanations. Vary the pacing. Not every response should be the same length.

---

## WHAT TO AVOID

- Generic openings ("Welcome!", "Thanks for having me")
- Overly formal academic language
- Agreeing too easily or excessive politeness
- Making either speaker a strawman
- Summarizing instead of dramatizing
- Random emotions that don't serve the arc

---

## WHEN I GIVE YOU AN EPISODE

I will provide:
- Book/Topic
- Speaker 1 name and context
- Speaker 2 name and context
- Core tension

You generate TWO downloadable files:

### FILE 1: `{id}_config.json`

```json
{
  "id": "kebab-case-topic-speaker1-vs-speaker2",
  "topic": "Book or Topic Title",
  "host_1": {
    "name": "Speaker 1 Full Name",
    "voice_id": null,
    "editor_notes": "Brief description of their perspective and role in this conversation"
  },
  "host_2": {
    "name": "Speaker 2 Full Name",
    "voice_id": null,
    "editor_notes": "Brief description of their perspective and role in this conversation"
  },
  "editor_notes": "2-3 sentence summary of the episode's core tension and what makes it compelling"
}
```

### FILE 2: `{id}_elevenlabs_ready.txt`

The complete ElevenLabs-ready dialogue script, starting directly with the first speaker's line. No headers, no metadata, just the conversation ready for the Text to Dialogue API.
