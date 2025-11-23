#!/usr/bin/env python3
"""
Chess client for Chess Arena server.

Handles WebSocket communication, matchmaking, and game management.
Strategy for move selection is injected as a dependency.
"""

import argparse
import asyncio
import glob
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

# Type alias for websocket connection
if TYPE_CHECKING:
    WebSocketConnection = Any

import chess
import websockets
from rich.console import Console

from chess_arena_client.strategy_base import StrategyBase

# Color configuration for board display
BG_COLOR = "grey23"
WHITE_PIECE_COLOR = "bold white"
WHITE_PIECE_COLOR_BG = "black"
BLACK_PIECE_COLOR = "black"
BLACK_PIECE_COLOR_BG = "white"
BORDER_COLOR = "cyan"
RANK_FILE_COLOR = "cyan"

# Unicode chess piece symbols
PIECE_SYMBOLS = {
    'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',
    'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙',
    ' ': ' '
}
USE_PIECE_SYMBOLS = False

console = Console()


def board_pretty_print(board: chess.Board) -> None:
    """
    Print a pretty chess board with Unicode pieces and colored display.

    :param board: Chess board to display
    :type board: chess.Board
    """
    board_state = []
    for rank in range(7, -1, -1):
        row = []
        for file in range(8):
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            if piece:
                symbol = piece.symbol()
                row.append(symbol)
            else:
                row.append(' ')
        board_state.append(row)

    # Print top border
    console.print(f"[{BORDER_COLOR}] +---+---+---+---+---+---+---+---+[/{BORDER_COLOR}]")

    # Print each rank
    for rank_idx, row in enumerate(board_state):
        rank_number = 8 - rank_idx
        line_parts = [f"[{RANK_FILE_COLOR}]{rank_number}[/{RANK_FILE_COLOR}]"]

        for piece_char in row:
            unicode_piece = PIECE_SYMBOLS.get(piece_char, ' ') if USE_PIECE_SYMBOLS else piece_char
            if piece_char.isupper():
                # White pieces
                piece_display = (
                    f"[{WHITE_PIECE_COLOR} on {WHITE_PIECE_COLOR_BG}] {unicode_piece} "
                    f"[/{WHITE_PIECE_COLOR} on {WHITE_PIECE_COLOR_BG}]"
                )
            elif piece_char.islower():
                # Black pieces
                piece_display = (
                    f"[{BLACK_PIECE_COLOR} on {BLACK_PIECE_COLOR_BG}] {unicode_piece} "
                    f"[/{BLACK_PIECE_COLOR} on {BLACK_PIECE_COLOR_BG}]"
                )
            else:
                # Empty square
                piece_display = "   "

            line_parts.append(f"[{BORDER_COLOR}]|[/{BORDER_COLOR}]")
            line_parts.append(piece_display)

        line_parts.append(f"[{BORDER_COLOR}]|[/{BORDER_COLOR}]")
        console.print("".join(line_parts))

        # Print horizontal border
        console.print(f"[{BORDER_COLOR}] +---+---+---+---+---+---+---+---+[/{BORDER_COLOR}]")

    # Print file letters
    file_letters = "    a   b   c   d   e   f   g   h"
    console.print(f"[{RANK_FILE_COLOR}]{file_letters}[/{RANK_FILE_COLOR}]")


