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

    @staticmethod
    def values():
        return [c.value for c in COLUMNS]

    @staticmethod
    def from_value(value):
        enums = [c for c in COLUMNS if c.value == value]
        if value:
            return enums[0]
        raise KeyError(f"{value} not found in COLUMNS")


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
        changes_made = [file.patch for file in files_changed if file.filename == file_changed]
        changes_made = "" if not changes_made else changes_made[0]
        prs.append((title, content, changes_made))

    return prs


def ticket_mentioned_in_pr(ticket_number, pr_infos):
    """Returns true if the specified ticket number is mentioned in any of the specified PRs"""
    contains_ticket_number = []
    for pr_details in pr_infos:
        contains_ticket_number.extend([str(ticket_number) in info for info in pr_details])
    return any(contains_ticket_number)


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
