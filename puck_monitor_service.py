from typing import Dict, Any
from utils.devices import create_dewar_class
import argparse
import yaml
from pathlib import Path
from import_pucks import start_app


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [FILE]...",
        description="Start the puck monitor service",
    )

    parser.add_argument(
        "-v", "--version", action="version", version=f"{parser.prog} version 1.0.0"
    )
    parser.add_argument("config", help="yaml file containing the configuration")
    return parser


def parse_config(config_path: Path):
    with config_path.open("r") as f:
        config = yaml.safe_load(f)
    if not all(key in config for key in ["suffix", "sector", "pucks"]):
        return None
    return config


def main():
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

    print("Starting script")
    config: "dict[str, Any] | None" = parse_config(config_path)
    if not config:
        print("Error parsing config file, missing suffix, sector or pucks")
        exit()
    try:
        dewar = create_dewar_class(config)
    except:
        print("Exception: {}")

    while True:
        pass


if __name__ == "__main__":
    main()
