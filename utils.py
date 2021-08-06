from local_defs import GITHUB_TOKEN
from github import Github, Repository
from enum import Enum
from github import Issue
import os
import glob
from git import Git, Repo, InvalidGitRepositoryError, NoSuchPathError


class COLUMNS(Enum):
    BUCKET = "Bucket"
    READY = "Ready"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    COMPLETE = "Review Complete"
    DONE = "Done"
    IMPEDED = "Impeded"
    UNKNOWN = "Unknown"
    IGNORED = "Ignored"

    @staticmethod
    def values():
        return [c.value for c in COLUMNS]

    @staticmethod
    def from_value(value):
        enums = [c for c in COLUMNS if c.value == value]
        try:
            return enums[0]
        except IndexError:
            if value.startswith("Sprint"):
                return COLUMNS.IGNORED
            return COLUMNS.UNKNOWN

    def __lt__(self, other):
        return self.value < other.value

    def __str__(self):
        return self.value


def get_IBEX_repo():
    github = Github(GITHUB_TOKEN)
    return github.get_repo("ISISComputingGroup/IBEX")


def get_project_columns(repo: Repository, project_board_name):
    """
    Gets the columns of the specified project from the specified repo.
    Args:
        repo: The repository to search
        project_board_name: The name of the project to return the columns for
    Return:
        The columns
    """
    found_projects = [project for project in repo.get_projects() if project.name == project_board_name]

    if len(found_projects) != 1:
        raise KeyError(f"{project_board_name} not found in IBEX repo")

    ibex_project = found_projects[0]
    print(f"## Checking project {ibex_project.name} ##\n")

    return ibex_project.get_columns()


def sort_cards_into_columns(columns):
    """
    Get a dictionary of column: cards for every column that we are aware of.
    """
    columns_dict = {}
    for column in columns:
        try:
            columns_dict[COLUMNS.from_value(column.name)] = column.get_cards()
        except KeyError:
            pass
    return columns_dict


def get_all_info_for_PRs(repository, file_changed):
    """Get the title, content and file changes for all PRs.
    Args:
        repository: The repository to check PRs for
        file_changed: The filename to get changes for
    Return:
        A list of tuples of (title, PR body text, code changes in specified file)
    """
    release_notes_prs = repository.get_pulls(state="open")
    prs = []
    for pr in release_notes_prs:
        title, content, files_changed = pr.title, pr.body, pr.get_files()
        if content is None:
            content = ''
        changes_made = [file.patch for file in files_changed if os.path.basename(file.filename) == file_changed]
        changes_made = "" if not changes_made else changes_made[0]
        prs.append((title, content, changes_made))

    return prs


def ticket_mentioned_in_pr(ticket_number, pr_infos):
    """Returns a tuple of whether the ticket number is in a title
    and whether the ticket number is mentioned in any of the specified PRs"""
    contains_ticket_number_anywhere = []
    contains_ticket_number_in_title = []
    for pr_details in pr_infos:
        contains_ticket_number_in_title.append(str(ticket_number) in pr_details[0])
        contains_ticket_number_anywhere.extend([str(ticket_number) in info for info in pr_details[1:]])
    return any(contains_ticket_number_in_title), any(contains_ticket_number_anywhere)


def get_issues_from_cards(cards):
    """Returns the content of all cards that are issues.
    Calls to get_context aren't cached so don't use list comprehension.
    """
    content_list = []
    for card in cards:
        content = card.get_content()
        if isinstance(content, Issue.Issue):
            content_list.append(content)
    return content_list


def pull_or_clone_repository(repo_path, repo_url):
    try:
        repository = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
        Git().clone(repo_url, repo_path)
        repository = Repo(repo_path)
    repository.remote().fetch()
    repository.git.checkout("master")
    repository.remote().pull()


def get_text_with_extension(folder_path, file_extension):
    """Get all the text from files with the specified extension."""
    contents = ""
    files = glob.glob(os.path.join(folder_path, f"*.{file_extension}"), recursive=True)
    for file_name in files:
        with open(file_name, "r") as file:
            contents += file.read()
    return contents

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
