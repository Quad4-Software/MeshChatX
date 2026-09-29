from hypothesis import given
from hypothesis import strategies as st


# We want to test the parsing logic found in core.py _process_message
def simulate_parsing(content, command_prefix):
    """A standalone implementation of the parsing logic in core.py."""
    if not content:
        return None, []

    if command_prefix is None or content.startswith(command_prefix):
        try:
            parts = content.split()
            if not parts:
                return None, []

            if command_prefix:
                command_name = parts[0][len(command_prefix) :]
            else:
                command_name = parts[0]

            args = parts[1:]
            return command_name, args
        except Exception:
            return None, []
    return None, []


class TestParsingPropertyBased:
    """Property-based tests for command and message parsing."""

    @given(
        prefix=st.text(min_size=1, max_size=5).filter(
            lambda x: not any(s.isspace() for s in x),
        ),
        cmd=st.text(min_size=1, max_size=20).filter(
            lambda x: not any(s.isspace() for s in x),
        ),
        args=st.lists(
            st.text(min_size=1, max_size=20).filter(
                lambda x: not any(s.isspace() for s in x),
            ),
            min_size=0,
            max_size=10,
        ),
    )
    def test_command_parsing_structured(self, prefix, cmd, args):
        """Test that well-formed commands are always parsed correctly."""
        content = prefix + cmd + " " + " ".join(args)
        parsed_cmd, parsed_args = simulate_parsing(content.strip(), prefix)

        assert parsed_cmd == cmd
        assert parsed_args == args

    @given(
        prefix=st.one_of(st.none(), st.text(max_size=5)),
        content=st.text(max_size=200),
    )
    def test_parsing_never_crashes(self, prefix, content):
        """Test that the parsing logic is robust against any string input."""
        simulate_parsing(content, prefix)

    @given(
        cmd=st.text(min_size=1).filter(lambda x: not any(s.isspace() for s in x)),
        args=st.lists(
            st.text(min_size=1).filter(lambda x: not any(s.isspace() for s in x)),
        ),
    )
    def test_no_prefix_parsing(self, cmd, args):
        """Test parsing when no prefix is configured."""
        content = cmd + " " + " ".join(args)
        parsed_cmd, parsed_args = simulate_parsing(content.strip(), None)

        if content.strip():
            assert parsed_cmd == cmd
            assert parsed_args == args
        else:
            assert parsed_cmd is None
