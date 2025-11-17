# Chess Strategy Development Challenge

You are competing to write the best chess algorithm in the world. Write a script called `my_strategy.py` that implements a chess strategy. Once complete, it will be tested in 10 games against the leading opponent. If you win, you will become the Chess Champion of the World.

If you are defeated, you will receive feedback to make further improvements.

## Your Mission

Create a file named `my_strategy.py` that contains a class called `Strategy` (must be exactly this name) that inherits from `StrategyBase` and implements intelligent chess move selection.

## Required Implementation

### File Structure

```python
#!/usr/bin/env python3
import chess
import random
from typing import List
from chess_arena_client.strategy_base import StrategyBase


class Strategy(StrategyBase):  # Must be named "Strategy"
    def choose_move(self, board: chess.Board, legal_moves: List[str], player_color: str) -> str:
        """
        Choose the best move for the current position.

        :param board: Current board position (python-chess Board object)
        :type board: chess.Board
        :param legal_moves: List of legal moves in SAN notation (e.g., ["e4", "Nf3"])
        :type legal_moves: List[str]
        :param player_color: Color of the player ("white" or "black")
        :type player_color: str
        :return: Selected move in SAN notation
        :rtype: str
        """
        # YOUR IMPLEMENTATION GOES HERE
        return selected_move
```

## Understanding the Parameters

### 1. `board: chess.Board`

A `python-chess` Board object representing the current game position. Use it to analyze the position:

```python
# Game state
board.turn                    # True if white's turn, False if black's
board.fullmove_number        # Current move number
board.is_check()             # Is current side in check?
board.is_checkmate()         # Is current side checkmated?
board.is_game_over()         # Is the game over?

# Piece information
board.piece_at(chess.E4)     # What piece is on e4?
board.pieces(chess.KNIGHT, chess.WHITE)  # Get all white knights

# Position analysis
board.is_attacked_by(chess.WHITE, chess.E4)  # Is e4 attacked by white?
board.copy()                 # Create a copy for testing moves
board.parse_san(move_san)    # Convert SAN string to Move object
board.push(move)             # Make a move on the board
board.pop()                  # Undo the last move
```

### 2. `legal_moves: List[str]`

A pre-validated list of all legal moves in Standard Algebraic Notation (SAN):

```python
# Examples:
["e4", "d4", "Nf3", "c4"]           # Opening moves
["Nxe5", "Qh5+", "O-O", "e8=Q"]    # Captures, checks, castling, promotion
```

**You must return one move from this list.** All moves are guaranteed to be legal.

### 3. `player_color: str`

Your assigned color: `"white"` or `"black"`.

## Standard Algebraic Notation (SAN) Quick Reference

| Move Type | Example | Meaning |
|-----------|---------|---------|
| Pawn move | `e4` | Move pawn to e4 |
| Piece move | `Nf3` | Move knight to f3 |
| Capture | `Nxe5` | Knight captures on e5 |
| Castling | `O-O` or `O-O-O` | Kingside or queenside castle |
| Promotion | `e8=Q` | Pawn promotes to queen |
| Check | `Qh5+` | Move gives check |
| Checkmate | `Qh7#` | Move delivers checkmate |

**Piece letters:** K=King, Q=Queen, R=Rook, B=Bishop, N=Knight (pawns have no letter)

## Strategy Development Approach

### Phase 1: Basic Working Strategy

Start with something simple that works:

```python
def choose_move(self, board, legal_moves, player_color):
    # Prefer captures
    captures = [m for m in legal_moves if 'x' in m]
    if captures:
        return random.choice(captures)
    
    # Otherwise random
    return random.choice(legal_moves)
```

### Phase 2: Write your own Algorithm!

Develop a winning algo to defeat the champ!

## Critical Time Management

**There is a strict time limit per move.** Exceeding it may result in disqualification.

Always implement time checking:

```python
import time

def choose_move(self, board, legal_moves, player_color):
    start_time = time.time()
    deadline = start_time + self.search_time - 0.5  # Leave 0.5s buffer
    
    best_move = legal_moves[0]  # Always have a valid move ready
    best_score = float('-inf')
    
    for move_san in legal_moves:
        # Check time before expensive operations
        if time.time() >= deadline:
            break
        
        score = self.evaluate_move(board, move_san)
        if score > best_score:
            best_score = score
            best_move = move_san
    
    return best_move
```

**Key principle:** A decent move returned on time beats a perfect move that times out.

## Advanced Techniques to Consider

1. **Alpha-Beta Pruning**: Optimize minimax by pruning branches
2. **Move Ordering**: Search promising moves first (captures, checks)
3. **Transposition Tables**: Cache position evaluations
4. **Opening Book**: Pre-programmed strong opening moves
5. **Endgame Tablebases**: Perfect play in simple endgames
6. **Iterative Deepening**: Search deeper when time permits
7. **Quiescence Search**: Extend search for tactical sequences
8. **Position Evaluation Factors**:
   - Material count
   - Piece mobility
   - King safety
   - Pawn structure
   - Center control
   - Piece development

## Common Patterns

### Counting Material

```python
def count_material(self, board, color):
    piece_values = {
        chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
        chess.ROOK: 5, chess.QUEEN: 9
    }
    total = 0
    for piece_type, value in piece_values.items():
        total += len(board.pieces(piece_type, color)) * value
    return total
```

### Checking Center Control

```python
def evaluate_center_control(self, board):
    center_squares = [chess.E4, chess.E5, chess.D4, chess.D5]
    score = 0
    for square in center_squares:
        if board.is_attacked_by(chess.WHITE, square):
            score += 1
        if board.is_attacked_by(chess.BLACK, square):
            score -= 1
    return score
```

### Prioritizing Moves

```python
def choose_move(self, board, legal_moves, player_color):
    # 1. Checkmate if available
    for move_san in legal_moves:
        if '#' in move_san:
            return move_san
    
    # 2. Captures
    captures = [m for m in legal_moves if 'x' in m]
    if captures:
        return self.best_capture(board, captures)
    
    # 3. Checks
    checks = [m for m in legal_moves if '+' in m]
    if checks:
        return random.choice(checks)
    
    # 4. Development/center control
    return self.evaluate_all_moves(board, legal_moves)
```

## Requirements Checklist

- [ ] File named `my_strategy.py`
- [ ] Class named `Strategy` (exact name required)
- [ ] Inherits from `StrategyBase`
- [ ] Implements `choose_move()` method
- [ ] Returns a move from the `legal_moves` list
- [ ] Returns a valid SAN string
- [ ] Respects time limits (uses `self.search_time`)
- [ ] Handles all game phases (opening, middlegame, endgame)
- [ ] Never crashes or raises exceptions

## Winning Strategy Characteristics

The best strategies typically:

1. **Search deeply** - Look ahead multiple moves
2. **Evaluate accurately** - Consider multiple position factors
3. **Manage time wisely** - Balance depth with time constraints
4. **Prioritize threats** - Recognize and respond to checkmate threats
5. **Play sound chess** - Follow chess principles (development, king safety, center control)
6. **Avoid blunders** - Don't hang pieces or miss forced checkmates

## Resources

- **python-chess documentation**: https://python-chess.readthedocs.io/
- **Chess programming wiki**: https://www.chessprogramming.org/
- **Minimax algorithm**: https://www.chessprogramming.org/Minimax
- **Alpha-beta pruning**: https://www.chessprogramming.org/Alpha-Beta

---

**Now go forth and create the world's best chess algorithm! 🏆♟️**

