from django.utils.safestring import mark_safe
from django.urls import re_path, reverse
from django.shortcuts import redirect, HttpResponse, render
from django.forms import Form
from django.forms import widgets
from django.forms import fields
from curd.service.sites import site, CURDConfig
from curd.service.views import SearchOption

from datetime import date

from crm import models
from crm.configs.customer import CustomerConfig
from crm.configs.customer_distribution import CustomerDistributionConfig


class DepartmentConfig(CURDConfig):
    list_display = ['title', 'numbering']
    edit_link = ['title']


site.register(models.Department, DepartmentConfig)


class UserConfig(CURDConfig):
    """ 用户表配置

    """

    list_display = ['name', 'login_name', 'login_password', 'email', 'department']
    combain_search_field_list = [
        SearchOption(
            field_name='department',
            text_func_name=lambda x: str(x),
            val_func_name=lambda x: x.numbering  # 自定义的主键
        )
    ]
    edit_link = ['name']
    show_search_form = True
    search_list = ['name__contains', 'login_name__contains']


site.register(models.User, UserConfig)


class ClassListConfig(CURDConfig):
    def course_semester(self, obj=None, is_header=False):
        """ 将课程和班级拼接后显示在单元格 """
        if is_header:
            return '班级'
        return '%s(%s)' % (obj.course, obj.semester)

    def teachers(self, obj=None, is_header=False):
        """ 构造列表页面表格中"任课老师"字段
        Args:
            obj: 当前行记录对象
            is_header: 是否是表头
        Return:
            当is_header为True的时候，返回表头数据，否则返回有教师名拼接成的字符串
        """

        if is_header:
            return '授课老师'
        teacher_list = [
            '<span>%s &nbsp;</span>' % str(teacher)
            for teacher in obj.teachers.all()
        ]
        teacher_html = ''.join(teacher_list)
        return mark_safe(teacher_html)

    def num(self, obj=None, is_header=False):
        if is_header:
            return '人数'
        return 666

    def get_list_display(self):
        """ 修改curd默认的功能权限，不对该用户提供删除和修改等功能，
            只有查看表格信息的权限

        """

        result = []
        if self.list_display:
            result.extend(self.list_display)
        return result


    list_display = ['school', course_semester, teachers, num, 'price', 'head_teacher']
    edit_link = [course_semester]


site.register(models.ClassList, ClassListConfig)


class SchoolConfig(CURDConfig):
    list_display = ['school_name']
    edit_link = ['school_name']


site.register(models.School, SchoolConfig)


class CourseConfig(CURDConfig):
    list_display = ['course_name']
    edit_link = ['course_name']


site.register(models.Course, CourseConfig)




site.register(models.Customer, CustomerConfig)


class StudentConfig(CURDConfig):
    def score_display(self, obj=None, is_header=False):
        if is_header:
            return '学生成绩'
        return mark_safe('<a href="%s?student_id=%s">查看学生成绩</a>' % (self.get_chart_url(obj.id), obj.id))

    def extra_url(self):
        url_patterns= [
            re_path(r'chart/', self.add_request_decorator(self.show_score_chart_view), name="%s_%s_chart" % self.get_app_model())
        ]
        return url_patterns

    def get_chart_url(self, student_id):
        return reverse('curd:%s_%s_chart' % self.get_app_model())

    def show_score_chart_view(self, request):
        student_id = request.GET.get('student_id')
        print(request.GET.dict())
        student = models.Student.objects.filter(id=student_id).first()
        return render(request, "student_score.html", {"student": student})


    list_display = ['username', score_display]


site.register(models.Student, StudentConfig)


class ConsultRecordConfig(CURDConfig):
    list_display = ['date', 'note']
    show_combain_search = False
    combain_search_field_list = [
        SearchOption(
            field_name='customer',
        )
    ]

    def show_view(self, request, *args, **kwargs):
        customer_id = request.GET.get('customer')
        current_user_id = 9
        if not models.Customer.objects.filter(consultant_id=current_user_id, id=customer_id).count():
            return HttpResponse('你没有权限查看当前客户跟进记录')
        return super().show_view(request, *args, **kwargs)

site.register(models.ConsultRecord, ConsultRecordConfig)

