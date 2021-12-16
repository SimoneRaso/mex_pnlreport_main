from datetime import datetime,timezone,date
from typing import List
import json

import okex.Account_api as Account
import okex.Funding_api as Funding
import okex.Market_api as Market
import okex.Public_api as Public
import okex.Trade_api as Trade
import okex.status_api as Status
import okex.subAccount_api as SubAccount
import okex.TradingData_api as TradingData

from orderstatus import OrderStatus
from incomesummary import IncomeSummary
from positionsummary import PositionSummary
from botsummary import BotSummary

# constanti
INST_TYPE = "SWAP"                      #Mercato di riferimento

class OkexBotSummary:
    accountAPI = None
    tradeAPI = None
    marketAPI = None

    def __init__(self,
                bot_name : str, 
                api_key : str, 
                api_secret : str,
                passphrase :  str, 
                start_timestamp : int = 0,
                end_timestamp :  int = 0,
                demoTrading : str = '') -> None:
        self.bot_name : str = bot_name
        self.api_key : str = api_key
        self.api_secret : str = api_secret
        self.passphrase :  str = passphrase
        self.start_timestamp :  int = start_timestamp
        self.end_timestamp :  int = end_timestamp
        self.demoTrading :  str = demoTrading #'0' o '1'


    def get_JSON_summary(self) -> BotSummary:
        # demoTrading is the key parameter which can help you to change between demo and real trading.
 
        self.accountAPI = Account.AccountAPI(self.api_key, self.api_secret, self.passphrase, False, self.demoTrading)    # account api
        self.tradeAPI = Trade.TradeAPI(self.api_key, self.api_secret, self.passphrase, False, self.demoTrading)          # trade api
        self.marketAPI = Market.MarketAPI(self.api_key, self.api_secret, self.passphrase, False, self.demoTrading)      # market api
        #accountPositionRisk = self.accountAPI.get_position_risk(instType=INST_TYPE)                                     # position risk (inutilizzato)
       
        print ('okex_bot_summary logs')
        now=datetime.now(tz=timezone.utc)
        print ('now=',now)
        bot_summary = BotSummary(self.bot_name, int(now.timestamp() * 1000)) #1000 = seconds to milliseconds

        if (self.start_timestamp == 0) or (self.end_timestamp == 0):
            print('start_timestamp o end_timestamp non valorizzato.')
            return {}

        #loggo i valori delle date 
        print("start_timestamp:",self.start_timestamp," end_timestamp:",self.end_timestamp)
        start_win=date.fromtimestamp(self.start_timestamp/1000)
        end_win=date.fromtimestamp(self.end_timestamp/1000)
        print("cerco elementi compresi tra (start_win): ",start_win.strftime("%Y-%m-%d %H:%M:%S")," e (end_win): ",end_win.strftime("%Y-%m-%d %H:%M:%S"))

        bot_summary.start_timestamp = self.start_timestamp
        bot_summary.end_timestamp = self.end_timestamp

        positions_by_symbol = {}
        wallet_by_symbol = {}
        orders_by_symbol = {}

        #Retriving account information
        try:
            account = self.accountAPI.get_account('USDT')
        except Exception as e: 
            print('Eccezione raggiunta durante richiesta get_account: ',e)
            account = {}
        #botf.__dump_obj_to_file(account,'account.json')

        #Retriving postions information
        positions= self.accountAPI.get_positions()
        try:
            postions = self.accountAPI.get_positions(instType=INST_TYPE)
            #recupero il balance dell'account
            bot_summary.balance = float(account['data'][0]['details'][0]['cashBal'])
            #carico le posizioni divise per symbol
            for p in postions['data']:
                symbol = self.__get_symbol(p)
                positions_by_symbol[symbol] = p
        except Exception as e: 
            print('Eccezione raggiunta durante richiesta get_positions: ',e)
            account = {}
        #botf.__dump_obj_to_file(positions,'positions.json')

        #Retriving wallet information
        try:
            wallet = self.accountAPI.get_account('USDT')
            for data in wallet['data']:
                for details in data['details']:
                    symbol = details['ccy']
                    wallet_by_symbol[symbol] = details
        except:
            wallet = {}

        try:
            orders = self.tradeAPI.get_orders_history(instType=INST_TYPE)
        except Exception as e: 
            print('Eccezione raggiunta durante richiesta get_orders_history: ',e)
            orders = {}

        for o in orders['data']:
            symbol = self.__get_symbol(o)
            if symbol not in orders_by_symbol:
                orders_by_symbol[symbol] = OrderStatus()
            obs = orders_by_symbol[symbol]
            qty = (float(o['sz']) - float(o['fillSz'])) * (1 if o['side'] == 'buy' else -1)
            price = float(o['px']) if o['px'] != '' else 0
            value = price * qty
            pos_qty = float(positions_by_symbol[symbol]['pos']) if symbol in positions_by_symbol else 0.0
            
            #gli ordini su Okex sono tutti reduceOnly quindi ho lasciato solo il codice per questo caso
            obs.closingCount = obs.closingCount + 1
            obs.closingAmt = obs.closingAmt + qty
            obs.closingValue = obs.closingValue + value
            if obs.tpPrice == 0:
                obs.tpPrice = price
            elif pos_qty >= 0:
                obs.tpPrice = max(obs.tpPrice, price)
            else:
                obs.tpPrice = min(obs.tpPrice, price)

        
        income_by_symbol: dict[str, IncomeSummary] = {}

        trades = self.__getTrades(self.start_timestamp,self.end_timestamp,'fillTime')
        for t in trades:
            symbol = self.__get_symbol(t)

            #inizio codice semplificato per mancanza di informazioni precise. Chiedere al team se va bene lo stesso
            commission_asset = t['feeCcy']#riga orig: commission_asset = t['commissionAsset']
            commission_asset_price = self.get_asset_price(commission_asset, self.end_timestamp, now)
            margin_asset = t['feeCcy'] #corretto? riga orig: margin_asset = t['marginAsset']
            #fine codice semplificato
            margin_asset_price = self.get_asset_price(commission_asset, self.end_timestamp, now)
            commission = float(t['fee']) * commission_asset_price
            realizedPnl = float(t['pnl']) * margin_asset_price
            if symbol not in income_by_symbol:
                income_by_symbol[symbol] = IncomeSummary()
            tbs = income_by_symbol[symbol]
            if float(t['pnl']) != 0.0:
                tbs.count = tbs.count + 1
            #ho invertito il segno delle commissioni perchè da okex arrivano negative. riga originale tbs.netRealizedPnl = tbs.netRealizedPnl + commission + realizedPnl 
            tbs.netRealizedPnl = tbs.netRealizedPnl + commission + realizedPnl 
            tbs.realizedPnl = tbs.realizedPnl + realizedPnl
            tbs.commission = tbs.commission + commission
        
        incomes = self.__getIncomes(self.start_timestamp,self.end_timestamp,'2') #prima era '8'
        for t in incomes:
            symbol = t['instId']
            asset = t['ccy']
            asset_price = self.get_asset_price(commission_asset, self.end_timestamp, now)
            income_type = self.__getBillType(t['type'])
            income = float(t['pnl']) * asset_price
            if symbol not in income_by_symbol:
                income_by_symbol[symbol] = IncomeSummary()
            tbs = income_by_symbol[symbol]
            
            # ho messo 'Trade' e 'Interest deduction' ma non sono sicuro che questi due tipi corrispondano ai vecchi 'realizedPnl' e 'commission'
            if income_type not in (self.__getBillType('2'), self.__getBillType('7')): 
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
            bot_summary.balance = self.__getFloatFromString(self.__json_extract(account,'cashBal')[0])#totalWalletBalance
            bot_summary.totUnrealizedProfit = self.__getFloatFromString(self.__json_extract(account,'upl')[0]) #totalUnrealizedProfit
            bot_summary.totInitialMargin = self.__getFloatFromString(self.__json_extract(account,'imr')[0])#totalPositionInitialMargin  
            bot_summary.totOpenOrderInitialMargin = self.__getFloatFromString(self.__json_extract(account,'ordFrozen')[0])#totalOpenOrderInitialMargin
            bot_summary.availableBalance = self.__getFloatFromString(self.__json_extract(account,'availBal')[0])#availableBalance
            bot_summary.totalMaintMargin = self.__getFloatFromString(self.__json_extract(account,'mmr')[0])#totalMaintMargin
            
            filterPositions = [p for p in positions['data']  if float(p['pos']) != 0 or self.__get_symbol(p) in income_by_symbol or self.__get_symbol(p) in orders_by_symbol]

            for p in filterPositions:
                symbol = self.__get_symbol(p)
                ps = PositionSummary(symbol)
                income = income_by_symbol[symbol] if symbol in income_by_symbol else IncomeSummary()
                order = orders_by_symbol[symbol] if symbol in orders_by_symbol else None
                ps.leverage = self.__getFloatFromString(p['lever'])
                ps.unrealizedProfit = self.__getFloatFromString(p['upl'])
                ps.entryPrice = self.__getFloatFromString(p['avgPx'])
                ps.positionAmt = self.__getFloatFromString(p['pos'])
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
                if p['posSide'].upper() in accepted_positionSide:               #Aggiungo al report solo le tuple che hanno positionSide LONG o SHORT ignorando quelle BOTH
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


    def __get_symbol(self,p):
        return p['instId'] + ('_' + p['posSide'] if p['posSide'] != 'BOTH' else '')

    def get_asset_price(self,asset, end_timestamp,  now):

        asset_prices = {
            'USDT': 1.0
        }

        try:
            if asset in asset_prices:
                asset_price = asset_prices[asset]
            elif int(now.timestamp()) - end_timestamp > 24 * 60 * 60 * 1000:
                kline = self.marketAPI.get_candlesticks(instId=asset + 'USDT', bar='1d', limit=1, before=end_timestamp)
                asset_price = float(kline[0][4])
                asset_prices[asset] = asset_price
            else:
                avg_price = self.tradeAPI.get_order_list(instType=asset)
                asset_price = float(avg_price['price'])
                asset_prices[asset] = asset_price
        except Exception as e: 
            asset_price = 1.0
        return asset_price

    #Funzioni aggiunte da me...
    #dump object on file
    def __dump_obj_to_file(self,object,filename):
        with open(filename, 'w') as f:
            json.dump(object, f)
        return

    #filter element of array of object, with after and before data , converting timestamp to datetime 
    def __filter_with_data(self,collection,after='', before='', maxnum=1000, incomeType='',timefield='') -> List:
        trade_filtered = []
        
        if (after=='') or (before==''):
            return
        
        after_win=datetime.fromtimestamp(after/1000)    #/1000 convert in second
        before_win=datetime.fromtimestamp(before/1000)
    
        print("cerco elementi compresi tra (before): ",after_win," e (after): ",before_win)

        for elem in collection:
            ts= int(elem[timefield])
            #print("esamino elem con data:",datetime.fromtimestamp(ts/1000), end='')
            count=0
            if (ts>before) and (ts<after) and (count<=maxnum):
                #print(" - compreso!")
                trade_filtered.append(elem) 
                count+=1
                #else:
                    #print(" - escluso")

        return trade_filtered

    def __getBillType(self,type)-> str:

        d = {'1' : 'Transfer', '2' : 'Trade', '3' : 'Delivery' ,'4': 'Auto token conversion', '5' : 'Liquidation', '6' : 'Margin transfer', 
            '7' : 'Interest deduction', '8' : 'Funding fee', '9' : 'ADL', '10' : 'Clawback','11' : 'System token conversion','12' : 'Strategy transfer','13' : 'ddh'}

        keys=list(d.keys())
        values=d.values()
        try:
            bill_type = d.get(type)
        except:
            bill_type = 'not found'

        return bill_type

    def __getFloatFromString(self,strNum)-> object:
        retVal=0
        if (strNum=='') :
            return 0
        try:
            retVal = float(strNum)
        except Exception as e: 
            print('__getFloatFromString: stringa ', strNum, ' non covertibile in numero')
            
        return retVal

    def __getIncomes(self,start_timestamp, end_timestamp,type)-> object:
        incomes = []
        ilen = -1
        max_num_incomes = 100
        last_num_incomes = max_num_incomes
        start_timestamp_cpy = start_timestamp
        while len(incomes) > ilen and last_num_incomes == max_num_incomes:
            try:
                JSONincomes = self.accountAPI.get_bills_details(instType=INST_TYPE,type=type)
                incomes_array= JSONincomes['data']
                tmp_incomes=self.__filter_with_data(incomes_array,after=end_timestamp, before=start_timestamp_cpy, maxnum=max_num_incomes,timefield='ts')
            except Exception as e: 
                print('Eccezione raggiunta durante __getIncomes: ',e)
                tmp_incomes = []

            last_num_incomes = len(tmp_incomes)
            if last_num_incomes > 0:
                max_time = max(tmp_incomes, key=lambda k: k['ts'])['ts']
                ilen = len(incomes)
                new_incomes = [t for t in tmp_incomes if t['ts'] < max_time or last_num_incomes < max_num_incomes]
                incomes.extend(new_incomes)
                start_timestamp_cpy = max_time
        
        return incomes

    def __getTrades(self,start_timestamp, end_timestamp,timefield)-> object:
        trades = []
        tlen = -1
        max_num_trades = 100
        last_num_trds = max_num_trades
        start_timestamp_cpy = start_timestamp
        while len(trades) > tlen and last_num_trds == max_num_trades:
            try:
                JSONtrades = self.tradeAPI.orders_history_archive(instType=INST_TYPE)
                trades_array= JSONtrades['data']
                tmp_trades=self.__filter_with_data(trades_array,after=end_timestamp, before=start_timestamp_cpy, maxnum=max_num_trades,timefield=timefield)
            except Exception as e: 
                print('Eccezione raggiunta durante richiesta __filter_with_data: ',e)
                tmp_trades = []

            last_num_trds = len(tmp_trades)
            if last_num_trds > 0:
                max_time = max(tmp_trades, key=lambda k: k['fillTime'])['fillTime']
                tlen = len(trades)
                new_trades = [t for t in tmp_trades if t['fillTime'] < max_time or last_num_trds < max_num_trades]
                trades.extend(new_trades)
                start_timestamp_cpy = max_time
        
        return trades
    
    def __json_extract(self,obj, key):
        #"""Recursively fetch values from nested JSON."""
        arr = []

        def extract(obj, arr, key):
            """Recursively search for values of key in JSON tree."""
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        extract(v, arr, key)
                    elif k == key:
                        arr.append(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract(item, arr, key)
            return arr

        values = extract(obj, arr, key)
        return values