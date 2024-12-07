import sys
import os
import pygame
import copy

# Constants
FPS = 10
WINDOWWIDTH = 1100
WINDOWHEIGHT = 1000
CELLSIZE = 100
OUTLINE_WIDTH = 4
WAIT_TIME = 5000

# Colors
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
BGCOLOR = GRAY

PIECE_IMAGES = {}

# Load Piece Images
def load_images():
    pieces = ['wp', 'wr', 'wn', 'wb', 'wq', 'wk', 'bp', 'br', 'bn', 'bb', 'bq', 'bk']
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_folder = os.path.join(script_dir, "Chess_PNGs")
    
    for name in pieces:
        image_path = os.path.join(image_folder, f"{name}.png")
        image = pygame.image.load(image_path)
        resized_image = pygame.transform.scale(image, (CELLSIZE, CELLSIZE))
        PIECE_IMAGES[name] = resized_image

# Base Class for Pieces
class Piece:
    def __init__(self, color, position):
        self.color = color
        self.position = position
        self.has_moved = False

    def move(self, new_position):
        self.position = new_position

    def get_image_key(self):
        raise NotImplementedError("Must be implemented in subclass")

    def is_valid_move(self, end_position, board):
        raise NotImplementedError("Must be implemented in subclass")

# Pawn Class
class Pawn(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.can_be_captured_en_passant = False

    def get_image_key(self):
        return f'{self.color}p'

    def is_valid_move(self, end_position, board):
        start_x, start_y = self.position
        end_x, end_y = end_position
        direction = -1 if self.color == 'w' else 1
        start_row = 6 if self.color == 'w' else 1

        # Single square forward
        if end_y == start_y and end_x == start_x + direction and not board.get_piece(end_position):
            return True

        # Double square forward
        if (start_x == start_row and end_y == start_y and 
            end_x == start_x + 2 * direction and 
            not board.get_piece([start_x + direction, start_y]) and
            not board.get_piece(end_position)):
            return True

        # Diagonal capture
        if abs(end_y - start_y) == 1 and end_x == start_x + direction:
            target = board.get_piece(end_position)
            if target and target.color != self.color:
                return True

            # En passant
            adjacent_pawn = board.get_piece([start_x, end_y])
            if isinstance(adjacent_pawn, Pawn) and adjacent_pawn.color != self.color:
                if adjacent_pawn.can_be_captured_en_passant:
                    return True

        return False

# Rook Class
class Rook(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)

    def get_image_key(self):
        return f'{self.color}r'

    def is_valid_move(self, end_position, board):
        start_x, start_y = self.position
        end_x, end_y = end_position

        if start_x != end_x and start_y != end_y:
            return False

        # Path clearance
        if start_x == end_x:  # Vertical move
            step = 1 if end_y > start_y else -1
            for y in range(start_y + step, end_y, step):
                if board.get_piece([start_x, y]):
                    return False
        else:  # Horizontal move
            step = 1 if end_x > start_x else -1
            for x in range(start_x + step, end_x, step):
                if board.get_piece([x, start_y]):
                    return False
        return True

# Knight Class
class Knight(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)

    def get_image_key(self):
        return f'{self.color}n'

    def is_valid_move(self, end_position, board):
        start_x, start_y = self.position
        end_x, end_y = end_position
        dx = abs(end_x - start_x)
        dy = abs(end_y - start_y)
        return (dx, dy) in [(2, 1), (1, 2)]  # Knight move L-shape

# Bishop Class
class Bishop(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)

    def get_image_key(self):
        return f'{self.color}b'

    def is_valid_move(self, end_position, board):
        start_x, start_y = self.position
        end_x, end_y = end_position
        dx = end_x - start_x
        dy = end_y - start_y
        if abs(dx) != abs(dy):
            return False
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        for i in range(1, abs(dx)):
            if board.get_piece([start_x + i * step_x, start_y + i * step_y]):
                return False
        return True

# Queen Class
class Queen(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)

    def get_image_key(self):
        return f'{self.color}q'

    def is_valid_move(self, end_position, board):
        # Queen moves like both a Rook and a Bishop
        rook = Rook(self.color, self.position)
        bishop = Bishop(self.color, self.position)
        return rook.is_valid_move(end_position, board) or bishop.is_valid_move(end_position, board)

# King Class
class King(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)

    def get_image_key(self):
        return f'{self.color}k'

    def is_valid_move(self, end_position, board):
        start_x, start_y = self.position
        end_x, end_y = end_position

        # Normal king move (one square in any direction)
        if abs(end_x - start_x) <= 1 and abs(end_y - start_y) <= 1:
            target = board.get_piece(end_position)
            return target is None or target.color != self.color

        # Castling
        if not self.has_moved and start_x == end_x and abs(end_y - start_y) == 2:
            direction = 1 if end_y > start_y else -1
            rook_y = 7 if direction == 1 else 0
            rook = board.get_piece([start_x, rook_y])

            # Verify the rook is present and hasn't moved
            if isinstance(rook, Rook) and not rook.has_moved:
                # Check that all squares between king and rook are empty
                for y in range(start_y + direction, rook_y, direction):
                    if board.get_piece([start_x, y]) is not None:
                        return False

                # Check that the king does not pass through or end in check
                for y in range(start_y, start_y + 3 * direction, direction):
                    test_position = [start_x, y]
                    if y != rook_y:  # Ignore the rook's position
                        board.board[start_x][start_y] = None  # Temporarily move king
                        board.board[start_x][y] = self
                        in_check = board.is_king_in_check(self.color)
                        board.board[start_x][y] = None  # Reset
                        board.board[start_x][start_y] = self
                        if in_check:
                            return False
                return True
            
        return False

# Chess Board Class
class ChessBoard:
    def __init__(self):
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.setup_board()
        self.last_state = None

    def setup_board(self):
        # Place pawns
        for i in range(8):
            self.board[1][i] = Pawn('b', [1, i])
            self.board[6][i] = Pawn('w', [6, i])

        # Place Rooks
        self.board[0][0] = Rook('b', [0, 0])
        self.board[0][7] = Rook('b', [0, 7])
        self.board[7][0] = Rook('w', [7, 0])
        self.board[7][7] = Rook('w', [7, 7])

        # Place Knights
        self.board[0][1] = Knight('b', [0, 1])
        self.board[0][6] = Knight('b', [0, 6])
        self.board[7][1] = Knight('w', [7, 1])
        self.board[7][6] = Knight('w', [7, 6])

        # Place Bishops
        self.board[0][2] = Bishop('b', [0, 2])
        self.board[0][5] = Bishop('b', [0, 5])
        self.board[7][2] = Bishop('w', [7, 2])
        self.board[7][5] = Bishop('w', [7, 5])

        # Place Queens
        self.board[0][3] = Queen('b', [0, 3])
        self.board[7][3] = Queen('w', [7, 3])

        # Place Kings
        self.board[0][4] = King('b', [0, 4])
        self.board[7][4] = King('w', [7, 4])

    def draw_board(self):
        colors = [WHITE, GRAY]
        for row in range(8):
            for col in range(8):
                color = colors[(row + col) % 2]
                rect = pygame.Rect(col * CELLSIZE + 300, row * CELLSIZE + 100, CELLSIZE, CELLSIZE)
                pygame.draw.rect(DISPLAYSURF, color, rect)

                piece = self.board[row][col]
                if piece:
                    piece_image = PIECE_IMAGES.get(piece.get_image_key())
                    if piece_image:
                        DISPLAYSURF.blit(piece_image, rect.topleft)
                pygame.draw.rect(DISPLAYSURF, BLACK, (296, 96,807,807), OUTLINE_WIDTH)

    def save_state(self):
         self.last_state = copy.deepcopy(self.board)

    def undo_move(self):
        if self.last_state:
            self.board = self.last_state
            self.last_state = None  


    def get_piece(self, position):
        x, y = position
        if 0 <= x < 8 and 0 <= y < 8:
            return self.board[x][y]
        return None

    def move_piece(self, start_pos, end_pos, color):
        start_x, start_y = start_pos
        end_x, end_y = end_pos
        piece = self.get_piece(start_pos)

        if not piece or piece.color != color:
            return False
        
        self.save_state()
        if piece.is_valid_move(end_pos, self):
            # Handle en passant capture
            if isinstance(piece, Pawn) and abs(end_y - start_y) == 1 and not self.get_piece(end_pos):
                # If moving diagonally to an empty square, remove the pawn captured en passant
                captured_pawn_pos = [start_x, end_y]
                captured_pawn = self.get_piece(captured_pawn_pos)
                self.board[captured_pawn_pos[0]][captured_pawn_pos[1]] = None

            # Clear en passant eligibility for all pawns of the same color
            for row in self.board:
                for p in row:
                    if isinstance(p, Pawn) and p.color == color:
                        p.can_be_captured_en_passant = False

            # Handle double square pawn move
            if isinstance(piece, Pawn) and abs(end_x - start_x) == 2:
                piece.can_be_captured_en_passant = True
                        
            # Handle castling
            if isinstance(piece, King) and abs(end_y - start_y) == 2:
                direction = 1 if end_y > start_y else -1
                rook_y = 7 if direction == 1 else 0
                rook = self.get_piece([start_x, rook_y])
                if rook and isinstance(rook, Rook):
                    # Move rook to the square next to the king
                    self.board[start_x][rook_y] = None
                    self.board[start_x][start_y + direction] = rook
                    rook.move([start_x, start_y + direction])
                    
            # Simulate the move
            original_piece = self.board[end_x][end_y]
            self.board[end_x][end_y] = piece
            self.board[start_x][start_y] = None
            piece.move(end_pos)

            # Update last moved piece
            self.last_moved_piece = piece

            # Check if the move leaves the king in check
            if self.is_king_in_check(color):
                # Undo the move if it leaves the king in check
                self.board[start_x][start_y] = piece
                self.board[end_x][end_y] = original_piece
                piece.move(start_pos)

                # Undo en passant capture, if applicable
                if isinstance(piece, Pawn) and abs(end_y - start_y) == 1 and not self.get_piece([start_x + direction, start_y]):
                    self.board[captured_pawn_pos[0]][captured_pawn_pos[1]] = captured_pawn
                
                # Undo castling rook move, if applicable
                if isinstance(piece, King) and abs(end_y - start_y) == 2:
                    self.board[start_x][start_y + direction] = None
                    self.board[start_x][rook_y] = rook
                    rook.move([start_x, rook_y])
                    
                return False
            
            piece.has_moved = True  # Mark the piece as having moved
            return True

        return False
    
    def is_king_in_check(self, color):
        """ Check if the king of the given color is in check. """
        king_position = None
        opponent_color = 'b' if color == 'w' else 'w'

        # Find the king's position
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and isinstance(piece, King) and piece.color == color:
                    king_position = [row, col]
                    break
            if king_position:
                break

        if not king_position:
            raise ValueError(f"No king found for color {color} on the board.")

        # Check if any opponent piece can attack the king
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece and piece.color == opponent_color:
                    if piece.is_valid_move(king_position, self):
                        return True
        return False

    def is_game_over(self, color):
        """Check if the game is over due to checkmate or stalemate."""
        # Iterate through all pieces of the current color
        for row in range(8):
            for col in range(8):
                piece = self.get_piece([row, col])
                if piece and piece.color == color:
                    # Check all possible moves for the piece
                    for end_row in range(8):
                        for end_col in range(8):
                            end_position = [end_row, end_col]
                            # Simulate the move to test its validity
                            if piece.is_valid_move(end_position, self):
                                target_piece = self.get_piece(end_position)
                                if not isinstance(target_piece, King):
                                    # Temporarily move the piece
                                    original_start_piece = self.board[row][col]
                                    original_end_piece = self.board[end_row][end_col]
                                    self.board[row][col] = None
                                    self.board[end_row][end_col] = piece
                                    piece.move(end_position)

                                    # Check if the move leaves the king in check
                                    if not self.is_king_in_check(color):
                                        # Undo the move
                                        self.board[row][col] = original_start_piece
                                        self.board[end_row][end_col] = original_end_piece
                                        piece.move([row, col])
                                        return False  # A valid move exists

                                    # Undo the move
                                    self.board[row][col] = original_start_piece
                                    self.board[end_row][end_col] = original_end_piece
                                    piece.move([row, col])

        # No valid moves found; determine the result
        if self.is_king_in_check(color):
            return "checkmate"  # King is in check and no valid moves
        return "stalemate"  # No valid moves but king is not in check

def draw_ui(turn, score_b, score_w):
    # Draws Buttons
    draw_text(150,450,"New game",BLACK,1)
    draw_text(150,550,"Step back",BLACK,1)
    draw_text(150,650,"Draw",BLACK,1)
    draw_text(150,750,"Forfeit",BLACK,1)
    pygame.draw.rect(DISPLAYSURF, BLACK, (0, 400, 300, 100+2),OUTLINE_WIDTH)
    pygame.draw.rect(DISPLAYSURF, BLACK, (0, 500-2, 300, 100+4),OUTLINE_WIDTH)
    pygame.draw.rect(DISPLAYSURF, BLACK, (0, 600-2, 300, 100+4),OUTLINE_WIDTH)
    pygame.draw.rect(DISPLAYSURF, BLACK, (0, 700-2, 300, 100+4),OUTLINE_WIDTH)

    # Players
    draw_text(500, 50, "Player 2", BLACK, 1)
    pygame.draw.rect(DISPLAYSURF, BLACK, (300, 0, 100, 100))
    pygame.draw.rect(DISPLAYSURF, BLACK, (398, 0, 200+4, 100),OUTLINE_WIDTH)
    draw_text(500, 950, "Player 1", BLACK, 1)
    pygame.draw.rect(DISPLAYSURF, WHITE, (296, 900+3, 100+1, 100-6))
    pygame.draw.rect(DISPLAYSURF, BLACK, (296, 900, 106, 100), OUTLINE_WIDTH)
    pygame.draw.rect(DISPLAYSURF, BLACK, (398, 900, 200+4, 100),OUTLINE_WIDTH)

    # Score
    draw_text(150, 50, f"Score: {score_b}", BLACK, 1)
    pygame.draw.rect(DISPLAYSURF, BLACK, (0,0, 300, 100), OUTLINE_WIDTH)
    draw_text(150, 950, f"Score: {score_w}", BLACK, 1)
    pygame.draw.rect(DISPLAYSURF, BLACK, (0, 900, 300, 100), OUTLINE_WIDTH)

    # Whos move
    if turn == "w":
        draw_text(150,150,"White's", WHITE, 1)
        pygame.draw.rect(DISPLAYSURF, RED, (300,903, 100, 94), OUTLINE_WIDTH)
    else:
        draw_text(150,150,"Black's", BLACK, 1)
        pygame.draw.rect(DISPLAYSURF, RED, (300,3, 100, 94), OUTLINE_WIDTH)
    draw_text(150,250,"turn", BLACK, 1)
    pygame.draw.rect(DISPLAYSURF, BLACK, (0,96,300,206), OUTLINE_WIDTH)



def draw_text(cord_x, cord_y, text ,color, style):
    # Draws text with specified place, text, color, style.
    if style == 1:
        text_surface_object = BASICFONT.render(text, True, color)
    elif style == 2:
        text_surface_object = THROUGHSCREENFONT2.render(text, True, color)

    text_rect_object = text_surface_object.get_rect()
    text_rect_object.center = (cord_x, cord_y)
    DISPLAYSURF.blit(text_surface_object, text_rect_object)

def draw_promotion_choices(color):
    """Draw promotion choices (Knight, Bishop, Rook, Queen) with Knight and Bishop below Queen and Rook."""
    promotion_pieces = ['q', 'r', 'n', 'b']
    x_start = 600
    y_start = 400
    for i, piece in enumerate(promotion_pieces):
        if i < 2:  # First row (Queen and Rook)
            rect = pygame.Rect(x_start + i * CELLSIZE, y_start, CELLSIZE, CELLSIZE)
        else:  # Second row (Knight and Bishop)
            rect = pygame.Rect(x_start + (i - 2) * CELLSIZE, y_start + CELLSIZE, CELLSIZE, CELLSIZE)
        
        pygame.draw.rect(DISPLAYSURF, WHITE, rect)
        pygame.draw.rect(DISPLAYSURF, BLACK, rect, OUTLINE_WIDTH)
        piece_image = PIECE_IMAGES.get(f'{color}{piece}')
        if piece_image:
            DISPLAYSURF.blit(piece_image, rect.topleft)

def draw_end_screen(message, opacity=150):
    """Draws an end screen overlay with a message."""

    overlay = pygame.Surface(DISPLAYSURF.get_size(), pygame.SRCALPHA)  # Allow transparency
    overlay.fill((0, 0, 0, opacity))  # Black with specified opacity
    DISPLAYSURF.blit(overlay, (0, 0))  # Draw the overlay on the main surface
    draw_text(WINDOWWIDTH//2,WINDOWHEIGHT//2,message,RED,2)


# Main Game Loop
def main():
    global DISPLAYSURF, BASICFONT, THROUGHSCREENFONT2
    pygame.init()
    load_images()
    DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
    pygame.display.set_caption("Chess")
    clock = pygame.time.Clock()
    BASICFONT = pygame.font.Font('freesansbold.ttf', 45)
    THROUGHSCREENFONT2 = pygame.font.Font('freesansbold.ttf', 90)


    promoting_pawn = None  # The pawn being promoted
    promotion_color = None  # Color of the promoting pawn

    board = ChessBoard()
    selected_piece = None
    player_turn = 'w'
    score_b=0
    score_w=0

    while True:
        DISPLAYSURF.fill(BGCOLOR)
        board.draw_board()
        draw_ui(player_turn, score_b, score_w)

        if promoting_pawn:
            draw_promotion_choices(promotion_color)

        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_x, mouse_y = event.pos



                
                if mouse_x >= 300 and (mouse_y >= 100 and mouse_y <= 900): #ChessBoard part
                    row = (mouse_y - 100) // CELLSIZE
                    col = (mouse_x - 300) // CELLSIZE
                    if promoting_pawn:
                        # Handle promotion selection
                        x_start = 600
                        y_start = 400
                        for i, piece in enumerate(['q', 'r', 'n', 'b']):  # New order
                            if i < 2:  # First row (Queen and Rook)
                                rect = pygame.Rect(x_start + i * CELLSIZE, y_start, CELLSIZE, CELLSIZE)
                            else:  # Second row (Knight and Bishop)
                                rect = pygame.Rect(x_start + (i - 2) * CELLSIZE, y_start + CELLSIZE, CELLSIZE, CELLSIZE)
                            
                            if rect.collidepoint(mouse_x, mouse_y):
                                # Promote pawn
                                row, col = promoting_pawn
                                if piece == 'n':
                                    board.board[row][col] = Knight(promotion_color, [row, col])
                                elif piece == 'b':
                                    board.board[row][col] = Bishop(promotion_color, [row, col])
                                elif piece == 'r':
                                    board.board[row][col] = Rook(promotion_color, [row, col])
                                elif piece == 'q':
                                    board.board[row][col] = Queen(promotion_color, [row, col])
                                promoting_pawn = None
                                promotion_color = None
                                # Switch turns
                                player_turn = 'b' if player_turn == 'w' else 'w'
                                break  # Exit after promotion
                    if selected_piece:
                        if board.get_piece([row, col]) is not None and board.get_piece([row, col]).color == player_turn:
                            selected_piece = [row, col]
                        elif board.move_piece(selected_piece, [row, col], player_turn):
                            piece = board.get_piece([row, col])
                            selected_piece = None
                            # Check for promotion
                            if isinstance(piece, Pawn) and (row == 0 or row == 7):
                                promoting_pawn = [row, col]
                                promotion_color = piece.color
                            else:
                                # Switch turns
                                player_turn = 'b' if player_turn == 'w' else 'w'

                    else:
                        piece = board.get_piece([row, col])
                        if piece and piece.color == player_turn:
                            selected_piece = [row, col]
                else: #UI part
                    row = mouse_y // CELLSIZE
                    col = mouse_x // CELLSIZE
                    if row == 4:
                        board.__init__()
                        selected_piece = None
                        player_turn = 'w'
                    elif row == 5:
                        if board.last_state is not None:
                            board.undo_move()
                            selected_piece = None
                            player_turn = 'b' if player_turn == 'w' else 'w'
                    elif row == 6:
                        draw_end_screen(f"Draw!")
                        pygame.display.update()
                        pygame.time.wait(WAIT_TIME)    
                        selected_piece = None
                        player_turn = 'w'
                        score_w += 0.5
                        score_b += 0.5
                    elif row == 7:
                        winner = 'White' if player_turn == 'b' else 'Black'
                        draw_end_screen(f"Forfeit! {winner} wins!")
                        pygame.display.update()
                        pygame.time.wait(WAIT_TIME)
                        if winner == "Black":
                            score_b += 1
                        else:
                            score_w += 1
                        board.__init__()        
                        selected_piece = None
                        player_turn = 'w'

        if selected_piece:
            pygame.draw.rect(DISPLAYSURF, RED, (selected_piece[1] * CELLSIZE + 300, selected_piece[0] * CELLSIZE + 100, CELLSIZE, CELLSIZE), OUTLINE_WIDTH)

        # Check if the game is over
        game_status = board.is_game_over(player_turn)
        if game_status:
            if game_status == "checkmate":
                board.draw_board()
                winner = 'White' if player_turn == 'b' else 'Black'
                draw_end_screen(f"Checkmate! {winner} wins!")
                pygame.display.update()
                pygame.time.wait(WAIT_TIME)
                if winner == "Black":
                    score_b += 1
                else:
                    score_w += 1
                board.__init__()        
                selected_piece = None
                player_turn = 'w'
            elif game_status == "stalemate":
                # Currently not working properly             
                draw_end_screen("Stalemate! The game is a draw.")
                pygame.display.update()
                pygame.time.wait(WAIT_TIME)
                score_w += 0.5
                score_b += 0.5
                board.__init__()        
                selected_piece = None
                player_turn = 'w'

        pygame.display.update()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