class CourseRecordConfig(CURDConfig):
    def course_display(self, obj=None, is_header=False):
        if is_header:
            return '课程'
        return '%s_(day%s)' % (obj.class_obj, obj.day_num)

    def date_display(self, obj=None, is_header=False):
        if is_header:
            return '上课日期'
        return date.strftime(obj.date, '%Y-%m-%d')

    def multi_init(self, request):
        """ 为每一个course_record对应的所有学生生成一条StudyRecord记录
        Args:
            request: 当前请求对象
        """

        course_record_ids = request.POST.getlist('id')
        for course_record_id in course_record_ids:
            course_record_obj = models.CourseRecord.objects.filter(id=course_record_id).first()
            student_list = models.Student.objects.filter(class_list=course_record_obj.class_obj)
            course_record_already_exists = models.StudyRecord.objects.filter(course_record=course_record_obj).exists()
            if not course_record_already_exists:
                study_recody_list = [
                    models.StudyRecord(course_record=course_record_obj, student=student)
                    for student in student_list
                ]
                models.StudyRecord.objects.bulk_create(study_recody_list)
                print('ok')
    multi_init.func_description = '批量初始化'

    def attendance(self, obj=None, is_header=False):
        """ 生成考勤管理列

        """

        if is_header:
            return '考勤管理'
        return mark_safe('<a href="/curd/crm/studyrecord/?course_record=%s">考勤管理</a>' % obj.id)

    def extra_url(self):
        url_patterns = [
            re_path(
                r'(?P<course_record_id>\d+)/load_score/',
                self.add_request_decorator(self.load_score_view),
                name="%s_%s_load_score" % self.get_app_model()
            )
        ]
        return url_patterns

    def get_load_score_url(self, course_record_id):
        return reverse('curd:%s_%s_load_score' % self.get_app_model(), args=(course_record_id, ))

    def load_score_view(self, request, course_record_id):
        if request.method == 'GET':
            study_record_list = models.StudyRecord.objects.filter(course_record_id=course_record_id)
            study_record_package = []
            for study_record in study_record_list:
                form_class = type(
                    'LoadScoreModelForm',
                    (Form,),
                    {
                        'score_%s' % study_record.id : fields.ChoiceField(choices=models.StudyRecord.score_choices,
                                                                          widget=widgets.TextInput(attrs={"class": "form-control"})),
                        'homework_note_%s' % study_record.id: fields.CharField(max_length=520,
                                                          widget= widgets.Textarea(attrs={'placeholder': '作业评语',
                                                                                         "class": "form-control",
                                                                                          "cols": 30, "rows": 2}))
                    }
                )
                study_record_package.append({
                    'study_record': study_record,
                    'form': form_class(initial={
                        'score_%s' % study_record.id :study_record.score,
                        'homework_note_%s' % study_record.id: study_record.homework_note,
                    })
                })
            return render(request, 'load_score.html', {"study_record_package": study_record_package})
        else:
            post_score_data = request.POST.dict()       # 'score_16': '85', 'homework_note_16': 'aaaa'
            del post_score_data['csrfmiddlewaretoken']
            temp_dict = {}          # 组装将用来保存到数据库的数据
            for key, value in post_score_data.items():
                name, study_record_id = key.rsplit('_', 1)
                if study_record_id in temp_dict:
                    temp_dict[study_record_id][name] = value
                else:
                    temp_dict[study_record_id] = {name: value}
            for study_record_id, update_values in temp_dict.items():
                models.StudyRecord.objects.filter(id=study_record_id).update(**update_values)
            return HttpResponse('ok')

    def load_score(self, obj=None, is_header=False):
        if is_header:
            return '录入成绩'
        return mark_safe('<a href="%s">录入成绩</a>' % self.get_load_score_url(obj.id))

    action_list = [multi_init, ]
    show_action_form = True
    list_display = [course_display, 'teacher', load_score, attendance, date_display]

site.register(models.CourseRecord, CourseRecordConfig)


class StudyRecordConfig(CURDConfig):
    def multi_checked(self, request):
        study_record_id_list = request.POST.getlist('id')
        models.StudyRecord.objects.filter(id__in=study_record_id_list).update(record='checked')
    multi_checked.func_description = '已到'

    def multi_vacate(self, request):
        study_record_id_list = request.POST.getlist('id')
        models.StudyRecord.objects.filter(id__in=study_record_id_list).update(record='vacate')
    multi_vacate.func_description = '请假'

    def multi_late(self, request):
        study_record_id_list = request.POST.getlist('id')
        models.StudyRecord.objects.filter(id__in=study_record_id_list).update(record='late')
    multi_late.func_description = '迟到'

    def multi_noshow(self, request):
        study_record_id_list = request.POST.getlist('id')
        models.StudyRecord.objects.filter(id__in=study_record_id_list).update(record='noshow')
    multi_noshow.func_description = '旷课'

    def multi_leave_early(self, request):
        study_record_id_list = request.POST.getlist('id')
        models.StudyRecord.objects.filter(id__in=study_record_id_list).update(record='leave_early')
    multi_leave_early.func_description = '早退'

    show_action_form = True
    action_list = [multi_checked, multi_late, multi_leave_early, multi_noshow, multi_vacate]
    list_display = ['course_record', 'student', 'record']
    combain_search_field_list = [
        SearchOption(
            'course_record'
        )
    ]
site.register(models.StudyRecord, StudyRecordConfig)


site.register(models.CustomerDistribution, CustomerDistributionConfig)

class DistributionCofig(CURDConfig):
    list_display = ['user', 'weight']
    edit_link = ['user']

site.register(models.Distribution, DistributionCofig)