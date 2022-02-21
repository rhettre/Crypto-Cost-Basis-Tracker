import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import gemini
import cbpro

#Link to Base Spreadsheet - https://docs.google.com/spreadsheets/d/1VYuy5cSnZiQqF4yp6_sVFpLXXXszCGEiMh-Z37mKims/edit?usp=sharing
#Enter Gemini Keys to Link Gemini Account

gemini_public_key = ''  
gemini_private_key = ''
gemini_symbols = ["BATBTC","ETHUSD","BTCUSD"]
gemini_creds = [gemini_public_key,gemini_private_key]

#Enter Coinbase Pro Keys to Link Coinbase Pro Account
cbpro_passphrase = ''
cbpro_secret = ''
cbpro_key = ''
cbpro_symbols = ["BTC-USD", "ETH-USD", "LINK-USD", "ADA-USD", "XLM-USD","XTZ-USD"]
cbpro_creds = [cbpro_key, cbpro_secret, cbpro_passphrase]

#The name of your google sheet file
google_sheet_file_name = "The New Definitive Crypto Sheet"
#The name of the audit file sheet that you want to import transactions into
audit_file_sheet_name = "Audit File"
#Google Sheets Credentials File Name
sheets_creds_file_name ='sheets_creds.json'

#TODO:
#Implement Kraken, Binance, OKCoin, etc

def _authenticateSpreadsheet():
    #Set up access to the spreadsheet
    scope = ["https://spreadsheets.google.com/feeds",
            'https://www.googleapis.com/auth/spreadsheets',
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(sheets_creds_file_name, scope)
    client = gspread.authorize(creds)

    return client.open(google_sheet_file_name).worksheet(audit_file_sheet_name)

def _addGeminiTransaction(transaction):
    #populate transaction details
    transaction_date = str(datetime.fromtimestamp(transaction['timestamp']).date())
    transaction_id = float(transaction['tid'])
    exchange = "Gemini"
    symbol = transaction['symbol']
    side = transaction['type']
    amount = float(transaction['amount'])
    price = float(transaction['price'])
    fee = float(transaction['fee_amount'])
    sell_side_amount = amount * price + fee
    #populate with new row
    return [transaction_date, exchange, transaction_id, side, symbol, amount, price, sell_side_amount, fee]

def populateGemini(audit_file, symbol):
    #Establish connection to Gemini
    trader = gemini.PrivateClient(gemini_creds[0], gemini_creds[1])
    #Need to run these filters to make sure that you're only bringing over Gemini transactions that have a Transaction ID that is later than the last Transaction ID for a given symbol
    last_gemini_transaction = (list(filter(lambda filterExchange: filterExchange['Exchange'] == 'Gemini', audit_file.get_all_records())))
    last_symbol_transaction = (list(filter(lambda filterSymbol: filterSymbol['Symbol'] == symbol, last_gemini_transaction)))
    if(last_symbol_transaction):
        #pull transactions from Gemini
        transactions = trader.get_past_trades(symbol)[::-1]
        for transaction in transactions:
            #If the transactions from Gemini are after your most recent Transaction for a given symbol in the sheet - add the transaction to the sheet 
            if(transaction['tid'] > last_symbol_transaction[-1]['Transaction ID']):
                audit_file.append_row(_addGeminiTransaction(transaction), value_input_option="USER_ENTERED")

def _addCBProTransaction(transaction):
    #populate transaction details
    transaction_date = str(transaction['created_at'][0:10])
    exchange = "Coinbase Pro"
    transaction_id = transaction['trade_id']
    symbol = transaction['product_id'].replace('-','')
    side = transaction['side'].capitalize()
    amount = float(transaction['size'])
    price = float(transaction['price'])
    fee = float(transaction['fee'])
    sell_side_amount = float(transaction['usd_volume']) + float(fee)
    #populate with new row
    return [transaction_date, exchange, transaction_id, side, symbol, amount, price, sell_side_amount, fee]

def populateCBPro(audit_file, symbol):
    auth_client = cbpro.AuthenticatedClient(cbpro_creds[0], cbpro_creds[1], cbpro_creds[2])
    #Need to run these filters to make sure that you're only bringing over Coinbase Pro transactions that have a Transaction ID that is later than the last Transaction ID for a given symbol
    last_cbpro_transaction = (list(filter(lambda filterExchange: filterExchange['Exchange'] == 'Coinbase Pro', audit_file.get_all_records())))
    last_symbol_transaction = (list(filter(lambda filterSymbol: filterSymbol['Symbol'] == symbol.replace('-',''), last_cbpro_transaction)))
    #print(f"Last Symbol Transaction: {last_symbol_transaction}")
    #pull transactions from Coinbase Pro
    transactions = list(auth_client.get_fills(product_id=symbol))
    for transaction in transactions[::-1]:
        print(f"Transaction Trade ID: {transaction['trade_id']}")
        print(f"Last Symbol Transaction: {last_symbol_transaction[-1]['Transaction ID']}")
        #If the transactions from Coinbase Pro are after your most recent Transaction for a given symbol in the sheet - add the transaction to the sheet 
        if transaction['trade_id'] > last_symbol_transaction[-1]['Transaction ID']:
            audit_file.append_row(_addCBProTransaction(transaction), value_input_option="USER_ENTERED")

def lambda_handler(event, context):
    for symbol in cbpro_symbols:
        populateCBPro(_authenticateSpreadsheet(), symbol)

    for symbol in gemini_symbols:
        populateGemini(_authenticateSpreadsheet(), symbol)
    return {
        'statusCode': 200,
        'body': json.dumps('End of script')
    }
