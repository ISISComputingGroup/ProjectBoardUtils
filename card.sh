#!/bin/sh
export PYTHONPATH=/home/faa59/card

## check default ibex project board
python3 /home/faa59/card/card.py --milestone

## check other boards
#python3 /home/faa59/card/card.py --project="Reflectometry"
