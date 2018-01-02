from django.utils.safestring import mark_safe
from copy import deepcopy
from django.http import QueryDict


class ShowView(object):
    """ 列表页面功能类

    """
    def __init__(self, config_obj, queryset):
        self.queryset = queryset
        self.config_obj = config_obj
        self.request = config_obj.request
        self.model_class = self.config_obj.model_class

        # 用于标注
        self.list_display = self.config_obj.get_list_display()
        self.show_add_btn = self.config_obj.get_add_url()
        self.search_list = self.config_obj.get_search_list()
        self.show_search_form = self.config_obj.get_show_search_form()
        self.action_list = self.config_obj.get_action_list()
        self.show_action_form = self.config_obj.get_show_action_form()
        self.combain_search_field_list = self.config_obj.get_combain_search_field_list()
        self.edit_link = self.config_obj.get_edit_link()
        self.show_combain_search = self.config_obj.get_show_combain_search()

        from curd.service.pagintator import Paingator

        page_obj = Paingator(
            base_url=self.request.path_info,
            obj_count=queryset.count(),     # 所有记录的总个数
            params=self.request.GET,
            per_page_count=10,
            init_page_count=11,
            request=self.request
        )
        self.page_obj = page_obj
        self.page_data_list = queryset[page_obj.start:page_obj.end]     # 用于生成指定页码对应页面记录

    def th_list(self):
        """ 用于列表页面生成表头数据
        Return:
            返回值为包含表头数据的列表
        """

        if self.list_display:
            head_list = []
            for field in self.list_display:
                if isinstance(field, str):
                    verbose_name = self.config_obj.model_class._meta.get_field(field).verbose_name

                else:
                    verbose_name = field(self.config_obj, is_header=True)
                head_list.append(verbose_name)
        else:
            head_list = [self.config_obj.model_class._meta.verbose_name_plural]
        return head_list

    def td_list(self):
        """ 用于生成表格数据
        Return:
            返回一个包含了单元格数据的生成器
        """

        def generator_tr(objects):
            def generator_td(obj):
                if self.config_obj.get_list_display():
                    for field in self.list_display:
                        if isinstance(field, str):
                            val = getattr(obj, field)
                        else:
                            val = field(self.config_obj, obj, is_header=False)
                        if field in self.edit_link:
                            val = self.get_edit_link_url(obj, val)
                        yield val
                # else:
                #     yield from self.config_obj.model_class.objects.all()
            yield from [generator_td(obj) for obj in objects]
        return generator_tr(self.page_data_list)

    def get_edit_link_url(self, obj, text):
        query_str = self.request.GET.urlencode()
        if not query_str:
            return mark_safe('<a href="%s">%s</a>' % (self.config_obj.get_change_url(obj.id), text))
        else:
            params = QueryDict(mutable=True)
            params[self.config_obj._query_str_key] = query_str
            return mark_safe('<a href="%s?%s">%s</a>' % (self.config_obj.get_change_url(obj.id), params.urlencode(), text))

    def template_modify_action_list(self):
        """ 为批量操作的actions下拉框提供渲染时使用的数据
        Return:
            返回存放了action批量操作的函数的函数名以及该函数的func_description属性组成的俩表
        """

        result = []
        for func in self.action_list:
            temp = {
                'func_description': func.func_description,
                'func_name': func.__name__
            }
            result.append(temp)
        return result

    def add_url(self):
        return self.config_obj.get_add_url()

    def template_combain_search_field_list(self):
        """ 生成器函数。渲染列表页面的组合搜索
        Return:
            返回一个可迭代的search_row对象。search_row对象内部实现了 "__iter__" 方法，
            遍历该对象时，返回的将是该对象data属性中存放的一个个记录对象对应搜索选项的超链接。
        """

        from django.db.models import ForeignKey, ManyToManyField

        for search_option_obj in self.combain_search_field_list:
            field = self.model_class._meta.get_field(search_option_obj.field_name)
            if isinstance(field, ForeignKey):               # 外键字段
                row = SearchRow(
                    option_obj=search_option_obj,
                    request=self.request,
                    data=search_option_obj.get_queryset(field)
                )
            elif isinstance(field, ManyToManyField):        # 多对多字段
                row = SearchRow(
                    option_obj=search_option_obj,
                    request=self.request,
                    data=search_option_obj.get_queryset(field)
                )
            else:                                           # choices字段
                row = SearchRow(
                    option_obj=search_option_obj,
                    request=self.request,
                    data=search_option_obj.get_choices(field)
                )
            yield row



