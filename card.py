"""
project board scan
"""
import os
import sys
import json
import argparse
from statistics import mode
import datetime
from datetime import date
from github import Issue
from utils import get_IBEX_repo, get_project_columns, COLUMNS

parser = argparse.ArgumentParser(description='projects')
parser.add_argument('--project', dest='project', default='IBEX Project Board')
parser.add_argument('--data', action='store_true')
parser.add_argument('--milestone', action='store_true')
args = parser.parse_args()

# these are labels that apply to a column i.e. there should
# only be one such label on a ticket
WORKFLOW_LABELS = ['bucket', 'ready', 'in progress', 'review',
                   'completed', 'awaiting', 'impeded']
POINTSUM_COLUMNS = [COLUMNS.READY, COLUMNS.IN_PROGRESS, COLUMNS.REVIEW, COLUMNS.COMPLETE, COLUMNS.IMPEDED]
ZERO_POINT_LABELS = {'training', 'HLM', 'Cryomagnet', 'Friday',
                     'Datastreaming', 'standdown'}
NO_POINT_LABELS = {'support', 'duplicate', 'sub-ticket', 'wontfix'}

NUM_ERROR = 0
NUM_WARNING = 0

def print_error(*args, **kwargs):
    global NUM_ERROR
    print(*args, **kwargs)
    NUM_ERROR += 1

def print_warning(*args, **kwargs):
    global NUM_WARNING
    print(*args, **kwargs)
    NUM_WARNING += 1

# get names who are assigned to an issue
# we use login rather than name attribute as name may not be set
def get_assigned(issue):
    assigned = [x.login for x in issue.assignees]
    if issue.assignee is not None:
        assigned.append(issue.assignee.login)
    assigned = [x if x is not None else 'None' for x in assigned]
    assigned = set(assigned)
    if len(assigned) > 0:
        return ','.join(assigned)
    else:
        return 'None'

def check_labels(labels, check, issue, present):
    assigned = get_assigned(issue)
    if present:
        diff = set(check).difference(labels)
        if len(diff) > 0:
            print_error('ERROR: issue {} does NOT have the following required labels: {} (assigned: {})'
                        .format(issue.number, ','.join(diff),assigned))
    if not present:
        diff = labels.intersection(set(check))
        if len(diff) > 0:
            print_error('ERROR: issue {} has the following INVALID labels: {} (assigned: {})'.format(issue.number, ','.join(diff), assigned))

def check_column_label(labels, label, issue):
    check_labels(labels, [label], issue, True)
    no_labels = [x for x in WORKFLOW_LABELS if x != label]
    check_labels(labels, no_labels, issue, False)

def check_if_stale(issue, label_name, days_allowed, assigned):
    created = None
    for event in issue.get_events(): # or get_timeline() and '
#        if event.event == 'moved_columns_in_project' and event.column_name == 'Review':
#            print(event.created_at)
        if event.event == 'labeled' and event.label.name == label_name:
            created = event.created_at
    if created is not None:
        dur = datetime.datetime.now() - created
        if dur > datetime.timedelta(days_allowed):
            print_warning('WARNING: Issue {} has been in {} for {} days (assigned: {})'.format(issue.number, label_name, dur.days, assigned))


repo = get_IBEX_repo()
columns = get_project_columns(repo, args.project)

issue_size = {}
issue_column = {}
column_tickets = {}
column_points = {}
milestones = []

