import importlib

from django.conf import settings


def send_message(to, name, subject, body):
    """  发送邮件、短信、微信信息
    Args:
        to: 目标email地址
        name: 目标用户名称
        subject: 主题
        body: 正文
    """

    for str_cls_path in settings.MEASSAGE_CLASS:
        module_path, class_name = str_cls_path.rsplit('.', 1)
        message_module = importlib.import_module(name=module_path)
        message_obj = getattr(message_module, class_name)()
        message_obj.send(to, name, subject, body)
