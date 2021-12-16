class OrderStatus:
    def __init__(self,
                 openingCount: int = 0,
                 closingCount: int = 0,
                 openingAmt: float = 0.0,
                 closingAmt: float = 0.0,
                 openingValue: float = 0.0,
                 closingValue: float = 0.0,
                 lastGridPrice: float = 0.0,
                 tpPrice: float = 0.0
                 ):
        self.openingCount: int = openingCount
        self.closingCount: int = closingCount
        self.openingAmt: float = openingAmt
        self.closingAmt: float = closingAmt
        self.openingValue: float = openingValue
        self.closingValue: float = closingValue
        self.lastGridPrice: float = lastGridPrice
        self.tpPrice: float = tpPrice