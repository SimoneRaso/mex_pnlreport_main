from typing import Optional
import json
import datetime
from orderstatus import OrderStatus
from incomesummary import IncomeSummary
from positionsummary import PositionSummary
from botsummaryencoder import BotSummaryEncoder

class BotSummary:
    def __init__(self,
                 name: str,
                 timestamp: int,
                 balance: float = 0.0,
                 totUnrealizedProfit: float = 0.0,
                 totRealizedProfitPerc: float = 0.0,
                 totRealizedProfit: float = 0.0,
                 totInitialMargin: float = 0.0,
                 totOpenOrderInitialMargin: float = 0.0,
                 availableBalance: float = 0.0,
                 totalMaintMargin: float = 0.0,
                 lastGridExposure: float = 0.0,
                 lastGridLoss: float = 0.0,
                 lastGridAvailableBalance: float = 0.0,
                 lastGridExposurePerc: float = 0.0,
                 lastGridLossToLiquidation: float = 0.0
                 # positions: dict[str, PositionSummary] = None,
                 # orders: dict[str, OrderStatus] = None,
                 # incomes: dict[str, IncomeSummary] = None,
                 # positionsTot = None
                 ):
        self.name: str = name
        self.timestamp: int = timestamp
        self.balance: float = balance
        self.totUnrealizedProfit: float = totUnrealizedProfit
        self.totRealizedProfitPerc: float = totRealizedProfitPerc
        self.totRealizedProfit: float = totRealizedProfit
        self.totInitialMargin: float = totInitialMargin
        self.totOpenOrderInitialMargin: float = totOpenOrderInitialMargin
        self.availableBalance: float = availableBalance
        self.totalMaintMargin: float = totalMaintMargin
        self.lastGridExposure: float = lastGridExposure
        self.lastGridLoss: float = lastGridLoss
        self.lastGridAvailableBalance: float = lastGridAvailableBalance
        self.lastGridExposurePerc: float = lastGridExposurePerc
        self.lastGridLossToLiquidation: float = lastGridLossToLiquidation
        self.positions: Optional[dict[str, PositionSummary]] = None
        self.orders: Optional[dict[str, OrderStatus]] = None
        self.incomes: Optional[dict[str, IncomeSummary]] = None
        self.positionsTot: Optional[PositionSummary] = None
        self.start_timestamp: int = 0
        self.end_timestamp: int = 0

    # noinspection PyListCreation
    def to_str(self):
        def zero_to_blank(n: float, f: str):
            return f.format(n) if n != 0 else ''

        tot = self.positionsTot
        fmtl_str =  '| {:12} | {:>12} | {:>18} | {:>15} | {:>12} | {:>12} | {:>21} | {:>16} | {:>26} | {:>16} | {:>15} | {:>15} |'
        fmth_str = '| {:^12} | {:^12} | {:^18} | {:^15} | {:^12} | {:^12} | {:^21} | {:^16} | {:^26} | {:^16} | {:^15} | {:^15} |'
        header  = fmth_str.format('Symbol', 'Unrealized',  'Net Realized', 'Gross Realized', 'Commission', 'Funding', 'Exposure',      'Number of',    'Open Grid Orders',           'Open TP Orders',   'Position', 'Position' )
        header2 = fmth_str.format('',       'Profit',      'Profit',       'Profit',         'Fees',       'Fees',    '(% of wallet)', 'take profits', '  n°  value  (% of wallet)', 'n°  value',        'Amount',   'Entry Price' )

        out_str: list[str] = []
        # out_str.append('#' * len(header))
        # out_str.append('# BOT  {}  updated at: {}'.format(self.name, datetime.datetime.fromtimestamp(self.timestamp / 1000).isoformat(sep=' ', timespec='seconds')))
        # out_str.append('#')
        out_str.append('BOT {}'.format(self.name))
        out_str.append('  from : {}'.format(datetime.datetime.fromtimestamp(self.start_timestamp / 1000).isoformat(sep=' ', timespec='seconds')))
        out_str.append('  to   : {}'.format(datetime.datetime.fromtimestamp(self.end_timestamp / 1000).isoformat(sep=' ', timespec='seconds')))
        out_str.append('')
        out_str.append('Wallet Balance             : {:15,.2f}'.format(self.balance                  ))
        out_str.append('Unrealized Profit          : {:15,.2f}'.format(self.totUnrealizedProfit      ))
        out_str.append('Position Initial Margin    : {:15,.2f}'.format(self.totInitialMargin         ))
        out_str.append('Open Order Initial Margin  : {:15,.2f}'.format(self.totOpenOrderInitialMargin))
        out_str.append('Available Balance          : {:15,.2f}'.format(self.availableBalance         ))
        out_str.append('')
        out_str.append('Today Realized Profit      : {:15,.2f}'.format(self.totRealizedProfit        ))
        out_str.append('Today Realized Profit %    : {:15,.2%}'.format(self.totRealizedProfitPerc    ))
        out_str.append('')
        out_str.append('Last grid exposure         : {:15,.2f}'.format(self.lastGridExposure))
        out_str.append('Last grid loss             : {:15,.2f}'.format(self.lastGridLoss))
        out_str.append('Last grid available balance: {:15,.2f}'.format(self.lastGridAvailableBalance))
        out_str.append('Last grid exposure %       : {:15,.2%}'.format(self.lastGridExposurePerc))
        out_str.append('')
        out_str.append('-' * len(header))
        out_str.append(header)
        out_str.append(header2)
        out_str.append('-' * len(header))
        for p in sorted(self.positions.values(), key=lambda p: -p.realizedPnl):
            out_str.append(fmtl_str.format(
                p.symbol,
                zero_to_blank(p.unrealizedProfit, '{:,.2f}'),
                '{} {:>8}'.format(
                    zero_to_blank(p.realizedPnl, '{:,.2f}'),
                    zero_to_blank(p.realizedPnl / tot.realizedPnl, '({:,.1%})') if tot.realizedPnl != 0 else '-'
                ),
                zero_to_blank(p.grossRealizedPnl, '{:,.2f}'),
                zero_to_blank(p.commission, '{:,.2f}'),
                zero_to_blank(p.fundingFee, '{:,.2f}'),
                '{} {:>8}'.format(
                    zero_to_blank(p.exposure, '{:,.2f}'),
                    zero_to_blank(p.exposurePerc, '({:,.1%})')
                ),
                '{} {:>8}'.format(
                    zero_to_blank(p.tradeCount, '{:d}'),
                    zero_to_blank(p.tradeCountPerc, '({:,.1%})')
                ),
                '{} {:>12} {:>9}'.format(
                    zero_to_blank(p.openingOrderCount, '{:,d}'),
                    zero_to_blank(p.openingOrderValue, '{:,.2f}'),
                    zero_to_blank(p.openingOrderValuePerc, '({:,.1%})')
                ),
                '{} {:>12}'.format(
                    zero_to_blank(p.closingOrderCount, '{:,d}'),
                    zero_to_blank(p.closingOrderValue, '{:,.2f}')
                ),
                zero_to_blank(p.positionAmt, '{:,.6f}'),
                zero_to_blank(p.entryPrice, '{:,.6f}'),
            ))
        out_str.append('=' * len(header))
        out_str.append(fmtl_str.format(
            'TOT',
            zero_to_blank(tot.unrealizedProfit, '{:,.2f}'),
            '{} {:>8}'.format(
                zero_to_blank(tot.realizedPnl, '{:,.2f}'),
                zero_to_blank(1, '({:,.1%})')
            ),
            zero_to_blank(tot.grossRealizedPnl, '{:,.2f}'),
            zero_to_blank(tot.commission, '{:,.2f}'),
            zero_to_blank(tot.fundingFee, '{:,.2f}'),
            '{} {:>8}'.format(
                zero_to_blank(tot.exposure, '{:,.2f}'),
                zero_to_blank(tot.exposurePerc, '({:,.1%})')
            ),
            '{} {:>8}'.format(
                zero_to_blank(tot.tradeCount, '{:,d}'),
                zero_to_blank(1, '({:,.1%})')
            ),
            '{} {:>12} {:>9}'.format(
                zero_to_blank(tot.openingOrderCount, '{:,d}'),
                zero_to_blank(tot.openingOrderValue, '{:,.2f}'),
                zero_to_blank(tot.openingOrderValuePerc, '({:,.1%})')
            ),
            '{} {:>12}'.format(
                zero_to_blank(tot.closingOrderCount, '{:,d}'),
                zero_to_blank(tot.closingOrderValue, '{:,.2f}')
            ),
            '',
            '',
        ))
        out_str.append('-' * len(header))
        return '\n'.join(out_str)

    def to_json(self):
        return json.dumps(self, indent=2, cls=BotSummaryEncoder)