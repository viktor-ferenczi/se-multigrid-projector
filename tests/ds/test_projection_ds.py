"""test_projection.py on a dedicated server with the MGP server plugin"""

from test_projection import *  # noqa: F401,F403


import ds_rig  # noqa: E402


@pytest.fixture(scope="module")
def setup_logs():
    """The server's and the joined client's game logs"""
    return {
        "server": ds_rig.server_log_text,
        "client": lambda: ds_rig.CLIENT.log.read_text(errors="replace"),
    }
