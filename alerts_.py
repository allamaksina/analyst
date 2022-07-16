from CH import Getch
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import telegram

sns.set()

# AU_feed
# AU_message
# Views
# Likes
# CTR
# SentMessages


def raise_alert(metric_name: str, current_x: float, dev: float):
    
    text = None
    
    if abs(dev) > 1:   
    
        if metric_name == 'CTR':
            text = f'Metric {metric_name}: \nCurrent value {current_x:.2f}. Deviation {round(dev * 100)}%.'
        else:
            text = f'Metric {metric_name}: \nCurrent value {current_x}. Deviation {round(dev * 100)}%.'
    
    return text
    
    
def last_value_dev_an(data, col):

    if col == 'Unique users f':
        metric_name = 'Users (feed)'
    elif col == 'Unique users':
        metric_name = 'Users (messages)'
    elif col == 'likes':
        metric_name = 'Likes'
    elif col == 'views':
        metric_name = 'Views'
    elif col == 'Sent messages':
        metric_name = col
    else:
        metric_name = 'CTR'
        
        
    t = str(data.iloc[1]['time'])
    filtered = data.loc[data['time'] == t]
    
    n_mean = 31
    
    mean = filtered[2:][col][:n_mean].mean()
    std = filtered[2:][col][:n_mean].std()
    cur_x = filtered.iloc[0][col]
    
    max_dev = 3 * std
    cur_dev = (cur_x - mean) / max_dev
    
    return metric_name, cur_x, cur_dev


query_feed = 'SELECT toDateTime(intDiv(toUInt32(toDateTime(time)), 900)*900) AS __timestamp, \
    count(DISTINCT user_id) AS "Unique users f", \
    countIf(user_id, action=\'view\') AS "views",\
    countIf(user_id, action=\'like\') AS "likes" \
    FROM simulator_20220520.feed_actions\
    GROUP BY toDateTime(intDiv(toUInt32(toDateTime(time)), 900)*900) \
    ORDER BY __timestamp DESC;'

query_message = 'SELECT toDateTime(intDiv(toUInt32(toDateTime(time)), 900)*900) AS __timestamp, \
    count(DISTINCT user_id) AS "Unique users",\
    count(reciever_id) as "Sent messages"\
    FROM simulator_20220520.message_actions\
    GROUP BY toDateTime(intDiv(toUInt32(toDateTime(time)), 900)*900) \
    ORDER BY __timestamp DESC;'


data = Getch(query_feed).df
data_mess = Getch(query_message).df

data = data.merge(data_mess, on='__timestamp')

data['time'] = data['__timestamp'].astype(str).apply(lambda x: x[-8:-3])
today = data['__timestamp'].astype(str).apply(lambda x: x[:10])
data['CTR'] = data['likes'] / data['views']


def alert_report(data):
    
    chat_id = -652068442
    token='5502600983:AAFHmlonuDADjN0dMui0QbOOcYhNPf_3uyM'
    bot = telegram.Bot(token=token)
    
    cols = ['Unique users f', 'views', 'likes', 'CTR', 'Unique users', 'Sent messages']
    
    res_text = ''
    
    for col in cols:
        
        vals = last_value_dev_an(data, col)  
        msg = raise_alert(*vals)
        
        if msg is not None:
            
            res_text = res_text + '\n----------------\n' + msg
            
    if res_text:
        
        res_text = res_text + '\n' + 'Link:\n' + \
        'https://superset.lab.karpov.courses/superset/dashboard/1056/'
        bot.send_message(chat_id=chat_id, text='Alert\n' + res_text)
        
    
alert_report(data)

      
