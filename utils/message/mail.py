import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from utils.message.basemsg import BaseMessage
from django.conf import settings


class EmailMessage(BaseMessage):
    """ 实现发送邮件功能

    """

    def __init__(self):
        self.user = settings.EMAIL_USER
        self.password = settings.EMAIL_PWD
        self.email = settings.EMAIL_ADDR

    def send(self, to, name, subject, body):
        """ 实现发送邮件功能
        Args:
            to: 目标email地址
            name: 目标用户名称
            subject: 主题
            body: 正文
        """

        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From'] = formataddr([self.user, self.email], charset='utf-8')
        msg['TO'] = formataddr([name, to])
        msg['Subject'] = subject
        s = smtplib.SMTP()
        with s.connect("smtp.qq.com", 465) as server:
            print('in login')
            server.login(
                self.email,
                self.password
            )
            print('login successgul')
            server.sendmail(
                from_addr=self.email,
                to_addrs=[to, ],
                msg=msg.as_string()
            )


# if __name__ == '__main__':
#
    # e = Email()
    # e.send(
    #     to='1146877568@qq.com',
    #     name='ziawang',
    #     subject='haha',
    #     body='ssssssssssssssssss'
    # )
