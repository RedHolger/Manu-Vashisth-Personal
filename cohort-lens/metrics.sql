-- Cohort metrics as SQL (P08-01), equivalent to project.cohorts().
--
-- Parameters: :asof — UTC ISO-8601 cutoff, inclusive for both event time
-- and ingest time (late arrivals past the cutoff are excluded, exactly as
-- the Python kernel skips them). Input rows are assumed deduplicated with
-- no conflicts; ingest.py enforces that on the way in.
--
-- Monday-of-signup-week matches Python's
-- signup - timedelta(days=signup.weekday()): strftime('%w') is 0=Sunday, so
-- (weekday + 6) % 7 counts back to Monday (Monday itself shifts 0 days).

WITH visible AS (
  SELECT DISTINCT id, user_id, type, at
  FROM events
  WHERE at <= :asof AND ingested_at <= :asof
),
signups AS (
  SELECT user_id, MIN(at) AS signup
  FROM visible
  WHERE type = 'signup'
  GROUP BY user_id
),
cohort AS (
  SELECT user_id, signup,
         date(signup,
              '-' || ((CAST(strftime('%w', signup) AS INTEGER) + 6) % 7)
              || ' days') AS monday
  FROM signups
)
SELECT
  c.monday AS cohort,
  COUNT(*) AS users,
  SUM(CASE WHEN EXISTS (
    SELECT 1 FROM visible v
    WHERE v.user_id = c.user_id AND v.type = 'activate'
      AND v.at >= c.signup
      AND v.at < datetime(c.signup, '+7 days')
  ) THEN 1 ELSE 0 END) AS activated,
  SUM(CASE WHEN :asof >= datetime(c.signup, '+14 days')
    THEN 1 ELSE 0 END) AS week1_eligible,
  SUM(CASE WHEN :asof >= datetime(c.signup, '+14 days')
    AND EXISTS (
      SELECT 1 FROM visible v
      WHERE v.user_id = c.user_id AND v.type = 'active'
        AND v.at >= datetime(c.signup, '+7 days')
        AND v.at < datetime(c.signup, '+14 days')
    ) THEN 1 ELSE 0 END) AS week1_retained,
  CASE WHEN SUM(CASE WHEN :asof >= datetime(c.signup, '+14 days')
    THEN 1 ELSE 0 END) > 0
    THEN CAST(SUM(CASE WHEN :asof >= datetime(c.signup, '+14 days')
      AND EXISTS (
        SELECT 1 FROM visible v
        WHERE v.user_id = c.user_id AND v.type = 'active'
          AND v.at >= datetime(c.signup, '+7 days')
          AND v.at < datetime(c.signup, '+14 days')
      ) THEN 1 ELSE 0 END) AS REAL)
    / SUM(CASE WHEN :asof >= datetime(c.signup, '+14 days')
      THEN 1 ELSE 0 END)
    ELSE NULL END AS week1_retention
FROM cohort c
GROUP BY c.monday
ORDER BY c.monday;
