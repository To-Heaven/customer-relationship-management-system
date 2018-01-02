"""
    包含curd的核心类CURDConfig和CURDSite，用来为每一个在curd.py中注册
    了的模型类生成增、删、改、查功能对应的url。

    使用:
        在启动文件curd.py中派生CURDConfig类
        class AuthorConfig(CURDConfig):

            def gender_display(seld, obj=None, is_header=False):
                if is_header:
                    return '性别'
                return self.get_gender_display()

            list_display = ['author_name', gender_display, 'age']

        site.register(Author, AuthorConfig)
"""

from django.urls import path, re_path, include
from django.shortcuts import render, HttpResponse, redirect
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.forms import ModelForm
from django.http import QueryDict
from curd.service.views import ShowView
from json import dumps


class CURDConfig:
    """ 用于处理CURD组件中增删改查的基类，对于每一个模型类，都需要有一个对应的配置类继承自该类;
        并为每一个`model_class`模型类生成url路径与视图函数之间的映射关系
    Example:
        class AuthorConfig(CURDConfig):
            list_display = ['name']
            ......

        site.register(Author, AuthorConfig)

    功能:
        1. 生成2级路由及视图函数
        2. 添加记录
        3. 表格中显示指定字段
        4. 搜索记录
        5. 记录的删除、编辑功能
        6. 编辑链接与其他字段结合
            edit_link = ['name']
        7. 组合搜索
        8. 批量操作action

    派生类中可以实现的功能:
        1. 扩展路由映射(须自定义视图函数并未视图函数添加装饰器)
        2. 根据权限覆盖get_list_display
        3. 根据权限确定是否显示添加按钮
        4. 根据权限确定是否显示批量操作action
            show_action_form = True
        5. 根据权限确定是否显示 "搜索" or "组合搜索"
            show_search_form = True

        6. 扩展记录对应的功能(须扩展路由和视图函数)
            def like_this(self, obj=None, is_header=False):
                ....

            def like_view(self, request, *args, **kwargs)：
                ....

            def extra_urls(self):
                url_patterns = [
                    re_path(
                        r'xx/xx/xx/$',
                        self.add_request_decorator(self.like_view),
                        name="%s_%s_like" % self.get_app_model())
                ]

            list_display = [like_this, 'xxx', ...]

        7. 覆盖 or 扩展视图函数
        8. 自定义派生ModelForm(须通过参数传入该类)
            model_form_class = YourModelForm
        9. 自定义字段显示的格式
            def xxx_display(self, obj=None, is_header=False):
                ....

    Methods 分类:
        路由部分:
                add_request_decorator
                get_urls
                extra_url

        功能权限部分:
                get_list_display
                get_show_add_btn
                get_show_search_form
                get_search_list
                get_show_action_form
                get_action_list

        记录操作权限部分:
                delete
                change
                checkbox

        反向解析url部分:
                get_delete_url
                get_change_url
                get_add_url
                get_show_url

        视图函数部分:
                show_view
                add_view
                delete_view
                change_view

        表单部分:
                get_model_form_class

        搜索功能部分:
                create_search_condition

    """

    def __init__(self, model_class, curb_site_obj):
        self.model_class = model_class
        self.site = curb_site_obj
        self.request = None
        self._query_str_key = '_filter'

    def get_app_model(self):
        """ 获取当前模型类的名称和该模型类所在应用的名称
        Return:
              返回一个存放二元元组: (模型类名, 应用名)
        """

        app_model = (
            self.model_class._meta.app_label,
            self.model_class._meta.model_name
        )
        return app_model

    def add_request_decorator(self, view_func):
        """ 在执行进入视图函数之前为config对象添加request属性
            本项目中没有使用语法糖"@"，而是使用了比较原始的方式.
            比如：
                使用"self.add_request_decorator(self.show_view)"
        Args:
            view_func: 要被装饰的视图函数
        """

        def inner(request, *args, **kwargs):
            self.request = request
            return view_func(request, *args, **kwargs)
        return inner

    def get_urls(self):
        """ 生成路径与视图函数映射关系的列表，并扩展该列表
        Return:
            返回存放路由关系的列表
        """

        # 生成增、删、改、查基本映射关系
        app_model = self.get_app_model()
        urlpatterns = [
            re_path(r'^$', self.add_request_decorator(self.show_view), name='%s_%s_show' % app_model),
            re_path(r'^add/$', self.add_request_decorator(self.add_view), name='%s_%s_add' % app_model),
            re_path(r'^(\d+)/delete/$', self.add_request_decorator(self.delete_view), name='%s_%s_delete' % app_model),
            re_path(r'^(\d+)/change/$', self.add_request_decorator(self.change_view), name='%s_%s_change' % app_model),
        ]

        # 扩展路由映射关系
        extra_patterns = self.extra_url()
        urlpatterns.extend(extra_patterns)
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls()

    def extra_url(self):
        """ 为用户扩展urls提供的接口，只需要在CURDConfig派生类中派生覆盖此方法即可
        Return:
            存放了路径与视图函数映射关系的列表(re_path, path, url)
        """

        return []

    list_display = []  # 存放列表页面表格要显示的字段

    def get_list_display(self):
        """ 处理用户权限之内的相关操作，派生CURDConfig类中可以根据用户权限来分配响应的功能按钮/链接，
            实现每个类中可以在增删改查之外，再扩展自己类的URL
        Return:
            包含了权限操作按钮/链接在内的列表
        """

        data = []
        if self.list_display:
            data.extend(self.list_display)
            data.append(CURDConfig.delete)      # 注意：是函数而不是方法！
            data.append(CURDConfig.change)
            data.insert(0, CURDConfig.checkbox)
        return data

    show_add_btn = False        # 先否显示添加按钮权限接口

    def get_show_add_btn(self):
        """ CURDConfig中，根据用户权限来判断用户是否有添加记录按钮对应的权限，如果有则返回True
        Return:
            布尔值，代表用户是否有权限，该值将传递给上下文中用于渲染页面添加按钮
        """

        # 中间存放业务逻辑
        return self.show_add_btn

    def delete(self, obj=None, is_header=False):
        """ 列表页面单条记录删除按钮/链接，可以在CURDConfig派生类中根据用户权限分配该功能
        Args:
            obj: 该记录对象
            is_header: 当用于生成列表标题"<th>"的时候为True
        Return:
            一个SafeText对象，可以将字符串中的html内容转化为标签，
            此处为删除功能的超链接
        """

        if is_header:
            return '删除'
        return mark_safe('<a href="%s">删除</a>' % (self.get_delete_url(obj.id), ))

    def change(self, obj=None, is_header=False):
        """ 列表页面单条记录编辑按钮/链接，可以在CURDConfig派生类中根据用户权限分配该功能
        Args:
            obj: 该记录对象
            is_header: 当用于生成列表标题"<th>"的时候为True
        Return:
            编辑功能超链接
        """

        if is_header:
            return '编辑'
        query_str = self.request.GET.urlencode()
        if not query_str:
            return mark_safe('<a href="%s">编辑</a>' % (self.get_change_url(obj.id), ))
        else:
            params = QueryDict(mutable=True)
            params[self._query_str_key] = query_str
            return mark_safe('<a href="%s?%s">编辑</a>' % (self.get_change_url(obj.id), params.urlencode(), ))

    def checkbox(self, obj=None, is_header=False):
        """ 列表页面单条记录的选择checkbox，用于批量记录操作，可以在CURDConfig派生类中根据用户权限分配该功能
        Args:
            obj: 该checkbox所在记录对象
            is_header: 当用于生成列表标题"<th>"的时候为True
        Return:
            关于选择该条记录的checkbox框
        """

        if is_header:
            return '选择'
        return mark_safe('<input type="checkbox" name="id" value="%s" />' % (obj.id, ))

    def get_delete_url(self, nid):
        """ 获取删除记录对应的路径
        Args:
            nid: 该记录的id
        Return:
            字符串形式的路径
        """

        alias = 'curd:%s_%s_delete' % self.get_app_model()
        return reverse(alias, args=(nid, ))

    def get_change_url(self, nid):
        """ 获取编辑记录对应的url
        Args:
            nid: 该记录的id
        Return:
            字符串形式的路径
        """

        alias = 'curd:%s_%s_change' % self.get_app_model()
        return reverse(alias, args=(nid, ))

    def get_show_url(self):
        """ 获取列表页面的url
        Return:
            字符串形式的路径
        """

        alias = 'curd:%s_%s_show' % self.get_app_model()
        return reverse(alias)

    def get_add_url(self):
        """ 获取增加记录对应的url
        Return:
            字符串形式的路径
        """

        alias = 'curd:%s_%s_add' % self.get_app_model()
        return reverse(alias)

    def show_view(self, request, *args, **kwargs):
        """ 列表页面对应的视图函数
        功能:
            1. 对于GET请求，返回列表页面
            2. 对于批量操作action的POST请求，执行该action，执行完该action之后，可以自定义返回值，也可以没有，按需求而定
        Return:
            HttpResponse: 返回包含渲染好了的页面的响应对象
        """

        if request.method == 'POST' and self.get_show_action_form():
            func_name = request.POST.get('action')
            func = getattr(self, func_name)
            if func:
                ret = func(request, *args, **kwargs)

        combain_condition = {}
        option_list = self.get_combain_search_field_list()
        for key in request.GET.keys():
            value_list = request.GET.getlist(key)
            flag = False
            for option in option_list:
                if option.field_name == key:
                    flag = True
                    break
            if flag:
                combain_condition['%s__in' % key] = value_list

        objects = self.model_class.objects.filter(self.create_search_condition()).filter(**combain_condition).order_by(*self.get_order_list()).distinct()
        show_obj = ShowView(self, objects)
        return render(request, 'curd/show.html', {"show_obj": show_obj})

    model_form_class = None

    def get_model_form_class(self):
        """ 获取modelform表单，如果在派生的CURDConfig中创建了ModelForm派
            生类，就使用该类，否则使用默认的ViewModelForm

        Return:
            ModelForm类的派生类
        """

        if self.model_form_class:
            return self.model_form_class
        else:
            meta_class = type(
                'Meta',
                (object, ),
                {"model": self.model_class,
                 "fields": "__all__"})

            view_model_form_class = type(
                'ViewModelForm',
                (ModelForm, ),
                {"Meta": meta_class})
            return view_model_form_class

    show_search_form = False

    def get_show_search_form(self):
        """ 获取用户搜索权限对应的值。show_search_form默认为false，
            可以在派生类中根据用户权限修改
        Return:
            用户有搜索权限("show_search_form=True")对应的布尔值
        """

        return self.show_search_form

    search_list = []

    def get_search_list(self):
        """ 获取要被搜索的字段，该字段来源于列表search_list，
            可以在派生类中覆盖该列表或根据用户搜索的权限范围划定

        """

        result = []
        if self.search_list:
            result.extend(self.search_list)
        return result

    def create_search_condition(self):
        """ 根据列表页面搜索框中提交的value创建查询条件
        Return:
            返回一个包含了查询条件的Q对象
        """

        from django.db.models import Q

        query_str = self.request.GET.get('query')
        query_condition = Q()
        query_condition.connector = 'OR'
        if query_str and self.get_show_search_form():       # self.get_show_search_form()判断是为了防止没有所有权限的用户通过url搜索
            for field in self.get_search_list():
                query_condition.children.append((field, query_str), )
        return query_condition

    show_action_form = False

    def get_show_action_form(self):
        """ 获取用户action批量操作功能对应的权限。show_action_form默认为false，
            同样需要在派生类中根据用户权限来修改该值
        Return:
            用户action权限对应的布尔值
        """

        return self.show_action_form

    action_list = []

    def get_action_list(self):
        """ 获取action批量操作的具体内容，比如批量删除"multi_delete"，
            action_list中的元素需要是函数/方法。

        """
        result = []
        if self.action_list:
            result.extend(self.action_list)
        return result

    def add_view(self, request):
        """ 添加记录路径对应的视图函数
        Args:
            request: 当前请求对象
        Return:
            HttpResponse: 包含响应结果的响应对象。如果是GET请求，返回页面，如果是POST请求，将重定向至列表页面
        """

        model_form_class = self.get_model_form_class()

        if request.method == 'GET':
            return render(request, 'curd/add.html', {"form":model_form_class(), "config_obj":self})
        else:
            form = model_form_class(data=request.POST)
            if form.is_valid():
                from django.db.models.fields.reverse_related import ManyToOneRel

                model_name = request.GET.get('model_name')
                related_name = request.GET.get('related_name')
                obj = form.save()
                _popbackid = request.GET.get('_popbackid')
                if _popbackid:                              # popup功能开始
                    response_data = {"status": False, "id": None, "text": None, "_popbackid": _popbackid}

                    for related_obj in obj._meta.related_objects:   # 获取记录对象的每一个关联字段
                        if type(related_obj) is ManyToOneRel:       # 处理多对多字段没有field_name属性的bug
                            _field_name = related_obj.field_name
                        else:
                            _field_name = 'pk'
                        _related_name = related_obj.related_name
                        _limit_choices_to = related_obj.limit_choices_to
                        _model_name = related_obj.field.model._meta.model_name
                        if _model_name == model_name and str(_related_name) == str(related_name):   # 获取有效的_limit_choices_to
                            obj = self.model_class.objects.filter(**_limit_choices_to, pk=obj.pk)
                            if obj:
                                response_data["status"] = True
                                response_data["id"] = getattr(obj[0], _field_name),           # 关联字段不一定都是pk，不能写死
                                response_data["text"] = str(obj[0])
                                response_data["_popbackid"] = _popbackid,
                                return render(request, "curd/popback.html", {"response_data": dumps(response_data, ensure_ascii=True)})

                    return render(request, "curd/popback.html", {"response_data": dumps(response_data, ensure_ascii=True)})
                else:
                    return redirect(to=self.get_show_url())
            else:
                return render(request, 'curd/add.html', {"form": form, "config_obj":self})

    def delete_view(self, request, nid):
        """ 删除一条记录
        Args:
            request: 当前请求对象
            nid: 当前要被删除的记录的id
        Return:
            HttpResponse: 重定向到列表页面
        """

        obj = self.model_class.objects.filter(id=nid)
        obj.delete()
        return redirect(self.get_show_url())

    def change_view(self, request, nid):
        """ 编辑一条记录
        Args:
            request: 当前请求对象
            nid: 当前要被编辑的记录的id
        Return:
            GET请求: 返回编辑页面
            POST请求: 验证编辑后的数据
                1. 验证通过，重定向到列表页面
                2. 验证失败，返回包含错误信息的编辑页面
        """

        obj = self.model_class.objects.filter(id=nid).first()
        if not obj:
            return redirect(self.get_show_url())

        model_form_class = self.get_model_form_class()

        if request.method == 'GET':
            form = model_form_class(instance=obj)
            return render(request, 'curd/change.html', {"form":form,  "model_class": self.model_class})
        else:
            form =model_form_class(data=request.POST, instance=obj)
            if form.is_valid():
                form.save()
                # 保证编辑完返回查询的结果路径
                if request.GET.get(self._query_str_key):
                    url_redirect = '%s?%s' % (self.get_show_url(), request.GET.get(self._query_str_key))
                else:
                    url_redirect = self.get_show_url()
                return redirect(to=url_redirect)
            else:
                return render(request, 'curd/change.html', {"form": form, "model_class": self.model_class})

    show_combain_search = False

    def get_show_combain_search(self):
        """ 检测用户是否具备使用组合搜索的权限，如果用户具备该权限，
            在列表界面中将显示组合搜索选项
        """

        return self.show_combain_search

    combain_search_field_list = []

    def get_combain_search_field_list(self):
        """ 获取组合搜索中要作为搜索条件的字段，可以在派生类中指定字段

        """

        result = []
        if self.combain_search_field_list:
            result.extend(self.combain_search_field_list)
        return result

    edit_link = []

    def get_edit_link(self):
        result = []
        if self.edit_link:
            result.extend(self.edit_link)
        return result

    order_list = []

    def get_order_list(self):
        result = []
        if self.order_list:
            result.extend(self.order_list)
        return result


