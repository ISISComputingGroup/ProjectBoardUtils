# Project Board Utils

This program will check out the repositories associated with the IBEX project and run the following checks on them:

* Various rules about whether issues are being correctly managed using the agreed workflow
* Release notes are being adequately kept up to date

## Install and Setup

This program is run on a central system at ISIS, which doesn't have the usual IBEX python installation. As such it has requirements that are not included in `genie_python`. It is recommended to create a virtual environment to install these dependencies and run the program on a dev machine. To do this:

* Follow the instructions on https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token (As the program uses the github API it requires a github API token. For security reasons this is not included in the repository.)

* Create a `local_defs.py` file at the top level of this repository containing `GITHUB_TOKEN = "MY_TOKEN_HERE"` (Remember to never add this token into git!)

* Clone the repository into a your \Instrument folder

* Open a cmd window and navigate to "C:\Instrument\ProjectBoardUtils"

* Run 'make_venv.bat'

From this command prompt you will now be able to run `python card.py` to display the ProjectBoardChecks seen on Jenkins Console Output. 

(You can also set pycharm up to point at this virtual env.)
