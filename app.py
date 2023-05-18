import json
import os
from urllib.parse import urljoin
from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS, cross_origin
from lib.db import UseSQLServer
from utils.common import my_md5, generate_token, allowed_file, random_filename, upload, upload_update, del_file

secret = 'attend'
random_str = 'attend~%!$#^&*'
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
UPLOAD_FOLDER = './attachment'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def job():
    sql = "update studnet set tag='false'"
    con = UseSQLServer()
    con.update_mssql_data(sql)


scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(job, 'cron', hour=0, minute=0)
scheduler.start()


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


@app.route('/get/data', methods=['GET'])
def get_data():
    sql = request.args.get('sql')
    con = UseSQLServer()
    df = con.get_mssql_data(sql)
    return jsonify(code=200, data=df.fillna('').to_dict('records'), msg="success")


@app.route('/password/reset', methods=['GET'])
def password_reset():
    username = request.args.get('username')
    con = UseSQLServer()
    sql = f"update user_table set password='055b3a993737b01c9c042f46420c84fe',has_login=0 where username='{username}'"
    df = con.update_mssql_data(sql)
    if df == 'success':
        return jsonify(code=200, msg=df)
    else:
        return jsonify(code=404, msg="操作失败")


@app.route('/delete', methods=['GET'])
def delete():
    id = request.args.get('id')
    table = request.args.get('table')
    con = UseSQLServer()
    sql1 = f"delete from {table} where id='{id}'"
    df1 = con.update_mssql_data(sql1)
    if table == 'notice':
        sql = f"select file_url from file_table where original_id='{id}' and type=N'通知'"
        df = con.get_mssql_data(sql)
        files = df['file_url'].to_numpy()
        del_file(files, id, '通知', con, app.root_path)
    if table == 'board':
        sql = f"select file_url from file_table where original_id='{id}' and type=N'公告'"
        df = con.get_mssql_data(sql)
        files = df['file_url'].to_numpy()
        del_file(files, id, '公告', con, app.root_path)
    if df1 == 'success':
        return jsonify(code=200, msg=df1)
    else:
        return jsonify(code=404, msg="操作失败")


@app.route('/see', methods=['get'])
def see():
    id = request.args.get('id')
    table = request.args.get('table')
    con = UseSQLServer()
    if table == 'process':
        sql = f"select * from process_item where process_id={id}"
    else:
        sql = f"select * from {table} where id={id}"
    df = con.get_mssql_data(sql)
    return jsonify(code=200, data=df.fillna('').to_dict('records'), msg="success")


@app.route('/upload/data', methods=['POST'])
def upload_data():
    def convert_privilege(value):
        if value == '学生':
            return 0
        elif value == '老师':
            return 1
        else:
            return value

    file = request.files['file']
    df = pd.read_excel(file)
    df = df.rename(columns={'用户名': 'username', '姓名': 'name', '身份': 'privilege'})
    df['privilege'] = df['privilege'].apply(convert_privilege)
    con = UseSQLServer()
    con.write_table('user_table', df)
    return jsonify(code=200, msg='上传成功')


@app.route('/student/health_record/get', methods=['GET'])
def student_health_record_get():
    username = request.args.get('username')
    sql = f"select * from student where username='{username}'"
    con = UseSQLServer()
    df = con.get_mssql_data(sql)
    if not df.empty:
        return jsonify(code=200, data=df.fillna('').to_dict('records'), msg="success")
    else:
        return jsonify(code=404, msg='未找到资源'), 404


@app.route('/ask_for_leave/preview', methods=['get'])
def ask_for_leave_preview():
    con = UseSQLServer()
    id = request.args.get('id')
    sql = f"select a.start_time,a.end_time,a.reason from ask_for_leave a where a.id={id}"
    df = con.get_mssql_data(sql)
    return jsonify(code=200, msg="success", data=df.fillna('').to_dict('records'))


@app.route('/ask_for_leave/add', methods=['POST'])
def ask_for_leave_add():
    con = UseSQLServer()
    data = request.form
    files = request.files.getlist('file')
    username = data['username']
    name = data['name']
    reason = data['reason']
    start_time = data['start_time']
    end_time = data['end_time']
    df1 = pd.DataFrame()
    df1 = df1.append(
        {"username": username, "name": name, 'reason': reason, 'start_time': start_time, 'end_time': end_time},
        ignore_index=True)
    con.write_table('ask_for_leave', df1)
    sql = 'SELECT MAX(id) as id FROM ask_for_leave'
    df = con.get_mssql_data(sql)
    id = df.iloc[0]['id']
    return upload(files, id, '请假', con, app.root_path)


