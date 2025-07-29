import pymysql
conn = pymysql.connect(
    host='localhost',
    user='user',
    password='12345678',
    database='case_mgmt'
)
print("連線成功")
