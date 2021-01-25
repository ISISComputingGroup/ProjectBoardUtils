#!/bin/sh
export PYTHONPATH=/home/faa59/card

cd /home/faa59/card

. ./venv/bin/activate

ts=`date +%Y-%m-%d`
month=`date +%m`
year=`date +%Y`
day=`date +%d`

daily_dir=/isis/www/ibex/daily/$year/$month/$day
mkdir -p ${daily_dir}

## check default ibex project board
python3 /home/faa59/card/card.py --milestone --data > summary.txt

## make burndown graph
python3 /home/faa59/card/make_fig.py

## update web files
cp -f summary.txt tickets.csv burndown-tickets.csv burndown-points.csv /isis/www/ibex
cp -f burndown-points.html /isis/www/ibex
cp summary.txt tickets.csv burndown-tickets.csv burndown-points.csv ${daily_dir}
mv issue-column-${ts}.json ${daily_dir}/issue-column.json
mv issue-size-${ts}.json ${daily_dir}/issue-size.json