@app.route('/ask_for_leave/delete', methods=['POST'])
def ask_for_leave_delete():
    val = json.loads(request.get_data())
    con = UseSQLServer()
    id = val['id']
    sql = f"select file_url from file_table where original_id='{id}' and type=N'请假'"
    df = con.get_mssql_data(sql)
    files = df['file_url'].to_numpy()
    sql = f"DELETE FROM ask_for_leave WHERE id={id}"
    con = UseSQLServer()
    del_file(files, id, '请假', con, app.root_path)
    df = con.update_mssql_data(sql)
    if df == 'success':
        return jsonify(code=200, msg=df)
    else:
        return jsonify(code=404, msg="删除失败")


@app.route('/student/health_record/update', methods=['POST'])
def student_health_record_update():
    val = json.loads(request.get_data())
    sql = f"update student set address=N'{val['address']}',genetic_history=N'{val['genetic_history']}',drug_allergy_history=N'{val['drug_allergy_history']}'," \
          f"common_disease=N'{val['common_disease']}',else_disease=N'{val['else_disease']}',is_marriage=N'{val['is_marriage']}'" \
          f" where username='{val['username']}'"
    con = UseSQLServer()
    df = con.update_mssql_data(sql)
    if df == 'success':
        return jsonify(code=200, msg=df)
    else:
        return jsonify(code=404, msg="更新失败")


@app.route('/attachment/<path:filename>')
def get_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/old_file/get', methods=['get'])
def old_file_get():
    original_id = request.args.get('original_id')
    type = request.args.get('type')
    sql = f"select file_name,file_url from file_table where type=N'{type}' and original_id='{original_id}'"
    con = UseSQLServer()
    df = con.get_mssql_data(sql)
    return jsonify(code=200, msg="success", data=df.fillna('').to_dict('records'))


@app.route('/ask_for_leave/update', methods=['POST'])
def ask_for_leave_update():
    con = UseSQLServer()
    data = request.form
    id = data['id']
    reason = data['reason']
    start_time = data['start_time']
    end_time = data['end_time']
    old_file = eval(data['old_file'])
    old_file_string = "','".join(old_file)
    new_file = request.files.getlist('file')
    sql = f"UPDATE ask_for_leave SET reason = '{reason}', start_time = '{start_time}', end_time = '{end_time}' " \
          f"WHERE id = {id}"
    con.update_mssql_data(sql)
    return upload_update(id, '请假', old_file_string, new_file, con, app.root_path)


@app.route('/student/info/get', methods=['get'])
def student_info_get():
    username = request.args.get('username')
    sql = f"select * from student where name=N'{username}'"
    con = UseSQLServer()
    df = con.get_mssql_data(sql)
    return jsonify(code=200, msg="success", data=df.fillna('').to_dict('records'))


@app.route('/process/submit', methods=['POST'])
def process_submit():
    con = UseSQLServer()
    val = json.loads(request.get_data())
    type = val['type']
    username = val['username']
    sql = f"insert process(type,username) values(N'{type}','{username}')"
    con.update_mssql_data(sql)
    sql = f"select max(id) id from process "
    df1 = con.get_mssql_data(sql)
    df = pd.DataFrame(val['table'])
    df['id'] = df1.iloc[0]['id']
    con.write_table('process_item', df.fillna(''))
    return jsonify(code=200, msg="success")

@app.route('/process/get',methods=['get'])
def process_get():
    name = request.args.get('name')
    sql=f"select class from class where name=N'{name}'"
    con=UseSQLServer()
    df=con.get_mssql_data(sql)
    class_name=df.iloc[0]['class']
    sql=f"select username from student where class=N'{class_name}'"
    df=con.get_mssql_data(sql)
    username="','".join(df['username'])
    sql=f"select id,username,time,condition from ask_for_leave where username in ('{username}')"
    df_leave=con.get_mssql_data(sql)
    df_leave['type']='请假'
    sql=f"select id,username,time,type,condition from process where username in ('{username}')"
    df_process=con.get_mssql_data(sql)
    result = pd.concat([df_leave, df_process])
    return jsonify(code=200, msg="success",data=result.fillna('').to_dict('records'))

@app.route('/process/approval',methods=['get'])
def process_approval():
    id=request.args.get('id')
    type=request.args.get('type')
    condition=request.args.get('condition')
    con=UseSQLServer()
    if type == '请假':
        sql=f"update ask_for_leave set condition='{condition}' where id={id}"
        con.update_mssql_data(sql)
    else:
        sql=f"update process set condition='{condition}' where id={id}"
        con.update_mssql_data(sql)
    return jsonify(code=200, msg="success")

