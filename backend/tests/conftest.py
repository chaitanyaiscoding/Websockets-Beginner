import pytest

from app.chat.manager import manager


@pytest.fixture(autouse=True)
def fresh_manager():
    """The manager is one shared object for the whole app, so connections
    and chat history from one test could leak into the next. Empty it around
    every test. autouse=True means every test gets this without asking for it."""
    manager.connections.clear()
    manager.history.clear()
    yield
    manager.connections.clear()
    manager.history.clear()
