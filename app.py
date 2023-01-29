

from flask import Flask, request
from flask_cors import CORS
import jwt

from lib.db import UseSQLServer

secret='attend'
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/get/data',methods=['GET'])
def get_data():  # put application's code here
    sql=request.args.get('sql')
    print(sql)
    con=UseSQLServer()
    df=con.get_mssql_data(sql)
    print(df)
    return 'Hello World!'


if __name__ == '__main__':
    app.run(debug='True')

