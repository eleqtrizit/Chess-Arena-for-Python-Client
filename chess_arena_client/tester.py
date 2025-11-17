#!/usr/bin/env python3
"""
Chess Arena Client Tester - Test your chess strategies against predefined game states.

Loads test data from test_data/game_states.jsonl and runs user strategies against it.
Each test case includes a FEN position, legal moves, and player color.
Results are displayed with color-coded pass/fail indicators and running counts.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List

import chess
from rich.console import Console

from chess_arena_client.strategy_base import StrategyBase

console = Console()


def load_test_data(file_path: str) -> List[dict]:
    """
    Load test data from JSONL file.

    :param file_path: Path to the JSONL file
    :type file_path: str
    :return: List of test cases
    :rtype: List[dict]
    :raises FileNotFoundError: If test data file is not found
    :raises json.JSONDecodeError: If JSON is malformed
    """
    test_cases = []
    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:  # Skip empty lines
                    try:
                        test_case = json.loads(line)
                        test_cases.append(test_case)
                    except json.JSONDecodeError as e:
                        console.print(f"[red]✗ Error parsing JSON on line {line_num}:[/red] {e}")
                        raise
        return test_cases
    except FileNotFoundError:
        console.print(f"[red]✗ Test data file not found:[/red] {file_path}")
        raise
    except Exception as e:
        console.print(f"[red]✗ Error reading test data file:[/red] {e}")
        raise


def load_strategy_from_file(file_path: str) -> StrategyBase:
    """
    Dynamically load a Strategy class from a Python file.

    :param file_path: Path to the strategy file
    :type file_path: str
    :return: Strategy instance
    :rtype: StrategyBase
    :raises ImportError: If the strategy file cannot be loaded
    :raises AttributeError: If the Strategy class is not found
    """
    import importlib.util

    try:
        spec = importlib.util.spec_from_file_location("strategy_module", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {file_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["strategy_module"] = module
        spec.loader.exec_module(module)

        if not hasattr(module, 'Strategy'):
            raise AttributeError(
                f"[red]✗ Strategy class not found in {file_path}[/red]\n"
                f"[yellow]Please ensure your strategy file contains a class named 'Strategy' "
                f"that inherits from StrategyBase.[/yellow]"
            )

        strategy_class = getattr(module, 'Strategy')
        # Create instance with default search time of 1.0 second for testing
        return strategy_class(search_time=1.0)
    except Exception as e:
        console.print(f"[red]✗ Error loading strategy from {file_path}:[/red] {e}")
        raise


def run_test_case(strategy: StrategyBase, test_case: dict, test_index: int,
                  passed: int, total: int, timeouts: int) -> tuple[bool, bool]:
    """
    Run a single test case against the strategy.

    :param strategy: Strategy instance to test
    :type strategy: StrategyBase
    :param test_case: Test case data
    :type test_case: dict
    :param test_index: Index of the test case (for display)
    :type test_index: int
    :param passed: Number of tests passed so far
    :type passed: int
    :param total: Total number of tests
    :type total: int
    :param timeouts: Number of timeouts so far
    :type timeouts: int
    :return: Tuple of (test_passed, timeout_occurred)
    :rtype: tuple[bool, bool]
    """
    import time

    try:
        fen = test_case["fen"]
        legal_moves = test_case["legal_moves"]
        player_color = test_case["player_color"]

        # Create board from FEN
        board = chess.Board(fen)

        # Call strategy to choose a move with timing
        start_time = time.time()
        chosen_move = strategy.choose_move(board, legal_moves, player_color)
        elapsed_time = time.time() - start_time

        # Check if move took too long (with small buffer to account for system timing)
        timeout_occurred = elapsed_time > (strategy.search_time + 0.1)

        # Check if chosen move is in legal moves
        if chosen_move in legal_moves:
            if timeout_occurred:
                console.print(
                    f"[green]✓[/green] Test {test_index}: PASS "
                    f"({passed+1}/{total} passed) ({timeouts+1} timeouts) - Move: {chosen_move} (TIMED OUT)")
                return True, True
            else:
                console.print(
                    f"[green]✓[/green] Test {test_index}: PASS "
                    f"({passed+1}/{total} passed) ({timeouts} timeouts) - Move: {chosen_move}")
                return True, False
        else:
            if timeout_occurred:
                console.print(
                    f"[red]✗[/red] Test {test_index}: FAIL ({passed}/{total} passed) ({timeouts+1} timeouts) - "
                    f"Chosen move '{chosen_move}' not in legal moves: {legal_moves} (TIMED OUT)")
                return False, True
            else:
                console.print(
                    f"[red]✗[/red] Test {test_index}: FAIL ({passed}/{total} passed) ({timeouts} timeouts) - "
                    f"Chosen move '{chosen_move}' not in legal moves: {legal_moves}")
                return False, False

    except Exception as e:
        console.print(f"[red]✗[/red] Test {test_index}: ERROR ({passed}/{total} passed) ({timeouts} timeouts) - {e}")
        return False, False


def main() -> None:
    """
    Main entry point for the chess arena client tester.
    """
    parser = argparse.ArgumentParser(
        description='Chess Arena Client Tester - Test your chess strategies',
        epilog='Test your strategies against predefined game states'
    )
    parser.add_argument(
        '--strategy',
        type=str,
        help='Path to custom strategy file containing a Strategy class'
    )
    parser.add_argument(
        '--search-time',
        type=float,
        default=5.0,
        help='Maximum search time per move in seconds (default: 5.0)'
    )
    parser.add_argument(
        '--sample',
        type=int,
        help='Run only a random sample of N tests instead of all tests'
    )
    parser.add_argument(
        '--get-agent-prompt',
        action='store_true',
        help='Output the AGENT.md prompt to STDOUT (not compatible with other flags)'
    )
    parser.add_argument(
        '--test-data-path',
        type=str,
        help='Path to custom test data file (default: packaged test_data/game_states.jsonl)'
    )

    args = parser.parse_args()

    # Handle --get-agent-prompt flag
    if args.get_agent_prompt:
        agent_md_path = Path(__file__).parent / "AGENT.md"
        try:
            with open(agent_md_path, 'r') as f:
                print(f.read())
            sys.exit(0)
        except FileNotFoundError:
            console.print(f"[red]✗ AGENT.md not found at:[/red] {agent_md_path}")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]✗ Error reading AGENT.md:[/red] {e}")
            sys.exit(1)

    # Validate required arguments for normal operation
    if not args.strategy:
        parser.error("--strategy is required unless using --get-agent-prompt")

    console.print("[bold blue]♟ Chess Arena Client Tester[/bold blue]")
    console.print(f"[cyan]Strategy file:[/cyan] {args.strategy}")
    console.print(f"[cyan]Search time:[/cyan] {args.search_time}s")

    # Check if strategy file exists
    if not Path(args.strategy).exists():
        console.print(f"[red]✗ Strategy file not found:[/red] {args.strategy}")
        sys.exit(1)

    # Load test data
    if args.test_data_path:
        test_data_path = Path(args.test_data_path)
    else:
        # Try packaged data first
        packaged_data = Path(__file__).parent / "test_data" / "game_states.jsonl"
        if packaged_data.exists():
            test_data_path = packaged_data
        else:
            # Fall back to current directory
            test_data_path = Path("test_data/game_states.jsonl")

    if not test_data_path.exists():
        console.print(f"[red]✗ Test data file not found:[/red] {test_data_path}")
        console.print("[yellow]Please ensure test_data/game_states.jsonl exists.[/yellow]")
        sys.exit(1)

    try:
        test_cases = load_test_data(str(test_data_path))
        console.print(f"[cyan]Loaded {len(test_cases)} test cases[/cyan]")

        # Store original count for display
        original_total = len(test_cases)

        # Sample tests if requested
        if args.sample is not None:
            import random
            if args.sample < 1:
                console.print("[red]✗ Sample size must be at least 1[/red]")
                sys.exit(1)
            if args.sample < len(test_cases):
                test_cases = random.sample(test_cases, args.sample)
                console.print(f"[cyan]Sampled {len(test_cases)} test cases[/cyan]")
            else:
                console.print(
                    f"[yellow]Sample size ({args.sample}) is greater than or equal to "
                    f"total tests ({len(test_cases)}), running all tests[/yellow]")
    except Exception:
        sys.exit(1)

    # Set total to the actual number of tests we'll run
    total = len(test_cases)

    # Load strategy with search time
    try:
        strategy = load_strategy_from_file(args.strategy)
        # Set the search time for the strategy
        strategy.search_time = args.search_time
        console.print("[green]✓ Strategy loaded successfully[/green]")
    except Exception:
        sys.exit(1)

    # Run tests
    passed = 0
    total = len(test_cases)
    timeouts = 0

    console.print("\n[bold]Running tests...[/bold]")

    for i, test_case in enumerate(test_cases, 1):
        test_passed, timeout_occurred = run_test_case(strategy, test_case, i, passed, total, timeouts)
        if test_passed:
            passed += 1
        if timeout_occurred:
            timeouts += 1

    # Display final results
    console.print("\n[bold]Final Results:[/bold]")
    if args.sample is not None and args.sample < original_total:
        console.print(f"[cyan]Passed:[/cyan] {passed}/{total} (sampled from {original_total} total tests)")
    else:
        console.print(f"[cyan]Passed:[/cyan] {passed}/{total}")

    # Write test results to JSON file
    import json
    failed = total - passed
    test_results = {
        "passed": passed,
        "failed": failed,
        "timeouts": timeouts,
        "total_tests": total
    }

    # Add sampling information if applicable
    if args.sample is not None and args.sample < original_total:
        test_results["sampled"] = True
        test_results["original_total_tests"] = original_total
    else:
        test_results["sampled"] = False

    try:
        with open("test_result.json", "w") as f:
            json.dump(test_results, f, indent=2)
        console.print("[green]✓[/green] Test results written to test_result.json")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to write test results to JSON file: {e}")

    if passed == total:
        console.print("[bold green]🎉 All tests passed![/bold green]")
    else:
        console.print(f"[bold red]❌ {failed} test(s) failed[/bold red]")
        sys.exit(1)


if __name__ == '__main__':
    main()
