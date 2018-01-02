from utils.message.basemsg import BaseMessage

class MsgMessage(BaseMessage):
    def __init__(self):
        pass

    def send(self, to, name, subject,body):
        print('in msg message')