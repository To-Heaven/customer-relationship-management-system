from django.template import Library
from django.urls import reverse
from django.forms.models import ModelChoiceField

register = Library()


@register.inclusion_tag(filename='curd/form.html')
def form_popup(form_obj, model_class):
    """ 渲染表单，并为单选框/复选框后面添加popup链接按钮
    Args:
        form_obj: 视图函数响应上下文中的form对象
    Return:
        上下文对象(字典)，用于渲染表单
    """

    new_form = []
    for bound_field in form_obj:
        temp = {"is_popup": False, "bound_field": bound_field}

        if isinstance(bound_field.field, ModelChoiceField):
            # print(bound_field.field.queryset)
            # print(list(bound_field.field.choices))
            # print(bound_field.field.to_field_name)
            field_related_model_class = bound_field.field.queryset.model
            app_model = (
                field_related_model_class._meta.app_label,
                field_related_model_class._meta.model_name
            )
            model_name = model_class._meta.model_name
            from django.db.models.fields.related import ForeignKey
            from django.db.models.fields.reverse_related import ManyToOneRel
            related_name = model_class._meta.get_field(bound_field.name).remote_field.related_name
            base_url = reverse("curd:%s_%s_add" % app_model)
            popup_url = "%s?_popbackid=%s&model_name=%s&related_name=%s" % (
                base_url,
                bound_field.auto_id,
                model_name,
                related_name
            )
            temp["is_popup"] = True
            temp["popup_url"] = popup_url
        new_form.append(temp)

    return {"form": new_form}
