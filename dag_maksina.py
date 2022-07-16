# coding=utf-8

# В feed_actions для каждого юзера посчитаем число просмотров и лайков контента.
# В message_actions для каждого юзера считаем, сколько он получает и отсылает
# сообщений, скольким людям он пишет, сколько людей пишут ему.

from datetime import datetime, timedelta
import pandas as pd
import pandahouse as ph

from airflow.decorators import dag, task

default_args = {
    'owner': 'a-maksina-7',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2022, 6, 14),
}

connection = {
    'host': 'https://clickhouse.lab.karpov.courses',
    'password': 'dpo_python_2020',
    'user': 'student',
    'database': 'simulator_20220520'
}

# Интервал запуска DAG
schedule_interval = '0 23 * * *'


def eval_col(col_name, df_cube):
    df_cube_slice = df_cube[['event_date',
                              col_name,
                              'views',
                              'likes',
                              'messages_received',
                              'messages_sent',
                              'users_received',
                              'users_sent']] \
        .groupby(['event_date', col_name]) \
        .sum() \
        .reset_index().rename(columns={col_name: 'slice_value'})
    df_cube_slice.insert(1, 'slice', col_name)

    return df_cube_slice


@dag(default_args=default_args,
     schedule_interval=schedule_interval,
     catchup=False)
def dag_maksina():

    @task()
    def extract_feed():
        query = """SELECT  
                       user_id as id,
                       toDate(time) as event_date,
                       countIf(action='like') as likes,
                       countIf(action='view') as views, 
                       age,
                       gender,
                       os                      
                    FROM 
                        simulator_20220520.feed_actions 
                    WHERE 
                        toDate(time) = today() - 1 
                    GROUP BY
                        id,
                        age, 
                        gender,
                        os,
                        event_date"""

        df_cube_feed = ph.read_clickhouse(query=query, connection=connection)

        return df_cube_feed

    @task()
    def extract_message():
        query_message = """SELECT *
                            FROM 
                                                    
                            (SELECT user_id as id, 
                                    toDate(time) as event_date,
                                    count(reciever_id) as messages_sent,
                                    count(distinct reciever_id) as users_sent,
                                    age, 
                                    gender,
                                    os
                            FROM
                                simulator_20220520.message_actions 
                            WHERE 
                                toDate(time) = today() - 1 
                            GROUP BY id, age, gender, os, event_date) t1
                            
                            JOIN
                            
                            (SELECT reciever_id as id, 
                                    count(user_id) as messages_received,
                                    count(distinct user_id) as users_received
                            FROM
                                simulator_20220520.message_actions 
                            WHERE 
                                toDate(time) = today() - 1 
                            GROUP BY id) t2
                             
                            USING id"""
        df_cube_message = ph.read_clickhouse(query=query_message, connection=connection)

        return df_cube_message

    @task
    def merge_dfs(df_cube_feed, df_cube_message):
        dfs_cube = df_cube_feed\
            .merge(df_cube_message, on=['id',
                                     'os',
                                     'age',
                                     'gender',
                                     'event_date'],
                   how='outer')\
            .rename(columns={'id': 'user_id'})
        dfs_cube.fillna(0, inplace=True)
        return dfs_cube

    @task
    def transform_gender(df_cube):
        df_cube_gender = eval_col('gender', df_cube)
        return df_cube_gender

    @task
    def transform_os(df_cube):
        df_cube_os = eval_col('os', df_cube)
        return df_cube_os

    @task
    def transform_age(df_cube):
        df_cube['age'] = \
            pd.cut(df_cube['age'], [0, 13, 18, 20, 30, 40, 50, 60, 70, 200],
                   retbins=True)[0]
        df_cube_age = eval_col('age', df_cube)
        df_cube_age = df_cube_age.dropna()

        return df_cube_age

    @task()
    def concat_dfs(*args):
        return pd.concat(args, axis=0)

    @task
    def load(df_res):

        connection_test = {
            'host': 'https://clickhouse.lab.karpov.courses',
            'password': '656e2b0c9c',
            'user': 'student-rw',
            'database': 'test'
        }
        
        cols = df_res.columns.to_list()
        cols.remove('event_date')
        cols.remove('slice')
        cols.remove('slice_value')
        for c in cols:
            df_res[c] = df_res[c].astype(int)

        ph.to_clickhouse(df=df_res,
                         table='maksina8',
                         index=False,
                         connection=connection_test)

    df_feed = extract_feed()
    df_message = extract_message()
    df_cube = merge_dfs(df_feed, df_message)
    df_gender = transform_gender(df_cube)
    df_os = transform_os(df_cube)
    df_age = transform_age(df_cube)
    df_res = concat_dfs(df_gender, df_os, df_age)
    load(df_res)


dag_maksina = dag_maksina()
