#!/usr/bin/env python3
"""
Test strategy that will timeout to verify the timeout detection.
"""

import random
import time
from typing import List

import chess

from chess_arena_client.strategy_base import StrategyBase


class Strategy(StrategyBase):
    """
    A test strategy that artificially delays to trigger timeout detection.
    """

    def choose_move(self, board: chess.Board, legal_moves: List[str], player_color: str) -> str:
        # Sleep for longer than the search time to trigger timeout
        time.sleep(self.search_time + 0.5)

        # Return a valid move
        return random.choice(legal_moves)
