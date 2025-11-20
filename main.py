"""
constellation viewer
"""

import json
import curses

# configuration for ASCII art
height = 25
width = 80
scale = " .,:;+*#@"

with open("stars.json") as f:
    data = json.load(f)

print(data["Orion"])