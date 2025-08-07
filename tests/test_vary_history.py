import unittest
import os
import json
import io
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

# Make the script importable
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vary_history import GitHistoryFaker, handle_init

class TestGitHistoryFakerLogic(unittest.TestCase):

    @patch('vary_history.subprocess.run')
    @patch('vary_history.random.choice', return_value='test commit')
    @patch('vary_history.random.random', return_value=0.5)
    @patch('vary_history.random.randint')
    def test_run_backfill_logic_is_correct(self, mock_randint, mock_random, mock_choice, mock_subprocess):
        """
        A self-contained test for the backfill logic.
        """
        # 1. Config
        test_config = {
            "commit_persona": {"author": {"name": "Test", "email": "test@test.com"}, "commit_messages": ["msg"]},
            "backfill_settings": {"commit_frequency_per_day": 1.0},
            "commit_clustering": {"enabled": False},
            "commit_content": {"target_file": "test_log.md"}
        }

        # 2. Mocks - There are 3 calls to randint per day when clustering is off.
        mock_randint.side_effect = [
            10, 5, 10, # Day 1: hour=10, minute=5, unused_offset=10
            14, 25, 10, # Day 2: hour=14, minute=25, unused_offset=10
            18, 55, 10  # Day 3: hour=18, minute=55, unused_offset=10
        ]

        # 3. Instantiate and run
        with patch.object(GitHistoryFaker, '_load_config', return_value=test_config):
            faker = GitHistoryFaker()
            faker.config = test_config

            f = io.StringIO()
            with redirect_stdout(f):
                faker.run_backfill("2023-02-01", "2023-02-03", dry_run=True)
            output = f.getvalue()

        # 4. Assertions
        self.assertIn("Would create commit: 'test commit' at 2023-02-01T10:05:00", output)
        self.assertIn("Would create commit: 'test commit' at 2023-02-02T14:25:00", output)
        self.assertIn("Would create commit: 'test commit' at 2023-02-03T18:55:00", output)

        # Ensure no actual git commands were run
        mock_subprocess.assert_not_called()

class TestCliHandlers(unittest.TestCase):
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.input', side_effect=['y', 'Test User', 'test@example.com'])
    @patch('os.path.exists', return_value=True)
    def test_handle_init_overwrite(self, mock_exists, mock_input, mock_file):
        """Test the interactive config file creation when file exists."""
        with patch('vary_history.CONFIG_FILE', 'config.json'):
            handle_init(None)

        mock_exists.assert_called_with('config.json')
        mock_input.assert_any_call("Enter Author Name: ")
        mock_file.assert_called_with('config.json', 'w')
        self.assertTrue(mock_file().write.called)

if __name__ == '__main__':
    unittest.main()
