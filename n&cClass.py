
class nAndc:
    def __init__(self):
        self.__elements = [' '] * 9
        # self.__elements = ['X', 'O', 'O', 'O', 'X', 'O', 'O', 'O', 'X']
        self.__moves = 0
        self.winner = ' '

    def getElem(self, x, y):
        return self.__elements[(x % 3) + 3*(y % 3)]
    
    def setElem(self, x, y, player):
        if self.getElem(x,y) == ' ':
            self.__elements[(x % 3) + 3*(y % 3)] = player
            return True
        else:
            return False
    
    def getMoves(self):
        return self.__moves
    
    def increMoves(self):
        self.__moves += 1
    
    def check(self, x, y):

        # maybe ensure it doesn't check empty elements
        a = self.getElem(x,y)
        if self.getElem(x + 1,y) == a:
            if self.getElem(x - 1,y) == a:
                return True
        if self.getElem(x + 1,y + 1) == a:
            if self.getElem(x - 1,y - 1) == a:
                return True
        if self.getElem(x, y + 1) == a:
            if self.getElem(x, y - 1) == a:
                return True
        return False

class ult_nAndc:

    def __init__(self):
        self.__elements = [nAndc()] * 9
        self.winner = ' '
    
    def getElem(self, x, y):
        return self.__elements[x + 3*y]
    
    def setElem(self, x, y, player):
        if self.getElem(x,y).winner == ' ':
            self.__elements[x + 3*y].winner = player
            return True
        else:
            return False
    
    def check(self, x, y):
        a = self.getElem(x,y)
        if self.getElem(x + 1,y) == a:
            return True
        if self.getElem(x - 1,y) == a:
            return True
        if self.getElem(x,y + 1) == a:
            return True
        if self.getElem(x,y - 1) == a:
            return True


