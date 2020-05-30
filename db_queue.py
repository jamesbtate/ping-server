"""
The DBQueue class
"""

from mysql.connector.errors import DatabaseError, OperationalError
import database_mysql


class DBQueue(object):
    """
    Represents a MySQL-backed message queue
    """

    def __init__(self, db: database_mysql.DatabaseMysql):
        self.db: database_mysql.DatabaseMysql = db
        self.table_name: str = "message_queue"
        self._check_create_table()

    def _check_create_table(self) -> None:
        """ Check if the queue table already exists and create it if it does not exist. """
        query = "DESCRIBE {}".format(self.table_name)
        try:
            self.db.execute(query)
        except DatabaseError or OperationalError as e:
            if e.errno == 1234567:
                # placeholder. make table here.
                pass
            else:
                raise

    def push(self, message: str) -> None:
        """ Push a message to the back of the queue """
        pass

    def pop(self) -> str:
        """ Pop a message from the front of the queue """
        pass