class SearchOption(object):
    """ 用于封装配置信息

    """

    def __init__(self, field_name, is_multi=False, condition=None, is_choices=False, text_func_name=None, val_func_name=None):
        self.field_name = field_name
        self.is_multi = is_multi
        self.condition = condition
        self.is_choices = is_choices
        self.text_func_name = text_func_name
        self.val_func_name = val_func_name

    def get_choices(self, field):
        """ 获取字段的choices参数对应列表
        Args:
            field: 一个初始化了choices参数的field对象
        Return:
            返回choices二元元组组成的列表
        """

        return field.choices

    def get_queryset(self, field):
        """ 获取ForeignKey/ManyToManyKey关联的主键表的满足筛选条件的所有记录对象
        Args:
            field: 一个ForeignKey或者ManyToManyKey字段对象
        Return:
            返回主键表满足条件的记录对象组成的QuerySet对象
        """

        if self.condition:
            try:
                results = field.related_model.objects.filter(**self.condition)      # Dajngo2.0, 也可使用"field.model"
            except AttributeError as e:
                print(e)
                results = field.rel.to.objects.filter(**self.condition)             # Django2.0以下版本
            return results
        return field.related_model.objects.all()


class SearchRow(object):
    """ 用于生成每一行的选项

    """

    def __init__(self, option_obj, request, data):
        self.option_obj = option_obj
        self.request = request
        self.data = data

    def __iter__(self):
        params = deepcopy(self.request.GET)
        params._mutable = True
        current_id = params.get(self.option_obj.field_name)
        current_id_list = params.getlist(self.option_obj.field_name)

        if self.option_obj.field_name in params:
            origin_list = params.pop(self.option_obj.field_name)
            url = "{0}?{1}".format(self.request.path_info, params.urlencode())
            yield mark_safe('<a href="{0}">全部</a>'.format(url))
            params.setlist(self.option_obj.field_name, origin_list)
        else:
            url = "{0}?{1}".format(self.request.path_info, params.urlencode())
            yield mark_safe('<a class="active" href={0}>全部</a>'.format(url))

        # 遍历choices列表或者quersyet，取出渲染模板需要的数据
        for obj in self.data:
            if self.option_obj.is_choices:          # 选项为二元元组组成的列表形式
                pk, text = str(obj[0]), obj[1]
            else:                                   # 选项为QuerySet
                pk = self.option_obj.val_func_name(obj) if self.option_obj.val_func_name else str(obj.pk)
                text = self.option_obj.text_func_name(obj) if self.option_obj.text_func_name else str(obj)
            if not self.option_obj.is_multi:        # 单选
                params[self.option_obj.field_name] = pk
                url = "{0}?{1}".format(self.request.path_info, params.urlencode())
                if current_id == pk:
                    yield mark_safe('<a class="active" href="{0}">{1}</a>'.format(url, text))
                else:
                    yield mark_safe('<a href="{0}">{1}</a>'.format(url, text))
            else:                                   # 选项为多选
                _params = deepcopy(params)      # ！！
                id_list = _params.getlist(self.option_obj.field_name)

                if pk in current_id_list:       # 取消勾选条件
                    id_list.remove(pk)
                    _params.setlist(self.option_obj.field_name, id_list)
                    url = "{0}?{1}".format(self.request.path_info, _params.urlencode())
                    yield mark_safe('<a class="active" href="{0}">{1}</a>'.format(url, text))
                else:
                    id_list.append(pk)
                    _params.setlist(self.option_obj.field_name, id_list)
                    url = "{0}?{1}".format(self.request.path_info, _params.urlencode())
                    yield mark_safe('<a href="{0}">{1}</a>'.format(url, text))

