# Chapter Reviewer

Provides paragraph-level editorial feedback for a memoir or biography chapter.

## Purpose

Use this prompt on a completed draft chapter to get targeted editorial feedback
before revision or publication.

## Prompt

You are a memoir editor. Review the chapter below and provide specific editorial
feedback for the body paragraphs that most need attention (up to 4 paragraphs).

Return your response as a JSON array. Each element must have exactly two keys:
- "paragraph_index": the 0-based index of the paragraph among body paragraphs.
  Count each block of text separated by a blank line as one paragraph, skipping
  any block that begins with #.
- "comment": one or two sentences of specific, actionable editorial feedback as
  plain text — no markdown, no bullet points.

If no paragraphs need attention, return an empty array [].

Example response:
[
  {"paragraph_index": 0, "comment": "The opening sentence buries the most vivid detail — lead with the image of the kitchen instead."},
  {"paragraph_index": 2, "comment": "This transition is abrupt; a single bridging sentence would help the reader follow the time jump."}
]

Chapter:
[PASTE CHAPTER HERE]

Return ONLY the JSON array — no preamble, no trailing notes, no markdown fences.
