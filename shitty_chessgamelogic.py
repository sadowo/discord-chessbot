import re
import copy

import numpy as np

class InvalidMove(Exception):
    pass

class AmbiguousMove(Exception):
    pass

class ParseError(Exception):
    pass

class Piece:

    chess_symbols = {1: {'K': '♔', 'Q': '♕', 'B': '♗', 'N': '♘', 'P': '♙', 'R': '♖'}, -1: {'K': '♚', 'Q': '♛', 'B': '♝', 'N': '♞', 'P': '♟', 'R': '♜'}}

    def __init__(self, color, type, pos, id):
        self.color = color  # 1 or -1
        self.type = type
        self.pos = pos
        self.pinned = set()
        self.incheck = []
        self.id = id
        self.blockcheck = []
        self.sp = ''
        if type in {'K', 'R'}:
            self.sp = 'Castle'

        self.moves = []

    def __eq__(self, other):
        if isinstance(other, Piece):
            return self.__dict__ == other.__dict__
        return False


    def __repr__(self):
        return Piece.chess_symbols[self.color][self.type]

    @staticmethod
    def is_inside(index):
        return np.min(index) >= 0 and np.max(index) <= 7

    @staticmethod
    def rotation90(point, center = np.array([0,0])):
        return (point - center)[::-1] * (-1, 1) + center

    def merrygoround(self, board, shift, attacker = False):
        point = np.array(self.pos) + shift
        for i in range(4):
            point = Piece.rotation90(point, np.array(self.pos))
            if Piece.is_inside(point) and (board[tuple(point)] is None or attacker or board[tuple(point)].color != self.color):
                self.moves.append(tuple(point))
                if board[tuple(point)] is not None and board[tuple(point)].type == 'K':
                    board[tuple(point)].incheck.append(self.pos)

    def straightline(self, board, increment, attacker = False):
        for i in range(4):
            increment = Piece.rotation90(increment)
            point = np.array(self.pos) + increment
            block = []
            while Piece.is_inside(point):
                cur = board[tuple(point)]
                if cur is None:
                    self.moves.append(tuple(point))
                    block.append(tuple(point))
                elif cur.color == self.color:
                    if attacker:
                        self.moves.append(tuple(point))
                    break

                elif cur.color != self.color:
                    self.moves.append(tuple(point))
                    if board[tuple(point)] is not None and board[tuple(point)].type == 'K':
                        board[tuple(point)].incheck.append(self.pos)
                        board[tuple(point)].blockcheck += block

                    point += increment
                    if Piece.is_inside(point) and board[tuple(point)] is not None and board[tuple(point)].type == 'K':
                        board[tuple(point - increment)].pinned = set(block+[self.pos])
                    break
                point += increment

    def diag1(self, board, side, forward_side, attacker = False):
        if Piece.is_inside(forward_side) and board[forward_side] is not None and board[forward_side].color != self.color:
            self.moves.append(forward_side)

            if board[forward_side].type == 'K':
                board[forward_side].incheck.append(self.pos)

        elif Piece.is_inside(forward_side) and attacker:
            self.moves.append(forward_side)

        if Piece.is_inside(side) and board[side] is not None and board[side].color != self.color and board[side].sp == 'En Passant':
            self.moves.append(forward_side)
            print('yo')

    def reset(self):
        self.moves = []
        self.pinned = set()
        self.incheck = []
        self.blockcheck = []

    def legal_moves(self, board, attacked_set: set = None, king = None):
        if attacked_set is None:
            attacked_set = set()

        attacker = king is None

        if self.type == 'P':

            forward = tuple(np.array(self.pos) + (self.color, 0))

            if Piece.is_inside(forward) and board[forward] is None and king is not None:
                self.moves.append(forward)

                forward2 = tuple(np.array(self.pos) + (self.color * 2, 0))
                if (self.pos[0] * self.color) % 7 == 1 and board[forward2] is None:
                    self.moves.append(forward2)

            self.diag1(board, tuple(np.array(self.pos) + (0, -1)), tuple(np.array(self.pos) + (self.color, -1)), attacker)
            self.diag1(board, tuple(np.array(self.pos) + (0, 1)), tuple(np.array(self.pos) + (self.color, 1)), attacker)


        elif self.type == 'N':
            self.merrygoround(board, (2, 1), attacker)
            self.merrygoround(board, (2, -1), attacker)


        elif self.type == 'K':
            self.merrygoround(board, (1, 0), attacker)
            self.merrygoround(board, (1, 1), attacker)

            backrank = {1: 0, -1: 7}[self.color]

            if board[backrank, 7] is not None and self.sp == 'Castle' == board[backrank, 7].sp and {(backrank, i) for i in range(4, 7)}.intersection(attacked_set) == set() and np.equal(board[backrank,5:7], None).all():
                self.moves.append((backrank, 6))
            if board[backrank, 0] is not None and self.sp == 'Castle' == board[backrank, 0].sp and {(backrank, i) for i in range(2, 5)}.intersection(attacked_set) == set() and np.equal(board[backrank,2:4], None).all():
                self.moves.append((backrank, 2))
            self.moves = list(set(self.moves) - attacked_set)

        if self.type in {'R', 'Q'}:
            self.straightline(board, (1, 0), attacker)


        if self.type in {'B', 'Q'}:
            self.straightline(board, (1, 1), attacker)

        if self.pinned != set():
            self.moves = list(self.pinned.intersection(set(self.moves)))

        if king is not None and self.type != 'K':
            if len(king.incheck) == 2:
                self.moves = []
            elif len(king.incheck) == 1:
                self.moves = list(set(self.moves).intersection(set(king.incheck + king.blockcheck)))

    def move(self, board, pieces, to, promote = None):
        side = tuple(np.array(to) + (-self.color, 0))
        if promote is None:
            promote = 'Q'

        if to in self.moves:

            if self.type != 'K':
                self.sp = ''

            if board[to] is not None:
                pieces[board[to].id] = None

            elif self.type == 'P' and board[to] is None and board[side] is not None and board[side].sp == 'En Passant':
                pieces[board[side].id] = None
                board[side] = None

            if self.type == 'P' and (self.pos[0] * self.color) % 7 == 1 and (to[0] * self.color) % 7 == 3:
                self.sp = 'En Passant'

            if self.type == 'P' and (to[0] * self.color) % 7 == 0:
                self.type = promote

            board[self.pos], board[to] = None, self
            self.pos = to

            if self.type == 'K' and self.sp == 'Castle':
                if to[1] % 4 == 2:
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
            raise InvalidMove