@app.route('/process/update', methods=['post'])
def update():
    val = json.loads(request.get_data())
    id = val['id']
    df = pd.DataFrame(val['table'])
    sql = f"delete from process_item where process_id={id}"
    con = UseSQLServer()
    con.update_mssql_data(sql)
    df = df.loc[:, ['item1', 'item2', 'item3', 'item4', 'item5', 'item6']]
    df['process_id'] = id
    con.write_table('process_item', df.fillna(''))
    return jsonify(code=200, msg="success")


@app.route('/stu/submit', methods=['GET'])
def submit():
    mysql_connect = UseSQLServer()
    username = request.args.get('username')
    body_condition = request.args.get('body_condition')
    is_infection = request.args.get('is_infection')
    temperature = request.args.get('temperature')
    location = request.args.get('location')
    infection_count = request.args.get('infection_count')
    other_condition = request.args.get('other_condition')
    sql = "INSERT INTO health_declartion (username, is_infection, temperature, location, body_condition,infection_count," \
          f"other_condition) VALUES ('{username}', '{is_infection}', '{temperature}', {location}, '{body_condition}'," \
          f" '{infection_count}','{other_condition}');"
    df = mysql_connect.update_mssql_data(sql)
    sql = f"update student set tag='true' where username='{username}'"
    df = mysql_connect.update_mssql_data(sql)
    if df == 'success':
        return jsonify(code=200, msg=df)
    else:
        return jsonify(code=404, msg="insert failed")


@app.route('/notice/submit', methods=['post'])
def notice_submit():
    con = UseSQLServer()
    data = request.form
    files = request.files.getlist('notice_file')
    author = data['author']
    text = data['text']
    course = data['course']
    df1 = pd.DataFrame()
    df1 = df1.append(
        {"author": author, "text": text, 'course': course},
        ignore_index=True)
    con.write_table('notice', df1)
    sql = 'SELECT MAX(id) as id FROM notice'
    df = con.get_mssql_data(sql)
    id = df.iloc[0]['id']
    return upload(files, id, '通知', con, app.root_path)

@app.route('/notice/get',methods=['get'])
def notice_get():
    username=request.args.get('username')
    sql="select a.* from notice a inner join course b on a.course=b.course inner join student c on b.class=c.class " \
        f"where c.username='{username}'"
    con=UseSQLServer()
    df=con.get_mssql_data(sql)
    print(df)
    return jsonify(code=200, msg="success",data=df.fillna('').to_dict('records'))
@app.route('/class/submit', methods=['post'])
def class_submit():
    con = UseSQLServer()
    data = json.loads(request.get_data())
    name = data['name']
    class_name = data['class']
    df1 = pd.DataFrame()
    df1 = df1.append(
        {"name": name, 'class': class_name},
        ignore_index=True)
    con.write_table('class', df1)
    return jsonify(code=200, msg="success")


@app.route('/attend/submit', methods=['post'])
def attend_submit():
    con = UseSQLServer()
    data = json.loads(request.get_data())
    course = data['course']
    class_name = data['class']
    teacher = data['teacher']
    df1 = pd.DataFrame()
    df1 = df1.append(
        {"course": course, 'class': class_name, 'teacher': teacher},
        ignore_index=True)
    con.write_table('course', df1)
    return jsonify(code=200, msg="success")


@app.route('/class/update', methods=['post'])
def class_update():
    con = UseSQLServer()
    data = json.loads(request.get_data())
    id = data['id']
    name = data['name']
    class_name = data['class']
    sql = f"update class set name=N'{name}',class=N'{class_name}' where id={id}"
    con.update_mssql_data(sql)
    return jsonify(code=200, msg="success")


@app.route('/board/submit', methods=['post'])
def board_submit():
    con = UseSQLServer()
    data = request.form
    files = request.files.getlist('board_file')
    author = data['author']
    text = data['text']
    title = data['title']
    df1 = pd.DataFrame()
    df1 = df1.append(
        {"author": author, "text": text, 'title': title},
        ignore_index=True)
    con.write_table('board', df1)
    sql = 'SELECT MAX(id) as id FROM notice'
    df = con.get_mssql_data(sql)
    id = df.iloc[0]['id']
    return upload(files, id, '公告', con, app.root_path)


@app.route('/board/get', methods=['get'])
def get_board():
    con = UseSQLServer()
    sql = "select top 5 a.* from board a"
    df = con.get_mssql_data(sql)
    return jsonify(code=200, msg="success", data=df.fillna('').to_dict('records'))


