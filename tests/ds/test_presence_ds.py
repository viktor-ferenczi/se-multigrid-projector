"""The presence packet (SE-1273): a server with MGP 1.x tells a joined client
it has the plugin a moment after the join, then again at every interval. The
test config shortens the delay to 1 s and the interval to 3 s."""

from __future__ import annotations

import compat

BENCHES = ["large"]
WORLD_SETTINGS = {"GameMode": "Creative"}
MGP_SERVER_CONFIG = compat.FAST_PRESENCE


def test_client_switches_to_full_mode_soon_after_joining(game):
    joined = compat.client_lines("Comms: MultiplayerClient")
    assert joined, "the client's Comms did not start"
    full = compat.wait_until(lambda: compat.client_lines(compat.FULL_MODE), 30)
    assert len(full) == 1
    delay = (full[0][0] - joined[0][0]).total_seconds()
    # The server waits 1 s after the player shows up; the client loads a while
    # before that
    assert 0 < delay < 30, delay


def test_presence_repeats_at_the_interval(game):
    def four():
        packets = compat.client_lines(compat.PRESENCE)
        return packets if len(packets) >= 4 else None

    packets = compat.wait_until(four, 30)
    assert packets, compat.client_lines(compat.PRESENCE)
    gaps = [(b[0] - a[0]).total_seconds() for a, b in zip(packets, packets[1:])]
    # The server checks its schedule once a second
    assert all(2.0 <= g <= 5.0 for g in gaps), gaps


def test_nothing_was_ignored(game):
    assert not compat.client_lines(compat.IGNORED)
