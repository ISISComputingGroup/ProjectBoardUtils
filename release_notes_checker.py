import sys

import regex as re

from utils import *

RELEASE_NOTES_REPO_PATH = "release_notes_repo"
RELEASE_NOTES_FOLDER = "release_notes"

UPCOMING_CHANGES_FILE = "ReleaseNotes_Upcoming.md"

LABELS_TO_IGNORE = ["no_release_notes", "HLM"]


def check_review_in_prs(repository, column_dict):
    in_error = False
    pull_or_clone_repository(
        RELEASE_NOTES_REPO_PATH, "https://github.com/ISISComputingGroup/IBEX.git"
    )
    all_release_notes_text = get_text_with_extension(
        os.path.join(RELEASE_NOTES_REPO_PATH, RELEASE_NOTES_FOLDER), "md"
    )
    prs = get_all_info_for_PRs(repository, UPCOMING_CHANGES_FILE)

    for ticket in get_issues_from_cards(column_dict[COLUMNS.REVIEW]):
        ticket_labels = set([label.name for label in ticket.labels])
        if ticket_labels.intersection(LABELS_TO_IGNORE):
            continue
        ticket_number = ticket.number
        ticket_in_title, ticket_anywhere = ticket_mentioned_in_pr(ticket_number, prs)
        if not ticket_in_title:
            in_error = True
            if ticket.html_url in all_release_notes_text:
                print(
                    f"ERROR: issue {ticket_number} has merged release notes but is still in review (assigned: {get_assigned(ticket)})"
                )
            else:
                print(
                    f"ERROR: issue {ticket_number} is not mentioned in the title of any open PRs modifying release notes (assigned: {get_assigned(ticket)})"
                )
        if not ticket_mentioned_in_pr(ticket_number, prs):
            in_error = True
            print(
                f"ERROR: issue {ticket_number} has no PR modifying release notes ({ticket.html_url}, assigned: {get_assigned(ticket)})"
            )
    return in_error


def check_for_dangling_release_notes(repository):
    """
    A release note is considered dangling release note when its corresponding issue is closed.
    Returns: error or not
    """
    in_error = False
    prs = get_all_info_for_PRs(repository, UPCOMING_CHANGES_FILE)
    regex_list = [r"(?i:Ticket |Ticket|#)\K\d+", r"([0-9]+)(?=[^\/]*$)"]
    for pr in prs:
        ticket_number = (
            re.search(regex_list[0], pr[0]).group() if re.search(regex_list[0], pr[0]) else None
        )
        if not ticket_number and pr[1]:
            for regex in regex_list:
                if re.search(regex, pr[1]):
                    ticket_number = re.search(regex, pr[1]).group()
        if ticket_number:
            try:
                if repository.get_issue(int(ticket_number)).state == "closed":
                    in_error = True
                    print(
                        f"ERROR: issue {ticket_number} is closed but its associated Release note PR titled "
                        f'"{pr[0]}" is open'
                    )
            except:
                print(f"INFO: cannot find issue {ticket_number}")
                pass

    return in_error


def check_complete_in_a_file(column_dict):
    in_error = False
    pull_or_clone_repository(
        RELEASE_NOTES_REPO_PATH, "https://github.com/ISISComputingGroup/IBEX.git"
    )

    done_tickets = get_issues_from_cards(column_dict[COLUMNS.COMPLETE])

    all_release_notes_text = get_text_with_extension(
        os.path.join(RELEASE_NOTES_REPO_PATH, RELEASE_NOTES_FOLDER), "md"
    )

    for ticket in done_tickets:
        ticket_labels = set([label.name for label in ticket.labels])
        if ticket_labels.intersection(LABELS_TO_IGNORE):
            continue
        if ticket.html_url not in all_release_notes_text:
            in_error = True
            print(
                f"ERROR: issue {ticket.number} merged but not linked in release notes (assigned: {get_assigned(ticket)})"
            )
    return in_error


def main():
    project_board_repository = get_IBEX_repo()
    columns = get_project_columns(project_board_repository, "IBEX Project Board")
    column_dict = sort_cards_into_columns(columns)
    in_error = check_for_dangling_release_notes(project_board_repository)
    in_error |= check_review_in_prs(project_board_repository, column_dict)
    in_error |= check_complete_in_a_file(column_dict)
    return in_error


if __name__ == "__main__":
    sys.exit(main())
