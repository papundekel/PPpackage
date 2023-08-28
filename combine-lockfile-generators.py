#!/usr/bin/env python

import json
import sys

if __name__ == "__main__":
    lockfile_path = sys.argv[1]
    generators_path = sys.argv[2]

    with open(lockfile_path, "r") as lockfile_file:
        with open(generators_path, "r") as generators_file:
            output = dict()

            lockfile = json.load(lockfile_file)
            generators = json.load(generators_file)

            json.dump({"lockfile": lockfile, "generators": generators}, sys.stdout)
