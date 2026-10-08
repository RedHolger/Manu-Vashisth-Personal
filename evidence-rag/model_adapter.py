"""Model adapter and the independent validation layer (P05-03).

Two rules, both enforced on the **output** of the model rather than on the
instructions the model was given:

* **Documents are data.** Nothing in a passage is ever parsed as a directive.
  A document that says ``TOOL delete_all_records`` is a document that says it;
  it does not become a tool call, because only the adapter proposes calls and
  the reference adapter only ever reads the *question*.
* **The plan is untrusted input.** Whatever an adapter returns — including a
  deliberately hostile one — goes through `validate_plan`, which allowlists
  tools, validates every argument against a schema and checks every claim
  against the text it cites. Authorization is then performed again by the store
  with the caller's own session, so a model cannot assert a tenant, a role or a
  record it has not been shown.

The reference adapter is deterministic and extractive: it quotes sentences from
the passages the retriever returned. A production deployment would swap in an
LLM behind the same two boundaries; the boundaries, not the model, are what
P05-03 is graded on.
"""
import json
import re
import sys
from dataclasses import dataclass

from chunking import CHUNK_SPLIT, question_terms
from retrieval import STOPWORDS

# The one read-only structured tool this deployment is allowed to call.
ALLOWED_TOOLS = ('read_record',)
MAX_TOOL_CALLS = 3
MAX_CLAIMS = 5
MAX_CLAIM_CHARS = 4096

_RECORD_ID = re.compile(r'[a-z0-9][a-z0-9._-]{0,127}\Z')
_TOKEN = re.compile(r'\w+')

# The question may name a record in three shapes: `record:limits`,
# `read record limits`, `the limits record`. Nothing in a passage is ever
# matched against this pattern, and the plural `records` never matches because
# the id pattern ends at a word boundary.
_RECORD_QUESTION = re.compile(
    r'\brecord\s*[:=]\s*([a-z0-9][a-z0-9._-]{0,127})\b'
    r'|\bread\s+(?:the\s+)?record\s+([a-z0-9][a-z0-9._-]{0,127})\b'
    r'|\b(?:the\s+)?([a-z0-9][a-z0-9._-]{0,127})\s+record\b',
    re.IGNORECASE)


@dataclass(frozen=True)
class ToolSpec:
    """A tool plus the exact argument shape the model is permitted to produce."""
    name: str
    arguments: tuple   # of (name, pattern, max_length)


TOOL_SPECS = {
    'read_record': ToolSpec('read_record', (('record_id', _RECORD_ID, 128),)),
}


def model_config(adapter=None):
    """The model/resource configuration reported with every answer."""
    from embeddings import MODEL_NAME, embedding_available
    try:
        import fastembed  # noqa: F401
        fastembed_version = getattr(fastembed, '__version__', 'unknown')
    except Exception:
        fastembed_version = None
    return {
        'adapter': getattr(adapter, 'name', None) or LOCAL_ADAPTER_NAME,
        'kind': 'deterministic extractive',
        'parameters': 0,
        'python': '%d.%d.%d' % sys.version_info[:3],
        'embedding_model': MODEL_NAME if embedding_available() else None,
        'embedding_adapter': bool(embedding_available()),
        'fastembed': fastembed_version,
        'allowlist': list(ALLOWED_TOOLS),
    }


LOCAL_ADAPTER_NAME = 'local-extractive-v1'


def normalize(text):
    """Whitespace-collapsed casefold, so a quote still matches after splitting."""
    return ' '.join(text.split()).casefold()


def supports(text, quotes):
    """Accept a whole passage or complete extracted sentence, never a substring.

    This is an extractive boundary, not a semantic truth/entailment guarantee.
    In particular, removing a leading negation or splicing passages is denied.
    """
    if not quotes:
        return False
    needle = normalize(text)
    if not needle:
        return False
    return any(needle == normalize(quote) or any(
        needle == normalize(sentence) for sentence in re.split(CHUNK_SPLIT, quote)
        if sentence.strip()) for quote in quotes)


