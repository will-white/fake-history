import pytest
from unittest.mock import MagicMock, patch
from vary_history import GitHistoryFaker, CONFIG_FILE
import json
import datetime

@pytest.fixture
def mock_faker(mocker):
    """Fixture to create a GitHistoryFaker instance with mocked config."""
    # Mock the os.path.exists and open calls to simulate a config file
    mock_config = {
        "commit_persona": {
            "author": {"name": "Test User", "email": "test@example.com"},
            "commit_messages": ["Test commit"]
        },
        "run_settings": {
            "working_hours": {
                "enabled": True,
                "start_hour": 9,
                "end_hour": 17,
                "work_on_saturday": False,
                "work_on_sunday": False
            },
            "skip_run_chance": 0.2
        }
    }
    mocker.patch('os.path.exists', return_value=True)
    mocker.patch('builtins.open', mocker.mock_open(read_data=json.dumps(mock_config)))

    # We need to bypass the __init__ of the real class that tries to load the file
    # and instead inject our mock config directly.
    with patch.object(GitHistoryFaker, '_load_config', return_value=mock_config) as mock_load:
        faker = GitHistoryFaker()
        yield faker

class TestIsTimeToWork:

    @pytest.mark.parametrize("hour", [9, 12, 16])
    def test_during_working_hours_weekday(self, mock_faker, mocker, hour):
        """Test that it returns True during working hours on a weekday."""
        mock_datetime = mocker.patch('vary_history.datetime')
        mock_datetime.now.return_value = datetime.datetime(2025, 1, 6, hour, 30) # A Monday

        mocker.patch('vary_history.random.random', return_value=0.3) # Above skip_run_chance
        assert mock_faker.is_time_to_work() is True

    @pytest.mark.parametrize("hour", [8, 17, 23])
    def test_outside_working_hours_weekday(self, mock_faker, mocker, hour):
        """Test that it returns False outside working hours on a weekday."""
        mock_datetime = mocker.patch('vary_history.datetime')
        mock_datetime.now.return_value = datetime.datetime(2025, 1, 6, hour, 30) # A Monday
        assert mock_faker.is_time_to_work() is False

    @pytest.mark.parametrize("weekday", [5, 6]) # Saturday, Sunday
    def test_on_weekend_disabled(self, mock_faker, mocker, weekday):
        """Test that it returns False on a weekend if disabled."""
        # January 4th, 2025 is a Saturday, 5th is a Sunday
        mock_datetime = mocker.patch('vary_history.datetime')
        mock_datetime.now.return_value = datetime.datetime(2025, 1, 4 + (weekday - 5), 14, 0)
        assert mock_faker.is_time_to_work() is False

    def test_on_weekend_enabled(self, mock_faker, mocker):
        """Test that it returns True on a weekend if enabled."""
        mock_faker.config['run_settings']['working_hours']['work_on_saturday'] = True
        mock_datetime = mocker.patch('vary_history.datetime')
        mock_datetime.now.return_value = datetime.datetime(2025, 1, 4, 14, 0) # A Saturday
        mocker.patch('vary_history.random.random', return_value=0.3) # Above skip_run_chance
        assert mock_faker.is_time_to_work() is True

    def test_skip_run_chance_triggers(self, mock_faker, mocker):
        """Test that it returns False if the random skip chance is met."""
        mock_datetime = mocker.patch('vary_history.datetime')
        mock_datetime.now.return_value = datetime.datetime(2025, 1, 6, 14, 0) # A Monday
        mocker.patch('vary_history.random.random', return_value=0.1) # Below skip_run_chance of 0.2
        assert mock_faker.is_time_to_work() is False

    def test_working_hours_disabled(self, mock_faker, mocker):
        """Test that it returns True if working hours are disabled."""
        mock_faker.config['run_settings']['working_hours']['enabled'] = False
        mock_datetime = mocker.patch('vary_history.datetime')
        mock_datetime.now.return_value = datetime.datetime(2025, 1, 5, 2, 0) # A Sunday, outside hours
        mocker.patch('vary_history.random.random', return_value=0.9) # High skip chance
        assert mock_faker.is_time_to_work() is True


class TestConfigHandling:

    def test_load_config_exists(self, mocker):
        """Test that config is loaded correctly if the file exists."""
        mock_config_data = {"key": "value"}
        mocker.patch('os.path.exists', return_value=True)
        mocker.patch('builtins.open', mocker.mock_open(read_data=json.dumps(mock_config_data)))
        # We test the private method directly
        faker = MagicMock() # Use a generic mock to call the method
        config = GitHistoryFaker._load_config(faker)
        assert config == mock_config_data

    def test_load_config_not_exists(self, mocker):
        """Test that it returns None if the config file does not exist."""
        mocker.patch('os.path.exists', return_value=False)
        faker = MagicMock()
        config = GitHistoryFaker._load_config(faker)
        assert config is None

    def test_init_no_config_exits(self, mocker):
        """Test that GitHistoryFaker exits if the config file is not found."""
        mocker.patch('os.path.exists', return_value=False)
        # Configure the mock to raise SystemExit when called, like the real sys.exit does.
        mock_exit = mocker.patch('sys.exit', side_effect=SystemExit(1))

        with pytest.raises(SystemExit) as e:
            # The sys.exit call is what we want to test for.
            # We wrap the constructor call in a context manager that catches the SystemExit.
            GitHistoryFaker()

        # Check that sys.exit was called with the correct exit code
        mock_exit.assert_called_once_with(1)
        # Optionally, check the exception value from pytest.raises
        assert e.type == SystemExit
        assert e.value.code == 1


class TestBackfill:

    def test_backfill_dry_run_output(self, mocker, capsys):
        """
        Tests the backfill command in dry-run mode, asserting on the stdout.
        This provides a good functional test of the commit generation logic
        without needing to mock subprocess calls.
        """
        mock_config = {
            "commit_persona": {
                "author": {"name": "Test User", "email": "test@example.com"},
                "commit_messages": ["feat: Test feature", "fix: Test fix"]
            },
            "backfill_settings": {
                # Use a small, predictable date range
                "start_date": "2025-01-01",
                "end_date": "2025-01-02",
                # Set frequency to 1.0 to guarantee commits on both days
                "commit_frequency_per_day": 1.0
            },
            "commit_clustering": {
                "enabled": True,
                # Force a predictable number of commits
                "min_commits_per_cluster": 2,
                "max_commits_per_cluster": 2
            }
        }

        with patch.object(GitHistoryFaker, '_load_config', return_value=mock_config):
            faker = GitHistoryFaker()
            faker.run_backfill(
                start_date=mock_config['backfill_settings']['start_date'],
                end_date=mock_config['backfill_settings']['end_date'],
                dry_run=True
            )

        captured = capsys.readouterr()

        # We expect 2 days * 2 commits/day = 4 commit messages
        assert captured.out.count("[DRY RUN] Would create commit") == 4

        # Check that one of the expected commit messages is present
        assert "feat: Test feature" in captured.out or "fix: Test fix" in captured.out

        # Check that the final summary line is present
        assert "--- Dry Run Complete. No history was changed. ---" in captured.out
