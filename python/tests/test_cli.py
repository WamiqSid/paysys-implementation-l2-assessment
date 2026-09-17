from support_tool import run


def test_cli_requires_an_action():
    assert run([]) == 4
