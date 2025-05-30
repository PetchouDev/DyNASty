# argparser.py

import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Push config files to nodes")

    parser.add_argument("file", type=str, help="Configuration JSON file", nargs='?')
    parser.add_argument("--opendir", action="store_true", help="Open directory after config")
    parser.add_argument(
        "--push",
        nargs="?",
        const=True,
        default=None,
        help="Push configurations (optionally specify project name)",
        metavar="PROJECT_NAME"
    )
    parser.add_argument("--nopush", dest="push", action="store_false", help="Do not push configurations (do not show the dialog).")

    parser.set_defaults(push=True)

    return parser.parse_args()
