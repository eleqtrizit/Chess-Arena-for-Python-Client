# Chess Arena Client Tester

The Chess Arena Client Tester is an easy-to-use command-line tool that allows you to test your chess strategies against predefined game states. This tool helps you validate your strategy implementation and performance before competing in actual games.

## Table of Contents
1. [Installation](#installation)
2. [Basic Usage](#basic-usage)
3. [Test Data Format](#test-data-format)
4. [Strategy Requirements](#strategy-requirements)
5. [Command-Line Options](#command-line-options)
6. [Output Format](#output-format)
7. [Test Results](#test-results)
8. [Performance Testing](#performance-testing)
9. [Sampling Tests](#sampling-tests)
10. [Examples](#examples)

## Installation

The tester is included with the Chess Arena Client package. After installing the client, the tester command will be available:

```bash
# Install the client (and tester)
uv tool install git+https://github.com/eleqtrizit/Chess-Arena-for-Python-Client

# Or if you've cloned the repository
make install
```

## Basic Usage

To test your strategy, use the `chess-arena-client-tester` command with the `--strategy` parameter:

```bash
chess-arena-client-tester --strategy my_strategy.py
```

This will:
1. Load your strategy from the specified file
2. Load test data from `test_data/game_states.jsonl`
3. Run each test case against your strategy
4. Display pass/fail results with color-coded output
5. Generate a `test_result.json` file with summary statistics

## Test Data Format

Test cases are stored in `test_data/game_states.jsonl` (JSON Lines format). Each line contains a JSON object with:

- `fen`: The board position in FEN notation
- `legal_moves`: Array of legal moves in SAN notation
- `player_color`: The player's color ("white" or "black")

Example test case:
```json
{
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "legal_moves": ["a3", "a4", "b3", "b4", "c3", "c4", "d3", "d4", "e3", "e4", "f3", "f4", "g3", "g4", "h3", "h4", "Na3", "Nc3", "Nf3", "Nh3"],
  "player_color": "white"
}
```

The chess-arena server generates this data and stores it in `/tmp/game_states.jsonl`.  You can easily make your own data by running the default chess-arena and chess-arena-clients.

## Strategy Requirements

Your strategy file must:

1. Contain a class named `Strategy` that inherits from `StrategyBase`
2. Implement the `choose_move` method with the correct signature
3. Return a valid move from the `legal_moves` list

Example strategy:
```python
#!/usr/bin/env python3
import random
from typing import List
import chess
from chess_arena_client.strategy_base import StrategyBase

class Strategy(StrategyBase):
    def choose_move(self, board: chess.Board, legal_moves: List[str], player_color: str) -> str:
        # Return a random legal move
        return random.choice(legal_moves)
```

## Command-Line Options

### --strategy (required)
Path to your strategy file:
```bash
chess-arena-client-tester --strategy my_strategy.py
```

### --search-time (optional)
Maximum search time per move in seconds (default: 5.0):
```bash
chess-arena-client-tester --strategy my_strategy.py --search-time 2.0
```

### --sample (optional)
Run only a random sample of N tests instead of all tests:
```bash
chess-arena-client-tester --strategy my_strategy.py --sample 10
```

## Output Format

The tester provides real-time feedback during testing:

**Passing test:**
```
✓ Test 1: PASS (1/51 passed) (0 timeouts) - Move: e4
```

**Failing test:**
```
✗ Test 5: FAIL (3/51 passed) (0 timeouts) - Chosen move 'invalid_move' not in legal moves: ['e4', 'd4', 'Nf3']
```

**Timeout test:**
```
✓ Test 3: PASS (3/51 passed) (1 timeouts) - Move: Nf3 (TIMED OUT)
```

Color coding:
- Green ✓: Test passed
- Red ✗: Test failed or error occurred
- Yellow text: Additional information (timed out, etc.)

## Test Results

After all tests complete, results are displayed and saved to `test_result.json`:

```
Final Results:
Passed: 45/51

Test results written to test_result.json
```

The JSON file contains:
```json
{
  "passed": 45,
  "failed": 6,
  "timeouts": 2,
  "total_tests": 51,
  "sampled": false
}
```

When using sampling:
```json
{
  "passed": 8,
  "failed": 2,
  "timeouts": 1,
  "total_tests": 10,
  "sampled": true,
  "original_total_tests": 51
}
```

## Performance Testing

The tester monitors your strategy's performance and detects timeouts. A timeout occurs when your `choose_move` method takes longer than the specified `--search-time` plus a small buffer (0.1 seconds).

To test timeout handling, you can create a slow strategy:

```python
#!/usr/bin/env python3
import time
import random
from typing import List
import chess
from chess_arena_client.strategy_base import StrategyBase

class Strategy(StrategyBase):
    def choose_move(self, board: chess.Board, legal_moves: List[str], player_color: str) -> str:
        # Sleep longer than search time to trigger timeout
        time.sleep(self.search_time + 0.5)
        return random.choice(legal_moves)
```

## Sampling Tests

For quick validation during development, you can run a random sample of tests:

```bash
# Run only 10 random tests instead of all 51, limited to 2 seconds per test
chess-arena-client-tester --strategy my_strategy.py --sample 10 --search-time 2
```

Benefits of sampling:
- Faster feedback during development
- Reduced resource usage
- Good for CI/CD pipelines
- Still provides meaningful validation

## Examples

### Basic Testing
```bash
# Test with default settings (5.0 second search time)
chess-arena-client-tester --strategy my_strategy.py
```

### Performance Testing
```bash
# Test with strict time limits
chess-arena-client-tester --strategy my_strategy.py --search-time 1.0
```

### Quick Validation
```bash
# Run a sample of 5 tests for quick feedback
chess-arena-client-tester --strategy my_strategy.py --sample 5
```

### Comprehensive Testing
```bash
# Run all tests with generous time limits
chess-arena-client-tester --strategy my_strategy.py --search-time 10.0
```

## Troubleshooting

### Strategy Loading Errors
If you see "Strategy class not found", ensure your file contains a class named `Strategy` that inherits from `StrategyBase`.

### File Not Found Errors
Verify that:
- Your strategy file exists at the specified path
- The `test_data/game_states.jsonl` file exists
- You have read permissions for all files

### Test Failures
Common causes:
- Returning moves not in `legal_moves`
- Exceptions in your `choose_move` method
- Timeout exceeded (adjust `--search-time`)

### Performance Issues
If experiencing frequent timeouts:
- Profile your code to identify bottlenecks
- Implement early termination in search algorithms
- Use the `--search-time` parameter during development to catch issues early