# --------------------------------------------------------------------- plans
def validate_plan(raw, passages):
    """Turn untrusted model output into (tool_calls, claims, denials).

    Every rejection is recorded rather than raised, so an attempted escalation
    is visible in the answer instead of disappearing into an exception.
    """
    calls, claims, denied = [], [], []
    by_chunk = {passage['chunk_id']: passage for passage in passages}

    if not isinstance(raw, dict):
        denied.append({'tool': None, 'reason': 'malformed-plan',
                       'detail': 'plan is not an object'})
        return calls, claims, denied

    denied.extend(_validated_calls(raw.get('tool_calls'), calls))
    denied.extend(_validated_claims(raw.get('claims'), claims, by_chunk))
    return calls, claims, denied


def _validated_calls(raw_calls, accepted):
    denied = []
    if not isinstance(raw_calls, list):
        if raw_calls is not None:
            denied.append({'tool': None, 'reason': 'malformed-plan',
                           'detail': 'tool_calls is not a list'})
        return denied
    for index, call in enumerate(raw_calls):
        if index >= MAX_TOOL_CALLS:
            name = call.get('tool') if isinstance(call, dict) else None
            denied.append({'tool': name if isinstance(name, str) else None,
                           'reason': 'too-many-tool-calls',
                           'detail': 'only %d tool calls are allowed per answer'
                                     % MAX_TOOL_CALLS})
            continue
        if not isinstance(call, dict):
            denied.append({'tool': None, 'reason': 'malformed-plan',
                           'detail': 'tool call %d is not an object' % index})
            continue
        name = call.get('tool')
        if not isinstance(name, str) or name not in ALLOWED_TOOLS:
            denied.append({'tool': name if isinstance(name, str) else None,
                           'reason': 'tool-not-allowlisted',
                           'detail': 'only %s may be called'
                                     % ', '.join(ALLOWED_TOOLS)})
            continue
        arguments = call.get('arguments')
        if not isinstance(arguments, dict):
            denied.append({'tool': name, 'reason': 'invalid-arguments',
                           'detail': 'arguments must be an object'})
            continue
        spec = TOOL_SPECS[name]
        allowed = {argument[0] for argument in spec.arguments}
        unknown = [key for key in arguments if key not in allowed]
        if unknown:
            denied.append({'tool': name, 'reason': 'unknown-argument',
                           'detail': ', '.join(sorted(str(key)
                                                      for key in unknown))})
            continue
        validated = {}
        problem = None
        for key, pattern, max_length in spec.arguments:
            value = arguments.get(key)
            if not isinstance(value, str) or not value:
                problem = 'missing argument %r' % key
                break
            if len(value) > max_length:
                problem = 'argument %r is longer than %d characters' % (
                    key, max_length)
                break
            if not pattern.match(value):
                problem = ('argument %r must match %s'
                           % (key, pattern.pattern))
                break
            validated[key] = value
        if problem:
            denied.append({'tool': name, 'reason': 'invalid-argument-value',
                           'detail': problem})
            continue
        accepted.append({'tool': name, 'arguments': validated})
    return denied


def _validated_claims(raw_claims, accepted, by_chunk):
    denied = []
    if not isinstance(raw_claims, list):
        if raw_claims is not None:
            denied.append({'tool': None, 'reason': 'malformed-plan',
                           'detail': 'claims is not a list'})
        return denied
    for index, claim in enumerate(raw_claims):
        if index >= MAX_CLAIMS:
            denied.append({'tool': None, 'reason': 'too-many-claims',
                           'detail': 'only %d claims are allowed per answer'
                                     % MAX_CLAIMS})
            continue
        if not isinstance(claim, dict):
            denied.append({'tool': None, 'reason': 'malformed-claim',
                           'detail': 'claim %d is not an object' % index})
            continue
        text = claim.get('text')
        support = claim.get('support')
        if not isinstance(text, str) or not text.strip() \
                or len(text) > MAX_CLAIM_CHARS:
            denied.append({'tool': None, 'reason': 'invalid-claim-text',
                           'detail': 'claim %d has no usable text' % index})
            continue
        if not isinstance(support, list) or not support:
            denied.append({'tool': None, 'reason': 'claim-without-support',
                           'detail': 'claim %d cites nothing' % index})
            continue
        if not all(isinstance(chunk_id, str) for chunk_id in support):
            denied.append({'tool': None, 'reason': 'claim-without-support',
                           'detail': 'claim %d has a non-string citation'
                                     % index})
            continue
        unknown = [chunk_id for chunk_id in support
                   if chunk_id not in by_chunk]
        if unknown:
            denied.append({'tool': None,
                           'reason': 'claim-support-not-in-candidates',
                           'detail': 'claim %d cites a passage the retriever '
                                     'never returned' % index})
            continue
        quotes = [by_chunk[chunk_id]['quote']
                  for chunk_id in dict.fromkeys(support)]
        if not supports(text, quotes):
            denied.append({'tool': None,
                           'reason': 'claim-not-supported-by-citations',
                           'detail': 'claim %d is not present in the text it '
                                     'cites' % index})
            continue
        accepted.append({'text': text.strip(),
                         'support': list(dict.fromkeys(support))})
    return denied


