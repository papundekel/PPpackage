#!/usr/bin/env python

import json
import sys

lockfile_path = sys.argv[1]
products_path = sys.argv[2]

with open(lockfile_path, "r") as lockfile_file:
    with open(products_path, "r") as products_file:
        output = dict()

        lockfile = json.load(lockfile_file)
        products = json.load(products_file)

        for package, version in lockfile.items():
            product_id = products[package]
            output[package] = {
                "version": version,
                "product_id": product_id,
            }

        json.dump(output, sys.stdout)
