import urllib.parse

import pymssql
import pandas as pd


class UseSQLServer(object):
    def __init__(self, config=None):
        if config is None:
            config = {
                'host': "43.143.116.236",
                'port': "1433",
                'user':'sa',
                'password':'4568520sxgs.',
                'database': "attend",
                'charset': "UTF-8",

            }
        self.config = config
        self.con = pymssql.connect(**self.config)
        self.cur = self.con.cursor()

    def exists_table(self, tb_name):
        stmt = "select * from sysobjects where id = object_id('{}') and OBJECTPROPERTY(id, N'IsUserTable') = 1".format(
            tb_name)
        self.cur.execute(stmt)
        res = self.cur.fetchone()
        if res:
            return True
        else:
            return False

    def execute(self,sql):
        res=self.cur.execute(sql)
        self.con.commit()
        if res:
            return True
        else:
            return False

    def drop_table(self, tb_name):
        stmt = "DROP TABLE IF EXISTS {}".format(tb_name)
        self.cur.execute(stmt)
        self.con.commit()
        return True

    def create_table(self, tb_name, df):
        type_category = {'int64': 'varchar(250)', 'string': 'varchar(300)', 'float64': 'float',
                         'object': 'varchar(300)', 'datetime64[ns]': 'datetime'}
        field = []
        for col in df.columns:
            data_type = str(df[col].dtypes)
            field.append('{} {}'.format(col, type_category[data_type]))
        field = ','.join(field)
        stmt = '''CREATE TABLE {}\n({}) '''.format(tb_name, field)
        self.cur.execute(stmt)
        self.con.commit()
        return True

    def write_table(self, tb_name, df):
        # 构建 INSERT 语句
        columns = ', '.join(df.columns)
        values = ', '.join(['%s' for i in range(len(df.columns))])
        insert_query = f"INSERT INTO {tb_name} ({columns}) VALUES ({values})"

        # 执行 INSERT 语句
        cursor = self.con.cursor()
        for row in df.itertuples(index=False):
            # 将 row 转换为元组，并使用 N 前缀表示 Unicode 字符串
            row = tuple([f"{str(i)}" if isinstance(i, str) else i for i in row])
            cursor.execute(insert_query, row)
        self.con.commit()

    def get_mssql_data(self, sql):
        cur = self.cur
        try:
            cur.execute(sql)
            index = cur.description
            field_names = [field[0] for field in index]
            record = cur.fetchall()
            if len(record) > 0:
                df = pd.DataFrame(list(record))
            else:
                df = pd.DataFrame([''] * len(field_names))
            df.columns = field_names
        except:
            df = pd.DataFrame(columns=['temp', 'none', 'df'])
        return df

    def update_mssql_data(self, sql):
        cur = self.cur
        conn = self.con
        try:
            cur.execute(sql)
            conn.commit()
        except:
            return 'fail'
        return 'success'
