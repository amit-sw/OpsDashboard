insert into opsdashboard.question_prompts (title, prompt, status, prompt_group)
values
  ('Topics Discussed', 'Summarize the main topics covered during the session in a 3-5 bullet list - one line each', 'active', 'common'),
  ('Action Items', 'List any action items or tasks that were assigned during the session in a 3-5 bullet list - one line each', 'active', 'common'),
  ('Suggested Next Steps', 'Provide recommendations for follow-up actions or next steps based on the discussion', 'active', 'common'),
  ('Unclear items', 'Highlight any points that were unclear for the participants in a bullet list - one line each', 'active', 'common'),
  ('Questions', 'Prepare a bullet list of five to ten questions that can be asked to the participants to check their understanding of the session', 'active', 'common')
on conflict (title, prompt_group) do update
set prompt = excluded.prompt,
    status = excluded.status,
    updated_at = now();
