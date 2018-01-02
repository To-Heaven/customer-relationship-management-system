from curd.service import sites

from crm import models


class CustomerDistributionConfig(sites.CURDConfig):
    def status_display(self, obj=None, is_header=False):
        if is_header:
            return '状态'
        return obj.get_status_display()
    list_display = ['user', 'customer', status_display]

