"""
generate graph
"""

import datetime
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

## spreadsheet of sprint daily values
df = pd.read_csv("burndown-points.csv")

## target sprint storypoints saved by card.py
try:
    with open("milestone.json") as f:
        ms_dict = json.load(f)
    target_sp = ms_dict["SP"]
    due_on = datetime.datetime.fromisoformat(ms_dict["DUE"]).date()
    start_on = datetime.datetime.fromisoformat(ms_dict["START"]).date()
except:
    target_sp = 0
    due_on = datetime.datetime.now().date()
    start_on = datetime.datetime.fromisoformat("1970-01-01").date()

## sprint length and number of days so far
## will cange to calculate using spriunt end date on milestone
ntot = 28
start_index = 0
while datetime.date.fromisoformat(df["Date"][start_index]) < start_on:
    start_index = start_index + 1
first_day = datetime.date.fromisoformat(df["Date"][start_index])
ntot = (due_on - first_day).days + 1

## completed burndown
ncurr = len(df["Date"][start_index:])
burndown = df["Complete"].values[start_index:]
burndown = np.full((ncurr), target_sp) - burndown
last_val = burndown[ncurr - 1]
burndown = np.append(burndown, np.full((ntot - ncurr), last_val))

## review + completed burndown
rev = df["Review"].values[start_index:]
last_val = rev[ncurr - 1]
rev = np.append(rev, np.full((ntot - ncurr), last_val))
burndown_rev = burndown - rev

## date axis
last_day = datetime.date.fromisoformat(df["Date"][start_index + ncurr - 1])
dates = df["Date"][start_index:]
for i in range(1, ntot - ncurr + 1):
    dates = np.append(dates, [(last_day + datetime.timedelta(days=i)).isoformat()])

## ideal burndown axis
if target_sp > 0:
    initial = target_sp
else:
    initial = df["Points Sum"][start_index]
rate = initial / (ntot - 1.0)
ideal = []
for i in range(ntot):
    ideal.append(initial - i * rate)

## create graph
fig = go.Figure(
    go.Scatter(x=dates, y=burndown, name="Completed", line_color="red", mode="lines+markers"),
    layout_yaxis_title="Points",
)
# layout_title_text='Sprint Burndown'
fig.add_scatter(x=dates, y=ideal, name="Completed (Ideal)", line_color="green", mode="lines")
fig.add_scatter(
    x=dates,
    y=burndown_rev,
    name="Review + Completed",
    line=dict(color="blue", width=1, dash="dash"),
)
fig.update_layout(showlegend=True)
fig.write_html("burndown-points.html")
