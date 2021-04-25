from mysql.connector import connect, Error
from getpass import getpass
import credentials

class Database:

    def __init__(self,**kwargs):
        self._connection = connect(user = credentials.username, password = credentials.password, **kwargs)
        self._cursor = self._connection.cursor()
        
    def __enter__(self):
        return self

    def __exit__(self):
        self.close()

    @property
    def connection(self):
        return self._connection

    @property
    def cursor(self):
        return self._cursor 
    
    def commit(self):
        self._connection.commit()

    def close(self,commit=True):
        if commit:
            self.commit()
        self._connection.close()

    def execute(self,query,params=None):
        self._cursor.execute(query,params or ())

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()

    def query(self, sql, params=None):
        self._cursor.execute(sql, params or ())
        return self.fetchall()

    def rows(self):
        return self.cursor.rowcount

    def create_database(self,name,use=True):
        self.execute(f"SHOW DATABASES LIKE '{name}'")
        if not self.fetchone():
            self.execute(f"CREATE DATABASE {name}")

            if use:
                self.execute(f"USE {name}")
        else:
            print(f"Database {name} already exists.")
    
    def create_table(self,name,schema=""):
        self.execute(f"SHOW TABLES LIKE '{name}'")
        if not self.fetchone() and schema:
            self.execute(f"CREATE TABLE {name}({schema})")
        else:
            print(f"Table {name} already exists or schema is empty.") 
            

def initialise_database():
    model = Database(host="localhost")

    model.create_database("scraped_data")

    model.create_table("prog_textbooks","""
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(150),
    publish_year YEAR(4),
    prog_language VARCHAR(30),
    frequency INT
    """)

def load_database(name):
    model = Database(host="localhost",database=name)



if __name__ == "__main__":
    load_database("scraped_data")



