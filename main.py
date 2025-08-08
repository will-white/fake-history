import os
import sys
import json
import random
import subprocess
from datetime import datetime, timedelta
import tempfile
import shutil
from git import Repo

CONFIG_FILE = 'config.json'

# ==============================================================================
# This class is adapted from the original vary_history.py script.
# It's included here to make the Cloud Function self-contained.
# ==============================================================================

class GitHistoryFaker:
    """A class to handle all git history manipulation logic."""
    def __init__(self, base_path='.'):
        """Loads the configuration file upon initialization."""
        self.base_path = base_path
        self.config = self._load_config()
        if not self.config:
            # In a cloud function, exiting is not ideal. Raise an error.
            raise ValueError(f"Error: Config file '{CONFIG_FILE}' not found or empty in the repository.")

    def _load_config(self):
        """Loads config from CONFIG_FILE if it exists."""
        config_path = os.path.join(self.base_path, CONFIG_FILE)
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return None

    def _run_git_command(self, command, check=True):
        """Helper to run a git command and capture output."""
        try:
            # When running git commands, it's crucial to set the working directory.
            result = subprocess.run(command, text=True, capture_output=True, check=check, cwd=self.base_path)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running git command: {' '.join(command)}")
            print(f"Stderr: {e.stderr.strip()}")
            raise

    def make_content_change(self, custom_line=None):
        """Makes a trivial change to a specified file."""
        content_cfg = self.config.get('commit_content', {})
        target_file = os.path.join(self.base_path, content_cfg.get('target_file', 'activity_log.md'))
        line_prefix = content_cfg.get('line_prefix', '- Log entry:')
        line = custom_line or f"{line_prefix} {datetime.now().isoformat()}"
        with open(target_file, 'a') as f:
            f.write(f"{line}\n")
        self._run_git_command(['git', 'add', os.path.basename(target_file)])

    def is_time_to_work(self):
        """Checks if current time is within configured working hours."""
        run_cfg = self.config.get('run_settings', {})
        wh_cfg = run_cfg.get('working_hours', {})
        if not wh_cfg.get('enabled', False): return True

        now = datetime.now() # Assumes GCF instance runs in UTC, align with config
        if (now.weekday() == 5 and not wh_cfg.get('work_on_saturday', False)) or \
           (now.weekday() == 6 and not wh_cfg.get('work_on_sunday', False)):
            print("It's the weekend according to the config. Taking a break.")
            return False
        if not wh_cfg.get('start_hour', 9) <= now.hour < wh_cfg.get('end_hour', 17):
            print(f"Current hour ({now.hour}) is outside of configured working hours ({wh_cfg.get('start_hour')} - {wh_cfg.get('end_hour')}).")
            return False
        if random.random() < run_cfg.get('skip_run_chance', 0.0):
            print("Simulating a busy day. Skipping run based on skip_run_chance.")
            return False
        return True

# ==============================================================================
# Cloud Function Logic
# ==============================================================================

def create_new_commits(faker_instance):
    """Creates one or more new commits to simulate recent activity."""
    print("--- Creating new commits ---")
    run_cfg = faker_instance.config['run_settings']
    persona_cfg = faker_instance.config['commit_persona']
    author_str = f"{persona_cfg['author']['name']} <{persona_cfg['author']['email']}>"

    min_commits = run_cfg.get('min_commits_to_alter', 1)
    max_commits = run_cfg.get('max_commits_to_alter', 3)
    commits_to_create = random.randint(min_commits, max_commits)
    print(f"Attempting to create {commits_to_create} new commit(s).")

    for i in range(commits_to_create):
        faker_instance.make_content_change()
        commit_msg = random.choice(persona_cfg["commit_messages"])
        commit_date = datetime.now().isoformat()

        # Use the helper to run the git command from the correct directory
        faker_instance._run_git_command(['git', 'commit', '--author', author_str, '--date', commit_date, '-m', commit_msg])
        print(f"Created commit {i+1}/{commits_to_create}: '{commit_msg}'")

    print(f"Successfully created {commits_to_create} new commits.")


def run_history_variation(event, context):
    """
    Google Cloud Function entry point.
    Clones a Git repo, fakes some history by adding new commits, and pushes it back.

    Required Environment Variables:
    - GH_PAT: A GitHub Personal Access Token with repo write access.
    - REPO_URL: The repository URL (e.g., 'github.com/YourUser/YourRepo.git').
    - GIT_BRANCH: The branch to operate on (e.g., 'main').
    """
    GH_PAT = os.environ.get('GH_PAT')
    REPO_URL = os.environ.get('REPO_URL')
    GIT_BRANCH = os.environ.get('GIT_BRANCH', 'main')

    if not GH_PAT or not REPO_URL:
        print("FATAL: GH_PAT and REPO_URL environment variables are required.")
        raise ValueError("Missing required environment variables.")

    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")

    try:
        auth_repo_url = f"https://oauth2:{GH_PAT}@{REPO_URL}"
        print(f"Cloning repo from {REPO_URL} into {temp_dir}...")
        repo = Repo.clone_from(auth_repo_url, temp_dir, branch=GIT_BRANCH)
        print("Repository cloned successfully.")

        # Configure Git User for the push
        with repo.config_writer() as cw:
            cw.set_value("user", "name", "GCP History Faker Bot")
            cw.set_value("user", "email", "bot@example.com")

        # Instantiate Faker and run the logic
        faker = GitHistoryFaker(base_path=temp_dir)
        if faker.is_time_to_work():
            create_new_commits(faker)

            # Push changes
            print(f"Pushing changes to remote branch '{GIT_BRANCH}'...")
            repo.git.push('origin', GIT_BRANCH)
            print("Changes pushed successfully.")
        else:
            print("Not time to work according to config. Exiting gracefully.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Re-raise the exception to ensure the Cloud Function fails visibly for monitoring.
        raise

    finally:
        print(f"Cleaning up temporary directory: {temp_dir}")
        shutil.rmtree(temp_dir)

# Example of how to test locally (requires env vars to be set)
# if __name__ == '__main__':
#     run_history_variation(None, None)
