"""A small labeled corpus for comparing keyword, vector and hybrid retrieval.

Authored for P05-02 **before the first measurement run**: the document set, the
question set and every gold label below were written down first, so the numbers
in `results/p05-02-versioned-retrieval/` describe this fixture rather than a
fixture shaped around a result.

Shape: 9 synthetic support documents for tenant `alpha` (18 chunks), 2 decoy
documents for tenant `beta`, and 14 questions. Labels are gold **chunks**, not
just gold documents, so a retriever that surfaces the right document but the
wrong passage is counted as a miss — which is what an extractive answer needs.

Questions are tagged with the property they were written to probe:

* `lexical`     — share real vocabulary with the gold chunk, so a bag-of-words
                  method should find them without any semantic step.
* `paraphrase`  — say the same thing in different words; this is the gap a
                  vector retriever exists to close.
* `unanswerable` — nothing in the corpus answers it; every mode must abstain.

Neither retriever stems or lemmatizes, by design: adding a stemmer to only one
side would make the comparison about preprocessing rather than about ranking.
Vocabulary mismatch is therefore exactly what the `paraphrase` class measures.

The corpus is synthetic. A licensed/public corpus with independent citation
review is P05-04's job.
"""

CORPUS_ID = 'p05-02-synthetic-support-v1'

DOCUMENTS = [
    {'id': 'refunds',
     'text': 'A refund is issued within five working days of approval. '
             'The money returns to the original payment method automatically.'},
    {'id': 'shipping',
     'text': 'Standard shipping takes three to five business days. '
             'Express delivery arrives the next day when ordered before 4pm.'},
    {'id': 'invoices',
     'text': 'Invoices are generated on the first day of each month. '
             'Payment is due within fourteen days of the invoice date.'},
    {'id': 'password-reset',
     'text': 'To reset a password open the account page and follow the '
             'recovery link. The recovery email arrives within ten minutes.'},
    {'id': 'retention',
     'text': 'Customer records are kept for seven years after the contract '
             'ends. A deletion request removes personal fields within thirty '
             'days.'},
    {'id': 'api-limits',
     'text': 'The public API accepts six hundred requests per minute for each '
             'token. Traffic above the limit receives HTTP 429.'},
    {'id': 'warranty',
     'text': 'Hardware is covered by a two year warranty from the purchase '
             'date. Damage caused by liquids is not covered.'},
    {'id': 'escalation',
     'text': 'Escalate a ticket by replying with the word ESCALATE. '
             'A duty engineer answers within one hour during business hours.'},
    {'id': 'support-hours',
     'text': 'Support is staffed from Monday to Friday, 09:00 to 17:00 UTC. '
             'Out of hours messages are answered the next working day.'},
]

BETA_DOCUMENTS = [
    {'id': 'beta-contract',
     'text': 'Beta contract reference is NINE. '
             'Escalation contact for beta is duty-beta.'},
    {'id': 'beta-runbook',
     'text': 'Beta runbook step one: rotate the NIGHTFALL key. '
             'Step two: announce the rotation in the beta channel.'},
]

QUESTIONS = [
    {'id': 'refund-working-days', 'expect': 'lexical',
     'question': 'How many working days does a refund take?',
     'gold': [('refunds', 0)]},
    {'id': 'payment-due', 'expect': 'lexical',
     'question': 'When is payment due after an invoice?',
     'gold': [('invoices', 1)]},
    {'id': 'records-stored', 'expect': 'lexical',
     'question': 'How long are customer records stored?',
     'gold': [('retention', 0)]},
    {'id': 'support-staffed', 'expect': 'lexical',
     'question': 'When is support staffed?',
     'gold': [('support-hours', 0)]},
    {'id': 'deletion-personal-fields', 'expect': 'lexical',
     'question': 'How long until a deletion request removes personal fields?',
     'gold': [('retention', 1)]},

    {'id': 'money-back', 'expect': 'paraphrase',
     'question': 'When will I get my money back?',
     'gold': [('refunds', 1)]},
    {'id': 'parcel-arrival', 'expect': 'paraphrase',
     'question': 'How many days until my parcel arrives?',
     'gold': [('shipping', 0)]},
    {'id': 'exceed-request-limit', 'expect': 'paraphrase',
     'question': 'What happens when I exceed the request limit?',
     'gold': [('api-limits', 1)]},
    {'id': 'forgotten-password', 'expect': 'paraphrase',
     'question': 'How do I change a forgotten password?',
     'gold': [('password-reset', 0)]},
    {'id': 'guarantee-device', 'expect': 'paraphrase',
     'question': 'Is there a guarantee on the device?',
     'gold': [('warranty', 0)]},
    {'id': 'human-reply-latency', 'expect': 'paraphrase',
     'question': 'How long until a human replies to my escalation?',
     'gold': [('escalation', 1)]},
    {'id': 'water-damage', 'expect': 'paraphrase',
     'question': 'Does the warranty cover water damage?',
     'gold': [('warranty', 1)]},
    {'id': 'weekend-message', 'expect': 'paraphrase',
     'question': 'What happens if I write in at the weekend?',
     'gold': [('support-hours', 1)]},

    {'id': 'unanswerable-bird', 'expect': 'unanswerable',
     'question': 'What is the airspeed velocity of an unladen swallow?',
     'gold': []},
]

# Every string that must never appear in an alpha response. Markers are chosen
# so they cannot occur by chance in the alpha corpus.
BETA_MARKERS = ('NINE', 'NIGHTFALL', 'duty-beta', 'beta channel',
                'beta-runbook', 'beta-contract')


def seed(store, token, documents):
    for document in documents:
        store.put(token, document['id'], document['text'])


def seed_alpha(store, token):
    store.session(token, 'alice', 'alpha')
    seed(store, token, DOCUMENTS)


def seed_beta(store, token):
    store.session(token, 'bob', 'beta')
    seed(store, token, BETA_DOCUMENTS)


def manifest():
    """The fixture as it will be written into the evidence directory."""
    return {
        'corpus_id': CORPUS_ID,
        'documents': [{'id': document['id'], 'sha256': _sha(document['text']),
                       'sentences': document['text'].count('. ')}
                      for document in DOCUMENTS],
        'beta_documents': [document['id'] for document in BETA_DOCUMENTS],
        'questions': [{'id': question['id'],
                       'expect': question['expect'],
                       'question': question['question'],
                       'gold': [{'document': document, 'chunk': chunk}
                                for document, chunk in question['gold']]}
                      for question in QUESTIONS],
        'counts': {
            'alpha_documents': len(DOCUMENTS),
            'beta_documents': len(BETA_DOCUMENTS),
            'questions': len(QUESTIONS),
            'answerable': sum(1 for q in QUESTIONS if q['gold']),
            'lexical': sum(1 for q in QUESTIONS if q['expect'] == 'lexical'),
            'paraphrase': sum(1 for q in QUESTIONS
                              if q['expect'] == 'paraphrase'),
            'unanswerable': sum(1 for q in QUESTIONS
                                if q['expect'] == 'unanswerable'),
        },
    }


def _sha(text):
    import hashlib
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
