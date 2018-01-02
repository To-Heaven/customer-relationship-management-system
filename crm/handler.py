import redis
from collections import OrderedDict
from django.conf import settings

from crm import models

CONN = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
)


class HandlerDistribution(object):
    """ 实现客户资源分配
    功能:
        生成权重列表
    """

    salers = None
    salers_iter = None
    need_reset = False
    rollback_list = []

    @classmethod
    def fetchall(cls):
        """ 获取数据并组装成权重列表
        Return:
            权重列表，包含的是一个个销售记录对象
        """

        distributions = models.Distribution.objects.all().order_by('-weight')

        fetch_dict = OrderedDict()
        for distribution in distributions:
            fetch_dict[distribution.user] = distribution.num

        result = []
        max_range = max(fetch_dict.values())     # 获取最大循环数
        for i in range(max_range):
            for user, count in fetch_dict.items():
                if count>0:
                    result.append(user.id)
                    fetch_dict[user] -= 1

        if result:
            CONN.rpush(settings.SALE_ID_LIST, *result)
            CONN.rpush(settings.SALE_ID_LIST_ORIGIN, *result)           # [35, 34, 33, 34, 33, 33]
            return True
        return False

    @classmethod
    def get_saler_id(cls):
        """ 迭代salers_iter
        Return:
            返回值为销售人员的id
        """

        sale_id_origin_count = CONN.llen(settings.SALE_ID_LIST_ORIGIN)
        if not sale_id_origin_count:
            status = cls.fetchall()
            if not status:              # 数据库为空
                return None

        saler_id = CONN.lpop(settings.SALE_ID_LIST)
        if saler_id:                    # sale_id存在
            return saler_id

        # sale_id不存在，说明sale_id_list为空
        reset = CONN.get(settings.SALE_ID_RESET)
        if reset:                       # 需要重置，刷新sale_id_list_origin
            CONN.delete(settings.SALE_ID_LIST_ORIGIN)
            status = cls.fetchall()
            if not status:
                return None
            CONN.delete(settings.SALE_ID_RESET)
            return CONN.lpop(settings.SALE_ID_LIST)
        else:                           # 不需要重置，将sale_id_list_origin中数据保存一份到sale_id_list中
            sale_id_list_origin_count = CONN.llen(settings.SALE_ID_LIST_ORIGIN)
            for i in sale_id_list_origin_count:
                value = CONN.lindex(settings.SALE_ID_LIST_ORIGIN, i)
                CONN.rpush(settings.SALE_ID_LIST, value)
            return CONN.lpop(settings.SALE_ID_LIST)


    @classmethod
    def reset(cls):
        """ 当分配表中的记录变化时，此方法将会重置静态字段salers的值
        Return:
            None
        """

        CONN.set(settings.SALE_ID_RESET, 1)

    @classmethod
    def rollback(cls, sale_id):
        CONN.lpush(settings.SLAE_ID_LIST,sale_id)