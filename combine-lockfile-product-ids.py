#!/usr/bin/env python

import json
import sys


from PPpackage_PPpackage import merge_lockfile_product_ids


if __name__ == "__main__":
    lockfile_path = sys.argv[1]
    products_path = sys.argv[2]

    with open(lockfile_path, "r") as lockfile_file:
        with open(products_path, "r") as products_file:
            lockfile = json.load(lockfile_file)
            products = json.load(products_file)

            output = merge_lockfile_product_ids(lockfile, products)

            json.dump(output, sys.stdout)
