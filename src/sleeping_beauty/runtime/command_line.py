import sys

from sleeping_beauty.models.command_line_args import CommandLineArgs
from sleeping_beauty.runtime.logging_argument_parser import LoggingArgumentParser


class CommandLine:
    @staticmethod
    def parse_arguments() -> CommandLineArgs:
        """
        Parse command-line arguments and return a CommandLineArgs object.

        Supports subcommands:
          - hic-svnt
        """
        parser = LoggingArgumentParser(description="CLI for RangeSigil pipelines.")
        subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

        # === Hic Svnt Dracones ===
        hic_svnt_parser = subparsers.add_parser("hic-svnt", help="Where dragons lie")
        hic_svnt_parser.add_argument(
            "--config", type=str, help="Path to YAML config file"
        )
        hic_svnt_parser.add_argument(
            "--debug", action="store_true", help="Enable debug logging"
        )

        # ---------------------------------------------------
        # Parse and validate
        # ---------------------------------------------------
        args = parser.parse_args()

        if args.command is None:
            parser.print_help()
            sys.exit(1)

        command = args.command
        subparser = {
            "hic-svnt": hic_svnt_parser,
        }.get(command)

        args._explicit_args = set()
        if subparser:
            for action in subparser._actions:
                for opt in action.option_strings:
                    if opt in sys.argv:
                        args._explicit_args.add(action.dest)

        # --- Validation ---
        if args.command == "hic-svnt":
            CommandLine._validate_hic_svnt_args(args, parser)

        # --- Return structured CommandLineArgs ---
        return CommandLineArgs(
            command=args.command,
            _explicit_args=getattr(args, "_explicit_args", set()),
            config=getattr(args, "config", None),
            debug=getattr(args, "debug", False),
        )

    # ---------------------------------------------------
    # Validation helpers
    # ---------------------------------------------------
    @staticmethod
    def _validate_hic_svnt_args(args, parser):
        if getattr(args, "config", None) is None:
            print("❌ The `hic-svnt` command requires --config.")
            parser.print_help()
            sys.exit(1)
