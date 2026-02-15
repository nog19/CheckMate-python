import pygame
import chess
import sys

# Configurações
WIDTH, HEIGHT = 800, 600
BOARD_SIZE = 600
SQ_SIZE = BOARD_SIZE // 8
FPS = 60

COLORS = {
    'light': (240, 217, 181), 
    'dark': (148, 111, 81),   
    'bg': (25, 25, 25),
    'text': (255, 255, 255),
    'highlight': (170, 162, 58), 
    'piece_white': (255, 255, 255),
    'piece_black': (20, 20, 20),
    'button': (200, 50, 50),
    'menu_btn': (60, 60, 60)
}

class ChessGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Xadrez Python - Seleção de Tempo")
        self.font_pieces = pygame.font.SysFont("segoe uisymbol", 70)
        self.font_ui = pygame.font.SysFont("Segoe UI", 20, bold=True)
        self.font_big = pygame.font.SysFont("Segoe UI", 40, bold=True)
        self.clock = pygame.time.Clock()
        
        self.in_menu = True # Começa no menu de seleção
        self.selected_initial_time = 300 # Default 5 min
        self.reset_game()

    def reset_game(self):
        self.board = chess.Board()
        self.selected_sq = None
        self.move_history = []
        self.game_over = False
        self.white_time = float(self.selected_initial_time)
        self.black_time = float(self.selected_initial_time)
        self.increment = 3.0
        self.last_time = pygame.time.get_ticks()
        self.pending_move = None
        self.is_promoting = False

    def draw_menu(self):
        self.screen.fill(COLORS['bg'])
        title = self.font_big.render("SELECIONE O TEMPO", True, COLORS['text'])
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))

        # Botões de tempo (Tempo em segundos, Texto)
        options = [(60, "1 MIN"), (300, "5 MIN"), (600, "10 MIN")]
        self.menu_rects = []
        
        for i, (secs, label) in enumerate(options):
            rect = pygame.Rect(WIDTH//2 - 100, 250 + i*70, 200, 50)
            pygame.draw.rect(self.screen, COLORS['menu_btn'], rect, border_radius=10)
            txt = self.font_ui.render(label, True, COLORS['text'])
            self.screen.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))
            self.menu_rects.append((rect, secs))

    def draw_board(self):
        for r in range(8):
            for c in range(8):
                color = COLORS['light'] if (r + c) % 2 == 0 else COLORS['dark']
                square = chess.square(c, 7-r)
                if self.selected_sq == square: color = COLORS['highlight']
                pygame.draw.rect(self.screen, color, (c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

                piece = self.board.piece_at(square)
                if piece:
                    p_char = piece.unicode_symbol()
                    p_color = COLORS['piece_white'] if piece.color == chess.WHITE else COLORS['piece_black']
                    img = self.font_pieces.render(p_char, True, p_color)
                    self.screen.blit(img, img.get_rect(center=(c*SQ_SIZE + SQ_SIZE//2, r*SQ_SIZE + SQ_SIZE//2)))

    def draw_sidebar(self):
        pygame.draw.rect(self.screen, COLORS['bg'], (600, 0, 200, 600))
        w_min, w_sec = divmod(int(self.white_time), 60)
        b_min, b_sec = divmod(int(self.black_time), 60)
        
        self.screen.blit(self.font_ui.render(f"BRANCAS: {w_min:02}:{w_sec:02}", True, (255,255,255)), (615, 30))
        self.screen.blit(self.font_ui.render(f"PRETAS: {b_min:02}:{b_sec:02}", True, (150,150,150)), (615, 60))

        self.btn_restart = pygame.Rect(620, 530, 160, 40)
        pygame.draw.rect(self.screen, COLORS['button'], self.btn_restart, border_radius=5)
        self.screen.blit(self.font_ui.render("RESTART", True, (255,255,255)), (660, 537))

    def draw_promotion_overlay(self):
        overlay = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)); self.screen.blit(overlay, (0,0))
        pieces = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
        self.promo_rects = []
        for i, pt in enumerate(pieces):
            rect = pygame.Rect(100 + i*110, 250, 100, 100)
            pygame.draw.rect(self.screen, COLORS['light'], rect, border_radius=10)
            p_char = chess.Piece(pt, self.board.turn).unicode_symbol()
            img = self.font_pieces.render(p_char, True, COLORS['piece_black'])
            self.screen.blit(img, img.get_rect(center=rect.center))
            self.promo_rects.append((rect, pt))

    def update_timer(self):
        if self.game_over or self.is_promoting or self.in_menu: return
        now = pygame.time.get_ticks()
        dt = (now - self.last_time) / 1000.0
        self.last_time = now
        if self.board.turn == chess.WHITE: self.white_time -= dt
        else: self.black_time -= dt
        if self.white_time <= 0 or self.black_time <= 0: self.game_over = True

    def handle_click(self, pos):
        # Clique no Menu Inicial
        if self.in_menu:
            for rect, secs in self.menu_rects:
                if rect.collidepoint(pos):
                    self.selected_initial_time = secs
                    self.reset_game()
                    self.in_menu = False
            return

        # Clique no Restart (Volta ao Menu)
        if hasattr(self, 'btn_restart') and self.btn_restart.collidepoint(pos):
            self.in_menu = True
            return

        if self.is_promoting:
            for rect, pt in self.promo_rects:
                if rect.collidepoint(pos):
                    move = chess.Move(self.pending_move.from_square, self.pending_move.to_square, promotion=pt)
                    self.execute_move(move)
                    self.is_promoting = False
            return

        if pos[0] > 600 or self.game_over: return # pos[0] para evitar erro de tupla

        c, r = pos[0] // SQ_SIZE, 7 - (pos[1] // SQ_SIZE)
        sq = chess.square(c, r)

        if self.selected_sq is None:
            piece = self.board.piece_at(sq)
            if piece and piece.color == self.board.turn: self.selected_sq = sq
        else:
            move = chess.Move(self.selected_sq, sq)
            is_promo = False
            piece = self.board.piece_at(self.selected_sq)
            if piece and piece.piece_type == chess.PAWN:
                if (piece.color == chess.WHITE and r == 7) or (piece.color == chess.BLACK and r == 0):
                    is_promo = True

            if is_promo:
                if chess.Move(self.selected_sq, sq, chess.QUEEN) in self.board.legal_moves:
                    self.pending_move, self.is_promoting = move, True
            elif move in self.board.legal_moves:
                self.execute_move(move)
            self.selected_sq = None

    def execute_move(self, move):
        self.move_history.append(self.board.san(move))
        self.board.push(move)
        if self.board.turn == chess.BLACK: self.white_time += self.increment
        else: self.black_time += self.increment
        if self.board.is_game_over(): self.game_over = True
        self.last_time = pygame.time.get_ticks()

    def run(self):
        while True:
            self.update_timer()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)

            if self.in_menu:
                self.draw_menu()
            else:
                self.screen.fill(COLORS['bg'])
                self.draw_board()
                self.draw_sidebar()
                if self.is_promoting: self.draw_promotion_overlay()
                if self.game_over:
                    txt = self.font_ui.render("FIM DE JOGO!", True, (255, 50, 50))
                    self.screen.blit(txt, (200, 280))

            pygame.display.flip()
            self.clock.tick(FPS)

if __name__ == "__main__":
    ChessGame().run()
