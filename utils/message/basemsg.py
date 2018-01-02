from abc import ABCMeta
from abc import abstractmethod

#
# class BaseMessage(metaclass=ABCMeta):
#
#     @abstractmethod
#     def send(self, to, name, subject,body):
#         pass


class BaseMessage(object):
    def send(self, to, name, subject,body):
        raise NotImplementedError('你没有实现send方法昂')