tickets_under_review = 0
points_under_review = 0
current_rework = 0
completed_rework = 0
tickets_added_during_sprint = 0
points_added_during_sprint = 0
# all columns except Bucket should have sizes on tickets
# and this size should not be 0
for column in columns:
    total = 0
    is_bucket = False
    cards = column.get_cards()
    column_tickets[column.name] = cards.totalCount
    print("** Checking column \"{}\"".format(column.name))
    if column.name not in COLUMNS.values():
        is_bucket = True
        print("INFO: unknown column \"{}\" - assuming like Bucket".format(column.name))
    if column.name == COLUMNS.BUCKET:
        is_bucket = True
    for card in cards:
        content = card.get_content()
        if isinstance(content, Issue.Issue):
            issue = content
            assigned = get_assigned(issue)
            found_size = False
            under_review = False
            size = None
            labels = set()
            in_rework = False
            added_during_sprint = False
            in_progress = False
            ready = False
            for label in issue.labels:
                labels.add(label.name)
                if label.name == "under review":
                    under_review = True
                    tickets_under_review += 1
                if label.name == "rework":
                    in_rework = True
                if label.name == "added during sprint":
                    added_during_sprint = True
                if label.name == "in progress":
                    in_progress = True
                if label.name == "ready":
                    ready = True
                if label.name.isdigit():
                    if found_size:
                        print_error("ERROR: issue {} has multiple sizes (assigned: {})".format(issue.number, assigned))
                    else:
                        size = int(label.name)
                        found_size = True
            if size is None:
                no_labels = NO_POINT_LABELS.intersection(labels)
                if len(no_labels) > 0:
                    print("INFO: no size {} issue {}".format(','.join(no_labels), issue.number))
                elif is_bucket:
                    pass
                else:
                    print_error("ERROR: no size for issue {} in {} (assigned: {})".format(issue.number, column.name, assigned))
            elif size == 0:
                zero_labels = ZERO_POINT_LABELS.intersection(labels)
                if len(zero_labels) > 0:
                    print("INFO: size 0 {} issue {}".format(','.join(zero_labels), issue.number))
                else:
                    print_error("ERROR: size 0 not allowed for issue {} (assigned: {})".format(issue.number, assigned))
            else:
                if added_during_sprint:
                    points_added_during_sprint += size
                    tickets_added_during_sprint += 1
                if under_review:
                    points_under_review += size
                total += size
            if size is not None:
                issue_size[issue.number] = size
            issue_column[issue.number] = column.name
            if is_bucket and issue.milestone is not None:
                print_error("ERROR: issue {} has milestone {} (assigned: {})".format(issue.number, issue.milestone.title, get_assigned(issue)))
            if not is_bucket and issue.milestone is None:
                print_error("ERROR: issue {} has no milestone (assigned: {})".format(issue.number, assigned))
            if not is_bucket and issue.milestone is not None and issue.milestone.state == "open":
                milestones.append(issue.milestone.title)
            if (issue.milestone is not None) and (issue.milestone.state == 'closed'):
                print_error("ERROR: issue {} has a closed milestone (assigned: {})".format(issue.number, assigned))
            if column.name not in COLUMNS.values():
                check_labels(labels, ['rework'], issue, False)
            if column.name == COLUMNS.BUCKET:
                check_column_label(labels, 'bucket', issue)
                check_labels(labels, ['rework'], issue, False)
            if column.name == COLUMNS.READY:
                check_column_label(labels, 'ready', issue)
                check_labels(labels, ['proposal'], issue, False)
                check_if_stale(issue, 'rework', 7, assigned)
            if column.name == COLUMNS.IN_PROGRESS:
                check_column_label(labels, 'in progress', issue)
                check_if_stale(issue, 'in progress', 7, assigned)
            if column.name == COLUMNS.REVIEW:
                check_column_label(labels, 'review', issue)
                check_if_stale(issue, 'review', 7, assigned)
            if column.name == COLUMNS.COMPLETE:
                check_column_label(labels, 'completed', issue)
            if column.name == COLUMNS.DONE:
                check_column_label(labels, 'completed', issue)
            if column.name == COLUMNS.IMPEDED:
                check_column_label(labels, 'impeded', issue)
            if in_rework and column.name in [COLUMNS.READY, COLUMNS.IN_PROGRESS, COLUMNS.IMPEDED]:
                current_rework += 1
            if in_rework and column.name in [COLUMNS.REVIEW, COLUMNS.COMPLETE, COLUMNS.DONE]:
                completed_rework += 1
#            if addigned != 'None' and column.name in [ 'Bucket' ]:
#                print_error("ERROR: issue {} cannot be assigned to {}".format(issue.number,assigned))
            if assigned == 'None' and column.name in [COLUMNS.IN_PROGRESS, COLUMNS.REVIEW, COLUMNS.COMPLETE]:
                print_error("ERROR: issue {} must be assigned to somebody".format(issue.number))
        else:
            pr = card.get_content()
            print_error("ERROR: pullrequest {} not allowed".format(pr.number))
    print("INFO: column \"{}\" contains {} cards and {} points\n".format(column.name, cards.totalCount, total))
    column_points[column.name] = total

print("INFO: number of issues under review = {}".format(tickets_under_review))
print("INFO: number of points under review = {}".format(points_under_review))
print("INFO: number of issues still requiring rework = {}".format(current_rework))
print("INFO: number of issues with completed rework = {}".format(completed_rework))
print("INFO: number of issues added during sprint = {}".format(tickets_added_during_sprint))
print("")