@app.route('/teacher/get', methods=['get'])
def get_teacher():
    con = UseSQLServer()
    sql = "select name from user_table where privilege=1"
    df = con.get_mssql_data(sql)
    return jsonify(code=200, msg="success", data=df.fillna('').to_dict('records'))


@app.route('/class/get', methods=['get'])
def get_class():
    con = UseSQLServer()
    sql = "select class from class"
    df = con.get_mssql_data(sql)
    return jsonify(code=200, msg="success", data=df.fillna('').to_dict('records'))


@app.route('/course/get', methods=['get'])
def get_course():
    teacher = request.args.get('teacher')
    con = UseSQLServer()
    sql = f"select course,class from course where teacher='{teacher}'"
    df = con.get_mssql_data(sql)
    df['result'] = df['course'] + '-' + df['class']
    return jsonify(code=200, msg="success", data=df.fillna('').to_dict('records'))


@app.route('/attend/insert', methods=['get'])
def attend_insert():
    con = UseSQLServer()
    class_name=request.args.get('class')
    course=request.args.get('course')
    time=request.args.get('time')
    sql=f"select count(1) total from student where class=N'{class_name}'"
    df=con.get_mssql_data(sql)
    sql=f"insert into attend(class,course,total,minute) values(N'{class_name}',N'{course}',{df.iloc[0]['total']},{time})"
    con.update_mssql_data(sql)
    sql=f"select max(id) id from attend where class=N'{class_name}' and course=N'{course}'"
    df=con.get_mssql_data(sql)
    sql=f"update student set attend_tag='true' where class=N'{class_name}'"
    con.update_mssql_data(sql)
    return jsonify(code=200, msg="success",id=str(df.iloc[0]['id']))

@app.route('/attend/get',methods=['get'])
def attend_get():
    username = request.args.get('username')
    sql=f"select class from student where username='{username}'"
    con=UseSQLServer()
    df=con.get_mssql_data(sql)
    class_name=df.iloc[0]['class']
    sql=f"select top 1 time,minute from attend where class=N'{class_name}' order by id desc"
    df=con.get_mssql_data(sql)
    time=df.iloc[0]['time']
    minute=df.iloc[0]['minute']
    target_time=time+datetime.timedelta(minutes=int(minute))
    current_time = datetime.datetime.now()
    if target_time>current_time:
        tag=True
    else:
        tag=False
    print(target_time)
    print(current_time)
    print(tag)
    return jsonify(code=200, msg="success", tag=tag)
@app.route('/attend/start', methods=['get'])
def attend_start():
    con = UseSQLServer()
    code=request.args.get('code')
    id=request.args.get('id')
    sql=f"update attend set code='{code}' where  id={id}"
    con.update_mssql_data(sql)
    return jsonify(code=200, msg="success")

@app.route('/attend/emd', methods=['get'])
def attend_end():
    class_name=request.args.get('class_name')
    id=request.args.get('id')
    sql=f"select username from student where class=N'{class_name}' and attend_tag='false'"
    con=UseSQLServer()
    df=con.get_mssql_data(sql)
    usernames=",".join(df['username'])
    sql=f"update attend set usernames='{usernames}' where id={id}"
    con.update_mssql_data(sql)
    return jsonify(code=200, msg="success",usernames=usernames)
@app.route('/attend/check', methods=['get'])
def attend_check():
    con=UseSQLServer()
    code=request.args.get('code')
    username = request.args.get('username')
    sql = f"select class from student where username='{username}'"
    con = UseSQLServer()
    df = con.get_mssql_data(sql)
    class_name = df.iloc[0]['class']
    sql = f"select top 1 id,code from attend where class=N'{class_name}' order by id desc"
    df=con.get_mssql_data(sql)
    sql_code=df.iloc[0]['code']
    id=df.iloc[0]['id']
    if sql_code == code:
        sql=f"update student set attend_tag='true' where username='{username}'"
        con.update_mssql_data(sql)
        sql=f"update attend set attend=attend+1 where id={id}"
        con.update_mssql_data(sql)
        tag=True
    else:
        tag=False
    return jsonify(code=200, msg="success", tag=tag)

@app.route('/student_info/submit', methods=['post'])
def studnet_info_submit():
    con = UseSQLServer()
    val = json.loads(request.get_data())
    df=pd.DataFrame(val,index=[0])
    con.write_table('student', df)
    return jsonify(code=200, msg="success")

if __name__ == '__main__':
    app.run(debug='True', port=5001)
