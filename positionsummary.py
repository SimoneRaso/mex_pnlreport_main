class PositionSummary:
    def __init__(self,
                 symbol: str,
                 unrealizedProfit: float = 0.0,
                 entryPrice: float = 0.0,
                 positionAmt: float = 0.0,
                 tradeCount: int = 0,
                 pnl: float = 0.0,
                 exposure: float = 0.0,
                 exposurePerc: float = 0.0,
                 openingOrderCount: int = 0,
                 closingOrderCount: int = 0,
                 openingOrderQty: float = 0.0,
                 closingOrderQty: float = 0.0,
                 openingOrderValue: float = 0.0,
                 closingOrderValue: float = 0.0,
                 grossRealizedPnl: float = 0.0,
                 fundingFee: float = 0.0,
                 commission: float = 0.0,
                 realizedPnlPerc: float = 0.0,
                 tradeCountPerc: float = 0.0,
                 openingOrderValuePerc: float = 0.0,
                 lastGridExposure: float = 0.0,
                 lastGridLoss: float = 0.0,
                 tpPrice: float = 0.0,
                 currentPrice: float = 0.0,
                 diffCurPriceFromTpPerc: float = 0.0,
                 leverage: float = 0.0,
                 lastGridCost: float = 0.0,
                 lastGridEntryPrice: float = 0.0
                 ):
        self.symbol: str = symbol
        self.unrealizedProfit: float = unrealizedProfit
        self.entryPrice: float = entryPrice
        self.positionAmt: float = positionAmt
        self.tradeCount: int = tradeCount
        self.realizedPnl: float = pnl
        self.exposure: float = exposure
        self.exposurePerc: float = exposurePerc
        self.openingOrderCount: int = openingOrderCount
        self.closingOrderCount: int = closingOrderCount
        self.openingOrderQty: float = openingOrderQty
        self.closingOrderQty: float = closingOrderQty
        self.openingOrderValue: float = openingOrderValue
        self.closingOrderValue: float = closingOrderValue
        self.grossRealizedPnl: float = grossRealizedPnl
        self.fundingFee: float = fundingFee
        self.commission: float = commission
        self.realizedPnlPerc: float = realizedPnlPerc
        self.tradeCountPerc: float = tradeCountPerc
        self.openingOrderValuePerc: float = openingOrderValuePerc
        self.lastGridExposure: float = lastGridExposure
        self.lastGridLoss: float = lastGridLoss
        self.lastGridCost: float = lastGridCost
        self.lastGridEntryPrice: float = lastGridEntryPrice
        self.tpPrice: float = tpPrice
        self.currentPrice: float = currentPrice
        self.diffCurPriceFromTpPerc: float = diffCurPriceFromTpPerc
        self.leverage: float = leverage