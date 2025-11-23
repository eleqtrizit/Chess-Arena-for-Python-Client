#!/usr/bin/env python3

import os
import sys

from chess_arena_client.main import ChessClient
from chess_arena_client.strategy_base import StrategyBase

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class DemoStrategy(StrategyBase):
    def choose_move(self, board, legal_moves, player_color):
        # Always choose the first legal move for testing
        return legal_moves[0] if legal_moves else None


# Demo the game results functionality with timeout tracking
if __name__ == "__main__":
    # Create a demo client with the store_result_file parameter
    strategy = DemoStrategy(search_time=1.0)
    client = ChessClient(
        server_url="http://localhost:9002",
        strategy=strategy,
        store_result_file="demo_results.json"
    )

    print("=== Chess Arena Client - Game Results with Timeout Tracking ===\n")

    # Show initial results
    print("Initial game results:")
    initial_results = client.load_game_results()
    print(f"Wins: {initial_results.get('wins', 0)}")
    print(f"Losses: {initial_results.get('losses', 0)}")
    print(f"Draws: {initial_results.get('draws', 0)}")
    print(f"Timeouts: {initial_results.get('timeouts', 0)}")
    print(f"Games played: {len(initial_results.get('game_ids', []))}")
    print(f"Game IDs: {initial_results.get('game_ids', [])}\n")

    # Simulate a normal win
    print("Simulating a normal win...")
    client.game_id = "demo_game_win"
    client.update_game_results("win")

    results = client.load_game_results()
    print(
        f"Results after win: {results.get('wins', 0)} wins, {results.get('losses', 0)} losses, "
        f"{results.get('timeouts', 0)} timeouts\n")

    # Simulate a loss due to timeout
    print("Simulating a loss due to timeout...")
    client.game_id = "demo_game_timeout_loss"
    client.update_game_results("loss", timeout_occurred=True)

    results = client.load_game_results()
    print(
        f"Results after timeout loss: {results.get('wins', 0)} wins, {results.get('losses', 0)} losses, "
        f"{results.get('timeouts', 0)} timeouts\n")

    # Simulate a draw
    print("Simulating a draw...")
    client.game_id = "demo_game_draw"
    client.update_game_results("draw")

    results = client.load_game_results()
    print(
        f"Results after draw: {results.get('wins', 0)} wins, {results.get('losses', 0)} losses, "
        f"{results.get('draws', 0)} draws, {results.get('timeouts', 0)} timeouts\n")

    # Final summary
    print("=== Final Results ===")
    final_results = client.load_game_results()
    print(f"Wins: {final_results.get('wins', 0)}")
    print(f"Losses: {final_results.get('losses', 0)}")
    print(f"Draws: {final_results.get('draws', 0)}")
    print(f"Timeouts: {final_results.get('timeouts', 0)}")
    win_rate = (final_results.get('wins', 0) /
                max(1, final_results.get('wins', 0) + final_results.get('losses', 0) +
                    final_results.get('draws', 0)) * 100)
    print(f"Win rate: {win_rate:.1f}%")
    timeout_rate = (final_results.get('timeouts', 0) /
                    max(1, final_results.get('losses', 0)) * 100)
    print(f"Timeout rate: {timeout_rate:.1f}% of losses")
    print(f"Total games: {len(final_results.get('game_ids', []))}")
    print(f"Game IDs: {final_results.get('game_ids', [])}")
