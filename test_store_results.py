#!/usr/bin/env python3

import os
import sys

from chess_arena_client.main import ChessClient
from chess_arena_client.strategy_base import StrategyBase

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestStrategy(StrategyBase):
    def choose_move(self, board, legal_moves, player_color):
        # Always choose the first legal move for testing
        return legal_moves[0] if legal_moves else None


# Test the game results functionality
if __name__ == "__main__":
    # Create a test client with the store_result_file parameter
    strategy = TestStrategy(search_time=1.0)
    client = ChessClient(
        server_url="http://localhost:9002",
        strategy=strategy,
        store_result_file="test_results.json"
    )

    # Test loading existing results
    results = client.load_game_results()
    print("Loaded results:", results)

    # Test updating results without timeout
    client.game_id = "test_game_123"
    client.update_game_results("win")

    # Check updated results
    updated_results = client.load_game_results()
    print("Updated results (win):", updated_results)
    print("Wins:", updated_results.get("wins", 0))
    print("Losses:", updated_results.get("losses", 0))
    print("Draws:", updated_results.get("draws", 0))
    print("Timeouts:", updated_results.get("timeouts", 0))
    print("Game IDs:", updated_results.get("game_ids", []))

    # Test updating results with timeout
    client.game_id = "test_game_456"
    client.update_game_results("loss", timeout_occurred=True)

    # Check updated results with timeout
    updated_results = client.load_game_results()
    print("\nUpdated results (loss with timeout):", updated_results)
    print("Wins:", updated_results.get("wins", 0))
    print("Losses:", updated_results.get("losses", 0))
    print("Draws:", updated_results.get("draws", 0))
    print("Timeouts:", updated_results.get("timeouts", 0))
    print("Game IDs:", updated_results.get("game_ids", []))
