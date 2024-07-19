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
from utils import get_IBEX_repo, get_project_columns, COLUMNS, get_assigned

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
ZERO_POINT_LABELS = {'Good First Issue', 'HLM', 'Cryomagnet', 'Friday',
                     'Datastreaming', 'standdown', 'support'}
NO_POINT_LABELS = {'support', 'duplicate', 'sub-ticket', 'umbrella', 'wontfix'}

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


def check_labels(labels, check, issue, present):
    assigned = get_assigned(issue)
    if present:
        diff = set(check).difference(labels)
        if len(diff) > 0:
            print_error('ERROR: issue {} ({}) does NOT have the following required labels: {} (assigned: {})'
                        .format(issue.number, issue.title, ','.join(diff),assigned))
    if not present:
        diff = labels.intersection(set(check))
        if len(diff) > 0:
            print_error('ERROR: issue {} ({}) has the following INVALID labels: {} (assigned: {})'.format(issue.number, issue.title, ','.join(diff), assigned))


def check_column_label(labels, label, issue):
    check_labels(labels, [label], issue, True)
    no_labels = [x for x in WORKFLOW_LABELS if x != label]
    check_labels(labels, no_labels, issue, False)


def check_if_stale(issue, label_name, warn_days_allowed, error_days_allowed, assigned):
    created = None
    for event in issue.get_events(): # or get_timeline() and '
#        if event.event == 'moved_columns_in_project' and event.column_name == 'Review':
#            print(event.created_at)
        if event.event == 'labeled' and event.label.name == label_name:
            created = event.created_at
    if created is not None:
        dur = datetime.datetime.now(datetime.UTC) - created
        if dur > datetime.timedelta(error_days_allowed):
            print_warning('ERROR: Issue {} ({}) has been in "{}" for {} days (assigned: {})'.format(issue.number, issue.title, label_name, dur.days, assigned))
        elif dur > datetime.timedelta(warn_days_allowed):
            print_warning('WARNING: Issue {} ({}) has been in "{}" for {} days (assigned: {})'.format(issue.number, issue.title, label_name, dur.days, assigned))

def check_recent_comments(issue, error_days_allowed):
    comments = issue.get_comments()
    most_recent_comment = None
    for comment in comments:
        if most_recent_comment is None or comment.updated_at > most_recent_comment.updated_at:
            most_recent_comment = comment
    if most_recent_comment:
        # time ago comment was made
        days_ago = (datetime.datetime.now(datetime.UTC) -
                    most_recent_comment.updated_at).days

        if days_ago > error_days_allowed:
            check_if_stale(issue, 'impeded', error_days_allowed, error_days_allowed, assigned)
    else:
        check_if_stale(issue, 'impeded', error_days_allowed, error_days_allowed, assigned)

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
for github_column in columns:
    print(f'** Checking column "{github_column.name}"')
    column = COLUMNS.from_value(github_column.name)

    if column is COLUMNS.IGNORED:
        print(f"Ignoring column {github_column.name}")
        continue

    total = 0
    cards = github_column.get_cards()
    column_tickets[column] = cards.totalCount

    is_bucket = False
    if column is COLUMNS.UNKNOWN:
        is_bucket = True
        print("INFO: unknown column \"{}\" - assuming like Bucket".format(github_column.name))
    if column is COLUMNS.BUCKET:
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
                        print_error("ERROR: issue {} ({}) has multiple sizes (assigned: {})".format(issue.number, issue.title, assigned))
                    else:
                        size = int(label.name)
                        found_size = True
            if size is None:
                no_labels = NO_POINT_LABELS.intersection(labels)
                if len(no_labels) > 0:
                    print("INFO: no size {} issue {} ({})".format(','.join(no_labels), issue.number, issue.title))
                elif is_bucket:
                    pass
                else:
                    print_error("ERROR: no size for issue {} ({}) in {} (assigned: {})".format(issue.number, issue.title, column, assigned))
            elif size == 0:
                zero_labels = ZERO_POINT_LABELS.intersection(labels)
                if len(zero_labels) > 0:
                    print("INFO: size 0 {} issue {}".format(','.join(zero_labels), issue.number))
                else:
                    print_error("ERROR: size 0 not allowed for issue {} ({}) (assigned: {})".format(issue.number, issue.title, assigned))
            else:
                if added_during_sprint:
                    points_added_during_sprint += size
                    tickets_added_during_sprint += 1
                if under_review:
                    points_under_review += size
                total += size
            if size is not None:
                issue_size[issue.number] = size
            issue_column[issue.number] = column
            if is_bucket and issue.milestone is not None:
                print_error("ERROR: issue {} ({}) has milestone {} (assigned: {})".format(issue.number, issue.title, issue.milestone.title, get_assigned(issue)))
            if not is_bucket and issue.milestone is None:
                print_error("ERROR: issue {} ({}) has no milestone (assigned: {})".format(issue.number, issue.title, assigned))
            if not is_bucket and issue.milestone is not None and issue.milestone.state == "open":
                milestones.append(issue.milestone.title)
            if (issue.milestone is not None) and (issue.milestone.state == 'closed'):
                print_error("ERROR: issue {} ({}) has a closed milestone (assigned: {})".format(issue.number, issue.title, assigned))
            if column is COLUMNS.UNKNOWN:
                check_labels(labels, ['rework'], issue, False)
            if column is COLUMNS.BUCKET:
                check_column_label(labels, 'bucket', issue)
            if column is COLUMNS.READY:
                check_column_label(labels, 'ready', issue)
                check_labels(labels, ['proposal'], issue, False)
                check_if_stale(issue, 'rework', 7, 28, assigned)
            if column is COLUMNS.IN_PROGRESS:
                check_column_label(labels, 'in progress', issue)
                check_if_stale(issue, 'in progress', 14, 2800, assigned)
            if column is COLUMNS.REVIEW:
                check_column_label(labels, 'review', issue)
                check_if_stale(issue, 'review', 7, 28, assigned)
                if "under review" in issue.labels:
                    check_if_stale(issue, 'under review', 7, 28, assigned)
            # if column is COLUMNS.COMPLETE:
            #    check_column_label(labels, 'completed', issue)
            # if column is COLUMNS.DONE:
            #     check_column_label(labels, 'completed', issue)
            if column is COLUMNS.IMPEDED:
                check_column_label(labels, 'impeded', issue)
                check_recent_comments(issue, 28)
            if in_rework and column in [COLUMNS.READY, COLUMNS.IN_PROGRESS, COLUMNS.IMPEDED]:
                current_rework += 1
            if in_rework and column in [COLUMNS.REVIEW, COLUMNS.COMPLETE, COLUMNS.DONE]:
                completed_rework += 1
