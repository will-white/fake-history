import os
import sys
import json
import random
import argparse
import subprocess
from datetime import datetime, timedelta

CONFIG_FILE = 'config.json'

class GitHistoryFaker:
    """A class to handle all git history manipulation logic."""
    def __init__(self):
        """Loads the configuration file upon initialization."""
        self.config = self._load_config()
        if not self.config:
            print(f"Error: Config file '{CONFIG_FILE}' not found or empty.")
            print("Please run 'python vary_history.py init' to create one.")
            sys.exit(1)

    def _load_config(self):
        """Loads config from CONFIG_FILE if it exists."""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return None

    def _run_git_command(self, command, check=True):
        """Helper to run a git command and capture output."""
        try:
            result = subprocess.run(command, text=True, capture_output=True, check=check)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running git command: {' '.join(command)}")
            print(f"Stderr: {e.stderr.strip()}")
            raise

    def make_content_change(self, custom_line=None):
        """Makes a trivial change to a specified file."""
        content_cfg = self.config.get('commit_content', {})
        target_file = content_cfg.get('target_file', 'activity_log.md')
        line_prefix = content_cfg.get('line_prefix', '- Log entry:')
        line = custom_line or f"{line_prefix} {datetime.now().isoformat()}"
        with open(target_file, 'a') as f:
            f.write(f"{line}\n")
        self._run_git_command(['git', 'add', target_file])

    def run_backfill(self, start_date, end_date, dry_run=False):
        """Creates a history of commits, with clustering."""
        print(f"--- Backfill Mode Activated (Dry Run: {dry_run}) ---")
        persona_cfg = self.config['commit_persona']
        backfill_cfg = self.config['backfill_settings']
        clustering_cfg = self.config.get('commit_clustering', {})
        author = persona_cfg['author']
        author_str = f"{author['name']} <{author['email']}>"

        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        main_branch = "main" # Change if your default branch is different

        # [Logic to find base_commit or create a new root - same as previous version]
        # ... This part checks for existing history to splice into.
        
        print("Starting commit generation loop with clustering...")
        current_dt = start_dt
        while current_dt <= end_dt:
            if random.random() < backfill_cfg.get("commit_frequency_per_day", 0.75):
                num_commits = 1
                if clustering_cfg.get('enabled', False):
                    min_c = clustering_cfg.get('min_commits_per_cluster', 1)
                    max_c = clustering_cfg.get('max_commits_per_cluster', 4)
                    num_commits = random.randint(min_c, max_c)
                
                print(f"  Creating cluster of {num_commits} commit(s) for {current_dt.date()}")
                
                base_hour = random.randint(10, 16)
                base_minute = random.randint(0, 59)

                for i in range(num_commits):
                    commit_minute = base_minute + (i * random.randint(5, 20))
                    commit_hour = base_hour + (commit_minute // 60)
                    commit_minute %= 60
                    if commit_hour > 23: continue

                    commit_dt = current_dt.replace(hour=commit_hour, minute=commit_minute)
                    commit_msg = random.choice(persona_cfg["commit_messages"])
                    
                    if not dry_run:
                        self.make_content_change(f"Backfilled entry for {commit_dt.isoformat()}")
                        env = os.environ.copy()
                        env['GIT_COMMITTER_DATE'] = commit_dt.isoformat()
                        subprocess.run(['git', 'commit', '--author', author_str, '--date', commit_dt.isoformat(), '-m', commit_msg], env=env, check=True, capture_output=True)
                    else:
                        print(f"    [DRY RUN] Would create commit: '{commit_msg}' at {commit_dt.isoformat()}")
            current_dt += timedelta(days=1)
        
        if dry_run:
            print("\n--- Dry Run Complete. No history was changed. ---")
            return
            
        # [Logic to rebase and clean up - same as previous version]
        # ...
        print("--- Backfill Complete ---")
        return True

    def alter_recent_commits(self):
        """Amends a few recent commits. Used for scheduled 'run' command."""
        print("--- Regular Mode: Amending recent commits ---")
        # [This function's logic should be copied from the previous versions]
        # It uses git-filter-repo to amend the last N commits.
        print("Regular run complete.")

    def is_time_to_work(self):
        """Checks if current time is within configured working hours."""
        run_cfg = self.config['run_settings']
        wh_cfg = run_cfg.get('working_hours', {})
        if not wh_cfg.get('enabled', False): return True
        now = datetime.now()
        if (now.weekday() == 5 and not wh_cfg.get('work_on_saturday', False)) or \
           (now.weekday() == 6 and not wh_cfg.get('work_on_sunday', False)):
            print("Weekend. Taking a break.")
            return False
        if not wh_cfg.get('start_hour', 9) <= now.hour < wh_cfg.get('end_hour', 17):
            print("Outside working hours.")
            return False
        if random.random() < run_cfg.get('skip_run_chance', 0.0):
            print("Simulating a busy day. Skipping run.")
            return False
        return True

# --- CLI Handler Functions ---
def handle_init(args):
    """Interactively creates a new config.json file."""
    print("--- Git History Faker Initializer ---")
    if os.path.exists(CONFIG_FILE):
        if input(f"'{CONFIG_FILE}' already exists. Overwrite? (y/N): ").lower() != 'y':
            print("Initialization cancelled.")
            return

    config = {
        "commit_persona": {
            "author": { "name": input("Enter Author Name: "), "email": input("Enter Author Email: ") },
            "commit_messages": ["feat: Initial implementation", "fix: Correct bug", "refactor: Improve code"]
        },
        "backfill_settings": {"start_date": "2025-01-01", "end_date": "2025-01-31", "commit_frequency_per_day": 0.7},
        "commit_clustering": {"enabled": True, "min_commits_per_cluster": 2, "max_commits_per_cluster": 5},
        "run_settings": {"min_commits_to_alter": 1, "max_commits_to_alter": 3, "working_hours": {"enabled": True, "start_hour": 9, "end_hour": 17, "work_on_saturday": False, "work_on_sunday": False}, "skip_run_chance": 0.2},
        "commit_content": {"target_file": "activity.log", "line_prefix": "- Log:"}
    }
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=2)
    print(f"\nSuccessfully created '{CONFIG_FILE}'. Please review it for more options.")

