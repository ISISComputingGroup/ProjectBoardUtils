#!/bin/sh
export PYTHONPATH=/home/isissupport/card

cd /home/isissupport/card

. ./venv/bin/activate

ts=`date +%Y-%m-%d`
month=`date +%m`
year=`date +%Y`
day=`date +%d`

daily_dir=/isis/www/ibex/daily/$year/$month/$day
mkdir -p ${daily_dir}

## check default ibex project board
python3 /home/isissupport/card/card.py --milestone --data > summary.txt

## check release notes
python3 /home/isissupport/card/release_notes_checker.py > release_notes_check.txt

## make burndown graph
python3 /home/isissupport/card/make_fig.py

## update web files
cp -f release_notes_check.txt summary.txt tickets.csv burndown-tickets.csv burndown-points.csv burndown-points.html /isis/www/ibex
cp release_notes_check.txt summary.txt tickets.csv burndown-tickets.csv burndown-points.csv burndown-points.html ${daily_dir}
mv issue-column-${ts}.json ${daily_dir}/issue-column.json
mv issue-size-${ts}.json ${daily_dir}/issue-size.json
