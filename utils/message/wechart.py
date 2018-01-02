from utils.message.basemsg import BaseMessage


class WeChartMessage(BaseMessage):
    def __init__(self):
        pass

    def send(self, to, name, subject,body):
        print('in we chart')
