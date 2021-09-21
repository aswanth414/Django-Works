from django.http import JsonResponse,HttpResponse
from django.conf import settings
# from django.views.generic.base import TemplateView, View
from django.views.generic import TemplateView,View
from django.core.exceptions import *
from fms.utils.message_strings import *
from django.shortcuts import render
import xlsxwriter
from io import BytesIO
#from apps.fms_db.models import ()
from apps.fms_db.models import (Customermaster,Complaintheader, Logisticentry, Complaintentry)

# Create your views here.

class CustomerManagementView(TemplateView):

    template_name = "dashboard/customer_management/customer_management.html"


class customerManagementGrid(View):

    def get(self, request):

        queryset = Complaintentry.objects.using('firebird').all()
        data_list = list()
        result_dict = {}
        draw = request.GET.get('draw', None)
        start = int(request.GET.get('start', 0))
        tab_length = int(request.GET.get('length', 10))
        end = start + tab_length

        coloumns = {
            0: 'complaintreference',
            1: 'logisticreference__displaylogisticref',
            2: 'complaintcode',
            3: 'complaintdescription',
            4: 'status',
        }

        for col_index in range(0, 5):
            col_order = request.GET.get('order[' + str(col_index) + '][column]', None)
            col_order_dir = request.GET.get('order[' + str(col_index) + '][dir]', None)
            if col_order:
                break
        result_dict['draw'] = draw
        result_dict['recordsTotal'] = queryset.count()
        result_dict['recordsFiltered'] = queryset.count()

        if col_order:
            if col_order_dir == 'asc':
                queryset = queryset.order_by(coloumns[int(col_order)])[start:end]
            else:
                queryset = queryset.order_by('-' + coloumns[int(col_order)])[start:end]
        else:
            queryset = queryset[start:end]

        for record in queryset:
            row_list = []
            row_list.append(record.complaintreference)
            row_list.append(record.logisticreference.displaylogisticref)
            row_list.append(record.complaintcode.complaintname)
            row_list.append(record.complaintdescription)
            row_list.append(record.status)
            data_list.append(row_list)
        result_dict['data'] = data_list
        return JsonResponse(result_dict)
