"""
Root entrypoint.

Running `python main.py` launches the CLI in interactive mode (prompts for
a feature request). For sub-commands (analyse/design with flags), invoke the
Typer app directly:

    python -m app.cli.cli design "Build an online payment system." --format markdown
    python -m app.cli.cli analyse "Build a chat application."

This file exists purely for the "python main.py" convenience entrypoint
requested in the project spec; all real logic lives in app.cli.cli.
"""

from __future__ import annotations

from app.cli.cli import cli, interactive

if __name__ == "__main__":
    # No sub-command given (`python main.py` with no args) -> go interactive.
    import sys

    if len(sys.argv) == 1:
        interactive()
    else:
        cli()
