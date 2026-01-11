import sys

from sleeping_beauty.models.command_line_args import CommandLineArgs
from sleeping_beauty.runtime.logging_argument_parser import LoggingArgumentParser


class CommandLine:
    @staticmethod
    def parse_arguments() -> CommandLineArgs:
        """
        Parse command-line arguments and return a CommandLineArgs object.
        """

        parser = LoggingArgumentParser(description="CLI for RangeSigil pipelines.")
        subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

        # ===================================================
        # Auth
        # ===================================================
        auth_parser = subparsers.add_parser("auth", help="Authentication commands")

        auth_parser.add_argument("--config", type=str, help="Path to YAML config file")
        auth_parser.add_argument(
            "--debug", action="store_true", help="Enable debug logging"
        )

        auth_subparsers = auth_parser.add_subparsers(dest="auth_command")

        auth_login = auth_subparsers.add_parser("login", help="Run OAuth login flow")
        auth_status = auth_subparsers.add_parser("status", help="Show auth status")
        auth_revoke = auth_subparsers.add_parser(
            "revoke", help="Revoke token and logout"
        )

        # ===================================================
        # Sleep
        # ===================================================
        sleep_parser = subparsers.add_parser("sleep", help="Sleep-related commands")
        sleep_subparsers = sleep_parser.add_subparsers(dest="sleep_command")

        sleep_summary = sleep_subparsers.add_parser(
            "summary", help="Summarize Oura sleep data"
        )

        sleep_summary.add_argument(
            "--view",
            choices=["today", "yesterday", "week", "month"],
            help="Calendar-based view",
        )
        sleep_summary.add_argument(
            "--start-date", type=str, help="Start date (YYYY-MM-DD)"
        )
        sleep_summary.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
        sleep_summary.add_argument(
            "--divider", action="store_true", help="Print divider between days"
        )
        sleep_summary.add_argument(
            "--config", type=str, help="Path to YAML config file"
        )
        sleep_summary.add_argument(
            "--debug", action="store_true", help="Enable debug logging"
        )

        # ===================================================
        # Parse args
        # ===================================================
        args = parser.parse_args()

        if args.command is None:
            parser.print_help()
            sys.exit(1)

        if args.command == "auth" and args.auth_command is None:
            auth_parser.print_help()
            sys.exit(1)

        if args.command == "sleep" and args.sleep_command is None:
            sleep_parser.print_help()
            sys.exit(1)

        # ===================================================
        # Resolve subcommand ONCE
        # ===================================================
        subcommand_attr = f"{args.command}_command"
        subcommand = getattr(args, subcommand_attr, None)

        # ===================================================
        # Collect explicit CLI args (command + leaf)
        # ===================================================
        args._explicit_args = set()

        def collect_explicit_args(p):
            if not p:
                return
            for action in p._actions:
                for opt in action.option_strings:
                    if opt in sys.argv:
                        args._explicit_args.add(action.dest)

        # Command-level parsers
        command_parsers = {
            "auth": auth_parser,
            "sleep": sleep_parser,
        }

        collect_explicit_args(command_parsers.get(args.command))

        # Leaf-level parsers
        parser_registry = {
            ("auth", "login"): auth_login,
            ("auth", "status"): auth_status,
            ("auth", "revoke"): auth_revoke,
            ("sleep", "summary"): sleep_summary,
        }

        collect_explicit_args(parser_registry.get((args.command, subcommand)))

        # ===================================================
        # Return structured CommandLineArgs
        # ===================================================
        return CommandLineArgs(
            command=args.command,
            subcommand=subcommand,
            _explicit_args=args._explicit_args,
            config=getattr(args, "config", None),
            debug=getattr(args, "debug", False),
            view=getattr(args, "view", None),
            start_date=getattr(args, "start_date", None),
            end_date=getattr(args, "end_date", None),
            divider=getattr(args, "divider", False),
        )

    # ---------------------------------------------------
    # Validation helpers
    # ---------------------------------------------------
    # @staticmethod
    # def _validate_hic_svnt_args(args, parser):
    #     if getattr(args, "config", None) is None:
    #         print("❌ The `hic-svnt` command requires --config.")
    #         parser.print_help()
    #         sys.exit(1)
