#!/usr/bin/env python3
"""
Test strategy that will fail some tests to verify the output format.
"""

import random
from typing import List

import chess

from chess_arena_client.strategy_base import StrategyBase


class Strategy(StrategyBase):
    """
    A test strategy that randomly returns valid moves for most tests,
    but returns invalid moves for specific test indices to verify output format.
    """

    def choose_move(self, board: chess.Board, legal_moves: List[str], player_color: str) -> str:
        # For test indices 5, 10, 15, etc., return an invalid move to trigger FAIL output
        # We'll check the legal moves to determine which test this might be
        if len(legal_moves) == 20 and "e4" in legal_moves and "d4" in legal_moves:
            # This looks like one of the early tests, let's fail it
            return "invalid_move"

        # For most tests, return a valid move
        return random.choice(legal_moves)
