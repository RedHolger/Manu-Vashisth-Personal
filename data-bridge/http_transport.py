"""HTTP transport: request timeout, retry cap and Retry-After handling.

Transient failures (429/500/502/503/504, timeouts, connection resets) are
retried up to ``max_retries`` times against the *same* URL, so a failed attempt
can never advance a cursor.  When the cap is exhausted the transport raises the
reference ``TransientError`` and the importer checkpoint is left untouched.
Anything else is a permanent failure and raises ``PermanentError`` on the first
attempt.
"""
import calendar
import email.utils
import http.client
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from project import TransientError

TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})


class PermanentError(Exception):
    """Non-retryable failure; the page must fail explicitly, never silently."""


class Response:
    def __init__(self, status, headers, body, attempts=1):
        self.status = status
        self.headers = {str(k).lower(): str(v) for k, v in dict(headers).items()}
        self.body = body
        self.attempts = attempts


def retry_after_seconds(value, now=None):
    """Parse a Retry-After header: delta-seconds or an HTTP-date."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(text)
        if when is None:
            return None
        epoch = calendar.timegm(when.utctimetuple())
    except (TypeError, ValueError, OverflowError):
        return None
    reference = time.time() if now is None else now
    return max(0.0, epoch - reference)


class HttpClient:
    def __init__(self, base_url, timeout=1.0, max_retries=3, backoff_base=0.05,
                 max_retry_after=5.0, sleep=time.sleep):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.max_retry_after = max_retry_after
        self.sleep = sleep

    def url_for(self, path, params=None):
        url = self.base_url + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        return url

    def get(self, path, params=None):
        url = self.url_for(path, params)
        attempt = 0
        while True:
            attempt += 1
            try:
                with urllib.request.urlopen(url, timeout=self.timeout) as handle:
                    response = Response(handle.status, handle.headers, handle.read())
            except urllib.error.HTTPError as err:
                try:
                    body = err.read()
                finally:
                    err.close()
                response = Response(err.code, err.headers, body)
            except (urllib.error.URLError, TimeoutError, socket.timeout,
                    ConnectionError, http.client.HTTPException) as err:
                if attempt > self.max_retries:
                    raise TransientError(
                        'request to %s failed after %d attempts: %s'
                        % (url, attempt, err))
                self.sleep(self._backoff(attempt))
                continue

            if 200 <= response.status < 300:
                response.attempts = attempt
                return response

            if response.status in TRANSIENT_STATUSES:
                if attempt > self.max_retries:
                    raise TransientError(
                        'upstream %d from %s after %d attempts'
                        % (response.status, url, attempt))
                self.sleep(self._delay(response, attempt))
                continue

            raise PermanentError(
                'permanent upstream response HTTP %d from %s: %r'
                % (response.status, url, response.body[:200]))

    def _backoff(self, attempt):
        return min(self.backoff_base * (2 ** (attempt - 1)), self.max_retry_after)

    def _delay(self, response, attempt):
        if response.status == 429:
            delay = retry_after_seconds(response.headers.get('retry-after'))
            if delay is not None:
                return min(delay, self.max_retry_after)
        return self._backoff(attempt)
