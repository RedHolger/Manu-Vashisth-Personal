"""Static dashboard for CohortLens (P08-03): every number traces to source.

build_dashboard() renders the segmented cohort table as dependency-free
HTML. Each row carries data-source, data-cohort and data-segment attributes
plus explicit numerator/denominator text (e.g. 1/2), the data cutoff, the
window definition and a descriptive-only disclaimer. Incomplete windows
render as n/a — never as zero — so a young cohort cannot be misread as a
failed one.
"""
import html

from segments import segment_cohorts

SOURCE = 'segments.py:segment_cohorts + segments.sql (same contract)'


def _rate(numerator, denominator):
    if denominator == 0:
        return 'n/a (incomplete window)'
    return '%d/%d = %.3f' % (numerator, denominator,
                             numerator / denominator)


def build_dashboard(events, segments, as_of, activation_window_days=7,
                    title='CohortLens dashboard'):
    """Render dashboard HTML for the given inputs."""
    result = segment_cohorts(events, as_of, segments, activation_window_days)
    table = result['cohorts']
    rows = []
    for (monday, segment) in sorted(table):
        group = table[(monday, segment)]
        rows.append(
            '<tr data-source="%s" data-cohort="%s" data-segment="%s">'
            '<td>%s</td><td>%s</td><td data-numerators="true">%d</td>'
            '<td>%s</td><td>%s</td></tr>'
            % (html.escape(SOURCE), html.escape(monday),
               html.escape(segment), html.escape(monday),
               html.escape(segment), group['users'],
               html.escape(_rate(group['activated'],
                                 group['activation_eligible'])),
               html.escape(_rate(group['week1_retained'],
                                 group['week1_eligible']))))
    body = ('\n'.join(rows) if rows else
            '<tr><td colspan="5">no cohorts (empty store)</td></tr>')
    return """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>%s</title></head>
<body>
<h1>%s</h1>
<p data-cutoff="true">Data cutoff (as_of): %s</p>
<p data-definition="true">Definition: %s; activation window %d days.</p>
<p data-disclaimer="true">Descriptive summary only; differences across
cohorts or segments are observed associations. This table is not evidence
of influence on retention.</p>
<table>
<thead><tr><th>cohort (Monday)</th><th>segment</th><th>users</th>
<th>activated (numerator/denominator = rate)</th>
<th>week-1 retained (numerator/denominator = rate)</th></tr></thead>
<tbody>
%s
</tbody>
</table>
<p data-provenance="true">Source: %s; events supplied %d, cohort rows %d.
Regenerate with dashboard.build_dashboard() and segments.segment_cohorts().</p>
</body>
</html>""" % (html.escape(title), html.escape(title),
              html.escape(result['as_of']), html.escape(result['definition']),
              result['activation_window_days'], body,
              html.escape(SOURCE), len(events), len(table))


def write_dashboard(path, events, segments, as_of,
                    activation_window_days=7, title='CohortLens dashboard'):
    """Write dashboard HTML to path; returns the HTML string."""
    text = build_dashboard(events, segments, as_of, activation_window_days,
                           title)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text + '\n')
    return text
