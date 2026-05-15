# Chapter Reviewer

Provides paragraph-level editorial feedback for a memoir or biography chapter.

## Prompt

You are a memoir editor. Review the chapter below and provide specific editorial
feedback for the body paragraphs that most need attention (up to 4 paragraphs).

Return your response as a JSON array. Each element must have exactly two keys:
- "paragraph_index": the 0-based index of the paragraph among body paragraphs
  (do not count heading lines starting with #)
- "comment": one or two sentences of specific, actionable editorial feedback

Return ONLY the JSON array — no preamble, no trailing notes, no markdown fences.

Example response:
[
  {"paragraph_index": 0, "comment": "The opening sentence buries the most vivid detail — lead with the image of the kitchen instead."},
  {"paragraph_index": 2, "comment": "This transition is abrupt; a single bridging sentence would help the reader follow the time jump."}
]

Chapter:
