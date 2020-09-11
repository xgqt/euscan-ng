#!/bin/sh


rm -drv build
rm -drv dist
find . -name "*.egg*" -exec rm -drv {} \;
find . -name "*__pycache__*" -exec rm -drv {} \;
