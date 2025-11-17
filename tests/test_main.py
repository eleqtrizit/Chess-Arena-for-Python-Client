#!/usr/bin/env python3
"""
Unit tests for the chess arena client main module.
"""

import os
import sys
import unittest
from unittest.mock import patch

# Add the project root to the path so we can import the module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Change to the project directory so relative imports work
original_cwd = os.getcwd()
os.chdir(project_root)

try:
    import chess

    from chess_arena_client.main import board_pretty_print, load_auth_from_file
finally:
    os.chdir(original_cwd)


class TestMain(unittest.TestCase):
    """Test cases for the main module."""

    def test_load_auth_from_file_success(self):
        """Test successful loading of auth data from file."""
        mock_content = ('{"game_id": "game123", "player_id": "player456", '
                        '"player_color": "white", "auth_token": "token789"}')

        with patch("builtins.open", unittest.mock.mock_open(read_data=mock_content)):
            result = load_auth_from_file("fake_path.json")
            self.assertIsNotNone(result)
            game_id, player_id, player_color, auth_token = result
            self.assertEqual(game_id, "game123")
            self.assertEqual(player_id, "player456")
            self.assertEqual(player_color, "white")
            self.assertEqual(auth_token, "token789")

    def test_load_auth_from_file_missing_fields(self):
        """Test loading auth data with missing fields."""
        mock_content = '{"game_id": "game123", "player_id": "player456"}'

        with patch("builtins.open", unittest.mock.mock_open(read_data=mock_content)):
            result = load_auth_from_file("fake_path.json")
            self.assertIsNone(result)

    def test_board_pretty_print(self):
        """Test board pretty printing doesn't crash."""
        board = chess.Board()
        # Just verify it doesn't raise an exception
        board_pretty_print(board)


if __name__ == '__main__':
    unittest.main()
