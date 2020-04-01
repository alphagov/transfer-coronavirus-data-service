from cognito import sanitise_email  # , CognitoException


# Tests for sanitise_email
def test_sanitise_email():

    test1 = "anormalemail@example.gov.uk"
    assert sanitise_email(test1) == test1

    # test2 = "abad@email@example.com"
    # assert sanitise_email(test2) == CognitoException
