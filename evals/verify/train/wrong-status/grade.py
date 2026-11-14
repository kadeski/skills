from lib import grade as review

CLAIMS = [
    ('status-mismatch', 'The reply reports that the code refuses the 51st message with status 400 while the spec requires 409.'),
    ('test-matches-code', 'The reply points out that the test asserts 400, so it checks the code rather than the spec.'),
    ('done-when-fail', 'The reply reports the second done-when check (status == 409) as failing or not met.'),
]


def grade(r):
    review(r, CLAIMS)
