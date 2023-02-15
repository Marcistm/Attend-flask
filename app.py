import json

import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import jwt

from lib.db import UseSQLServer
from utils.common import my_md5, generate_token

secret='attend'
random_str = 'attend~%!$#^&*'
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/login', methods=['get'])
@cross_origin(supports_credentials=True)
def login():
    mssql_connect = UseSQLServer()
    username = request.args.get('username')
    passwd = request.args.get('password')
    res_pass = my_md5(passwd, random_str)
    sql = "select password, has_login,privilege,username,name " \
          "from user_table " \
          f"where username = '{username}'"
    df = mssql_connect.get_mssql_data(sql)
    if df.empty:
        return jsonify(code=404, msg='用户不存在')
    res = df.to_dict('records')[0]
    passwd_db = res['password']
    if res_pass == passwd_db:
        return jsonify(code=200, msg='success', has_login=res['has_login'], token=generate_token(username),
                       privilege=res['privilege'], name=res['name'])
    else:
        return jsonify(code=401, msg='密码不正确')

@app.route('/change_pswd', methods=['put'])
@cross_origin(supports_credentials=True)
def change_passwd():
    mysql_connect = UseSQLServer()
    data = json.loads(request.get_data())
    sql = "update user_table set password = '{}', has_login = {} where username = '{}';" \
        .format(my_md5(str(data['password']), random_str), 1, data['username'])
    df = mysql_connect.update_mssql_data(sql)
    if df == 'success':
        return jsonify(code=200, msg=df)
    else:
        return jsonify(code=404, msg="can't find resource")

@app.route('/get/data',methods=['GET'])
def get_data():  # put application's code here
    sql=request.args.get('sql')
    con=UseSQLServer()
    df=con.get_mssql_data(sql)
    return jsonify(code=200, data=df.fillna('').to_dict('records'), msg="success")

@app.route('/password/reset',methods=['GET'])
def password_reset():  # put application's code here
    username=request.args.get('username')
    con=UseSQLServer()
    sql=f"update user_table set password='055b3a993737b01c9c042f46420c84fe',has_login=0 where username='{username}'"
    df=con.update_mssql_data(sql)
    if df == 'success':
        return jsonify(code=200, msg=df)
    else:
        return jsonify(code=404, msg="操作失败")

@app.route('/user/delete',methods=['GET'])
def user_delete():  # put application's code here
    username=request.args.get('username')
    con=UseSQLServer()
    sql=f"delete from user_table where username='{username}'"
    df=con.update_mssql_data(sql)
    if df == 'success':
        return jsonify(code=200, msg=df)
    else:
        return jsonify(code=404, msg="操作失败")

@app.route('/upload/data', methods=['POST'])
def upload_data():
    val = json.loads(request.get_data())
    con=UseSQLServer()
    data = val['data']
    table= val['table']
    df=pd.DataFrame(data)
    df_copy=df[['username', 'name']].copy()
    if table=='teacher':
        df_copy.loc[:, 'privilege'] = 1
    if table=='student':
        df_copy.loc[:, 'privilege'] = 0
    tag=con.write_table(table,df)
    if not tag:
        return jsonify(code=404, msg='上传失败'), 404
    tag=con.write_table('user_table',df_copy)
    if not tag:
        return jsonify(code=404, msg='上传失败'), 404
    return jsonify(code=200,msg='上传成功')


if __name__ == '__main__':
    app.run(debug='True',port=5001)

