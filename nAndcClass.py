
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
            self.__moves += 1
            return True
        else:
            return False
    
    def getMoves(self):
        return self.__moves
    
    def getWinner(self):
        return self.__winner
    
    def check(self, x, y):
        if self.__moves > 2:
            # maybe ensure it doesn't check empty elements
            a = self.getElem(x,y)
            if self.getElem(x + 1,y) == a:
                if self.getElem(x - 1,y) == a:
                    self.__winner = a
                    return True
            if self.getElem(x + 1,y + 1) == a:
                if self.getElem(x - 1,y - 1) == a:
                    self.__winner = a
                    return True
            if self.getElem(x, y + 1) == a:
                if self.getElem(x, y - 1) == a:
                    self.__winner = a
                    return True
        return False
    
    def clear(self):
        for i in range(9):
            self.__elements = ' '

class ult_nAndc:

    def __init__(self):
        self.__elements = [nAndc()] * 9
        self.__victor = ' '
        self.__moves = 0
        self.__players = {'X','Y','Z'}
    
    def getElem(self, x, y):
        if x > 2 or x < 0 or y > 2 or y < 0:
            return ' '
        return self.__elements[x + 3*y]
    
    def setElem(self, x, y, player):
        if self.getElem(x,y).getWinner() in self.__players :
            self.__elements[x + 3*y].__victor = player
            self.__moves += 1
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