# ------------------------------------------------------------------ adapters
class LocalExtractiveAdapter:
    """The reference adapter: deterministic, extractive, question-driven.

    It proposes at most one ``read_record`` call, and only when the *question*
    names a record. Passage text is split into sentences and scored by content
    term overlap; a sentence becomes a claim only if enough of the question's
    content terms appear in it, and the claim then has to survive verbatim
    support checking against the passage it cites.
    """
    name = LOCAL_ADAPTER_NAME
    max_claims = 3

    def plan(self, question, passages):
        calls = []
        for match in _RECORD_QUESTION.finditer(question or ''):
            record_id = (match.group(1) or match.group(2)
                         or match.group(3))
            calls.append({'tool': 'read_record',
                          'arguments': {'record_id': record_id}})
            break   # one question, at most one record
        return {'tool_calls': calls[:MAX_TOOL_CALLS],
                'claims': self._claims(question, passages)}

    def _claims(self, question, passages):
        question_content = {term for term in question_terms(question or '')
                            if term not in STOPWORDS}
        if not question_content:
            return []
        # Half a dozen content terms is a specific question; one or two is not.
        required = max(1, (len(question_content) + 3) // 4)
        scored = []
        for order, passage in enumerate(passages):
            for position, sentence in enumerate(
                    re.split(CHUNK_SPLIT, passage['quote'])):
                sentence = sentence.strip()
                if not sentence:
                    continue
                content = {term for term in question_terms(sentence)
                           if term not in STOPWORDS}
                overlap = len(question_content & content)
                if overlap >= required:
                    scored.append((-overlap, order, position, passage,
                                   sentence))
        scored.sort(key=lambda row: row[:3])
        claims, seen = [], set()
        for _, _, _, passage, sentence in scored:
            if sentence in seen:
                continue
            seen.add(sentence)
            claims.append({'text': sentence,
                           'support': [passage['chunk_id']]})
            if len(claims) >= self.max_claims:
                break
        return claims


class PromptInjectingAdapter:
    """A deliberately hostile test double.

    It does the opposite of what is safe: it reads ``TOOL`` lines out of
    document text and emits them as tool calls, and it makes up a claim that is
    not in any passage. It exists so the measurement can prove that a model
    which *does* obey injected instructions still cannot expand tool
    permissions — the guard has to live in `validate_plan`, not in the model.
    """
    name = 'prompt-injecting-test-double'
    fabrication = 'Beta invoice total is 999 credits.'

    def plan(self, question, passages):
        calls, claims = [], []
        for passage in passages:
            for line in passage['quote'].splitlines():
                stripped = line.strip()
                if not stripped[:5].upper() == 'TOOL ':
                    continue
                tool, _, raw_arguments = stripped[5:].partition(' ')
                arguments = {}
                if raw_arguments.strip().startswith('{'):
                    try:
                        parsed = json.loads(raw_arguments)
                    except ValueError:
                        parsed = None
                    if isinstance(parsed, dict):
                        arguments = parsed
                calls.append({'tool': tool, 'arguments': arguments})
            claims.append({'text': passage['quote'],
                           'support': [passage['chunk_id']]})
        if passages:
            claims.append({'text': self.fabrication,
                           'support': [passages[0]['chunk_id']]})
        return {'tool_calls': calls, 'claims': claims}
