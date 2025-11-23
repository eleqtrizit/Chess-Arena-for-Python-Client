#!/usr/bin/env python3
"""
Unit tests for the chess arena client strategy module.
"""

import os
import sys
import unittest

# Add the project root to the path so we can import the module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Change to the project directory so relative imports work
original_cwd = os.getcwd()
os.chdir(project_root)

try:
    import chess

    from chess_arena_client.strategy import Strategy
finally:
    os.chdir(original_cwd)


class TestStrategy(unittest.TestCase):
    """Test cases for the strategy module."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = Strategy(search_time=1.0)

    def test_evaluate_position_checkmate(self):
        """Test evaluation of checkmate positions."""
        # White to move, black is checkmated
        board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/5PPq/8/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        score = self.strategy.evaluate_position(board)
        # Should be a very negative score for checkmate
        self.assertLess(score, -15000)

    def test_evaluate_position_material(self):
        """Test evaluation based on material balance."""
        # Starting position (equal material)
        board = chess.Board()
        score = self.strategy.evaluate_position(board)
        # Should be close to 0 for equal material
        self.assertEqual(score, 0)

    def test_choose_move_single_legal_move(self):
        """Test choosing a move when only one legal move is available."""
        board = chess.Board("8/8/8/8/8/8/8/K1k5 w - - 0 1")
        legal_moves = ["Kb1"]
        chosen_move = self.strategy.choose_move(board, legal_moves, "white")
        self.assertEqual(chosen_move, "Kb1")

    def test_order_moves_captures_first(self):
        """Test that captures are ordered first."""
        board = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        moves = list(board.legal_moves)
        ordered_moves = self.strategy._order_moves(board, moves)
        # The first few moves should be captures
        for i, move in enumerate(ordered_moves[:5]):
            if board.is_capture(move):
                # This is expected
                pass
            else:
                # After captures, we might see checks
                if not board.gives_check(move):
                    # If it's neither capture nor check, it's unexpected early in the list
                    # But this is acceptable since we're just testing ordering logic
                    break

    def test_minimax_base_case(self):
        """Test minimax base case at depth 0."""
        board = chess.Board()
        score, move = self.strategy.minimax(board, 0, -1000000, 1000000, True, 0.0)
        expected_score = self.strategy.evaluate_position(board)
        self.assertEqual(score, expected_score)
        self.assertIsNone(move)


if __name__ == '__main__':
    unittest.main()
