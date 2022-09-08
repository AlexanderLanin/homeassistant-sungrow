#!/usr/bin/env python3

# This file is required, because I'm not able to figure out how to import
# sungrow code directly from the scripts folder.
# Or how to get beartype working within this file directly.

import asyncio

from scripts.script_dump_raw_inverter_data import main

asyncio.run(main())
