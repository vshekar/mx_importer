import argparse
import yaml
from pathlib import Path
from import_pucks import start_app


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [FILE]...", description="Start the puck importer GUI"
    )

    parser.add_argument(
        "-v", "--version", action="version", version=f"{parser.prog} version 1.0.0"
    )
    parser.add_argument("config", help="yaml file containing the configuration")
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
        start_app(config_path)
    except Exception as e:
        print(f'Exception occurred: {e}')


if __name__ == "__main__":
    main()
