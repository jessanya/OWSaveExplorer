#!/usr/bin/env python

import logging

from OWSaveExplorer.app import OWSaveExplorerApp

#logging.basicConfig(
#    level="DEBUG",
#    format="%(asctime)s %(name)-8s %(levelname)-6s %(message)s",
#    filename="out.log",
#    filemode="w",
#)
logger = logging.getLogger("main")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Save File to edit")
    parser.add_argument(
        "-o", "--outfile", help="File to save edits to. Leave blank to edit in-place"
    )
    args = parser.parse_args()
    app = OWSaveExplorerApp({"file": args.file, "outfile": args.outfile})
    app.run()
