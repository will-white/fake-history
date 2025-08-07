Git History Faker
A sophisticated Python application designed to programmatically generate a realistic and authentic-looking Git history. This tool is ideal for populating a user's GitHub contribution graph, backfilling project history, or for any scenario where a curated commit history is desired.

The application operates in two primary modes: a scheduled "regular run" mode that amends recent commits to simulate daily activity, and a powerful "backfill" mode that can rewrite history to insert commits between two past dates.

✨ Features
Command-Line Interface (CLI): Easy-to-use commands for initializing the configuration (init), backfilling history (backfill), and performing a scheduled run (run).

Realistic Backfilling: Insert a commit history between any two dates, with the ability to create a new history root for empty repositories.

Commit Clustering: Simulates a real developer's workflow by creating bursts of multiple commits within a short time frame on a given day.

Working Hours Simulation: Restricts automated commits to specific days and hours to mimic a human work schedule.

Centralized JSON Configuration: All settings, from author persona to commit messages and scheduling, are managed in a single, easy-to-edit config.json file.

Safety First: Includes a --dry-run flag for the backfill command to preview changes without altering history.

CI/CD Integration: Comes with a pre-configured GitHub Actions workflow for automated, scheduled runs.

Unit Testing: Includes a test suite to verify the script's logic without performing real Git operations.

🏗️ Architecture Overview
The application is composed of three core components that work together:

vary_history.py (The Core Script):

This is the main Python script that contains all the logic for history manipulation.

It uses Python's argparse library to provide a clean command-line interface.

It's built around the GitHistoryFaker class, which reads the configuration and executes the requested git commands.

For history rewriting, it leverages the powerful and recommended git-filter-repo tool.

config.json (The Control File):

A central JSON file that acts as the "brain" for the script.

It defines the user persona (name and email), the pool of commit messages, the backfill date ranges, working hours, and commit clustering behavior.

Separating the configuration from the logic allows for easy customization without touching the Python code.

.github/workflows/history_faker.yml (The Automation Engine):

A GitHub Actions workflow file that automates the execution of the script.

It runs on a schedule (e.g., every hour) and executes the python vary_history.py run command.

This workflow is responsible for checking out the code, setting up the Python environment, and force-pushing the altered history back to the repository.

🚀 Setup and Usage
1. Prerequisites
Python 3.7+

pip for installing packages

2. Installation
Clone the repository and install the required dependency:

pip install git-filter-repo

3. Configuration
The easiest way to get started is to use the interactive init command. This will ask for your name and email and generate a config.json file for you.

python vary_history.py init

After running, review the newly created config.json file to customize commit messages, working hours, and other settings.

4. Running Commands
You can control the script using the following CLI commands:

Backfill History (Recommended First Step):
Use the backfill command to populate a past date range. Always use --dry-run first!

# See what would happen without making any changes
python vary_history.py backfill --start-date 2025-01-01 --end-date 2025-01-31 --dry-run

# If the dry run looks correct, run it for real
python vary_history.py backfill --start-date 2025-01-01 --end-date 2025-01-31

Perform a Regular Run:
This command is what the GitHub Action uses. It will amend a few recent commits to simulate daily activity.

python vary_history.py run

🧪 Testing
This project includes a suite of unit tests to ensure the core logic is working correctly. The tests are located in the `tests/` directory and use Python's built-in `unittest` framework.

The tests are designed to run without making any actual changes to your repository's history by using mock objects.

To run the tests, execute the following command from the root of the repository:

python tests/test_vary_history.py

A GitHub Actions workflow is also configured to run these tests automatically on every push and pull request to the `main` branch.

5. GitHub Actions Setup (for Automation)
To enable the scheduled runs, you must provide the workflow with a Personal Access Token (PAT) so it has permission to push to your repository.

Create a PAT: Go to your GitHub Settings > Developer settings > Personal access tokens > Tokens (classic). Generate a new token with the repo scope.

Create a Repository Secret: In your repository's Settings > Secrets and variables > Actions, create a new repository secret named GH_PAT and paste your token into it.

The workflow will now run automatically on its defined schedule.

⚠️ A Note on Safety
This tool rewrites Git history and uses git push --force-with-lease. These are inherently destructive operations. It is strongly recommended to only use this application on a personal repository where you are the sole contributor. Using it in a collaborative environment can overwrite the work of others.