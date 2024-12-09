import asyncio
import websockets
import random
import time

def create_grid():
    """
    make an empty grid
    """
    print('creating grid')
    grid = []
    for _ in range(6):
        grid.append([0] * 7)
    return grid

def duplicate_grid(grid):
    """
    copy the current game grid
    for testing moves
    """
    #print('duplicating grid')
    return [row[:] for row in grid]

def update_grid(player, col, grid):
    """
    update the grid with each move
    """
    #print('updating grid')
    for row in range(5, -1, -1):
        if grid[row][col] == 0:
            grid[row][col] = int(player)
            break

def simulate_move(player, col, grid):
    """
    make a copy of the grid and test moves
    """
    #print(f'simulating player {player} move in column {col}')
    test_grid = duplicate_grid(grid)
    update_grid(player, col, test_grid)
    return test_grid

def score_move(col, grid):
    score = 0

    # slight bonus if near center
    center_weight = [10, 20, 30, 30, 30, 20, 10]
    score += center_weight[col]

    # amazing bonus if results in immediate win
    if is_winning_move(1, col, grid):
        print(f"col {col}: + 100000. Winning move")
        score += 100000

    # terrible negative if allows opponent to win next turn
    test_grid = simulate_move(1, col, grid)
    for c in range(7):
        if is_winning_move(2, c, test_grid):
            print(f"col {col}: - 900. Allows opponent win")
            score -= 900
    
    # big bonus if blocks opponent win
    if is_winning_move(2, col, grid):
        print(f"col {col}: + 900. blocks opp win")
        score += 900

    before_connections = find_connection(1, grid)
    after_connections = find_connection(1, test_grid)
    if len(before_connections) > 0:
        longest_before = before_connections[0]
        for connection in before_connections:
            if len(connection) > len(longest_before):
                longest_before = connection
    else:
        longest_before = [0]
    if len(after_connections) > 0:
        longest_after = after_connections[0]
        for connection in after_connections:
            if len(connection) > len(longest_after):
                longest_after = connection
    else:
        longest_after = [0]    

    # bonus if increases length of a strip
    if len(longest_after) > len(longest_before):
        print(f"col {col}: + 100. Longer connection")
        score += 100
    # bonus if makes more connections
    if len(after_connections) > len(before_connections):
        print(f"col {col}: + 50. More connections")
        score += 50
    
    # bonus's for placing next to opponents pieces
    before_connections = find_connection(2, grid)
    after_connections = find_connection(2, test_grid)
    if len(before_connections) > 0:
        longest_before = before_connections[0]
        for connection in before_connections:
            if len(connection) > len(longest_before):
                longest_before = connection
    else:
        longest_before = [0]
    if len(after_connections) > 0:
        longest_after = after_connections[0]
        for connection in after_connections:
            if len(connection) > len(longest_after):
                longest_after = connection
    else:
        longest_after = [0]    

    # bonus if blocks opp increas length of a strip
    if len(longest_after) > len(longest_before):
        print(f"col {col}: + 80. Blocks opp getting longer connection")
        score += 80
    # bonus if blocks opp more connections
    if len(after_connections) > len(before_connections):
        print(f"col {col}: + 30. Blocks opponent increasing connections")
        score += 30

    # bonus if sets up a fork
    fork_count = 0
    test_grid = simulate_move(1, col, grid)    
    for c in range(7):
        if grid[0][col] == 0 and is_winning_move(1, c, test_grid):
            fork_count += 1
        
    
    if fork_count >= 2:
        print(f"col {col}: + 500. Fork created with {fork_count} winning moves")
        score += 500
    
    # negative if allows opponent to fork
    fork_count = 0
    test_grid = simulate_move(1, col, grid)
    for opp_col in range(7):
        if test_grid[0][opp_col] == 0:
            opp_test_grid = simulate_move(2, opp_col, test_grid)
            opponent_winning_moves = 0
            for next_col in range(7):
                if opp_test_grid[0][next_col] == 0 and is_winning_move(2, next_col, opp_test_grid):
                    opponent_winning_moves += 1
            
            # If opponent has two or more winning moves, fork
            if opponent_winning_moves >= 2:
                fork_count += 1
    
    if fork_count > 0:
        score -= fork_count *200
        print(f"col {col}: - {fork_count * 200} for allowing opponent fork with {fork_count} options")

    #Bonus if dual threats for opp
    test_grid = simulate_move(1, col, grid)
    opponent_threats = detect_dual_threats(2, test_grid)
    if opponent_threats > 0:
        score -= opponent_threats * 100
        print(f'Col {col} - {opponent_threats * 100}. opp dual threats')
    my_dual_threats = detect_dual_threats(1, test_grid)
    if my_dual_threats > 0:
        score += my_dual_threats * 200        
        print(f'Col {col} + {my_dual_threats * 100}. my dual threats')

    print(f'final score for col {col}: {score}')
    return score


