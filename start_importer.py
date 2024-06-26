import argparse
from pathlib import Path

import yaml


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [FILE]...", description="Start the puck importer GUI"
    )

    parser.add_argument(
        "-v", "--version", action="version", version=f"{parser.prog} version 1.0.0"
    )
    parser.add_argument("config", help="yaml file containing the configuration")
    parser.add_argument(
        "--beamline",
        dest="beamline",
        help="importer for the beamline (MX or LIX), default is MX",
        default="MX",
    )
    return parser


def main() -> None:
    parser = init_argparse()
    args = parser.parse_args()
    if not args.config:
        print("Please include the yaml file containing the app configuration")
        return
    config_path = Path(args.config)
    if not config_path.exists():
        print(
            f"Configuration file {config_path} does not exist, please provide a valid config path"
        )
        return

    try:
        if args.beamline == "MX":
            from import_pucks import start_app

            start_app(config_path)
        elif args.beamline == "LIX":
            from lix_importer import start_app as start_lix_app

            start_lix_app(config_path)
        else:
            raise NotImplementedError(f"Unrecognized beamline {args.beamline}")
    except Exception as e:
        print(f"Exception occurred: {e}")


if __name__ == "__main__":
    main()
