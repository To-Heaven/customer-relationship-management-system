from curd.service.sites import CURDConfig
from django.utils.safestring import mark_safe
from django.urls import re_path
from django.shortcuts import redirect, HttpResponse, render
from django.db.models import Q
from django.forms import ModelForm
from django.db.transaction import atomic

from utils.message import send_message
from django.conf import settings


from time import strftime
from datetime import date
import datetime

from crm import models
from crm import handler


class LoadSingleModelForm(ModelForm):
    class Meta:
        model = models.Customer
        exclude = ['recv_date', 'status', 'consultant', 'last_consult_date']


class CustomerConfig(CURDConfig):

    edit_link = ['qq']

    def gender_display(self, obj=None, is_header=False):
        """ 获取客户性别数据的函数 """

        if is_header:
            return '性别'
        return obj.get_gender_display()

    def course_display(self, obj=None, is_header=False):
        if is_header:
            return '感兴趣的课程'
        course_list = [
            '<a href="/curd/crm/customer/del_pre_course/%s/%s/?%s" style="display:inline-block; border: 1px solid blue; padding: 5px;margin: 3px">%s &nbsp;x</a>' % (obj.id, course.id, self.request.GET.urlencode(),str(course))
            for course in obj.course.all()
        ]
        return mark_safe(''.join(course_list))

    def del_pre_course(self, request, customer_id, course_id):
        customer = self.model_class.objects.filter(pk=customer_id).first()
        customer.course.remove(course_id)
        return redirect("%s?%s" % (self.get_show_url(), self.request.GET.urlencode()))

    def extra_url(self):
        urlpatterns = [
            re_path(r'del_pre_course/(\d+)/(\d+)/', self.add_request_decorator(self.del_pre_course), name="%s_%s_dc" % self.get_app_model()),
            re_path(r'public/', self.add_request_decorator(self.public_view), name="%s_%s_public" % self.get_app_model()),
            re_path(r'private/', self.add_request_decorator(self.private_view), name="%s_%s_private" % self.get_app_model()),
            re_path(r'(?P<customer_id>\d+)/competition/', self.add_request_decorator(self.competition_view), name="%s_%s_competition" % self.get_app_model()),
            re_path(r'single/', self.add_request_decorator(self.load_single_view), name="%s_%s_single" % self.get_app_model())
        ]
        return urlpatterns

    def record(self, obj=None, is_header=False):
        """ 生成表格中跟进记录

        """

        if is_header:
            return '跟进记录'
        return mark_safe('<a href="/curd/crm/consultrecord/?customer=%s">查看记录</a>' % (obj.pk))

    def public_view(self, request):
        """ 公司内部公共资源页面的视图函数
        Args:
            request: 当前请求对象
        """
        current_user_id = 35
        today = date.today()
        deadline_15 = today - datetime.timedelta(days=15)
        deadline_3 = today - datetime.timedelta(days=3)
        # # 方式一
        public_customer_list = models.Customer.objects.filter(
            Q(recv_date__lt=deadline_15) | Q(last_consult_date__lt=deadline_3),
            status=2
        )
        # 方式二
        # condition = Q()
        # cond1 = Q()
        # cond1.connector = 'OR'
        # cond1.children.append(("recv_date__lt", deadline_15))
        # cond1.children.append(("last_consult_date__lt", deadline_3))
        # cond2 = Q()
        # cond2.connector = 'OR'
        # cond2.children.append(("status", 2))
        # condition.add(cond1, 'AND')
        # condition.add(cond2, 'AND')
        # public_customer_list = models.Customer.objects.filter(condition)
        return render(request, 'public_view.html', {"public_customer_list": public_customer_list,
                                                    "current_user_id": current_user_id})

    def private_view(self, request):
        """ 用户个人客户资源详细信息页面

        """
        current_user_id = 35
        private_customer_distributions = models.CustomerDistribution.objects.filter(user_id=current_user_id).order_by('status')

        return render(request, 'user_view.html', {"private_customer_distributions": private_customer_distributions})

    def competition_view(self, request, customer_id):
        """ 接单功能视图
        Args:
            customer_id: 该条客户记录在客户表中id
        """

        current_user_id = 35
        today = date.today()
        deadline_15 = today - datetime.timedelta(days=15)
        deadline_3 = today - datetime.timedelta(days=3)
        customer_count = models.Customer.objects.filter(
            Q(recv_date__lt=deadline_15) | Q(last_consult_date__lt=deadline_3),
            status=2,
            id=customer_id
        ).exclude(consultant_id=current_user_id).update(recv_date=today,
                                                        last_consult_date=today,
                                                        consultant_id=current_user_id)

        if not customer_count:
            return HttpResponse('手速慢啦')

        models.CustomerDistribution.objects.create(user_id=current_user_id, customer_id=customer_id, ctime=today)

        return HttpResponse('抢单成功')

    def load_single_view(self, request):
        """ 单条录入客户资源时对应的视图函数

        """

        if request.method == 'GET':
            form = LoadSingleModelForm()
            return render(request, 'single.html', {"form": form})
        else:
            form = LoadSingleModelForm(data=request.POST)
            if form.is_valid():
                handler.HandlerDistribution.fetchall()
                saler_id = 35
                if not saler_id:
                    return HttpResponse('没有销售顾问，无法分配客户资源')

                today = date.today()

                # form.cleaned_data.setdefault("consultant_id", saler_id)                         # 分配客户
                # form.cleaned_data.setdefault("recv_date", today)
                #
                # course_id_list = [course.id for course in form.cleaned_data['course']]
                # del form.cleaned_data['course']
                #
                # new_customer = models.Customer.objects.create(**form.cleaned_data)             # 客户表新增数据
                # new_customer.course.add(*course_id_list)

                with atomic():
                    try:
                        form.instance.consultant_id = saler_id
                        form.instance.recv_date = today

                        new_customer = form.save()
                        models.CustomerDistribution.objects.create(                                     # 客户分配情况表新增数据
                            user_id=saler_id,
                            ctime=today,
                            customer=new_customer,
                        )
                    except Exception as e:
                        print(e)
                        handler.HandlerDistribution.rollback(sale_id=saler_id)
                        return HttpResponse('录入客户失败，出现异常')
                    # send_message(
                    #         to='1146877568@qq.com',
                    #         name='ziawang',
                    #         subject='haha',
                    #         body='ss'
                    #     )
                    print('发送邮件成功')
                return HttpResponse('录入客户成功')
            return render(request, 'single.html', {"form": form})

    search_list = ['name__contains']
    show_search_form = True

    list_display = ['name', gender_display, course_display, 'consultant', record]

