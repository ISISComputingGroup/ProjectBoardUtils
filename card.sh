#!/bin/sh
export PYTHONPATH=/home/faa59/card

. /home/faa59/card/venv/bin/activate

python3 -m pip install -r requirements.txt

## check default ibex project board
python3 /home/faa59/card/card.py --milestone

python3 /home/faa59/card/release_notes_checker.py

## check other boards
#python3 /home/faa59/card/card.py --project="Reflectometry"
