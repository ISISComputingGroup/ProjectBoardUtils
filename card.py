"""
project board scan
"""
import os
import sys
import json
import argparse
from statistics import mode
from datetime import date
from github import Github, Issue
from local_defs import GITHUB_TOKEN

parser = argparse.ArgumentParser(description='projects')
parser.add_argument('--project', dest='project', default='IBEX Project Board')
parser.add_argument('--data', action='store_true')
parser.add_argument('--milestone', action='store_true')
args = parser.parse_args()

# these are labels that apply to a column i.e. there should
# only be one such label on a ticket
WORKFLOW_LABELS = ['bucket', 'ready', 'in progress', 'review',
                   'completed', 'awaiting', 'impeded']
WORKFLOW_COLUMNS = ['Bucket', 'Ready', 'In Progress', 'Review',
                    'Review Complete', 'Done', 'Impeded']
POINTSUM_COLUMNS = ['Ready', 'In Progress', 'Review', 'Review Complete',
                    'Impeded']
ZERO_POINT_LABELS = {'training', 'HLM', 'Cryomagnet', 'Friday', 'standdown'}
NO_POINT_LABELS = {'support', 'duplicate', 'sub-ticket'}

NUM_ERROR = 0

def print_error(*args, **kwargs):
    global NUM_ERROR
    print(*args, **kwargs)
    NUM_ERROR += 1

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

g = Github(GITHUB_TOKEN)
repo = g.get_repo("ISISComputingGroup/IBEX")
for p in repo.get_projects():
    if p.name == args.project:
        ibex_project = p

print("## Checking project {} ##\n".format(ibex_project.name))

columns = ibex_project.get_columns()

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
    if column.name not in WORKFLOW_COLUMNS:
        is_bucket = True
        print("INFO: unknown column \"{}\" - assuming like Bucket".format(column.name))
    if column.name == 'Bucket':
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
            for label in issue.labels:
                labels.add(label.name)
                if label.name == "under review":
                    under_review = True
                    tickets_under_review += 1
                if label.name == "rework":
                    in_rework = True
                if label.name == "added during sprint":
                    added_during_sprint = True
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
            if column.name not in WORKFLOW_COLUMNS:
                check_labels(labels, ['rework'], issue, False)
            if column.name == 'Bucket':
                check_column_label(labels, 'bucket', issue)
                check_labels(labels, ['rework'], issue, False)
            if column.name == 'Ready':
                check_column_label(labels, 'ready', issue)
                check_labels(labels, ['proposal'], issue, False)
            if column.name == 'In Progress':
                check_column_label(labels, 'in progress', issue)
            if column.name == 'Review':
                check_column_label(labels, 'review', issue)
            if column.name == 'Review Complete':
                check_column_label(labels, 'completed', issue)
            if column.name == 'Done':
                check_column_label(labels, 'completed', issue)
            if column.name == 'Impeded':
                check_column_label(labels, 'impeded', issue)
            if in_rework and column.name in ['Ready', 'In Progress', 'Impeded']:
                current_rework += 1
            if in_rework and column.name in ['Review', 'Review Complete', 'Done']:
                completed_rework += 1
#            if addigned != 'None' and column.name in [ 'Bucket' ]:
#                print_error("ERROR: issue {} cannot be assigned to {}".format(issue.number,assigned))
            if assigned == 'None' and column.name in ['In Progress', 'Review', 'Review Complete']:
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
    ms_dict = json.loads(current_milestone.description)
except:
    ms_dict['SP'] = 0

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

sys.exit(NUM_ERROR)