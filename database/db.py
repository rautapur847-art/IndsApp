import os
import mysql.connector as mc
from dotenv import load_dotenv

load_dotenv() # reads .env in your project root

class Database:
    def __init__(self):
       self.conn = None
       self.cur = None
       try:
           connect_kwargs = dict(
               host=os.getenv("MYSQL_HOST"),
               port=int(os.getenv("MYSQL_PORT", "4000")),
               user=os.getenv("MYSQL_USER"),
               password=os.getenv("MYSQL_PASSWORD"),
               database=os.getenv("MYSQL_DATABASE"),
               autocommit=True,  # so every connection sees the latest
                                 # committed data immediately, instead of
                                 # reading a stale snapshot until this
                                 # connection's own next commit
           )
           # TiDB Cloud requires TLS. If you downloaded a CA cert (TiDB
           # Dedicated) put its path in MYSQL_CA_PATH; TiDB Serverless
           # usually works without one (just needs SSL enabled).
           ca_path = os.getenv("MYSQL_CA_PATH")
           if ca_path:
               connect_kwargs["ssl_ca"] = ca_path
               connect_kwargs["ssl_verify_cert"] = True
           else:
               connect_kwargs["ssl_disabled"] = False
           self.conn = mc.connect(**connect_kwargs)
           self.cur = self.conn.cursor(dictionary=True)
       except mc.Error as e:
           print(f"Database Connection Error: {e}")
           # Re-raise instead of silently continuing — otherwise every
           # method below fails later with a confusing, unrelated-looking
           # "'ChatBotDatabase' object has no attribute 'cur'" instead of
           # the actual connection error above.
           raise
       
    def get_user_by_id(self, my_id):

        sql = """ SELECT *FROM user WHERE id = %s"""
        self.cur.execute(sql, (my_id,))
        return self.cur.fetchone()

    def UserRegister(self,name,phone,email,password):
        sql="""insert into user(name,phone,email,password) values (%s, %s, %s, %s)""" 
        self.cur.execute(sql,(name,phone,email,password))  
        self.conn.commit()
        