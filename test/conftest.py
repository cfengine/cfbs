import os
import pytest


@pytest.fixture(scope="function")
def chdir(request):
    os.chdir(os.path.join(os.path.dirname(__file__), request.param))
    yield
    os.chdir(request.config.invocation_dir)