def handle_run(args):
    """Handles the regular 'amend recent' run for CI/CD."""
    faker = GitHistoryFaker()
    if faker.is_time_to_work():
        try:
            faker.alter_recent_commits()
        except Exception as e:
            print(f"Could not run 'alter_recent_commits', repo might be empty. Error: {e}")
    else:
        print("Not time to work. Exiting scheduled run.")

def handle_backfill(args):
    """Handles the backfill operation."""
    faker = GitHistoryFaker()
    config = faker.config['backfill_settings']
    start = args.start_date or config.get('start_date')
    end = args.end_date or config.get('end_date')
    if not start or not end:
        print("Error: Start/end dates required. Provide via CLI flags or in config.json.")
        return
    faker.run_backfill(start, end, args.dry_run)

def main():
    """Main function to parse CLI arguments and call the appropriate handler."""
    parser = argparse.ArgumentParser(description="A tool to fake Git history with realism.", formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest='command', required=True, help="Available commands")

    init_parser = subparsers.add_parser('init', help="Create a new config.json file interactively.")
    init_parser.set_defaults(func=handle_init)

    run_parser = subparsers.add_parser('run', help="Perform a regular run (for CI/CD). Amends recent commits.")
    run_parser.set_defaults(func=handle_run)

    backfill_parser = subparsers.add_parser('backfill', help="Backfill history for a given date range.")
    backfill_parser.add_argument('--start-date', help="Start date in YYYY-MM-DD format. Overrides config.")
    backfill_parser.add_argument('--end-date', help="End date in YYYY-MM-DD format. Overrides config.")
    backfill_parser.add_argument('--dry-run', action='store_true', help="Simulate the backfill without changing history.")
    backfill_parser.set_defaults(func=handle_backfill)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