class Game:
    def __init__(self):
        piecetype = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        self.pieces = np.array([[[Piece(1, 'P', (1, i), (0, 0, i)) for i in range(8)],  # white pawns
                            [Piece(1, piecetype[i], (0, i), (0, 1, i)) for i in range(8)]], # white pieces
                           [[Piece(-1, 'P', (6, i), (1, 0, i)) for i in range(8)], # black pawns
                            [Piece(-1, piecetype[i], (7, i), (1, 1, i)) for i in range(8)]]]) # black pieces

        self.board = np.full((8, 8), None)

        self.board[:2, :] = self.pieces[0,::-1]
        self.board[6:, :] = self.pieces[1]

        self.turn = 1
        self.allpositions = []
        self.moves = [[],[]] # white moves, black moves
        self.game_status = ''
        self.fiftymoves = 0
        self.history = []
        self.lastmove = ''
        self.regex_translate = re.compile('((?P<piece>[BKNPQR])?(?P<from_y>[a-h])?(?P<from_x>[1-8])?(?P<takes>x)?(?P<to_yx>[a-h][1-8])(?P<promote>=[BNQR])?|(?P<long>O-O-O)|(?P<short>O-O))(?P<check>\+)?(?P<mate>#)?')
        self.regex_pawnortakes = re.compile('[Px]')
    def __repr__(self):

        return str(np.select([np.equal(self.board, None)], [''] ,self.board)[::-1]).replace(' [', '').replace('[', '').replace(']', '').replace("''",'.')

    def all_moves(self):
        dico = {1 : (0,1), -1: (1,0)}
        current, opponent = dico[self.turn]

        for piece in self.pieces.flatten():
            if piece is not None:
                piece.reset()

        self.moves[opponent] = []
        for piece in self.pieces[opponent].flatten():
            if piece is not None:
                piece.legal_moves(self.board)
                self.moves[opponent] += piece.moves

        self.moves[current] = []

        king = self.pieces[current][1, 4]
        for piece in self.pieces[current].flatten():
            if piece is not None:
                piece.legal_moves(self.board, set(self.moves[opponent]), king)
                self.moves[current] += piece.moves


    def checkmate(self):
        dico = {1 : 0, -1: 1}
        current = dico[self.turn]
        king = self.pieces[current][1, 4]

        if self.moves[current] == []:
            if king.incheck == []:
                self.game_status = 'Stalemate'
            else:
                dico = {1: 'White', -1: 'Black'}
                self.game_status = dico[-king.color] + ' Wins'

    def threefoldrepetition(self):
        self.allpositions.append(copy.deepcopy(self.pieces))
        if np.all(self.allpositions == self.pieces, axis = (1,2,3)).sum() == 3:
            self.game_status = 'Draw by repetition'

    def insufficientmaterial(self):
        def check_alive(pieces):
            pieces_alive = []
            for piece in pieces:
                if piece is not None and piece.type != 'K':
                    pieces_alive.append(piece.type)
            if len(pieces_alive) == 0 or len(pieces_alive) == 1 and pieces_alive[0] in {'N', 'B'} or len(pieces_alive) == 2 and pieces_alive[0] == 'N' == pieces_alive[1]:
                return True
            return False

        if check_alive(self.pieces[0].flatten()) and check_alive(self.pieces[1].flatten()):
            self.game_status = 'Draw by insufficient material'

    def fiftymovesrule(self):
        if self.lastmove != '' and self.regex_pawnortakes.match(self.lastmove):
            self.fiftymoves = 0
        else:
            self.fiftymoves += 1

        if self.fiftymoves == 100:
            self.game_status = 'Draw by 50-move rule'

    def translate(self, move):
        match = self.regex_translate.match(move)
        if match is None:
            raise ParseError

        piece = match.group('piece')
        from_x = match.group('from_x')
        from_y = match.group('from_y')
        to_yx = match.group('to_yx')
        promote = match.group('promote')
        long = match.group('long')
        short = match.group('short')
        takes = match.group('takes')
        check = match.group('check')
        mate = match.group('mate')

        dico = {1: 0, -1: 1}
        current = dico[self.turn]
        king = self.pieces[current][1, 4]

        if piece is None:
            piece = 'P'

        if to_yx is not None:
            to = int(to_yx[1]) - 1, ord(to_yx[0]) - 97


            if from_x is not None:
                x = int(from_x) - 1

            if from_y is not None:
                y = ord(from_y) - 97

            elif piece == 'P':
                from_y = to_yx[0]
                y = ord(from_y) - 97


            if from_x is None or from_y is None:
                possiblepieces = []
                if from_x is not None:
                    for p in self.board[x, :]:
                        if p is not None and p.type == piece and p.color == self.turn and (to in p.moves):
                            possiblepieces.append(p)

                elif from_y is not None:
                    for p in self.board[:, y]:
                        if p is not None and p.type == piece and p.color == self.turn and (to in p.moves):
                            possiblepieces.append(p)

                else:
                    for p in self.pieces[current].flatten():
                        if p is not None and p.type == piece and (to in p.moves):
                            possiblepieces.append(p)

                if len(possiblepieces) == 0:
                    raise InvalidMove
                elif len(possiblepieces) >= 2:
                    raise AmbiguousMove

                else:
                    x,y = possiblepieces[0].pos

        if long is not None:
            piece = 'K'
            to = king.pos[0], 2
            x,y = king.pos
            notation = move
        elif short is not None:
            piece = 'K'
            to = king.pos[0], 6
            x, y = king.pos
            notation = move

        if to_yx is not None:
            notation = piece + str(x+1) + chr(y+97) + (takes or '') + to_yx + (check or '') + (mate or '') + (promote or '')


        if promote is not None:
            promote = promote[1]

        return (x,y), to, notation, promote

    def checkgamestatus(self):
        self.all_moves()

        self.threefoldrepetition()
        self.insufficientmaterial()
        self.fiftymovesrule()
        self.checkmate()



    def playturn(self, userinput):
        origin, to, notation, promote = self.translate(userinput)
        self.history.append(userinput)
        self.lastmove = notation
        self.board[origin].move(self.board, self.pieces, to, promote)
        self.turn *= -1

    def play(self):
        while True:
            print(self)
            self.checkgamestatus()
            if self.game_status != '':
                break
            while True:
                try:
                    self.playturn(input('What is your move ? \n'))
                except InvalidMove:
                    print('Invalid Move')
                except AmbiguousMove:
                    print('Ambiguous Move')
                except ParseError:
                    print('Failed to parse Move')
                else:
                    break

    def pgnreplay(self, pgn):
        pgn = pgn.replace('+', '').replace('?', '').replace('!', '').replace('\n', ' ').replace('-', '').replace('OOO','O-O-O').replace('OO','O-O')
        pgn = re.sub('\d+\.','', pgn)
        pgn = re.sub('  +',' ', pgn)
        pgn = re.sub('^ | $','', pgn)
        print(pgn)
        pgn = pgn.split(' ')

        print(self)
        for move in pgn:
            print(move)
            self.checkgamestatus()
            if self.game_status != '':
                break

            try:
                self.playturn(move)
            except InvalidMove:
                print('Invalid Move')
                break
            except AmbiguousMove:
                print('Ambiguous Move')
                break
            except ParseError:
                print('Failed to parse Move')
                break

            print(self)

        self.checkgamestatus()
        print(self.game_status)


