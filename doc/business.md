# 业务分析与功能实现

## 学生记录部分

## 销售部分

#### `内部公共客户资源`与`个人客户资源`
###### 场景
- 公司内部的客户资源分成两大类，一类是`内部公共客户资源`，另一类是`个人客户资源`
	- `内部公共客户资源`对**几乎**所有销售人员开放，销售人员可以`接手`公共资源上的客户，当该销售人员接手了一个客户资源之后，这个客户资源就会转移到改销售人员的个人客户资源列表中，其他销售将没有权限接手该客户资源，除非该客户资源重新成为公共资源
	- `个人客户资源`既可以是从公司内部接手或自动分配得到的，也可以是凭借个人能力获取的客户资源。

- `个人客户资源`转换成公共客户资源的必要条件
	1. 客户记录的状态必须为未报名
	2. 销售对该客户**最近一次的跟进记录距离当前时间**已经超过3天或者**该客户在被销售接手**的15天时间内，仍没有报名

- **细节注意**
	1. 一个销售人员的客户资源一旦变成公共资源，那么该销售人员不再具有获取该客户资源的权限
	2. 销售顾问个人通过其他渠道获取的客户资源在录入到客户表中时，该客户资源首先会被该销售顾问获取，但是也有可能会由于`三天未跟进`或`15天未签约`而变成公司内部公共资源

###### 思路与代码实现
1. 生成`公共客户资源`列表，思路流程
	1. 生成数据库数据的筛选条件，用来过滤客户列表中满足成为公共资源的客户记录
		- 这里使用Q对象来生成过滤条件，因为条件中既有`且`的关系，又有`或`的关系，Q对象可以完美解决这一情况
		- Q对象生成的筛选条件有两种
			1. 将索搜条件全部封装进Q对象中
			2. 将搜索条件分别封装进Q对象中，在`filter`中用`运算符`链接起来
	2. 利用筛选条件，获取满足公共资源的对象

```python
# ----------------方式1 ------------
    def public_view(self, request):
        """ 公司内部公共资源页面的视图函数
        Args:
            request: 当前请求对象
        """

        today = date.today()
        deadline_15 = today - datetime.timedelta(days=15)
        deadline_3 = today - datetime.timedelta(days=3)

        public_customer_list = models.Customer.objects.filter(
            Q(recv_date__lt=deadline_15) | Q(last_consult_date__lt=deadline_3),
            status=2
        )

        public_customer_list = models.Customer.objects.filter(condition)
        return render(request, 'public_view.html', {"public_customer_list": public_customer_list})

# ------------- 方式2 --------------------------
    def public_view(self, request):
        """ 公司内部公共资源页面的视图函数
        Args:
            request: 当前请求对象
        """

        today = date.today()
        deadline_15 = today - datetime.timedelta(days=15)
        deadline_3 = today - datetime.timedelta(days=3)

        condition = Q()
        cond1 = Q()
        cond1.connector = 'OR'
        cond1.children.append(("recv_date__lt", deadline_15))
        cond1.children.append(("last_consult_date__lt", deadline_3))
        cond2 = Q()
        cond2.connector = 'OR'
        cond2.children.append(("status", 2))
        condition.add(cond1, 'AND')
        condition.add(cond2, 'AND')

        public_customer_list = models.Customer.objects.filter(condition)

        return render(request, 'public_view.html', {"public_customer_list": public_customer_list})
```

2. `个人客户资源`列表
	- 销售人员的个人客户列表中四类状态的记录都需要显示，包括`正在跟进的`，` 已经签约的`，`跟进超过3天的`， `接单15天没签约的`。因此，用户个人资源页面中只需要通过该销售人员内的id就将其所有状态的客户资源显示到个人页面上
	- 代码实现如下	

```python
    def private_view(self, request):
        """ 用户个人客户资源详细信息页面
        
        """
        current_user_id = 35
        private_customer_distributions = models.CustomerDistribution.objects.filter(user_id=current_user_id).order_by('status')

        return render(request, 'user_view.html', {"private_customer_distributions": private_customer_distributions})
```



