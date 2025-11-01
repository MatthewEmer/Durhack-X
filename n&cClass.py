
class nAndc:
    def __init__(self):
        # self.__elements = [] * 9
        self.__elements = ['X', 'O', 'O', 'O', 'X', 'O', 'O', 'O', 'X']
        self.__moves = 0

    def getElem(self, x, y):
        return self.__elements[(x % 3) + 3*(y % 3)]
    
    def setElem(self, x, y, player):
        self.__elements[(x % 3) + 3*(y % 3)] = player
    
    def getMoves(self):
        return self.__moves
    
    def increMoves(self):
        self.__moves += 1
    
    def check(self, x, y):

        # maybe ensure it doesn't check empty elements
         
        if self.getElem(x + 1,y) == self.getElem(x,y):
            if self.getElem(x - 1,y) == self.getElem(x,y):
                return True
        if self.getElem(x + 1,y + 1) == self.getElem(x,y):
            if self.getElem(x - 1,y - 1) == self.getElem(x,y):
                return True
        if self.getElem(x, y + 1) == self.getElem(x,y):
            if self.getElem(x, y - 1) == self.getElem(x,y):
                return True
        return False


    


nc = nAndc()



print(nc.check(0,0))
