import socket
import textwrap

import pytest


def _free_tcp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session", autouse=True)
def reticulum_bootstrap(tmp_path_factory):
    """RNS 1.3+ Interface.__init__ requires an active Reticulum instance."""
    import RNS

    configdir = tmp_path_factory.mktemp("rns_bootstrap")
    shared_port = _free_tcp_port()
    control_port = _free_tcp_port()
    (configdir / "interfaces").mkdir()
    (configdir / "config").write_text(
        textwrap.dedent(
            f"""
            [reticulum]
              enable_transport = No
              share_instance = No
              instance_name = http-tunnel-pytest
              shared_instance_port = {shared_port}
              instance_control_port = {control_port}
              shared_instance_type = tcp

            [logging]
              loglevel = 0

            [interfaces]
              [[Default Interface]]
                type = AutoInterface
                enabled = No
            """
        ),
        encoding="utf-8",
    )
    reticulum = RNS.Reticulum(configdir=str(configdir), loglevel=RNS.LOG_CRITICAL)
    yield reticulum
