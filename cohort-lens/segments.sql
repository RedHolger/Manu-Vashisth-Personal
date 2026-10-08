-- Segmented cohorts as SQL (P08-02), equivalent to segments.segment_cohorts().
--
-- Parameters: :asof — UTC ISO-8601 cutoff (inclusive for event and ingest
-- time); :act_days — explicit activation window in days (integer 1..30,
-- validated in Python before this query runs).
--
-- Segments come from user_segments(user_id, segment); users without a row
-- fall into 'unknown' via COALESCE and are never dropped. Monday-of-signup
-- uses the same (weekday + 6) % 7 rule as metrics.sql. Denominators admit
-- only complete windows: activation needs asof >= signup + act_days,
-- week-1 needs asof >= signup + 14 days.

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
  SELECT
    s.user_id AS user_id,
    s.signup AS signup,
    date(s.signup,
         '-' || ((CAST(strftime('%w', s.signup) AS INTEGER) + 6) % 7)
         || ' days') AS monday,
    COALESCE((SELECT segment FROM user_segments
              WHERE user_segments.user_id = s.user_id), 'unknown') AS segment
  FROM signups s
)
SELECT
  c.monday AS cohort,
  c.segment AS segment,
  COUNT(*) AS users,
  SUM(CASE WHEN EXISTS (
    SELECT 1 FROM visible v
    WHERE v.user_id = c.user_id AND v.type = 'activate'
      AND v.at >= c.signup
      AND v.at < datetime(c.signup, '+' || :act_days || ' days')
  ) THEN 1 ELSE 0 END) AS activated,
  SUM(CASE WHEN :asof >= datetime(c.signup, '+' || :act_days || ' days')
    THEN 1 ELSE 0 END) AS activation_eligible,
  SUM(CASE WHEN :asof >= datetime(c.signup, '+14 days')
    THEN 1 ELSE 0 END) AS week1_eligible,
  SUM(CASE WHEN :asof >= datetime(c.signup, '+14 days')
    AND EXISTS (
      SELECT 1 FROM visible v
      WHERE v.user_id = c.user_id AND v.type = 'active'
        AND v.at >= datetime(c.signup, '+7 days')
        AND v.at < datetime(c.signup, '+14 days')
    ) THEN 1 ELSE 0 END) AS week1_retained,
  CASE WHEN SUM(CASE WHEN :asof >= datetime(c.signup,
                                          '+' || :act_days || ' days')
    THEN 1 ELSE 0 END) > 0
    THEN CAST(SUM(CASE WHEN :asof >= datetime(c.signup,
                                             '+' || :act_days || ' days')
      AND EXISTS (
        SELECT 1 FROM visible v
        WHERE v.user_id = c.user_id AND v.type = 'activate'
          AND v.at >= c.signup
          AND v.at < datetime(c.signup, '+' || :act_days || ' days')
      ) THEN 1 ELSE 0 END) AS REAL)
    / SUM(CASE WHEN :asof >= datetime(c.signup,
                                     '+' || :act_days || ' days')
      THEN 1 ELSE 0 END)
    ELSE NULL END AS activation_rate,
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
GROUP BY c.monday, c.segment
ORDER BY c.monday, c.segment;
