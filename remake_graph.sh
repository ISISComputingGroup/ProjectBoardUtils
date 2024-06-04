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

## make burndown graph
python3 /home/isissupport/card/make_fig.py

## update web files
cp -f tickets.csv burndown-tickets.csv burndown-points.csv burndown-points.html /isis/www/ibex
cp tickets.csv burndown-tickets.csv burndown-points.csv burndown-points.html ${daily_dir}
