"""mcdcli entry point."""
import sys

from . import __version__
from .client import MCPError
from .commands import build_parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "version", False):
        print(f"mcdcli {__version__}")
        return 0
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    try:
        return func(args) or 0
    except MCPError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
