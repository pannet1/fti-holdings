import sys

import pytest

from .Handler import HelloWorldHandler


class TestHelloWorldHandler:

    def test_execute_prints_hello_world(self, capsys):
        handler = HelloWorldHandler()
        result = handler.execute()
        captured = capsys.readouterr()
        assert captured.out == "hello world\n"
        assert result["status"] == "ok"
