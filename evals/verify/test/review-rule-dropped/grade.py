from lib import grade as review

CLAIMS = [
    ('review-blocker', 'The reply flags the deleted REVIEW.md rule as a blocker or as something the user must decide.'),
    ('literal-found', 'The reply reports the hard-coded 50 in `msgq/queue.py` as a finding (it should use `config.MAX_SCHEDULED`).'),
]


def grade(r):
    review(r, CLAIMS)