#            if addigned != 'None' and column.name in [ 'Bucket' ]:
#                print_error("ERROR: issue {} cannot be assigned to {}".format(issue.number,assigned))
            if assigned == 'None' and column in [COLUMNS.IN_PROGRESS, COLUMNS.REVIEW, COLUMNS.COMPLETE]:
                print_error("ERROR: issue {} ({}) must be assigned to somebody".format(issue.number, issue.title))
        else:
            pr = card.get_content()
            try:
                print_error("ERROR: pullrequest {} not allowed".format(pr.number))
            except AttributeError:
                print_warning("WARNING: Card is present on board instead of IBEX issue")
    print("INFO: column \"{}\" contains {} cards and {} points\n".format(column, cards.totalCount, total))
    column_points[column] = total

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

# format is SPRINT_YY_MM_DD
try:
    ms_parts = current_milestone.title.split('_')
    ms_dict['START'] = '-'.join(ms_parts[1:])
except:
    ms_dict['START'] = '1970-01-01'

with open('milestone.json', 'w') as f:
    json.dump(ms_dict, f)

for milestone in open_milestones:
    if milestone.title != current_milestone_title and milestone.title in milestones:
        milestone_issues = repo.get_issues(milestone=milestone, state='all')
        for issue in milestone_issues:
            if issue.number in issue_column:
                print_error("ERROR: issue {} ({}) ({}, assigned: {}) has old milestone {}".format(issue.number, issue.title, issue.state, get_assigned(issue), milestone.title))

if args.milestone:
    milestone_issues = repo.get_issues(milestone=current_milestone, state='all')
    for issue in milestone_issues:
        if issue.number not in issue_column:
            print_error("ERROR: issue {} ({}) ({}, assigned: {}) has current milestone but is not on board".format(issue.number, issue.title, issue.state, get_assigned(issue)))

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
    f.write(json.dumps({number: column.value for number, column in issue_column.items()}))

if not os.path.exists("burndown-points.csv"):
    with open("burndown-points.csv", "w") as f:
        f.write("Date,{},Points Sum,Points Added,Burndown\n".format(",".join([x.value for x in sorted(column_points.keys()) if x is not COLUMNS.UNKNOWN])))

if not os.path.exists("burndown-tickets.csv"):
    with open("burndown-tickets.csv", "w") as f:
        f.write("Date,{},Under Review,Current Rework,Completed Rework,Tickets Sum,Tickets Added,Burndown\n".format(",".join([x.value for x in sorted(column_tickets.keys()) if x is not COLUMNS.UNKNOWN])))

with open("burndown-points.csv", "a") as f:
    if COLUMNS.COMPLETE in column_points:
        completed = column_points[COLUMNS.COMPLETE]
    else:
        completed = 0
    f.write("{},{},{},{},{}\n".format(ts, ",".join([str(column_points[x]) for x in sorted(column_points.keys()) if x is not COLUMNS.UNKNOWN]), points_sum, points_added_during_sprint, points_sum - points_added_during_sprint-completed))

with open("burndown-tickets.csv", "a") as f:
    if COLUMNS.COMPLETE in column_tickets:
        completed = column_tickets[COLUMNS.COMPLETE]
    else:
        completed = 0
    f.write("{},{},{},{},{},{},{},{}\n".format(ts, ",".join([str(column_tickets[x]) for x in sorted(column_tickets.keys()) if x is not COLUMNS.UNKNOWN]),tickets_under_review,current_rework, completed_rework, tickets_sum, tickets_added_during_sprint, tickets_sum - tickets_added_during_sprint - completed))

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
        f.write("{},\"{}\",\"{}\",{},{}\n".format(issue.number, issue.title, get_assigned(issue), size, column))

sys.exit(0)
