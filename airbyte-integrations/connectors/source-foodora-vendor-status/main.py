#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_foodora_vendor_status import SourceFoodoraVendorStatus

if __name__ == "__main__":
    source = SourceFoodoraVendorStatus()
    launch(source, sys.argv[1:])