class CURDSite:
    """ 可以看作一个容器，其静态属性`_registry`放置着`model_class`模
        型类和模型对应的`config_obj`配置对象。
    功能:
        1. 注册模型类
        2. 生成一级路由

    """
    def __init__(self, name):
        self.name = name
        self._registry = {}         # 存放model及其对应的CURBConfig()实例键值对

    def register(self, model_class, curd_config_class=None):
        """ 注册传入的model模型类，如果没有提供配置类curd_config_class，默认使用CURDConfig类
        Args:
            model_class: models.py中要注册的模型类
            curd_config_class: 模型类对应的配置类
        Return:
            None
        """

        if not curd_config_class:
            curd_config_class = CURDConfig
        self._registry[model_class] = curd_config_class(model_class, self)

    def get_urls(self):
        """ 编辑包含已注册模型类的字典，生成路径与下一级路由分发的映射关系
        Return:
            包含映射关系的列表
        """

        urlpatterns = []
        for model_class, curd_config_obj in self._registry.items():
            app_name = model_class._meta.app_label
            model_name = model_class._meta.model_name
            temp_path = path(
                '{app_name}/{model_name}/'.format(app_name=app_name, model_name=model_name),
                (curd_config_obj.urls, None, None)
            )
            urlpatterns.append(temp_path)
        return urlpatterns

    @property
    def urls(self):
        """ 实现路由分发
        Return:
            返回一个元组:
                第一个元素为生成的一级路由映射关系组成的列表
                第二个元素为方向解析时会用到的路由空间
                第三个元素为site对象的name属性，实例化时提供，当namespace没有提供的时候，它将作为namespace被使用
        """

        return self.get_urls(), 'curd', self.name


site = CURDSite('curd')       # 实现单例模式
