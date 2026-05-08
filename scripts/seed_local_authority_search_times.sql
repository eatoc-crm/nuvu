-- Starter LA turnaround rows (re-runnable). Refine in Supabase as needed.

INSERT INTO local_authority_search_times (local_authority_name, avg_turnaround_days, updated_by)
VALUES
  ('Eden District Council', 20, 'seed'),
  ('Carlisle City Council', 15, 'seed'),
  ('South Lakeland', 18, 'seed')
ON CONFLICT (local_authority_name)
DO UPDATE SET
  avg_turnaround_days = EXCLUDED.avg_turnaround_days,
  last_updated = now(),
  updated_by = EXCLUDED.updated_by;
