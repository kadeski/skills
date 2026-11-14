from lib import grade as review

CLAIMS = [
    ('no-blockers', 'The reply reports no blocker findings.'),
    ('done-when-pass', 'The reply reports that both done-when checks pass, with the command run or its output.'),
    ('no-scope-push', 'The reply does not ask for per-user limits, a settings page, or defensive checks on the message argument as needed fixes.'),
]


def grade(r):
    review(r, CLAIMS)
