#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_foodora_partner import SourceFoodoraPartner

if __name__ == "__main__":
    source = SourceFoodoraPartner()
    launch(source, sys.argv[1:])
