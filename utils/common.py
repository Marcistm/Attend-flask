import base64
import hashlib
import hmac
import os
import uuid
from datetime import datetime
import time
from urllib.parse import urljoin
import pandas as pd
from flask import jsonify,request
UPLOAD_FOLDER = './attachment'


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def random_filename(filename):
    ext = os.path.splitext(filename)[-1]
    return uuid.uuid4().hex + ext


def generate_token(key, expire=3600):
    """
    :param key: 用户给定的用于生成token的key
    :param expire: token过期时间，默认1小时，单位为s
    :return: token:str
    """
    ts_str = str(time.time() + expire)
    ts_byte = ts_str.encode("utf-8")
    sha1_tshexstr = hmac.new(key.encode("utf-8"), ts_byte, 'sha1').hexdigest()
    token = ts_str + ':' + sha1_tshexstr
    b64_token = base64.urlsafe_b64encode(token.encode("utf-8"))
    return b64_token.decode("utf-8")


def my_md5(s, salt=''):
    """
    :param s: 要加密的字符串
    :param salt: 加密的盐，默认无
    :return: res: str
    """
    s = s + salt
    news = str(s).encode()
    m = hashlib.md5(news)
    return m.hexdigest()


def save_file(file,path):
    if not allowed_file(file.filename):
        return None
    filename = random_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(os.path.join(path, filepath))
    return urljoin(request.host_url, filepath)

def upload(files, original_id, type,con,path):
    df_list = []
    if files:
        for file in files:
            file_url = save_file(file, path)
            if file_url is None:
                return jsonify(code=400, msg="文件类型不允许")
            df_list.append(pd.DataFrame({"file_name": file.filename, "file_url": file_url, "original_id": original_id,
                                         "type": type}, index=[0]))
        df = pd.concat(df_list, ignore_index=True)
        con.write_table('file_table', df)
    return jsonify(code=200, msg="上传成功")

def upload_update(original_id, type, url_string,files,con,path):
    sql = f"select file_url from file_table where original_id='{original_id}' and type=N'{type}' " \
          f"and file_url not in ('{url_string}')"
    df=con.get_mssql_data(sql)
    url_list = df['file_url'].to_list()
    filename_list = [url.split('\\')[-1] for url in url_list]
    # 遍历列表中的文件名，删除对应的文件
    if filename_list[0]!='':
        for filename in filename_list:
            filepath = os.path.join(path, UPLOAD_FOLDER, filename)  # 拼接文件路径
            if os.path.exists(filepath):  # 如果文件存在，则删除
                os.remove(filepath)
        sql = f"delete from file_table where original_id='{original_id}' and type=N'{type}' " \
              f"and file_url not in ('{url_string}')"
        con.update_mssql_data(sql)
    return upload(files,original_id,type,con,path)

def del_file(urls,id,type,con,path):
    for i in urls:
        i=os.path.basename(i)
        i = os.path.join(path,UPLOAD_FOLDER, i)
        # 删除文件
        os.remove(i)
    sql = f"delete from file_table where original_id={id} and type=N'{type}'"
    con.update_mssql_data(sql)
