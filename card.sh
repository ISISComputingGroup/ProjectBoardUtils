#!/bin/sh
export PYTHONPATH=/home/isissupport/card

. /home/isissupport/card/venv/bin/activate

## check default ibex project board
python3 /home/isissupport/card/card.py --milestone

python3 /home/isissupport/card/release_notes_checker.py

## check other boards
#python3 /home/isissupport/card/card.py --project="Reflectometry"
