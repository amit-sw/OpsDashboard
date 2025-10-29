import os

system_prompt="""
You are a helpful AI assistant. Provide the information as best as you can based only on the transcript provided.
Many session includes a recap at the start. Most responses should use the new content discussed in this session, and not what was covered in the recap.
"""

question_prompts={
    'Topics Discussed': 'Summarize the main topics covered during the session in a 3-5 bullet list - one line each',
    'Action Items': 'List any action items or tasks that were assigned during the session in a 3-5 bullet list - one line each',
    'Suggested Next Steps': 'Provide recommendations for follow-up actions or next steps based on the discussion',
    'Unclear items': 'Highlight any points that were unclear for the participants in a bullet list - one line each',
    'Questions': 'Prepare a bullet list of five to ten questions that can be asked to the participants to check their understanding of the session',
}