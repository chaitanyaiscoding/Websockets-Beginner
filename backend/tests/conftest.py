import pytest

from app.chat.manager import manager


@pytest.fixture(autouse=True)
def fresh_manager():
    """The manager is one shared object for the whole app, so connections
    from one test could leak into the next. Empty it around every test.
    autouse=True means every test gets this without asking for it."""
    manager.connections.clear()
    yield
    manager.connections.clear()
