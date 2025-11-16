#!/usr/bin/env python3
"""
Unit tests for the chess arena client tester module.
"""

import os
import sys
import unittest
from unittest.mock import Mock, mock_open, patch

# Add the project root to the path so we can import the module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Change to the project directory so relative imports work
original_cwd = os.getcwd()
os.chdir(project_root)

try:
    from chess_arena_client.tester import load_test_data, run_test_case
finally:
    os.chdir(original_cwd)


class TestTester(unittest.TestCase):
    """Test cases for the tester module."""

    def test_load_test_data_success(self):
        """Test successful loading of test data."""
        # Create mock JSONL content
        mock_content = (
            '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", '
            '"legal_moves": ["e4", "d4"], "player_color": "white"}\n'
        )
        mock_content += (
            '{"fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1", '
            '"legal_moves": ["e5", "d5"], "player_color": "black"}\n'
        )

        with patch("builtins.open", mock_open(read_data=mock_content)):
            test_cases = load_test_data("fake_path.jsonl")
            self.assertEqual(len(test_cases), 2)
            self.assertEqual(test_cases[0]["fen"], "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            self.assertEqual(test_cases[0]["legal_moves"], ["e4", "d4"])
            self.assertEqual(test_cases[0]["player_color"], "white")

    def test_load_test_data_empty_lines(self):
        """Test loading test data with empty lines."""
        # Create mock JSONL content with empty lines
        mock_content = (
            '{"fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", '
            '"legal_moves": ["e4", "d4"], "player_color": "white"}\n'
        )
        mock_content += '\n'  # Empty line
        mock_content += (
            '{"fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1", '
            '"legal_moves": ["e5", "d5"], "player_color": "black"}\n'
        )

        with patch("builtins.open", mock_open(read_data=mock_content)):
            test_cases = load_test_data("fake_path.jsonl")
            self.assertEqual(len(test_cases), 2)  # Empty line should be skipped

    def test_run_test_case_success(self):
        """Test successful execution of a test case."""
        # Create a mock strategy
        mock_strategy = Mock()
        mock_strategy.choose_move.return_value = "e4"
        mock_strategy.search_time = 5.0

        # Create a test case
        test_case = {
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "legal_moves": ["e4", "d4"],
            "player_color": "white"
        }

        # Run the test case
        test_passed, timeout_occurred = run_test_case(mock_strategy, test_case, 1, 0, 1, 0)
        self.assertTrue(test_passed)
        mock_strategy.choose_move.assert_called_once()

    def test_run_test_case_failure(self):
        """Test failed execution of a test case."""
        # Create a mock strategy that returns an illegal move
        mock_strategy = Mock()
        mock_strategy.choose_move.return_value = "illegal_move"

        # Create a test case
        test_case = {
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "legal_moves": ["e4", "d4"],
            "player_color": "white"
        }

        # Run the test case
        test_passed, timeout_occurred = run_test_case(mock_strategy, test_case, 1, 0, 1, 0)
        self.assertFalse(test_passed)

    def test_run_test_case_exception(self):
        """Test execution of a test case that raises an exception."""
        # Create a mock strategy that raises an exception
        mock_strategy = Mock()
        mock_strategy.choose_move.side_effect = Exception("Test exception")
        # Mock the search_time attribute
        mock_strategy.search_time = 5.0

        # Create a test case
        test_case = {
            "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            "legal_moves": ["e4", "d4"],
            "player_color": "white"
        }

        # Run the test case
        test_passed, timeout_occurred = run_test_case(mock_strategy, test_case, 1, 0, 1, 0)
        self.assertFalse(test_passed)


if __name__ == '__main__':
    unittest.main()
