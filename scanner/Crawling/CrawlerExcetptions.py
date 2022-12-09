class NoMoreStatesToExplore(Exception):
    """
    Thrown when all states in the DB are explored and no new ones are detected.
    """
    pass

class NoResetEndpointInDB(Exception):
    """
    Thrown when the scanning configuration has no endpoint in the DB that resets the app to the initial state.
    """
    pass

