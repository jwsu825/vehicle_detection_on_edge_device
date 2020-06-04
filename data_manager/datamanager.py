import threading
import time
from datetime import datetime

import MySQLdb
import requests

import constants
from configuration.configuration import configuration


class DataManager:
    def __init__(self, input_q, username, password, database, table):
        self.conn = MySQLdb.connect("localhost", username, password, database)
        self.c = self.conn.cursor()
        self.table = table

        self.c.execute("desc " + self.table)

        self.status = constants.Status.RUNNING

        self.post_queue = input_q
        self.post_thread = threading.Thread(target=self.__post_thread)
        self.post_thread.start()

    @property
    def url(self):
        return configuration.get_value('data_management', 'push_location')

    @property
    def token(self):
        return configuration.get_value('data_management', 'push_token')

    @property
    def post_interval(self):
        tmp = configuration.get_value('data_management', 'push_interval')
        if tmp is None:
            return 60
        return tmp

    @property
    def black_list(self):
        tmp = configuration.get_value('data_management', 'black_list')
        if tmp is None:
            return []
        return tmp

    def store_multiple(self, results):
        for res in results:
            if res['category'] in self.black_list:
                continue
            self.store_tuple(res['category'], entry_time=datetime.fromtimestamp(res['time']))

    def store_tuple(self, category, entry_time=None, lat=0.000000, lon=0.000000, color=None, brand=None):
        if entry_time is None:
            entry_time = datetime.now()

        self.c.execute("INSERT INTO " + self.table + " VALUES (0, %s, %s)",
                       (entry_time, category))
        self.conn.commit()

    def fetch_from_queue(self):
        rows = []
        while not self.post_queue.empty():
            rows.append(self.post_queue.get())
        return rows

    def post_result(self, result):
        try:
            response = requests.post(self.url + '/api/devices/entries', json=result,
                                     headers={'Authorization': 'Token ' + self.token})
            print(response.status_code)
            return response.status_code == 200
        except Exception as e:
            print(e)
            return False

    def post_from_db(self):
        results = self.fetch_all()
        num_results = len(results)
        if num_results == 0:
            return
        if self.post_result(results):
            self.delete_rows(num_results)

    def post_from_queue(self):
        results = self.fetch_from_queue()
        num_results = len(results)
        if num_results == 0:
            return
        if not self.post_result(results):
            self.store_multiple(results)

    def __post_thread(self):
        while self.status == constants.Status.RUNNING:
            try:
                self.post_from_db()
                self.post_from_queue()
                time.sleep(self.post_interval)
            except Exception as e:
                self.store_multiple(self.fetch_from_queue())

    def fetch_all(self):
        rowcount = self.c.execute("SELECT * FROM " + self.table)
        results = self.c.fetchmany(rowcount)
        if results is not None:
            tmp_res = []
            for result in results:
                tmp_res.append({
                    'time': datetime.now().timestamp(),
                    'category': result[4]
                })
            return tmp_res
        return None

    def stop(self):
        self.status = constants.Status.STOPPED
        self.post_thread.join()

    def delete_rows(self, quantity):
        self.c.execute("DELETE FROM " + self.table + " LIMIT " + str(quantity))
        self.conn.commit()
