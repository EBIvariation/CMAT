import codecs
import json
import urllib.request

from eva_cttv_pipeline import config


class CellbaseRecords(object):
    def __init__(self, limit=config.BATCH_SIZE):
        self.skip = 0
        self.limit = limit

    def __iter__(self):
        while True:
            curr_result_list = self.__get_curr_result_list()
            if not curr_result_list:
                break
            for record in curr_result_list:
                yield record
            self.skip += config.BATCH_SIZE

    def __get_curr_response(self):
        reader = codecs.getreader("utf-8")
        url = 'http://' + config.HOST + \
              '/cellbase/webservices/rest/v3/hsapiens/' + \
              'feature/clinical/all?source=clinvar&skip=' + \
              str(self.skip) + '&limit=' + str(self.limit)
        answer = urllib.request.urlopen(url)
        curr_response = json.load(reader(answer))['response'][0]
        return curr_response

    def __get_curr_result_list(self):
        curr_response = self.__get_curr_response()
        curr_result_list = curr_response['result']
        if len(curr_result_list) == 0:
            return None
        return curr_result_list
