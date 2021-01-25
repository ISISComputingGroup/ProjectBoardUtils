#!/bin/sh
export PYTHONPATH=/home/faa59/card

. /home/faa59/card/venv/bin/activate

## check default ibex project board
python3 /home/faa59/card/card.py --milestone

## check other boards
#python3 /home/faa59/card/card.py --project="Reflectometry"
