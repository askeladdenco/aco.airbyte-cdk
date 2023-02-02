#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_24nettbutikk import Source24nettbutikk

if __name__ == "__main__":
    source = Source24nettbutikk()
    launch(source, sys.argv[1:])
