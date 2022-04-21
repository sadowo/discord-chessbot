import numpy as np
import re

class Piece:

    def __init__(self, color, type, pos, id):
        self.color = color  # 1 or -1
        self.type = type
        self.pos = np.array(pos)
        self.pinned = set()
        self.incheck = []
        self.id = id

        self.sp = ''
        if type in {'K', 'R'}:
            self.sp = 'Castle'

        self.moves = []

    def __repr__(self):
        dict = {1: '+',-1: '-'}
        return dict[self.color] + self.type

    @staticmethod
    def is_inside(index):
        return np.min(index) >= 0 and np.max(index) <= 7

    def rotation90(self, point):
        return (point - self.pos)[::-1] * (-1, 1) + self.pos

    def merrygoround(self, board, shift):
        point = self.pos + shift
        for i in range(4):
            point = self.rotation90(point)
            if Piece.is_inside(point) and (board[tuple(point)] is None or board[tuple(point)].color != self.color):
                self.moves.append(tuple(point))
                if board[tuple(point)] is not None and board[tuple(point)].type == 'K':
                    board[tuple(point)].incheck.append(self.pos)

    def straightline(self, board, increment):
        for i in range(4):
            increment = self.rotation90(increment)
            point = self.pos + increment

            while Piece.is_inside(point):
                cur = board[tuple(point)]
                if cur is None:
                    self.moves.append(point)

                elif cur.color == self.color:
                    break

                elif cur.color != self.color:
                    self.moves.append(point)
                    if board[tuple(point)].type == 'K':
                        board[tuple(point)].incheck.append(self.pos)

                    point += increment
                    if board[point].type == 'K':
                        board[point].pinned = set(self.pos)
                    break
                point += increment

    def diag1(self, board, side, forward_side):
        if Piece.is_inside(forward_side) and board[forward_side] is not None and board[forward_side].color != self.color:
            self.moves.append(forward_side)

            if board[forward_side].type == 'K':
                board[forward_side].incheck.append(self.pos)

        if Piece.is_inside(side) and board[side] is not None and board[side].color != self.color and board[side].sp == 'En passant':
            self.moves.append(forward_side)

    def reset(self):
        self.moves = []
        self.pinned = set()
        self.incheck = []

    def legal_moves(self, board, attacked_set: set = None, king = None):
        if attacked_set is None:
            attacked_set = set()

        self.reset()

        if self.type == 'P':

            forward = tuple(self.pos + (self.color, 0))

            if Piece.is_inside(forward) and board[forward] is None:
                self.moves.append(forward)

                forward2 = tuple(self.pos + (self.color * 2, 0))
                if (self.pos[0] * self.color) % 7 == 1 and board[forward2] is None:
                    self.moves.append(forward2)

            self.diag1(board, tuple(self.pos + (0, -1)), tuple(self.pos + (self.color, -1)))
            self.diag1(board, tuple(self.pos + (0, 1)), tuple(self.pos + (self.color, 1)))


        elif self.type == 'N':
            self.merrygoround(board, (2, 1))
            self.merrygoround(board, (2, -1))


        elif self.type == 'K':
            self.merrygoround(board, (1, 0))
            self.merrygoround(board, (1, 1))

            backrank = np.min((0, self.color))
            if self.sp == 'Castle' == board[backrank, 7].sp and {(backrank, i) for i in range(4, 7)} - attacked_set == set() == {board[(backrank, i)] for i in range(4, 7)} - {None}:
                self.moves += (backrank, 6)
            if self.sp == 'Castle' == board[backrank, 0].sp and {(backrank, i) for i in range(2, 5)} - attacked_set == set() == {board[(backrank, i)] for i in range(2, 5)} - {None}:
                self.moves += (backrank, 2)

            self.moves = list(set(self.moves) - attacked_set)


        elif self.type in {'R', 'Q'}:
            self.straightline(board, (1, 0))


        elif self.type in {'B', 'Q'}:
            self.straightline(board, (1, 1))

        if self.pinned != set():
            self.moves = list(self.pinned.intersection(set(self.moves)))

        if king is not None:
            if len(king.incheck) == 2 and self.type != 'K':
                self.moves = []
            elif len(king.incheck) == 1:
                self.moves = list(set(self.moves) - set(king.incheck))

    def move(self, board, to, promote = 'Q'):
        side = tuple(np.array(to) + (-self.color, 0))

        if to in self.moves:

            if self.type != 'K':
                self.sp = ''

            if board[to] is not None:
                pieces[board[to].id] = None

            elif self.type == 'P' and board[to] is None and board[side] is not None and board[side].sp == 'En passant':
                pieces[board[side].id] = None
                board[side] = None

            if self.type == 'P' and (self.pos[0] * self.color) % 7 == 1 and (to[0] * self.color) % 7 == 3:
                self.sp = 'En Passant'

            if self.type == 'P' and (to[0] * self.color) % 7 == 0:
                self.type = promote

            board[tuple(self.pos)], board[to] = None, self
            self.pos = np.array(to)

            if self.type == 'K' and self.sp == 'Castle':
                if to[1] == 2:
                    rook_from = (self.pos[0], 0)
                    rook_to = (self.pos[0], 3)

                elif to[1] == 6:
                    rook_from = (self.pos[0], 7)
                    rook_to = (self.pos[0], 5)

                board[rook_from].pos = rook_to
                board[rook_from], board[rook_to] = None, board[rook_from]
                self.sp = ''
        else:
            print('error')

def all_moves(board, current, opponent):
    attacked_li = []
    for piece in opponent.flatten():
        if piece is not None:
            piece.legal_moves(board)
            attacked_li += piece.moves

    king = current[1, 4]
    for piece in current.flatten():
        if piece is not None:
            piece.legal_moves(board, set(attacked_li), king)



board = np.full((8, 8), None)
piecetype = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
pieces = np.array([[[Piece(1, 'P', (1, i), (0,0,i)) for i in range(8)], [Piece(1, piecetype[i], (0, i), (0,1,i)) for i in range(8)]], [[Piece(-1, 'P', (6, i), (1,0,i)) for i in range(8)], [Piece(-1, piecetype[i], (7, i), (1,1,i)) for i in range(8)]]])
pieces_white = pieces[0]
pieces_black = pieces[1]


board[:2, :] = pieces_white[::-1]
board[6:, :] = pieces_black

all_moves(board, pieces_white, pieces_black)


pieces_white[1,1].move(board, (2,2))

print(board)
print(pieces[0,0,4].sp)

regex = re.compile('((?P<piece>[BKNQR])?(?P<from_x>[a-h])?(?P<from_y>[1-8])?x?(?P<to>[a-h][1-8])(=(?P<promote>[BNQR]))?|(?P<long>O-O-O)|(?P<short>O-O))\+?#?')
def translate(move, current):
    match = regex.match(move)
    piece = match.group('piece')
    from_x = match.group('from_x')
    from_y = match.group('from_y')
    to = match.group('to')
    promote = match.group('promote')
    long = match.group('long')
    short = match.group('short')

    king = current[1, 4]

    if piece is None:
        piece = 'P'

    if promote is None:
        promote = 'Q'

    if from_y is not None:
        from_y = int(from_y) - 1

    if from_x is not None:
        from_x = ord(from_x) - 97

    if to is not None:
        to = ord(to[0]) - 97, int(to[1]) - 1

    elif long is not None:
        to = king.pos[0], 2

    elif short is not None:
        to = king.pos[0], 6