#### 记录状态更新
###### 场景
- 当一个客户资源满足成为内部公共资源之后，需要将该客户资源所在的销售人员的`销售跟进记录表`中的记录状态，由`正在跟进`修改成`3天未跟进`或`15天未签约成功`。有三种方案：
	1. 当客户资源从个人资源变成公共资源时，其他销售接手该客户资源时再修改记录状态为"15天xxx"或"3天xxx"
		- 遇到的问题： 如果没有人接手呢？这个销售手中的记录就会一直是`正在跟进`的状态，显然时不正确的
	2. 当有销售查看公共资源，生成公共资源列表的时候，更新记录中的状态
		- 遇到的问题：如果没人看公共资源呢？虽然这个情况不可能，单逻辑上终究是不合理的
	3. 使用cromtab对脚本定时更新。
		- 可以在每天的凌晨，在用户使用最少的时候，更新数据库。而且由于是公司内部的crm系统，半夜了估计也没有人还在使用。
			- 方式一：使用pymysql链接数据库
			- 方式二：使用脚本运行Django，直接操作模型。

####### 代码实现

```python
import os
import sys
import django
import datetime
from datetime import date

from django.db.models import Q


sys.path.append(r'E:\customer_relationship_management_system')

os.chdir(r'E:\customer_relationship_management_system')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "customer_relationship_management_system.settings")

django.setup()					# 在项目外部启动了Django项目

from crm import models			# 启动项目后就可以导入模块了

today = date.today()
deadline_15 = today - datetime.timedelta(days=15)
deadline_3 = today - datetime.timedelta(days=3)

public_customer_list = models.Customer.objects.filter(
    Q(recv_date__lt=deadline_15) | Q(last_consult_date__lt=deadline_3),
    status=2
)

for customer in public_customer_list:			# 更新开始
    customer_distribution = models.CustomerDistribution.objects.filter(customer=customer)
    if customer.status == 1:
        customer_distribution.update(status=2)
    elif deadline_15 > customer.recv_date:
        customer_distribution.update(status=4)
    else:
        customer_distribution.update(status=3)
```


#### 录入客户信息后的自动分配
###### 场景
- 根据公司中每一个销售人员的销售能力的不同，对资源的分配也应该根据权重来进行分配

###### 思路
- 对于每一个销售人员，都对应一个`权重`和`客户数量`，**权重代表获取分配客户资源时的优先级**，**客户数量是一个销售人员当天能够接手的客户数量**， 数据库表结构如下

```python
class Distribution(models.Model):
    """ 分配表，用来保存每一个销售人员的最大接客数量和分配权重

    """

    user = models.ForeignKey(to='User', limit_choices_to={"department__numbering": 1000}, on_delete=models.CASCADE)
    num = models.IntegerField(verbose_name="数量")
    weight = models.IntegerField(verbose_name="权重")
```

- 举个简单的例子来介绍自动分配中`权重`和`客户数量`具体的作用

```
1. 现在有三个销售人员: a, b, c，所占权重和客户数量如下

Distribution表
user(销售人员)         num(客户数量)        weight(权重)		
a                        3                    1
b                        2                    2
c                        1                    3

2. 公司现在出现了14个客户资源，现在要分配给上述三个销售人员

3. 按照销售人员的权重和客户数量，组装成下面这个列表，并将该列表转换成迭代器

[c, b, a, b, a, a]	

4. 每一次分配客户资源给一个销售人员的时候，都会从迭代器中取出一个销售人员来生成一条CustomerDistribution表的记录，当迭代器中的销售人员全部迭代完，仍有客户资源的时候，就会再次生成一个相同的列表的迭代器，再次进行分配，所以，总共14个客户资源，分配列表应该是这样

[c, b, a, b, a, a, c, b, a, b, a, a, c, b]

5. 分配结果
	a:6个客户
	b:5个客户
	c:3个客户 



```

