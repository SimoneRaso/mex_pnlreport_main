class IncomeSummary:
    def __init__(self,
                 count: int = 0,
                 netRealizedPnl: float = 0.0,
                 transfer: float = 0.0,
                 welcomeBonus: float = 0.0,
                 realizedPnl: float = 0.0,
                 funding_fee: float = 0.0,
                 commission: float = 0.0,
                 insuranceClear: float = 0.0,
                 crossCollateralTransfer: float = 0.0,
                 commissionRebate: float = 0.0
                 ):
        self.count: int = count
        self.netRealizedPnl: float = netRealizedPnl
        self.transfer: float = transfer
        self.welcomeBonus: float = welcomeBonus
        self.realizedPnl: float = realizedPnl
        self.funding_fee: float = funding_fee
        self.commission: float = commission
        self.insuranceClear: float = insuranceClear
        self.crossCollateralTransfer: float = crossCollateralTransfer
        self.commissionRebate = commissionRebate