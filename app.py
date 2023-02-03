import json

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
    print(sql)
    con=UseSQLServer()
    df=con.get_mssql_data(sql)
    print(df)
    return 'Hello World!'


if __name__ == '__main__':
    app.run(debug='True',port=5001)