- 还有几种非常可能发生的情况需要考虑
	1. 如果市场部经理，在今天中午突然要给一个最近业绩较好的销售顾问增加`权重`或者`分配客户数量`，这个时候我们就得根据`Distribution`表中数据来修改迭代器中销售顾问id排列及重复情况。
		- 解决方案：当本次迭代器中的销售id对应的销售完成了一轮分配之后，再次生成改生成器的时候从数据库获取最新数据`fetchall()`。我们不能在迭代的过程中去中断分配，或者在迭代的过程中修改迭代器，这样会导致分配的不合理
	2. 如果在自动分配的过程中服务端出现了错误，导致分配失败，此时可能会衍生两个问题：
		1. `CustomerDistribution`表与`Customer`表中的数据不对称，有可能`Customer`数据库中成功为该客户关联了销售顾问而在`CustomerDistribution`中并没有生成，这个后果非常严重，会导致该销售顾问在自己的个人客户资源列表中无法显示该客户。
			- 解决方案：使用事务
		2. 如果在数据库产生记录之前就发生了错误，一方面，该销售顾问就无法获取到该客户资源，另一方面，由于迭代器的特性，当迭代出该销售顾问id之后下一次迭代就会返回下一个销售顾问的id，而此时前一个程序发生错误时的销售顾问会因为程序问题无法获取到顾客资源，这也是很严重的
			- 解决方案：定义一个类似"队列"的结构，实现先进先出的功能，将程序出错时获取的销售顾问id存放到该队列中，在`get_saler_id()`方法中，可以做一个判断，如果该队列中有值，就让该值优先返回用于分配 


###### 代码实现

1. 创建一个`HandlerDistribution`类专门处理客户资源分配。

```python
from crm import models
from collections import OrderedDict


class HandlerDistribution(object):
    """ 实现客户资源分配
    功能:
        生成权重列表
    """
    salers = None
    salers_iter = None
    need_reset = False

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
                    result.append(user.id)      # [<User: haha>, <User: 小鱼>, <User: 飞雪>, <User: 小鱼>, <User: 飞雪>, <User: 飞雪>]
                    fetch_dict[user] -= 1
        return result

    @classmethod
    def get_saler_id(cls):
        """ 迭代salers_iter

        Return:
            返回值为销售人员的id
        """

        if not cls.salers:
            cls.salers = cls.fetchall()
        if not cls.salers_iter:
            cls.salers_iter = iter(cls.salers)
        try:
            saler_id = next(cls.salers_iter)
        except StopIteration:
            if cls.need_reset:                      # 重置salers数据
                cls.salers = cls.fetchall()
                cls.need_reset = False
            cls.salers_iter = iter(cls.salers)
            saler_id = next(cls.salers_iter)        # 也可以 saler_id = cls.get_saler_id()
        return saler_id

    @classmethod
    def reset(cls):
        """ 当分配表中的记录变化时，此方法将会重置静态字段salers的值
        Return:
            None
        """

        cls.need_reset = True
```

2. 视图函数中根据迭代器返回的销售人员id生成记录

```python
    def load_single_view(self, request):
        """ 单条录入客户资源时对应的视图函数

        """

        if request.method == 'GET':
            form = LoadSingleModelForm()
            return render(request, 'single.html', {"form": form})
        else:
            form = LoadSingleModelForm(data=request.POST)
            if form.is_valid():
                saler_id = handler.HandlerDistribution.get_saler_id()
                if not saler_id:
                    return HttpResponse('没有销售顾问，无法分配客户资源')

                today = date.today()

                with atomic():
                    try:
                        form.instance.consultant_id = saler_id
                        form.instance.recv_date = today

                        new_customer = form.save()
                        models.CustomerDistribution.objects.create(                                     # CustomerDistribution表新增数据
                            user_id=saler_id,
                            ctime=today,
                            customer=new_customer,
                        )
                    except Exception as e:
                        print(e)
                        handler.HandlerDistribution.rollback(sale_id=saler_id)							# 分配失败，保留该销售顾问id，在下一次分配时仍然时候该id
                        return HttpResponse('录入客户失败，出现异常')
    
                    send_message(																		# 给销售顾问发送信息
                            to='xxxxx@qq.com',
                            name='ziawang',
                            subject='客户资源变动通知',
							body='你有分配到新的客户资源啦，快去个人客户列表中看一看吧'
                        )
                return HttpResponse('录入客户成功')
            return render(request, 'single.html', {"form": form})
```