open_milestones = repo.get_milestones(state='open')
current_milestone_title = mode(milestones)
for milestone in open_milestones:
    if milestone.title == current_milestone_title:
        current_milestone = milestone
print("INFO: Current milestone is {} and has {} open and {} closed issues".format(current_milestone.title, current_milestone.open_issues, current_milestone.closed_issues))

try:
    ms_dict = json.loads(current_milestone.description.split('\n')[0])
except:
    ms_dict = {}
    ms_dict['SP'] = 0

ms_dict['DUE'] = current_milestone.due_on.isoformat()

print("INFO: Current milestone target {SP} SP and is due on {DUE}".format(**ms_dict))

with open('milestone.json', 'w') as f:
    json.dump(ms_dict, f)

for milestone in open_milestones:
    if milestone.title != current_milestone_title and milestone.title in milestones:
        milestone_issues = repo.get_issues(milestone=milestone, state='all')
        for issue in milestone_issues:
            if issue.number in issue_column:
                print_error("ERROR: issue {} ({}, assigned: {}) has old milestone {}".format(issue.number, issue.state, get_assigned(issue), milestone.title))

if args.milestone:
    milestone_issues = repo.get_issues(milestone=current_milestone, state='all')
    for issue in milestone_issues:
        if issue.number not in issue_column:
            print_error("ERROR: issue {} ({}, assigned: {}) has current milestone but is not on board".format(issue.number, issue.state, get_assigned(issue)))

print("")

points_sum = 0
for x in sorted(column_points.keys()):
    print("INFO: Points in column {} = {}".format(x, column_points[x]))
    if x in POINTSUM_COLUMNS:
        points_sum += column_points[x]

tickets_sum = 0
for x in sorted(column_tickets.keys()):
    if x in POINTSUM_COLUMNS:
        tickets_sum += column_tickets[x]

print("\nINFO: Workflow columns are: {}".format(','.join(str(x) for x in POINTSUM_COLUMNS)))
print("INFO: Total points in workflow columns = {}".format(points_sum))
print("INFO: Total tickets in workflow columns = {}".format(tickets_sum))

if NUM_ERROR > 0:
    print("\nINFO: There are {} errors\n".format(NUM_ERROR))

if NUM_WARNING > 0:
    print("\nINFO: There are {} warnings\n".format(NUM_WARNING))

if not args.data:
    sys.exit(NUM_ERROR)

ts = date.today().isoformat()

with open("issue-size-{}.json".format(ts), "w") as f:
    f.write(json.dumps(issue_size))

with open("issue-column-{}.json".format(ts), "w") as f:
    f.write(json.dumps(issue_column))

if not os.path.exists("burndown-points.csv"):
    with open("burndown-points.csv", "w") as f:
        f.write("Date,{},Points Sum,Points Added,Burndown\n".format(",".join([x for x in sorted(column_points.keys())])))

if not os.path.exists("burndown-tickets.csv"):
    with open("burndown-tickets.csv", "w") as f:
        f.write("Date,{},Under Review,Current Rework,Completed Rework,Tickets Sum,Tickets Added,Burndown\n".format(",".join([x for x in sorted(column_tickets.keys())])))

with open("burndown-points.csv", "a") as f:
    if 'Review Complete' in column_points:
        completed = column_points['Review Complete']
    else:
        completed = 0
    f.write("{},{},{},{},{}\n".format(ts, ",".join([str(column_points[x]) for x in sorted(column_points.keys())]), points_sum, points_added_during_sprint, points_sum - points_added_during_sprint-completed))

with open("burndown-tickets.csv", "a") as f:
    if 'Review Complete' in column_tickets:
        completed = column_tickets['Review Complete']
    else:
        completed = 0
    f.write("{},{},{},{},{},{},{},{}\n".format(ts, ",".join([str(column_tickets[x]) for x in sorted(column_tickets.keys())]),tickets_under_review,current_rework, completed_rework, tickets_sum, tickets_added_during_sprint, tickets_sum - tickets_added_during_sprint - completed))

with open("tickets.csv", "w") as f:
    f.write("Number,Title,Assigned,Points,Column\n")
    for issue in milestone_issues:
        if issue.number in issue_column:
            column = issue_column[issue.number]
        else:
            column = "Unknown"
        if issue.number in issue_size:
            size = issue_size[issue.number]
        else:
            size = 0
        f.write("{},\"{}\",\"{}\",{},{}\n".format(issue.number, issue.title,get_assigned(issue), size, column))

sys.exit(0)
