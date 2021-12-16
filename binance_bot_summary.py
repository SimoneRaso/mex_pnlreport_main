import datetime
from binance.client import Client
from sys import platform
from orderstatus import OrderStatus
from incomesummary import IncomeSummary
from positionsummary import PositionSummary
from botsummary import BotSummary

class BinanceBotSummary:
    def __init__(self,
                bot_name : str, 
                api_key : str, 
                api_secret : str, 
                start_timestamp : int = 0,
                end_timestamp :  int = 0) -> None:
        self.bot_name : str = bot_name
        self.api_key : str = api_key
        self.api_secret : str = api_secret
        self.start_timestamp :  int = start_timestamp
        self.end_timestamp :  int = end_timestamp

    def get_JSON_summary(self) -> BotSummary:
        client = Client(self.api_key, self.api_secret)
        
        print ('binance_bot_summary logs')
        now=datetime.datetime.now(tz=datetime.timezone.utc)
        print ('now=',now)
        bot_summary = BotSummary(self.bot_name, int(now.timestamp() * 1000))#1000 = seconds to milliseconds

        if self.start_timestamp == 0:
            self.start_timestamp = int(datetime.datetime(now.year, now.month, now.day, tzinfo=datetime.timezone.utc).timestamp() * 1000) #1000 = seconds to milliseconds
            print('start_timestamp=0 pertanto lo calcolo: ', self.start_timestamp)

        if self.end_timestamp == 0:
            self.end_timestamp = int(datetime.datetime(now.year, now.month, now.day,23,59,59, tzinfo=datetime.timezone.utc).timestamp() * 1000) #1000 = seconds to milliseconds
            print('end_timestamp=0 pertanto lo calcolo: ', self.end_timestamp)

        #loggo i valori delle date 
        print("start_timestamp:",self.start_timestamp," end_timestamp:",self.end_timestamp)
        start_win=datetime.date.fromtimestamp(self.start_timestamp/1000)
        end_win=datetime.date.fromtimestamp(self.end_timestamp/1000)
        print("cerco elementi compresi tra (start_win): ",start_win.strftime("%Y-%m-%d %H:%M:%S")," e (end_win): ",end_win.strftime("%Y-%m-%d %H:%M:%S"))

        bot_summary.start_timestamp = self.start_timestamp
        bot_summary.end_timestamp = self.end_timestamp

        positions_by_symbol = {}
        orders_by_symbol = {}

        try:
            account = client.futures_account(timestamp= now.timestamp())
            for p in account['positions']:
                symbol = self.get_symbol(p)
                positions_by_symbol[symbol] = p
        except Exception as e: 
            print('Eccezione raggiunta durante richiesta futures_account: ',e)
            account = {}
        
        try:
            orders = client.futures_get_open_orders()
        except Exception as e: 
            print('Eccezione raggiunta durante richiesta futures_get_open_orders: ',e)
            orders = []

        for o in orders:
            symbol = self.get_symbol(o)
            if symbol not in orders_by_symbol:
                orders_by_symbol[symbol] = OrderStatus()
            obs = orders_by_symbol[symbol]
            qty = (float(o['origQty']) - float(o['executedQty'])) * (1 if o['side'] == 'BUY' else -1)
            price = float(o['price'])
            value = price * qty
            pos_qty = float(positions_by_symbol[symbol]['positionAmt']) if symbol in positions_by_symbol else 0.0
            if o['reduceOnly']:
                obs.closingCount = obs.closingCount + 1
                obs.closingAmt = obs.closingAmt + qty
                obs.closingValue = obs.closingValue + value
                if obs.tpPrice == 0:
                    obs.tpPrice = price
                elif pos_qty >= 0:
                    obs.tpPrice = max(obs.tpPrice, price)
                else:
                    obs.tpPrice = min(obs.tpPrice, price)
            elif (pos_qty >= 0 and o['side'] == 'BUY') or (pos_qty < 0 and o['side'] == 'SELL'):
                obs.openingCount = obs.openingCount + 1
                obs.openingAmt = obs.openingAmt + qty
                obs.openingValue = obs.openingValue + value
                if obs.lastGridPrice == 0:
                    obs.lastGridPrice = price
                elif pos_qty >= 0:
                    obs.lastGridPrice = min(obs.lastGridPrice, price)
                else:
                    obs.lastGridPrice = max(obs.lastGridPrice, price)

        trades = []
        tlen = -1
        max_num_incomes = 1000
        last_num_trds = max_num_incomes
        start_timestamp_copy = self.start_timestamp
        while len(trades) > tlen and last_num_trds == max_num_incomes:
            try:
                tmp_trades = client.futures_account_trades(startTime=start_timestamp_copy, endTime=self.end_timestamp, limit=max_num_incomes)
            except Exception as e: 
                print('Eccezione raggiunta durante richiesta futures_account_trades: ',e)
                tmp_trades = []

            last_num_trds = len(tmp_trades)
            if last_num_trds > 0:
                max_time = max(tmp_trades, key=lambda k: k['time'])['time']
                tlen = len(trades)
                new_trades = [t for t in tmp_trades if t['time'] < max_time or last_num_trds < max_num_incomes]
                trades.extend(new_trades)
                start_timestamp_copy = max_time

        incomes = []
        ilen = -1
        max_num_incomes = 1000
        last_num_incomes = max_num_incomes
        start_timestamp_copy = self.start_timestamp
        while len(incomes) > ilen and last_num_incomes == max_num_incomes:
            try:
                tmp_incomes = client.futures_income_history(startTime=start_timestamp_copy, endTime=self.end_timestamp, limit=max_num_incomes, incomeType='FUNDING_FEE', timestamp= now.timestamp() ) 
            except Exception as e: 
                print('Eccezione raggiunta durante richiesta futures_income_history: ',e)
                tmp_incomes = []

            last_num_incomes = len(tmp_incomes)
            if last_num_incomes > 0:
                max_time = max(tmp_incomes, key=lambda k: k['time'])['time']
                ilen = len(incomes)
                new_incomes = [t for t in tmp_incomes if t['time'] < max_time or last_num_incomes < max_num_incomes]
                incomes.extend(new_incomes)
                start_timestamp_copy = max_time

        asset_prices = {
            'USDT': 1.0
        }
        income_by_symbol: dict[str, IncomeSummary] = {}

        for t in trades:
            symbol = self.get_symbol(t)
            commission_asset = t['commissionAsset']
            commission_asset_price = self.get_asset_price(commission_asset, asset_prices, client, self.end_timestamp, now)
            margin_asset = t['marginAsset']
            margin_asset_price = self.get_asset_price(margin_asset, asset_prices, client, self.end_timestamp, now)
            commission = float(t['commission']) * commission_asset_price
            realizedPnl = float(t['realizedPnl']) * margin_asset_price
            if symbol not in income_by_symbol:
                income_by_symbol[symbol] = IncomeSummary()
            tbs = income_by_symbol[symbol]
            if float(t['realizedPnl']) != 0.0:
                tbs.count = tbs.count + 1
            tbs.netRealizedPnl = tbs.netRealizedPnl - commission + realizedPnl
            tbs.realizedPnl = tbs.realizedPnl + realizedPnl
            tbs.commission = tbs.commission + commission

        for t in incomes:
            symbol = t['symbol']
            asset = t['asset']
            asset_price = self.get_asset_price(asset, asset_prices, client, self.end_timestamp, now )
            income_type = str(t['incomeType']).lower()
            income = float(t['income']) * asset_price
            if symbol not in income_by_symbol:
                income_by_symbol[symbol] = IncomeSummary()
            tbs = income_by_symbol[symbol]
            if income_type not in ('realizedPnl', 'commission'):
                tbs.netRealizedPnl = tbs.netRealizedPnl + income
                if hasattr(tbs, income_type):
                    tbs.__dict__[income_type] = tbs.__dict__[income_type] + income

        tot = PositionSummary('TOTAL')
        tot.unrealizedProfit = 0.0
        tot.tradeCount = 0
        tot.realizedPnl = 0.0
        tot.exposure = 0.0
        tot.exposurePerc = 0.0
        tot.openingOrderCount = 0
        tot.closingOrderCount = 0
        tot.openingOrderValue = 0.0
        tot.closingOrderValue = 0.0
        bot_summary.positions = {}
        bot_summary.positionsTot = tot

        accepted_positionSide = {'LONG', 'SHORT'}
        if(account == {}):
            for symbol in income_by_symbol.keys():
                income = income_by_symbol[symbol]
                ps = PositionSummary(symbol)
                ps.tradeCount = income.count if income is not None else 0
                ps.realizedPnl = income.netRealizedPnl if income is not None else 0.0
                ps.grossRealizedPnl = income.realizedPnl if income is not None else 0.0
                ps.fundingFee = income.fundingFee if income is not None else 0.0
                ps.commission = income.commission + income.insuranceClear if income is not None else 0.0
                tot.tradeCount = tot.tradeCount + ps.tradeCount
                tot.realizedPnl = tot.realizedPnl + ps.realizedPnl
                tot.grossRealizedPnl = tot.grossRealizedPnl + ps.grossRealizedPnl
                tot.fundingFee = tot.fundingFee + ps.fundingFee
                tot.commission = tot.commission + ps.commission
                if ps.commission!= 0.0: ps.commission = -ps.commission           #Metto le commissioni negative per una visualizzazione più coerente del report finale
                if p['positionSide'].upper() in accepted_positionSide:          #Aggiungo al report solo le tuple che hanno positionSide LONG o SHORT ignorando quelle BOTH
                    bot_summary.positions[symbol] = ps

            for p in bot_summary.positions.values():
                p.realizedPnlPerc = p.realizedPnl / tot.realizedPnl if tot.realizedPnl != 0 else 0.0
                p.tradeCountPerc = p.tradeCount / tot.tradeCount if tot.tradeCount != 0 else 0.0 
        else:
            #bot_summary.balance = float(account['totalWalletBalance'])
            #dato che il qualche utente usa wallet con BUSD vado a sommarli al wallet come se fossero USDT (non corretto perchè hanno valori differenti)
            totalWalletBalance = 0.0
            for assets in account['assets']:
                if((assets['asset']=="USDT")or(assets['asset']=="BUSD")):
                    totalWalletBalance += float(assets['walletBalance'])
            bot_summary.balance = float(account['totalWalletBalance'])
            bot_summary.totUnrealizedProfit = float(account['totalUnrealizedProfit'])
            bot_summary.totInitialMargin = float(account['totalPositionInitialMargin'])
            bot_summary.totOpenOrderInitialMargin = float(account['totalOpenOrderInitialMargin'])
            bot_summary.availableBalance = float(account['availableBalance'])
            bot_summary.totalMaintMargin = float(account['totalMaintMargin'])
            
            positions = [p for p in account['positions'] if float(p['positionAmt']) != 0 or self.get_symbol(p) in income_by_symbol or self.get_symbol(p) in orders_by_symbol]

            for p in positions:
                symbol = self.get_symbol(p)
                ps = PositionSummary(symbol)
                income = income_by_symbol[symbol] if symbol in income_by_symbol else IncomeSummary()
                order = orders_by_symbol[symbol] if symbol in orders_by_symbol else None
                ps.leverage = float(p['leverage'])
                ps.unrealizedProfit = float(p['unrealizedProfit'])
                ps.entryPrice = float(p['entryPrice'])
                ps.positionAmt = float(p['positionAmt'])
                ps.tradeCount = income.count if income is not None else 0
                ps.realizedPnl = income.netRealizedPnl if income is not None else 0.0
                ps.openingOrderCount = order.openingCount if order is not None else 0
                ps.closingOrderCount = order.closingCount if order is not None else 0
                ps.openingOrderQty = order.openingAmt if order is not None else 0
                ps.closingOrderQty = order.closingAmt if order is not None else 0
                ps.openingOrderValue = order.openingValue if order is not None else 0.0
                ps.closingOrderValue = order.closingValue if order is not None else 0.0
                ps.grossRealizedPnl = income.realizedPnl if income is not None else 0.0
                ps.fundingFee = income.funding_fee if income is not None else 0.0
                ps.commission = income.commission + income.insuranceClear if income is not None else 0.0
                if ps.commission!= 0.0: ps.commission = -ps.commission           #Metto le commissioni negative per una visualizzazione più coerente del report finale
                ps.tpPrice = order.tpPrice if order is not None else 0.0
                ps.currentPrice = (ps.entryPrice * ps.positionAmt + ps.unrealizedProfit) / ps.positionAmt if ps.positionAmt != 0.0 else 0.0
                ps.diffCurPriceFromTpPerc = ps.currentPrice / ps.tpPrice - 1 if ps.tpPrice != 0.0 else 0.0
                tot.unrealizedProfit = tot.unrealizedProfit + ps.unrealizedProfit
                tot.tradeCount = tot.tradeCount + ps.tradeCount
                tot.realizedPnl = tot.realizedPnl + ps.realizedPnl
                ps.exposure = abs(ps.positionAmt * ps.entryPrice) + ps.unrealizedProfit
                ps.exposurePerc = ps.exposure / bot_summary.balance
                if order is not None and order.openingAmt != 0:
                    last_grid_amt = ps.positionAmt + order.openingAmt
                    ps.lastGridExposure = last_grid_amt * order.lastGridPrice
                    ps.lastGridCost = ps.positionAmt * ps.entryPrice + order.openingValue
                    ps.lastGridLoss = ps.lastGridExposure - ps.lastGridCost
                    ps.lastGridEntryPrice = ps.lastGridCost / last_grid_amt
                else:
                    ps.lastGridExposure = ps.exposure
                    ps.lastGridLoss = ps.unrealizedProfit
                    ps.lastGridCost = ps.positionAmt * ps.entryPrice
                    ps.lastGridEntryPrice = ps.entryPrice
                tot.exposure = tot.exposure + ps.exposure
                tot.exposurePerc = tot.exposurePerc + ps.exposurePerc
                tot.openingOrderCount = tot.openingOrderCount + ps.openingOrderCount
                tot.closingOrderCount = tot.closingOrderCount + ps.closingOrderCount
                tot.openingOrderValue = tot.openingOrderValue + ps.openingOrderValue
                tot.closingOrderValue = tot.closingOrderValue + ps.closingOrderValue
                tot.grossRealizedPnl = tot.grossRealizedPnl + ps.grossRealizedPnl
                tot.fundingFee = tot.fundingFee + ps.fundingFee
                ps.fundingFee = 0                                               #Una volta riportato nell totale il funding lo cancello dalle singole righe per evitare disguidi su griglie doppie
                if p['positionSide'].upper() in accepted_positionSide:          #Aggiungo al report solo le tuple che hanno positionSide LONG o SHORT ignorando quelle BOTH
                    bot_summary.positions[symbol] = ps
                tot.commission = tot.commission + ps.commission
                tot.lastGridExposure = tot.lastGridExposure + abs(ps.lastGridExposure)
                tot.lastGridLoss = tot.lastGridLoss + ps.lastGridLoss
                tot.lastGridCost = tot.lastGridCost + ps.lastGridCost

                for p in bot_summary.positions.values():
                    p.realizedPnlPerc = p.realizedPnl / abs(tot.realizedPnl) if tot.realizedPnl != 0 else 0.0
                    p.tradeCountPerc = p.tradeCount / tot.tradeCount if tot.tradeCount != 0 else 0.0
                    p.openingOrderValuePerc = p.openingOrderValue / bot_summary.balance if bot_summary.balance != 0 else 0.0
                    tot.openingOrderValuePerc = tot.openingOrderValuePerc + p.openingOrderValuePerc

                bot_summary.lastGridExposure = tot.lastGridExposure
                bot_summary.lastGridLoss = tot.lastGridLoss
                bot_summary.lastGridAvailableBalance = bot_summary.availableBalance + tot.lastGridLoss
                bot_summary.lastGridExposurePerc = tot.lastGridExposure / bot_summary.lastGridAvailableBalance

                mainteniance_perc = bot_summary.totalMaintMargin / bot_summary.totInitialMargin if bot_summary.totInitialMargin != 0.0 else 0.0
                last_grid_tot_initial_margin = bot_summary.totInitialMargin + bot_summary.totOpenOrderInitialMargin
                last_grid_mainteniance_margin = last_grid_tot_initial_margin * mainteniance_perc
                last_grid_max_loss_to_liquidation = bot_summary.lastGridAvailableBalance - last_grid_mainteniance_margin
                bot_summary.lastGridLossToLiquidation = last_grid_max_loss_to_liquidation / bot_summary.lastGridExposure if bot_summary.lastGridExposure != 0.0 else 0
            bot_summary.totRealizedProfitPerc = tot.realizedPnl / (bot_summary.balance - tot.realizedPnl)      

        bot_summary.totRealizedProfit = tot.realizedPnl

        return bot_summary.to_json()


    def get_symbol(self,p):
        return p['symbol'] + ('_' + p['positionSide'] if p['positionSide'] != 'BOTH' else '')


    def get_asset_price(self,asset, asset_prices, client, end_timestamp,  now):
        try:
            if asset in asset_prices:
                asset_price = asset_prices[asset]
            elif int(now.timestamp()) - end_timestamp > 24 * 60 * 60 * 1000:
                kline = client.get_klines(symbol=asset + 'USDT', interval='1d', limit=1, startTime=end_timestamp)
                asset_price = float(kline[0][4])
                asset_prices[asset] = asset_price
            else:
                avg_price = client.get_avg_price(symbol=asset + 'USDT')
                asset_price = float(avg_price['price'])
                asset_prices[asset] = asset_price
        except:
            asset_price = 1.0
        return asset_price