#### 接单功能
###### 新入职的销售的权限
- 对于新入职的销售而言，最初并不具备参与公司内部资源分配的权限，此时该销售在`Distribution(资源分配表)`中对应的`num(分配客户数量)=0 weight(权重)=0`，它能够获取客户资源的渠道主要有两个方面
	1. 通过自己个人的渠道获取客户资源
	2. 通过公司内部的公共资源列表中获取("接单")客户资源

- **新入职的销售顾问在刚进入公司之后不会直接给他分配客户，必须要经历销售之间的相互联系+老客户沟通的过程，当该销售做出销售成绩之后，再给其开权限，成单率越高，给他分配的数量和权限都会调整**

###### 接单功能背景
- 当一个个人客户资源满足了成为`公司内部公共资源`的条件时，对应一条数据库中的记录会显示在`公共资源页面`中，**除了该客户资源当前对应的销售人员**，其他销售人员在自己的登录界面都可以通过点击该记录对应的`接单`功能来接手该`客户资源`，数据库中的变化有以下几处
	1. 将该客户在`Customer`表中关联的`consultant(销售顾问)`修改成此时接单的销售顾问
	2. `CustomerDistribution`表中会生成一条该客户与新的销售顾问对应的一条**客户跟进记录**
		- `CustomerDistribution`表中该客户与之前销售顾问对应的几条记录的`status`字段会在每天的定时任务中修改

###### 接单功能代码实现
- 逻辑流程如下
	1. 首先得为每一条`customer`记录生成一个url路径，该路径会扩展到`curd`组件中
	2. 当前登陆销售顾问点击公共资源列表中一条记录中的`接单`按钮，会向服务端发送一条GET请求，该请求内携带客户记录id
	3. 根据客户id、当前登陆用户id（防止销售顾问重复获取客户资源）、公共资源的条件来获取数据库中对应的这条数据，然后修改该数据。
		- 如果执行修改后，返回的受影响的记录数量为0，表示该记录已经被其他销售顾问抢先一步接单
		- 如果受影响的记录数量不为0，那么数据库中该记录会被修改成功，这也意味着改销售顾问"接单成功"

```python
# 1. 配置路由
    def extra_url(self):
        urlpatterns = [
            re_path(r'del_pre_course/(\d+)/(\d+)/', self.add_request_decorator(self.del_pre_course), name="%s_%s_dc" % self.get_app_model()),
            re_path(r'public/', self.add_request_decorator(self.public_view), name="%s_%s_public" % self.get_app_model()),
            re_path(r'private/', self.add_request_decorator(self.private_view), name="%s_%s_private" % self.get_app_model()),
            re_path(r'(?P<customer_id>\d+)/competition/', self.add_request_decorator(self.competition_view), name="%s_%s_competition" % self.get_app_model()),
        ]

# 2. 视图函数
    def competition_view(self, request, customer_id):
        """ 接单功能视图
        Args:
            customer_id: 该条客户记录在客户表中id
        """

        current_user_id = request.session.get('user_id')
        today = date.today()
        deadline_15 = today - datetime.timedelta(days=15)
        deadline_3 = today - datetime.timedelta(days=3)
        customer_count = models.Customer.objects.filter(
            Q(recv_date__lt=deadline_15) | Q(last_consult_date__lt=deadline_3),
            status=2,
            id=customer_id
        ).exclude(consultant_id=current_user_id).update(recv_date=today,
                                                        last_consult_date=today,
                                                        consultant_id=current_user_id)					# 查看是否修改成功
	
        if not customer_count:																			# 记录状态修改失败
            return HttpResponse('手速慢啦')

        models.CustomerDistribution.objects.create(user_id=current_user_id, customer_id=customer_id, ctime=today)		# 记录状态修改成功

        return HttpResponse('抢单成功')
```


#### 消息提醒
###### 业务背景
- 公司市场部对每一个销售顾问分配公司内部客户资源的时候，当分配成功之后需要提醒该销售顾问，以保证销售顾问能够及时与客户取得沟通。

###### 思路
- 何时才应该向销售顾问发送分配成功的信息？
	- 显然是在分配成功之后. .. . emm..m..