##
if __name__ == "__main__":
    game = Game()
    game.play()

    print(game.game_status)
##
    pgn1 = '1.c4 c6 2.Nc3 d5 3.e3 Nf6 4.Nf3 g6 5.b3 Bg7 6.Bb2 O-O 7.Be2 Bg4 8.O-O e6 9.h3 Bxf3 10.Bxf3 Nbd7 11.d4 Re8 12.e4 dxe4 13.Nxe4 Nxe4 14.Bxe4 e5 15.Re1 exd4 16.Bxd4 Bxd4 17.Qxd4 Nf6 18.Qxd8 Raxd8 19.Bf3 Rxe1+ 20.Rxe1 Kf8 21.Rd1 Rxd1+ 22.Bxd1 Ne4 23.Bc2 Nc3 24.a4 Ke7 25.Kf1 Kd6 26.b4 c5 27.b5 Ke5 28.Ke1 Kd4 29.Bb3 Ne4 30.f3 Nd6 31.Kd2 Nxc4+ 32.Ke2 Nd6 33.Kd2 c4 34.Bc2 b6 35.h4 h6 36.g4 g5 37.hxg5 hxg5 38.Bh7 f6 39.Bg8 c3+ 40.Kc2 Nc4 41.Bh7 Nd2'

    pgn2 = '1. d4 d5 2. Nf3 e6 3. e3 c5 4. c4 Nc6 5. Nc3 Nf6 6. dxc5 Bxc5 7. a3 a6 8. b4 Bd6 9. Bb2 O-O 10. Qd2 Qe7 11. Bd3 dxc4 12. Bxc4 b5 13. Bd3 Rd8 14. Qe2 Bb7 15. O-O Ne5 16. Nxe5 Bxe5 17. f4 Bc7 18. e4 Rac8 19. e5 Bb6+ 20. Kh1 Ng4 21. Be4 Qh4 22. g3 Rxc3 23. gxh4 Rd2 24. Qxd2 Bxe4+ 25. Qg2 Rh3'

    pgn3 = '1.d4 d5 2.c4 e6 3.Nc3 c6 4.e4 dxe4 5.Nxe4 Bb4+ 6.Bd2 Qxd4 7.Bxb4 Qxe4+ 8.Be2 Na6 9.Bd6 Qxg2 10.Qd2! Nf6 11.Bf3 Qg6 12.O-O-O e5 13.Bxe5 Be6 14.Ne2 Qf5 15.Bf4 Qc5 16.Nc3! O-O 17.Bd6 Qxc4 18.Rhg1! Bf5 19.Rxg7+! Kxg7 20.Qg5+ Bg6 21.Be5 Qe6 22.Ne4 h6 23.Bxf6+ Kh7 24.Qh4 Qxa2 25.Bg5! Qc4+ 26.Kd2! Qb4+ 27.Ke3?? h5? 28.Be7! Qb3+ 29.Kf4 Qb5? 30.Rd5!! +- cxd5 31.Bxh5! dxe4 32.Be2+ Kg8 33.Bxb5 Nc7 34.Bc4! Ne8 35.Qh6 Ng7 36.Bf6 Nh5+ 37.Kg5 Nxf6 38.Kxf6'

    pgn4 = '1. e4 c6 2. d4 d5 3. Nc3 de4 4. Ne4 Bf5 5. Ng3 Bg6 6. h4 h6 7. Nf3 Nd7 8. h5 Bh7 9. Bd3 Bd3 10. Qd3 e6 11. Bf4 Ngf6 12. O-O-O Be7 13. Ne4 Qa5 14. Kb1 O-O 15. Nf6 Nf6 16. Ne5 Rad8 17. Qe2 c5 18. Ng6 fg6 19. Qe6 Kh8 20. hg6 Ng8 21. Bh6 gh6 22. Rh6 Nh6 23. Qe7 Nf7 24. gf7 Kg7 25. Rd3 Rd6 26. Rg3 Rg6 27. Qe5 Kf7 28. Qf5 Rf6 29. Qd7'

    pgn5 = '1. c4 g6 2. Nc3 Bg7 3. g3 c5 4. Bg2 Nc6 5. b3 e6 6. Bb2 Nge7 7. Na4 Bb2 8. Nb2 O-O 9. e3 d5 10. cd5 Nd5 11. Ne2 b6 12. d4 Ba6 13. dc5 Qf6 14. Nc4 Nc3 15. Nc3 Qc3 16. Kf1 Rfd8 17. Qc1 Bc4 18. bc4 Qd3 19. Kg1 Rac8 20. cb6 ab6 21. Qb2 Na5 22. h4 Nc4 23. Qf6 Qf5 24. Qf5 gf5 25. h5 Rd2 26. Rc1 Rc5 27. Rh4 Ne5 28. Rc5 bc5 29. Ra4 c4 30. h6 Kf8 31. Ra8 Ke7 32. Rc8 Ra2 33. Bf1 Rc2 34. Kg2 Ng4 35. Kg1 Rf2 36. Bc4 Rf3 37. Kg2 Re3 38. Rh8 Nh6 39. Rh7 Ng4 40. Bb5 Rb3 41. Bc6 Rb2 42. Kg1 Ne5 43. Ba8 Rb8 44. Bh1'

    pgn6 = '1.a4 Nf6 2.a5 b5 3.axb6 axb6 4.Rxa8 Nc6 5.Rxc8 Nd4 6.Ra8 Nb5 7.c4 Nd6 8.Qa4 Nde4 9.d3 Nxf2 10.e4 N2xe4 11.dxe4 Qb8 12.Qxd7+ Kxd7 13.e5 Kd8 14.e6 Qc8 15.Rxc8+ Kxc8 16.Bd3 b5 17.Nf3 bxc4 18.O-O c3 19.Nxc3 g5 20.exf7 Bg7 21.f8=Q+ Rxf8 22.Ne5 g4 23.Nf3 g3 24.Ne5 gxh2+ 25.Kf2 h1=N+ 26.Kg1 Ng3 27.Re1 h6 28.Re2 h5 29.Re3 h4 30.Re4 h3 31.Re3 h2+ 32.Kf2 h1=N+ 33.Ke1 Nf1 34.Rg3 Nh5 35.Be2 Nh1xg3 36.Bf3 Nh1 37.Bg4+ e6 38.Bf3 Nh1g3 39.Bg4 Ne3 40.Kd2 Nef1+ 41.Kd1 Bh6 42.Ne4 Rh8 43.Nc6 Rg8 44.Nc5 Rh8 45.Ne7+ Kd8 46.Bg5 Bg7 47.Nc6+ Kc8 48.Bxe6#'
##

    # game = Game()
    # game.pgnreplay(pgn6)