def detect_dual_threats(player, grid):
    dual_threats = 0
    for col in range(7):
        if grid[0][col] == 0:  # Check valid columns
            test_grid = simulate_move(player, col, grid)
            winning_moves = sum(1 for c in range(7) if is_winning_move(player, c, test_grid))
            if winning_moves >= 2:  # Detect two or more simultaneous threats
                dual_threats += 1
    return dual_threats


def is_winning_move(player, col, grid):
    """
    check for chance to win
    """
    #print(f'checking for player {player} winning move in col {col}')
    test_grid = simulate_move(player, col, grid)
    connections = find_connection(player, test_grid)
    for conn in range(len(connections)):
        if len(connections[conn]) == 4:
            #print(f'player {player} winning move detected in column {col}')
            return True
    return False

def find_connection(player, grid):
    """
    find all strings of connected pieces
    on the board
    """
    connections = []
    rows = len(grid)
    cols = len(grid[0])

    directions = [(-1, 0), (-1, 1), (0, 1), (1, 1)]  # [vertical, upright (/), horizontal, downright (\)]

    for row in range(rows):
        for col in range(cols):
            if grid[row][col] != player:
                continue
            
            # Check each direction
            for row_direction, col_direction in directions: 
                length = 1
                r, c = row, col
                connected = [(r, c)]  # Keep track of connected pieces

                # continue looking in the direction
                while True:
                    r += row_direction
                    c += col_direction
                    if 0 <= r < rows and 0 <= c < cols and grid[r][c] == player:
                        connected.append((r, c))
                        length += 1
                    else:
                        break

                if length > 2:
                    connections.append(connected)


    return connections

def calculate_move(grid):
    """
    choose a move and do all the math stuffs
    """
    print('calculating move')
    time.sleep(2)
    valid_cols = []
    for col in range(7):
        if grid[0][col] == 0:
            valid_cols.append(col)

    if not valid_cols: # in case of a full board
        return None

    scores = []
    for col in range(7):
        if col in valid_cols:
            scores.append(score_move(col, grid))
        else:
            scores.append(-9999999)
    
    print(scores)
    highest = []

    for i in range(len(scores)):
        if scores[i] == max(scores):
            highest.append(i)
     
    return random.choice(highest)


async def gameloop(socket, created):
    active = True
    grid = create_grid()

    while active:
        message = (await socket.recv()).split(':')

        match message[0]:
            case 'GAMESTART':
                if created:
                    col = calculate_move(grid)
                    if col is not None:
                        update_grid(1, col, grid)
                        await socket.send(f'PLAY:{col}')

            case 'OPPONENT':
                opponent_col = int(message[1])
                print("~" * 10)
                print(f"Opponent went in column {opponent_col}") # for debugging purposes
                update_grid(2, opponent_col, grid)
                col = calculate_move(grid)
                if col is not None:
                    update_grid(1, col, grid)
                    await socket.send(f'PLAY:{col}')

            case 'WIN' | 'LOSS' | 'DRAW' | 'TERMINATED':
                print(message[0])
                active = False

async def connect_and_play(server, endpoint, created):
    async with websockets.connect(f'ws://{server}/{endpoint}') as socket:
        await gameloop(socket, created)

async def create_game(server):
    await connect_and_play(server, "create", True)

async def join_game(server, id):
    await connect_and_play(server, f"join/{id}", False)

if __name__ == '__main__':
    server = input("Enter server id ==> ").strip()
    protocol = input("Join or Create game? (j/c) ==> ").strip()

    if protocol == 'c':
        asyncio.run(create_game(server))
    elif protocol == 'j':
        id = input('Game ID: ').strip()
        asyncio.run(join_game(server, id))
    else:
        print('Invalid protocol!')