def load_auth_from_file(file_path: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Load auth data from a JSON file.

    :param file_path: Path to the auth file
    :type file_path: str
    :return: Tuple of (game_id, player_id, player_color, auth_token) if found, None otherwise
    :rtype: Optional[Tuple[str, str, str, str]]
    """
    try:
        with open(file_path, 'r') as f:
            auth_data = json.load(f)

        game_id = auth_data.get("game_id")
        player_id = auth_data.get("player_id")
        player_color = auth_data.get("player_color")
        auth_token = auth_data.get("auth_token")

        if not all([game_id, player_id, player_color, auth_token]):
            console.print(f"[red]Error: Missing required fields in {file_path}[/red]")
            return None

        console.print(f"[cyan]Loaded auth token for player:[/cyan] {player_id}")
        console.print(f"[cyan]Game ID:[/cyan] {game_id}")
        console.print(f"[cyan]Color:[/cyan] {player_color}")
        return game_id, player_id, player_color, auth_token

    except FileNotFoundError:
        console.print(f"[red]Error: Auth file not found: {file_path}[/red]")
        return None
    except json.JSONDecodeError:
        console.print(f"[red]Error: Invalid JSON in auth file: {file_path}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]Error reading auth file:[/red] {e}")
        return None


def get_latest_auth() -> Optional[Tuple[str, str, str, str]]:
    """
    Find and load the most recent auth token file.

    :return: Tuple of (game_id, player_id, player_color, auth_token) if found, None otherwise
    :rtype: Optional[Tuple[str, str, str, str]]
    """
    auth_files = glob.glob(".*_auth")
    if not auth_files:
        return None

    # Sort by modification time, newest first
    auth_files.sort(key=os.path.getmtime, reverse=True)
    latest_file = auth_files[0]

    try:
        # Parse filename: .{player_id}_{game_id}_{color}_{auth_token}_auth
        filename = Path(latest_file).name
        if not filename.startswith('.') or not filename.endswith('_auth'):
            return None

        # Remove leading '.' and trailing '_auth'
        content = filename[1:-5]
        parts = content.split('_', 3)

        if len(parts) != 4:
            return None

        player_id, game_id, player_color, auth_token = parts
        console.print(f"[cyan]Found auth token for player:[/cyan] {player_id}")
        console.print(f"[cyan]Game ID:[/cyan] {game_id}")
        console.print(f"[cyan]Color:[/cyan] {player_color}")
        return game_id, player_id, player_color, auth_token

    except Exception as e:
        console.print(f"[red]Error reading auth file:[/red] {e}")
        return None


class ChessClient:
    """
    Chess client for WebSocket-based Chess Arena server.

    Handles connection management, matchmaking, and game state synchronization.
    Move selection is delegated to an injected Strategy implementation.

    :param server_url: Base WebSocket URL of the Chess Arena server
    :type server_url: str
    :param strategy: Strategy implementation for move selection
    :type strategy: StrategyBase
    :param continue_game: Whether to continue from an existing game
    :type continue_game: bool
    :param auth_file: Optional path to JSON file for storing/loading auth token
    :type auth_file: Optional[str]
    :param max_reconnect_attempts: Maximum number of reconnection attempts
    :type max_reconnect_attempts: int
    :param reconnect_delay: Initial delay between reconnection attempts in seconds
    :type reconnect_delay: float
    """

    # Task attributes
    _receive_task: Optional[asyncio.Task]
    _heartbeat_task: Optional[asyncio.Task]
    _health_monitor_task: Optional[asyncio.Task]

    def __init__(self, server_url: str, strategy: StrategyBase, continue_game: bool = False,
                 auth_file: Optional[str] = None, max_reconnect_attempts: int = 5,
                 reconnect_delay: float = 5.0, timeout: Optional[float] = None,
                 store_result_file: Optional[str] = None, aggressive_reconnect: bool = False):
        self.server_url = server_url.replace('http://', 'ws://').replace('https://', 'wss://')
        self.strategy = strategy
        self.continue_game = continue_game
        self.auth_file = auth_file
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.timeout = timeout
        self.game_id: Optional[str] = None
        self.player_id: Optional[str] = None
        self.auth_token: Optional[str] = None
        self.player_color: Optional[str] = None
        self.local_board = chess.Board()
        self.websocket: Optional['WebSocketConnection'] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.store_result_file: Optional[str] = store_result_file
        self.aggressive_reconnect = aggressive_reconnect

        # Task attributes
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._health_monitor_task: Optional[asyncio.Task] = None

        # Move timing tracking
        self.last_move_time: float = 0.0
        self.move_exceeded_time_limit: bool = False

        # Health check attributes
        self.last_heartbeat_response = time.time()
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 60   # seconds
        self.health_check_enabled = True

    async def reconnect_and_sync(self, reconnect_attempt: int = 0) -> bool:
        """
        Reconnect to the WebSocket and sync board state.

        :param reconnect_attempt: Current reconnection attempt number
        :type reconnect_attempt: int
        :return: True if it's our turn after syncing, False otherwise
        :rtype: bool
        :raises Exception: If reconnection fails after max attempts
        """
        try:
            # Close existing websocket if it exists
            if self.websocket:
                await self.websocket.close()

            # Reset health check attributes
            self.last_heartbeat_response = time.time()
            self.health_check_enabled = True

            # Reconnect to WebSocket
            console.print("[dim]Reconnecting to server...[/dim]")
            async with websockets.connect(self.server_url + "/ws") as websocket:
                self.websocket = websocket

                # Restart background tasks
                # Cancel existing tasks first
                if self._receive_task is not None and not self._receive_task.done():
                    self._receive_task.cancel()
                if self._heartbeat_task is not None and not self._heartbeat_task.done():
                    self._heartbeat_task.cancel()
                if self._health_monitor_task is not None and not self._health_monitor_task.done():
                    self._health_monitor_task.cancel()

                # Start new background tasks
                self._receive_task = asyncio.create_task(self.receive_messages())
                self._heartbeat_task = asyncio.create_task(self.send_heartbeat())
                self._health_monitor_task = asyncio.create_task(self.monitor_connection_health())

                # Sync board state
                return await self.sync_board_state(reconnect_attempt)

        except Exception as e:
            if reconnect_attempt < self.max_reconnect_attempts:
                console.print(f"[yellow]⚠ Reconnection failed:[/yellow] {str(e)}")
                console.print(f"[yellow]Attempt {reconnect_attempt + 1}/{self.max_reconnect_attempts}...[/yellow]")
                # Exponential backoff with jitter to prevent thundering herd
                import random
                jitter = random.uniform(0, self.reconnect_delay * 0.1)  # 10% jitter
                delay = self.reconnect_delay * (2 ** reconnect_attempt) + jitter
                console.print(f"[dim]Waiting {delay:.1f}s before next attempt...[/dim]")
                await asyncio.sleep(delay)
                # Try again
                return await self.reconnect_and_sync(reconnect_attempt + 1)
            else:
                # Even after max attempts, keep trying indefinitely for critical
                # operations if aggressive reconnect is enabled
                if self.aggressive_reconnect:
                    console.print(
                        f"[red]✗ Reconnection failed after {self.max_reconnect_attempts} attempts: {str(e)}[/red]")
                    console.print(
                        "[yellow]⚠ Continuing with infinite retry for critical "
                        "operations (aggressive mode)...[/yellow]")
                    # Wait longer but keep trying indefinitely
                    import random
                    jitter = random.uniform(0, self.reconnect_delay * 0.1)  # 10% jitter
                    delay = self.reconnect_delay * (2 ** (self.max_reconnect_attempts - 1)) + jitter
                    console.print(f"[dim]Waiting {delay:.1f}s before next attempt (infinite retry)...[/dim]")
                    await asyncio.sleep(delay)
                    # Try again with reset attempt counter to avoid overflow
                    return await self.reconnect_and_sync(0)
                else:
                    raise Exception(f"Reconnection failed after {self.max_reconnect_attempts} attempts: {str(e)}")

    async def send_message(self, message: Dict[str, Any]) -> None:
        """
        Send a message via WebSocket.

        :param message: Message dictionary to send
        :type message: Dict[str, Any]
        """
        if self.websocket:
            await self.websocket.send(json.dumps(message))

    async def send_heartbeat(self) -> None:
        """
        Send periodic heartbeat messages to maintain connection health.
        """
        while self.websocket and self.health_check_enabled:
            try:
                await self.send_message({"type": "health_check"})
                await asyncio.sleep(self.heartbeat_interval)
            except Exception:
                break

    async def monitor_connection_health(self) -> None:
        """
        Monitor connection health and detect timeouts.
        """
        # Track consecutive timeout warnings
        consecutive_timeouts = 0
        max_consecutive_timeouts = 3  # Allow some grace period before forcing reconnection

        while self.websocket and self.health_check_enabled:
            try:
                current_time = time.time()
                time_since_last_heartbeat = current_time - self.last_heartbeat_response

                # Warning threshold - warn user before actual timeout
                warning_threshold = self.heartbeat_timeout * 0.7  # 70% of timeout period

                if time_since_last_heartbeat > warning_threshold:
                    consecutive_timeouts += 1
                    if consecutive_timeouts == 1:
                        console.print(
                            f"[yellow]⚠ Connection health warning - no response for health check "
                            f"({time_since_last_heartbeat:.1f}s)[/yellow]")
                    elif consecutive_timeouts <= max_consecutive_timeouts:
                        console.print(
                            f"[yellow]⚠ Still waiting for server response "
                            f"({time_since_last_heartbeat:.1f}s elapsed)[/yellow]")

                    # Force reconnection after multiple consecutive timeouts
                    if time_since_last_heartbeat > self.heartbeat_timeout:
                        if consecutive_timeouts >= max_consecutive_timeouts:
                            console.print(
                                f"[red]✗ Server connection timeout - no response for health check "
                                f"({time_since_last_heartbeat:.1f}s)[/red]")
                            # Disable health checks to prevent further messages
                            self.health_check_enabled = False
                            # Close the websocket to trigger reconnection
                            if self.websocket:
                                await self.websocket.close()
                            break
                        else:
                            # Send additional health check to try to wake up the connection
                            try:
                                await self.send_message({"type": "health_check"})
                                console.print("[dim]Sent additional health check...[/dim]")
                            except Exception:
                                pass  # Ignore send errors
                else:
                    # Reset consecutive timeout counter when we get responses
                    consecutive_timeouts = 0

                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception:
                break

    async def receive_messages(self) -> None:
        """
        Background task to receive messages from WebSocket.

        :raises Exception: If WebSocket connection fails
        """
        if not self.websocket:
            return

        try:
            async for message in self.websocket:
                data = json.loads(message)

                # Handle server-initiated ping messages
                if data.get("type") == "ping":
                    # Respond immediately with pong
                    await self.send_message({"type": "pong"})
                    # Update heartbeat timestamp
                    self.last_heartbeat_response = time.time()
                    continue

                # Update heartbeat timestamp for any message
                self.last_heartbeat_response = time.time()

                await self.message_queue.put(data)
        except websockets.exceptions.ConnectionClosed:
            console.print("[red]✗ Connection to server closed[/red]")

    def save_auth_token(self) -> None:
        """
        Save auth token to file for reconnection.

        :raises Exception: If save fails
        """
        if not all([self.player_id, self.game_id, self.player_color, self.auth_token]):
            return

        if self.auth_file:
            # Save as JSON to custom file
            auth_data = {
                "game_id": self.game_id,
                "player_id": self.player_id,
                "player_color": self.player_color,
                "auth_token": self.auth_token
            }
            try:
                with open(self.auth_file, 'w') as f:
                    json.dump(auth_data, f, indent=2)
                console.print(f"[green]✓[/green] Auth token saved to {self.auth_file}")
            except Exception as e:
                console.print(f"[yellow]⚠ Failed to save auth token:[/yellow] {e}")
        else:
            # Legacy: save as empty file with encoded filename
            filename = f".{self.player_id}_{self.game_id}_{self.player_color}_{self.auth_token}_auth"
            try:
                Path(filename).touch()
                console.print(f"[green]✓[/green] Auth token saved to {filename}")
            except Exception as e:
                console.print(f"[yellow]⚠ Failed to save auth token:[/yellow] {e}")

    def load_game_results(self) -> Dict[str, Any]:
        """
        Load game results from file.

        :return: Game results dictionary
        :rtype: Dict[str, Any]
        """
        if not self.store_result_file:
            return {}

        try:
            with open(self.store_result_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # File doesn't exist yet, return empty dict
            return {}
        except json.JSONDecodeError:
            console.print(f"[yellow]⚠ Invalid JSON in results file: {self.store_result_file}[/yellow]")
            return {}
        except Exception as e:
            console.print(f"[yellow]⚠ Failed to load game results:[/yellow] {e}")
            return {}

    def save_game_results(self, results: Dict[str, Any]) -> None:
        """
        Save game results to file.

        :param results: Game results dictionary
        :type results: Dict[str, Any]
        :raises Exception: If save fails
        """
        if not self.store_result_file:
            return

        try:
            with open(self.store_result_file, 'w') as f:
                json.dump(results, f, indent=2)
            console.print(f"[green]✓[/green] Game results saved to {self.store_result_file}")
        except Exception as e:
            console.print(f"[yellow]⚠ Failed to save game results:[/yellow] {e}")

    def update_game_results(self, game_outcome: str, timeout_occurred: bool = False) -> None:
        """
        Update game results file with the outcome of the current game.

        :param game_outcome: Outcome of the game ('win', 'loss', 'draw')
        :type game_outcome: str
        :param timeout_occurred: Whether the game was lost due to timeout
        :type timeout_occurred: bool
        """
        if not self.store_result_file or not self.game_id:
            return

        # Load existing results
        results = self.load_game_results()

        # Initialize if empty
        if not results:
            results = {
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "timeouts": 0,
                "game_ids": []
            }

        # Update counts based on outcome
        if game_outcome == "win":
            results["wins"] = results.get("wins", 0) + 1
        elif game_outcome == "loss":
            results["losses"] = results.get("losses", 0) + 1
        elif game_outcome == "draw":
            results["draws"] = results.get("draws", 0) + 1

        # Track timeouts
        if timeout_occurred:
            results["timeouts"] = results.get("timeouts", 0) + 1

        # Add game ID to list if not already present
        if "game_ids" not in results:
            results["game_ids"] = []

        if self.game_id not in results["game_ids"]:
            results["game_ids"].append(self.game_id)

        # Save updated results
        self.save_game_results(results)

    async def sync_board_state(self, reconnect_attempt: int = 0) -> bool:
        """
        Request and sync current board state from server.

        :param reconnect_attempt: Current reconnection attempt number (for backoff calculation)
        :type reconnect_attempt: int
        :return: True if it's our turn after syncing, False otherwise
        :rtype: bool
        :raises Exception: If sync fails after max reconnection attempts
        """
        try:
            await self.send_message({
                "type": "get_board",
                "game_id": self.game_id,
                "player_id": self.player_id,
                "auth_token": self.auth_token
            })

            # Wait for board_state response
            while True:
                msg = await self.message_queue.get()
                if msg.get("type") == "board_state":
                    fen = msg.get("fen")
                    if fen:
                        self.local_board.set_fen(fen)
                    current_turn = msg.get("current_turn")
                    # Check if it's our turn
                    is_our_turn = current_turn == self.player_color
                    return is_our_turn
                elif msg.get("type") == "error":
                    error_message = msg.get('message', 'Unknown error')
                    # Check if this is a game cancellation error that might be recoverable
                    if "Game cancelled" in error_message and "not responding" in error_message:
                        if reconnect_attempt < self.max_reconnect_attempts:
                            console.print(f"[yellow]⚠ Game sync error:[/yellow] {error_message}")
                            console.print(
                                f"[yellow]Attempt {reconnect_attempt + 1}/"
                                f"{self.max_reconnect_attempts} to reconnect...[/yellow]")
                            # Exponential backoff
                            delay = self.reconnect_delay * (2 ** reconnect_attempt)
                            console.print(f"[dim]Waiting {delay:.1f}s before reconnect attempt...[/dim]")
                            await asyncio.sleep(delay)
                            # Try to reconnect
                            return await self.reconnect_and_sync(reconnect_attempt + 1)
                        else:
                            raise Exception(
                                f"Board sync error after {self.max_reconnect_attempts} attempts: {error_message}")
                    else:
                        # For other errors, don't attempt reconnection
                        raise Exception(f"Board sync error: {error_message}")
                await self.message_queue.put(msg)  # Put back if not for us
                await asyncio.sleep(0.01)
        except Exception as e:
            # If we get a connection error during sync, try to reconnect
            if reconnect_attempt < self.max_reconnect_attempts:
                console.print(f"[yellow]⚠ Connection error during sync:[/yellow] {str(e)}")
                console.print(
                    f"[yellow]Attempt {reconnect_attempt + 1}/{self.max_reconnect_attempts} to reconnect...[/yellow]")
                # Exponential backoff
                delay = self.reconnect_delay * (2 ** reconnect_attempt)
                console.print(f"[dim]Waiting {delay:.1f}s before reconnect attempt...[/dim]")
                await asyncio.sleep(delay)
                # Try to reconnect
                return await self.reconnect_and_sync(reconnect_attempt + 1)
            else:
                raise Exception(f"Board sync failed after {self.max_reconnect_attempts} "
                                f"attempts: {str(e)}")

    async def run(self) -> None:
        """
        Main game loop - join queue via WebSocket, wait for opponent, and make moves.

        :raises Exception: If critical errors occur
        """
        console.print("[bold green]♟ Chess client started[/bold green]")
        console.print(f"[cyan]Search time:[/cyan] {self.strategy.search_time}s")
        console.print(f"[cyan]Server:[/cyan] {self.server_url}")

        try:
            async with websockets.connect(self.server_url + "/ws") as websocket:
                self.websocket = websocket

                # Start background task to receive messages
                self._receive_task = asyncio.create_task(self.receive_messages())

                # Start heartbeat task for connection health
                self._heartbeat_task = asyncio.create_task(self.send_heartbeat())

                # Start connection health monitoring task
                self._health_monitor_task = asyncio.create_task(self.monitor_connection_health())

                # If continuing a game, skip matchmaking
                if self.continue_game and self.game_id and self.player_id and self.auth_token:
                    console.print("\n[green]✓ Reconnecting to existing game...[/green]")
                    console.print(f"[cyan]Game ID:[/cyan] [bold]{self.game_id}[/bold]")
                    console.print(f"[cyan]Player ID:[/cyan] [bold]{self.player_id}[/bold]")
                    match_found = True
                else:
                    # Join matchmaking queue
                    console.print("\n[yellow]⏳ Joining matchmaking queue...[/yellow]")
                    console.print("[dim]Waiting for opponent...[/dim]")

                    await self.send_message({"type": "join_queue"})

                    # Wait for match
                    match_found = False

                # Track queue retry attempts
                queue_retry_count = 0
                max_queue_retries = 5  # Maximum retries for queue timeout

                while not match_found:
                    try:
                        if self.timeout is not None:
                            msg = await asyncio.wait_for(self.message_queue.get(), timeout=self.timeout)
                        else:
                            msg = await self.message_queue.get()
                    except asyncio.TimeoutError:
                        # Instead of exiting, try rejoining queue with progressive timeout
                        queue_retry_count += 1
                        if queue_retry_count <= max_queue_retries:
                            console.print(
                                f"[yellow]⚠ Queue timeout ({self.timeout} seconds elapsed), "
                                f"retrying... (attempt {queue_retry_count}/{max_queue_retries})[/yellow]")
                            # Progressive timeout - increase wait time on each retry
                            retry_delay = self.reconnect_delay * queue_retry_count
                            console.print(f"[dim]Waiting {retry_delay:.1f}s before rejoining queue...[/dim]")
                            await asyncio.sleep(retry_delay)

                            # Rejoin queue
                            await self.send_message({"type": "join_queue"})
                            console.print("[dim]Rejoined matchmaking queue...[/dim]")

                            # Increase timeout for next attempt to be more patient
                            if self.timeout is not None:
                                self.timeout = min(self.timeout * 1.5, 300.0)  # Cap at 5 minutes
                        else:
                            console.print(
                                f"[red]✗ Queue timeout after {max_queue_retries} retries "
                                f"({self.timeout} seconds elapsed)[/red]")
                            return  # Exit the run method, which will terminate the client

                    msg_type = msg.get("type")

                    if msg_type == "match_found":
                        self.game_id = msg["game_id"]
                        self.player_id = msg["player_id"]
                        self.auth_token = msg["auth_token"]
                        self.player_color = msg["assigned_color"]
                        first_move_player = msg["first_move"]
                        server_search_time = msg.get("server_search_time")

                        console.print("[green]✓ Match found![/green]")
                        console.print(f"[cyan]Game ID:[/cyan] [bold]{self.game_id}[/bold]")
                        console.print(f"[cyan]Player ID:[/cyan] [bold]{self.player_id}[/bold]")
                        console.print(f"[cyan]Color:[/cyan] [bold]{self.player_color}[/bold]")

                        # Handle server-enforced search time
                        if server_search_time is not None:
                            console.print(f"[yellow]Server requires search time: {server_search_time}s[/yellow]")
                            client_search_time = self.strategy.search_time

                            if client_search_time < server_search_time:
                                console.print(
                                    f"[red bold]WARNING: You have selected a search time ({client_search_time}s) "
                                    f"lower than the server's ({server_search_time}s)![/red bold]"
                                )

                            # Use minimum of client and server time
                            final_search_time = min(client_search_time, server_search_time)
                            if final_search_time != client_search_time:
                                console.print(
                                    f"[yellow]Using server's search time: {final_search_time}s "
                                    f"(was {client_search_time}s)[/yellow]"
                                )
                                self.strategy.search_time = final_search_time

                        # Save auth token for reconnection
                        self.save_auth_token()

                        if self.player_id == first_move_player:
                            console.print("[green]You move first (White)[/green]")
                        else:
                            console.print("[yellow]Opponent moves first (White)[/yellow]")

                        match_found = True

                    elif msg_type == "queue_timeout":
                        console.print("[red]✗ Queue timeout, retrying...[/red]")
                        await asyncio.sleep(1)
                        await self.send_message({"type": "join_queue"})

                # Sync board state
                is_our_turn = await self.sync_board_state()
                console.print("[green]✓[/green] Board synced with server")

                # Main game loop
                move_count = 0
                game_over = False

                # Reset move timing tracking for new game
                self.last_move_time = 0.0
                self.move_exceeded_time_limit = False

                # If reconnecting and it's our turn, make a move
                if self.continue_game and is_our_turn and not self.local_board.is_game_over():
                    legal_moves = [self.local_board.san(m) for m in self.local_board.legal_moves]
                    if legal_moves:
                        console.print(
                            f"\n[bold magenta]━━━ Move {move_count + 1} ({self.player_color}) ━━━[/bold magenta]")
                        console.print(f"[cyan]Game ID:[/cyan] [bold]{self.game_id}[/bold]")
                        console.print(f"[cyan]Client:[/cyan] [bold]{self.player_id}[/bold]")
                        console.print(f"[dim]Legal moves ({len(legal_moves)}):[/dim] {', '.join(legal_moves[:10])}...")

                        move_start = time.time()
                        # Ensure player_color is not None (should be set after connecting to a game)
                        player_color = self.player_color or "white"  # fallback to "white" if somehow None
                        chosen_move = self.strategy.choose_move(self.local_board, legal_moves, player_color)
                        move_time = time.time() - move_start

                        # Check if move took too long
                        if move_time > self.strategy.search_time:
                            console.print(
                                f"[bold orange]⚠ WARNING: Move took {move_time:.2f}s, "
                                f"exceeding time limit of {self.strategy.search_time:.2f}s![/bold orange]"
                            )

                        console.print(
                            f"[bold green]➜ Chosen move:[/bold green] "
                            f"[bold white]{chosen_move}[/bold white] [dim](time: {move_time:.2f}s)[/dim]"
                        )

                        # Track if this move was close to or exceeded the time limit
                        self.last_move_time = move_time
                        self.move_exceeded_time_limit = move_time > self.strategy.search_time

                        await self.send_message({
                            "type": "make_move",
                            "data": {
                                "game_id": self.game_id,
                                "player_id": self.player_id,
                                "auth_token": self.auth_token,
                                "move": chosen_move
                            }
                        })

                        move_count += 1

                while not game_over:
                    try:
                        msg = await asyncio.wait_for(self.message_queue.get(), timeout=0.1)
                        msg_type = msg.get("type")

                        if msg_type == "move_made":
                            # Update local board
                            fen = msg.get("fen")
                            if fen:
                                self.local_board.set_fen(fen)

                            # Display board
                            console.print()
                            board_pretty_print(self.local_board)

                            if msg.get("game_over"):
                                console.print("\n[bold red]Game over![/bold red]")
                                reason = msg.get("game_over_reason", "Unknown")
                                console.print(f"[yellow]Reason:[/yellow] {reason}")

                                # Determine win/loss
                                if "checkmate" in reason.lower():
                                    # After checkmate, board.turn is the losing side
                                    losing_color = "white" if self.local_board.turn else "black"
                                    if losing_color == self.player_color:
                                        console.print("[bold red]I lost :([/bold red]")
                                        # Check if we lost due to timeout
                                        timeout_occurred = self.move_exceeded_time_limit
                                        self.update_game_results("loss", timeout_occurred)
                                    else:
                                        console.print("[bold green]I won :)[/bold green]")
                                        self.update_game_results("win")
                                elif "stalemate" in reason.lower() or "draw" in reason.lower():
                                    console.print("[yellow]Draw[/yellow]")
                                    # Check if draw was due to timeout
                                    timeout_occurred = self.move_exceeded_time_limit
                                    self.update_game_results("draw", timeout_occurred)

                                game_over = True
                                continue

                            # Check if it's our turn
                            if not self.local_board.is_game_over():
                                current_turn = "white" if self.local_board.turn else "black"
                                if current_turn == self.player_color:
                                    # Our turn - make a move
                                    legal_moves = [self.local_board.san(m) for m in self.local_board.legal_moves]

                                    if not legal_moves:
                                        console.print("[bold red]No legal moves - game over[/bold red]")
                                        game_over = True
                                        continue

                                    console.print(
                                        f"\n[bold magenta]━━━ Move {move_count + 1} "
                                        f"({self.player_color}) ━━━[/bold magenta]"
                                    )
                                    console.print(f"[cyan]Game ID:[/cyan] [bold]{self.game_id}[/bold]")
                                    console.print(f"[cyan]Client:[/cyan] [bold]{self.player_id}[/bold]")
                                    moves_preview = ', '.join(legal_moves[:10])
                                    console.print(f"[dim]Legal moves ({len(legal_moves)}):[/dim] {moves_preview}...")

                                    move_start = time.time()
                                    # Ensure player_color is not None (should be set after connecting to a game)
                                    player_color = self.player_color or "white"  # fallback to "white" if somehow None
                                    chosen_move = self.strategy.choose_move(
                                        self.local_board, legal_moves, player_color)
                                    move_time = time.time() - move_start

                                    # Check if move took too long
                                    if move_time > self.strategy.search_time:
                                        console.print(
                                            f"[bold orange]⚠ WARNING: Move took {move_time:.2f}s, "
                                            f"exceeding time limit of {self.strategy.search_time:.2f}s![/bold orange]"
                                        )

                                    console.print(
                                        f"[bold green]➜ Chosen move:[/bold green] "
                                        f"[bold white]{chosen_move}[/bold white] [dim](time: {move_time:.2f}s)[/dim]"
                                    )

                                    # Track if this move was close to or exceeded the time limit
                                    self.last_move_time = move_time
                                    self.move_exceeded_time_limit = move_time > self.strategy.search_time

                                    # Send move
                                    await self.send_message({
                                        "type": "make_move",
                                        "data": {
                                            "game_id": self.game_id,
                                            "player_id": self.player_id,
                                            "auth_token": self.auth_token,
                                            "move": chosen_move
                                        }
                                    })

                                    move_count += 1

                        elif msg_type == "opponent_disconnected":
                            console.print("[yellow]⚠ Opponent disconnected - waiting for reconnection...[/yellow]")

                        elif msg_type == "game_over":
                            status = msg.get("status")
                            message = msg.get("message", "Game ended")
                            console.print("\n[bold red]Game over![/bold red]")
                            console.print(f"[yellow]{message}[/yellow]")
                            if status == "forfeit":
                                winner = msg.get("winner")
                                if winner == self.player_id:
                                    console.print("[green]✓ You win by forfeit![/green]")
                                    console.print("[bold green]I won :)[/bold green]")
                                    self.update_game_results("win")
                                else:
                                    console.print("[red]✗ You lost by forfeit[/red]")
                                    console.print("[bold red]I lost :([/bold red]")
                                    # Check if forfeit was due to timeout
                                    timeout_occurred = self.move_exceeded_time_limit
                                    self.update_game_results("loss", timeout_occurred)
                            elif status == "disqualified":
                                winner = msg.get("winner")
                                disqualified_player = msg.get("disqualified_player")
                                reason = msg.get("reason", "Time limit exceeded")
                                console.print(f"[red]Disqualification reason: {reason}[/red]")
                                if disqualified_player == self.player_id:
                                    console.print("[red bold]✗ You were disqualified![/red bold]")
                                    console.print("[bold red]I lost :([/red bold]")
                                    # Check if disqualification was due to timeout
                                    timeout_occurred = "time" in reason.lower() or "timeout" in reason.lower()
                                    self.update_game_results("loss", timeout_occurred)
                                else:
                                    console.print("[green]✓ You win by opponent disqualification![/green]")
                                    console.print("[bold green]I won :)[/bold green]")
                                    self.update_game_results("win")
                            game_over = True

                        elif msg_type == "error":
                            error_msg = msg.get("message", "Unknown error")
                            console.print(f"[red]✗ Error:[/red] {error_msg}")

                    except asyncio.TimeoutError:
                        # Check if it's our turn to move initially
                        if self.game_id and not self.local_board.is_game_over():
                            current_turn = "white" if self.local_board.turn else "black"
                            if current_turn == self.player_color and move_count == 0:
                                # Make first move
                                legal_moves = [self.local_board.san(m) for m in self.local_board.legal_moves]

                                console.print(f"\n[bold magenta]━━━ Move 1 ({self.player_color}) ━━━[/bold magenta]")
                                console.print(f"[cyan]Game ID:[/cyan] [bold]{self.game_id}[/bold]")
                                console.print(f"[cyan]Client:[/cyan] [bold]{self.player_id}[/bold]")
                                console.print(
                                    f"[dim]Legal moves ({len(legal_moves)}):[/dim] {', '.join(legal_moves[:10])}...")

                                move_start = time.time()
                                # Ensure player_color is not None (should be set after connecting to a game)
                                player_color = self.player_color or "white"  # fallback to "white" if somehow None
                                chosen_move = self.strategy.choose_move(
                                    self.local_board, legal_moves, player_color)
                                move_time = time.time() - move_start

                                # Check if move took too long
                                if move_time > self.strategy.search_time:
                                    console.print(
                                        f"[bold orange]⚠ WARNING: Move took {move_time:.2f}s, "
                                        f"exceeding time limit of {self.strategy.search_time:.2f}s![/bold orange]"
                                    )

                                console.print(
                                    f"[bold green]➜ Chosen move:[/bold green] [bold white]{chosen_move}[/bold white] "
                                    f"[dim](time: {move_time:.2f}s)[/dim]"
                                )

                                # Track if this move was close to or exceeded the time limit
                                self.last_move_time = move_time
                                self.move_exceeded_time_limit = move_time > self.strategy.search_time

                                await self.send_message({
                                    "type": "make_move",
                                    "data": {
                                        "game_id": self.game_id,
                                        "player_id": self.player_id,
                                        "auth_token": self.auth_token,
                                        "move": chosen_move
                                    }
                                })

                                move_count += 1
                        continue

                # Cancel background tasks
                if self._receive_task is not None and not self._receive_task.done():
                    self._receive_task.cancel()
                if self._heartbeat_task is not None and not self._heartbeat_task.done():
                    self._heartbeat_task.cancel()
                if self._health_monitor_task is not None and not self._health_monitor_task.done():
                    self._health_monitor_task.cancel()

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Client stopped by user[/yellow]")
        except Exception as e:
            console.print(f"[red]✗ Connection error:[/red] {e}")


def load_strategy_from_file(file_path: str, search_time: float) -> StrategyBase:
    """
    Dynamically load a Strategy class from a Python file.

    :param file_path: Path to the strategy file
    :type file_path: str
    :param search_time: Maximum search time per move in seconds
    :type search_time: float
    :return: Strategy instance
    :rtype: StrategyBase
    :raises ImportError: If the strategy file cannot be loaded
    :raises AttributeError: If the Strategy class is not found
    """
    try:
        spec = importlib.util.spec_from_file_location("strategy_module", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["strategy_module"] = module
        spec.loader.exec_module(module)

        if not hasattr(module, 'Strategy'):
            raise AttributeError(f"Strategy class not found in {file_path}")

        strategy_class = getattr(module, 'Strategy')
        return strategy_class(search_time=search_time)
    except Exception as e:
        console.print(f"[red]✗ Error loading strategy from {file_path}:[/red] {e}")
        raise


def main() -> None:
    """
    Parse command-line arguments and start the chess client.
    """
    parser = argparse.ArgumentParser(description='Chess Arena Client - WebSocket Edition')
    parser.add_argument('--search-time', type=float, default=300.0,
                        help='Maximum search time per move in seconds (default: 300.0)')
    parser.add_argument('--host', type=str, default='localhost',
                        help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=9002,
                        help='Server port (default: 9002)')
    parser.add_argument('--continue', dest='continue_game', action='store_true',
                        help='Continue from the most recent saved game using auth token')
    parser.add_argument('--auth-file', type=str, default=None,
                        help='Path to file for storing/loading auth token (JSON format)')
    parser.add_argument('--strategy', type=str, default=None,
                        help='Path to custom strategy file (default: uses built-in strategy.py)')
    parser.add_argument('--max-reconnect-attempts', type=int, default=5,
                        help='Maximum number of reconnection attempts (default: 5)')
    parser.add_argument('--reconnect-delay', type=float, default=5.0,
                        help='Initial delay between reconnection attempts in seconds (default: 5.0)')
    parser.add_argument('-t', '--timeout', type=float, default=None,
                        help='Timeout in seconds for waiting for a game to start (default: None for indefinite wait)')
    parser.add_argument('--store-result', type=str, default=None,
                        help='Path to file for storing game results in JSON format')
    parser.add_argument('--aggressive-reconnect', action='store_true',
                        help='Enable aggressive reconnection with infinite retries for critical operations')

    args = parser.parse_args()

    server_url = f"http://{args.host}:{args.port}"

    # Load strategy from file or use default
    if args.strategy:
        strategy = load_strategy_from_file(args.strategy, args.search_time)
        console.print(f"[cyan]Using custom strategy:[/cyan] {args.strategy}")
    else:
        # Use default strategy.py from the package
        from chess_arena_client.strategy import Strategy
        strategy = Strategy(search_time=args.search_time)
        console.print("[cyan]Using default strategy[/cyan]")

    # If --continue flag is set, try to load auth token
    if args.continue_game:
        # Load from custom file if specified, otherwise use legacy method
        if args.auth_file:
            auth_data = load_auth_from_file(args.auth_file)
        else:
            auth_data = get_latest_auth()

        if auth_data:
            game_id, player_id, player_color, auth_token = auth_data
            console.print(f"[green]✓ Continuing as player {player_id}[/green]")
            # Create client with loaded auth data
            client = ChessClient(server_url, strategy, continue_game=True, auth_file=args.auth_file,
                                 max_reconnect_attempts=args.max_reconnect_attempts,
                                 reconnect_delay=args.reconnect_delay, timeout=args.timeout,
                                 store_result_file=args.store_result,
                                 aggressive_reconnect=args.aggressive_reconnect)
            client.game_id = game_id
            client.player_id = player_id
            client.player_color = player_color
            client.auth_token = auth_token
            asyncio.run(client.run())
        else:
            console.print("[red]✗ No saved auth token found. Starting new game instead.[/red]")
            client = ChessClient(server_url, strategy, auth_file=args.auth_file,
                                 max_reconnect_attempts=args.max_reconnect_attempts,
                                 reconnect_delay=args.reconnect_delay, timeout=args.timeout,
                                 store_result_file=args.store_result,
                                 aggressive_reconnect=args.aggressive_reconnect)
            asyncio.run(client.run())
    else:
        client = ChessClient(server_url, strategy, auth_file=args.auth_file,
                             max_reconnect_attempts=args.max_reconnect_attempts,
                             reconnect_delay=args.reconnect_delay, timeout=args.timeout,
                             store_result_file=args.store_result,
                             aggressive_reconnect=args.aggressive_reconnect)
        asyncio.run(client.run())


if __name__ == '__main__':
    main()
