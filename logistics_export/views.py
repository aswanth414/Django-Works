from django.shortcuts import render
from django.db.models import Q
from django.shortcuts import render
from fms.utils.fb_connect import get_fb_conn
import datetime
import json
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from fms.utils.fb_connect import get_fb_conn
from io import BytesIO
import xlsxwriter
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView, View
from django.db.models import Sum
from .forms import AddExportOrderForm, ContainerEntryForm
from apps.fms_db.models import (Transportermaster, Locationmaster, Containertypemaster, Customermaster,
                                Logisticentry, Logisticscontainerdetails, Statusmaster, Depotmaster, Cargotypemaster,
                                Shippinglinemaster, Vesseldetails, Shippinglinedetails,
                                Agentmaster, Commoditymaster, Distancemaster, Usermaster,
                                Forwardingagentmaster,Unitofmeasurement)
from django.utils.translation import ugettext_lazy as _
import datetime


# from .forms import AddOrderQuotationForm, AddOrderEntryForm, EditOrderQuotationForm, ContainerEntryForm, \
# AddAdditionalCostForm, EditAdditionalCostForm,CommodityEntryForm


class CustomerAjaxListView(View):

    def customer_type_converter(self, customertype):
        customer_map = {
            'CR': 'Consigner', 'CE': 'Consignee', 'IP': 'Invoice Party', 'SR': 'Shipper',
            'CRCEIP': 'Consigner - Consignee - Invoice Party', 'CRCESR': 'Consigner - Consignee - Shipper',
            'CRIPSR': 'Consigner - Invoice Party - Shipper', 'CEIPSR': 'Consignee - Invoice Party - Shipper',
            'CEIP': 'Consignee And Invoice Party', 'CRIP': 'Consigner And Invoice Party',
            'CRCE': 'Consigner And Consignee',
            'CESR': 'Consignee And Shipper', 'CRSR': 'Consigner And Shipper',
            'IPSR': 'Invoice Party And Shipper', 'CRCEIPSR': 'Consigner - Consignee - Invoice Party - Shipper'
        }

        try:
            text = customer_map[customertype]
        except:
            text = ''
        return text

    def post(self, request):
        search = self.request.GET.get('search', None)
        entity = self.request.GET.get('entity', None)
        currenttransporter = request.session['transporter_access']
        queryset = Customermaster.objects.using('firebird').filter(activecustomer='Y',
                                                                   transportercode=currenttransporter).exclude(
            customercode__startswith='*')
        if entity:
            if entity == 'customer':
                customer_types = ['CR', 'CRCE', 'CRIP', 'CRSR', 'CRCEIP', 'CRCESR', 'CRIPSR', 'CRCEIPSR']
            elif entity == 'consignee':
                customer_types = ['CE', 'CRCE', 'CEIP', 'CESR', 'CRCEIP', 'CRCESR', 'CEIPSR', 'CRCEIPSR']
            elif entity == 'invoice_party':
                customer_types = ['IP', 'CRIP', 'CEIP', 'IPSR', 'CRCEIP', 'CRIPSR', 'CEIPSR', 'CRCEIPSR']
            elif entity == 'shipper':
                customer_types = ['SR', 'CESR', 'CRSR', 'IPSR', 'CEIPSR', 'CRIPSR', 'CRCESR', 'CRCEIPSR']
            queryset = queryset.filter(customertype__in=customer_types)
        if search:
            queryset = queryset.filter(customername__icontains=search)
        data_list = list()
        result_dict = {}
        draw = request.POST.get('draw', None)
        start = int(request.POST.get('start', 0))
        tab_length = int(request.POST.get('length', 10))
        end = start + tab_length

        coloumns = {0: 'customername', 1: 'customertype', 2: 'address1',
                    3: 'address2',
                    4: 'locationcode__locationname', 5: 'countrycode__countryname'}

        for col_index in range(0, 7):
            col_order = request.POST.get('order[' + str(col_index) + '][column]', None)
            col_order_dir = request.POST.get('order[' + str(col_index) + '][dir]', None)
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
            row_list.append(record.customername)
            row_list.append(self.customer_type_converter(record.customertype))
            row_list.append(record.address1.strip() if record.address1 else "")
            row_list.append(record.address2.strip() if record.address2 else "")
            row_list.append(record.locationcode.locationname if record.locationcode else "")
            row_list.append(record.countrycode.countryname if record.countrycode else "")
            row_list.append(record.customercode)
            data_list.append(row_list)
        result_dict['data'] = data_list
        return JsonResponse(result_dict)


class ExportOrderListView(TemplateView):
    template_name = "dashboard/logistics/logistics_export/exportlist.html"

    def get_context_data(self, **kwargs):
        context = super(ExportOrderListView, self).get_context_data(**kwargs)
        context['cargos'] = Cargotypemaster.objects.using('firebird').filter(
            ~Q(cargotypecode__in=list([0, 5]))).order_by('cargotypename')
        username = self.request.user.username.strip()
        context['today'] = datetime.datetime.now().date()
        month_before = datetime.datetime.now() - datetime.timedelta(days=30)
        context['month_before'] = month_before.date()
        context['statuses'] = Statusmaster.objects.using('firebird').filter(statustype='L').order_by('statusdescription')
        return context


class ExportOrderGridView(View):

    def post(self, request):
        orderno = request.GET.get('orderno', None)
        customer = request.GET.get('customercode', None)
        origin = request.GET.get('origin', None)
        destination = request.GET.get('destination', None)
        commodity = request.GET.get('commodity', None)
        status = request.GET.get('status', None)
        cargotype = request.GET.get('cargotype', None)
        date_from = request.GET.get('date_from', None)
        date_to = request.GET.get('date_to', None)
        live = request.GET.get('live', None)

        if not date_from and not date_to:
            month_before = datetime.datetime.now() - datetime.timedelta(days=30)
            queryset = Logisticentry.objects.using('firebird').filter(filetype='E',
                                                                      transportercode=request.session[
                                                                          'transporter_access'],
                                                                      orderdate__gte=month_before) \
                .exclude(logisticreference__startswith='*')
        else:
            queryset = Logisticentry.objects.using('firebird').filter(filetype='E',
                                                                      transportercode=request.session[
                                                                          'transporter_access']) \
                .exclude(logisticreference__startswith='*')

        if orderno:
            if len(orderno) < 14 :
                queryset = queryset.filter(displaylogisticref__icontains=orderno) if queryset.filter(displaylogisticref__icontains=orderno)  else queryset.filter(logisticreference__icontains=orderno)
            elif len(orderno) == 14 :
                queryset = queryset.filter(logisticreference__iexact=orderno)
            else:
                queryset = queryset.none()
        if customer:
            queryset = queryset.filter(consignorcode=customer)
        if origin:
            queryset = queryset.filter(fromstationcode=origin)
        if destination:
            queryset = queryset.filter(tostationcode=destination)
        if commodity:
            queryset = queryset.filter(commoditycode=commodity)
        if status:
            queryset = queryset.filter(statuscode=status)
        if cargotype:
            queryset = queryset.filter(cargotypecode=cargotype)
        if date_from:
            date_from = datetime.datetime.strptime(date_from, "%d/%m/%Y").date()
            queryset = queryset.filter(orderdate__gte=date_from)
        if date_to:
            date_to = datetime.datetime.strptime(date_to, "%d/%m/%Y").date()
            queryset = queryset.filter(orderdate__lte=date_to)

        data_list = list()
        result_dict = {}
        draw = request.POST.get('draw', None)
        start = int(request.POST.get('start', 0))
        tab_length = int(request.POST.get('length', 10))
        end = start + tab_length

        coloumns = {
            0: 'logisticreference',
            1: 'displaylogisticref',
            2: 'statuscode__statusdescription',
            3: 'orderdate',
            4: '',
            5: 'consignorcode__customername',
            6: 'consigneecode__customername',
            7: 'invoicepartycode__customername',
            8: 'consignorcode__customername',
            9: 'clientreference',
            10: 'fromstatiocode__locationcode',
            11: 'tostatiocode__locationcode',
            12: 'loadingpointcode__depotcode',
            13: 'offloadingpointcode__depotcode',
            14: 'container20',
            15: 'container40',
            16: 'tonnage',
            17: 'cargotypecode',
            18: 'shippinglinecode__shippinglinename',
            19: 'agentcode',
            20: 'portagentcode__agentname',
            21: 'entryuser',
            22: 'comments',
            23: 'commoditycode__commodityname'
        }

        for col_index in range(0, 24):
            col_order = request.POST.get('order[' + str(col_index) + '][column]', None)
            col_order_dir = request.POST.get('order[' + str(col_index) + '][dir]', None)
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
            row_list.append(record.logisticreference)
            row_list.append(record.displaylogisticref)
            if record.statuscode:
                if record.statuscode.statuscode == '0039':  # PENDING
                    row_list.append("""<span class="st-label bg-blue">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0040':  # DOCUMENT RECEIVED
                    row_list.append("""<span class="st-label bg-aqua">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0041':  # UNDER CLEARANCE
                    row_list.append("""<span class="st-label bg-yellow">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0042':  # CLEARED
                    row_list.append("""<span class="st-label bg-fuchsia">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0043':  # TAXED
                    row_list.append("""<span class="st-label bg-navy">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0044':  # READY FOR LOADING
                    row_list.append("""<span class="st-label bg-green">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0045':  # PART LOADED
                    row_list.append("""<span class="st-label bg-maroon">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0046':  # LOADED
                    row_list.append("""<span class="st-label bg-teal">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0047':  # SHIPPED ON BOARD
                    row_list.append("""<span class="st-label bg-aqua-active">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0048':  # SHIPMENT COMPLETED
                    row_list.append("""<span class="st-label bg-purple">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0049':  # TRANSFERRED TO OPS
                    row_list.append("""<span class="st-label bg-lime">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0050':  # CANCELLED
                    row_list.append("""<span class="st-label bg-gray">"""+record.statuscode.statusdescription+"""</span>""")
                elif record.statuscode.statuscode == '0051':  # ON HOLD
                    row_list.append("""<span class="st-label bg-red">"""+record.statuscode.statusdescription+"""</span>""")
                else:
                    row_list.append(record.statuscode.statusdescription)
            else:
                row_list.append(None)
            row_list.append(record.orderdate.strftime("%d/%m/%Y") if record.orderdate else '')
            row_list.append(record.transportercode.transportername if record.transportercode else None)
            row_list.append(record.consignorcode.customername if record.consignorcode else None)
            row_list.append(record.consigneecode.customername if record.consigneecode else None)
            row_list.append(record.invoicepartycode.customername if record.invoicepartycode else None)
            row_list.append(record.consignorcode.customername if record.consignorcode else None)
            row_list.append(record.clientreference)
            row_list.append(record.fromstationcode.locationname if record.fromstationcode else None)
            row_list.append(record.tostationcode.locationname if record.tostationcode else None)
            row_list.append(record.loadingpointcode.depotname if record.loadingpointcode else None)
            row_list.append(record.offloadingpointcode.depotname if record.offloadingpointcode else None)
            row_list.append(record.container20)
            row_list.append(record.container40)
            row_list.append(record.tonnage)
            row_list.append(record.cargotypecode.cargotypename if record.cargotypecode else None)
            row_list.append(record.shippinglinecode.shippinglinename if record.shippinglinecode else None)
            row_list.append(record.agentcode.agentname if record.agentcode else None)
            row_list.append(record.portagentcode.agentname if record.portagentcode else None)
            row_list.append(record.entryuser)
            row_list.append(record.comments)
            row_list.append(record.commoditycode.commodityname if record.commoditycode else None)
            data_list.append(row_list)
        result_dict['data'] = data_list
        return JsonResponse(result_dict)


class ExportOderCreateView(FormView):
    template_name = "dashboard/logistics/logistics_export/export_entry.html"
    form_class = AddExportOrderForm
    success_url = reverse_lazy('logisticsexport:export-list')
    action_type = 'I'

    def get_context_data(self, **kwargs):
        context = super(ExportOderCreateView, self).get_context_data(**kwargs)
        transportercode = self.request.session['transporter_access']
        context['transporter_code'] = transportercode
        username = self.request.user.username.strip()
        context['orderreference'] = "*" * (14 - len(username)) + "{0}".format(username)
        context['containers'] = Containertypemaster.objects.using('firebird').filter(activecontainertype='Y')
        context['unitnames'] = Unitofmeasurement.objects.using('firebird').filter(activeunit='Y')
        context['locations'] = Locationmaster.objects.using('firebird').filter(activelocation='Y')
        context['transporter_name'] = Transportermaster.objects.using('firebird'). \
            get(transportercode=transportercode).transportername
        context['containerdropofflocation'] = Locationmaster.objects.using('firebird').filter(
            activelocation='Y').order_by(
            'locationname').exclude(locationcode='000000')
        return context

    def get(self, request, *args, **kwargs):
        username = self.request.user.username.strip()
        temp_order_reference = "*" * (14 - len(username)) + "{0}".format(username)
        con = get_fb_conn()
        cur = con.cursor()
        cur.callproc("DBPROCDELETETEMPLOGISTICORDER", (temp_order_reference,))
        outputParams = cur.fetchone()
        con.commit()
        if outputParams is None:
            raise Http404
        if outputParams and outputParams[0] != 'Y':
            raise Http404
        form = self.form_class(initial={
            'tab_number': 1,
            'next_tab': 'tab_1'
        })
        next_tab = 'tab_1'
        return self.render_to_response(self.get_context_data(form=form, next_tab=next_tab))


class ExportOrderEditView(FormView):
    form_class = AddExportOrderForm
    template_name = "dashboard/logistics/logistics_export/export_entry.html"
    success_url = reverse_lazy('logisticsexport:entry-list')
    action_type = 'E'

    def get(self, request, *args, **kwargs):
        edit_orderreference = self.request.GET.get('edit_orderreference', None)
        if edit_orderreference is None:
            raise Http404
        try:
            order_entry = Logisticentry.objects.using('firebird').get(logisticreference=edit_orderreference)
        except ObjectDoesNotExist:
            raise Http404
        con = get_fb_conn()
        cur = con.cursor()
        username = self.request.user.username.strip()
        temp_order_reference = "*" * (14 - len(username)) + "{0}".format(username)
        cur.callproc("DBPROCEDITLOGISTICSORDERENTRY", (edit_orderreference, temp_order_reference, username,))
        outputParams = cur.fetchone()
        con.commit()
        if outputParams is None:
            raise Http404
        if outputParams and outputParams[0] != 'Y':
            raise Http404
        form = self.form_class(initial={
            'entry_date': datetime.datetime.strptime(str(order_entry.orderdate), '%Y-%m-%d').strftime('%d/%m/%Y'),
            'order_owner': order_entry.transportercode,
            'customer_name': order_entry.consignorcode.customername,
            'customercode': order_entry.consigneecode.customercode,
            'consignee_name': order_entry.consigneecode.customername,
            'consigneecode': order_entry.consigneecode.customercode,
            'invoice_party_name': order_entry.invoicepartycode.customername,
            'invoice_partycode': order_entry.invoicepartycode.customercode,
            # 'invoice_currency': order_entry.invoicecurrency,
            'origin': order_entry.fromstationcode,
            'loading_point': order_entry.loadingpointcode.depotcode,
            'destination': order_entry.tostationcode,
            'offloading_point': order_entry.offloadingpointcode.depotcode,
            'commodity': order_entry.commoditycode,
            'cargo_type': order_entry.cargotypecode,
            'blnumber': order_entry.blnumber,
            'client_reference': order_entry.clientreference,
            'container_20': order_entry.container20,
            'container_40': order_entry.container40,
            'packing_unit': order_entry.unitcode,
            'weight': order_entry.bbweightinkg,
            # 'quantity': order_entry.quantity,
            'tonnage': order_entry.tonnage,
            'declaration_no': order_entry.declarationno,
            'report_comments': order_entry.comments,
            'cargo_details_ref': order_entry.cargodetails,
            'border_entry': '' if order_entry.bordercode is None else order_entry.bordercode.bordercode,
            'clearing_agent': '' if order_entry.agentcode is None else order_entry.agentcode.agentcode,
            'port_agent': order_entry.portagentcode,
            'broker' : order_entry.brokercode.brokercode if order_entry.brokercode else '',
            'remarks': order_entry.descriptionofgoods,

            # shipping line and vessel details

            'shippingline_name': order_entry.shippinglinecode.shippinglinecode if order_entry.shippinglinecode else None,
            'allowed_free_days': order_entry.shippingfreedays,
            'vessel': order_entry.vesselcode.vesselcode if order_entry.vesselcode else None,
            'voyage': order_entry.vesselvoyage,
            'etd': order_entry.vesseletd,
            'actual_departure': order_entry.vesseldeparture,
            'stack_closing': order_entry.stackclosingdate,
            'clearance_deadline': order_entry.exportclearancedeadline,
            'port_storage_starts': order_entry.shippingportstorage,

            # DOCUMENT RECEVIED

            'booking_received': order_entry.documentreceivedon,
            'forwarding_agent': order_entry.forwardingagentcode,
            'submitted_fa': order_entry.forwardingagentsubmitdate,
            'cleared_agent_name': order_entry.forwardingagentcleareddate,
            'nde_tax': order_entry.documenttaxed,
            'edit_orderreference': edit_orderreference

        })
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super(ExportOrderEditView, self).get_context_data(**kwargs)
        transportercode = self.request.session['transporter_access']
        context['transporter_code'] = transportercode
        username = self.request.user.username.strip()
        context['orderreference'] = "*" * (14 - len(username)) + "{0}".format(username)
        context['containers'] = Containertypemaster.objects.using('firebird').filter(activecontainertype='Y')
        context['unitnames'] = Unitofmeasurement.objects.using('firebird').filter(activeunit='Y')
        context['locations'] = Locationmaster.objects.using('firebird').filter(activelocation='Y')
        context['transporter_name'] = Transportermaster.objects.using('firebird'). \
            get(transportercode=transportercode).transportername
        context['containerdropofflocation'] = Locationmaster.objects.using('firebird').filter(
            activelocation='Y').order_by(
            'locationname').exclude(locationcode='000000')
        context['action_type'] = 'E'
        return context

    def get_form_kwargs(self):
        kwargs = super(ExportOrderEditView, self).get_form_kwargs()
        kwargs.update({"request": self.request})
        kwargs.update({"action_type": self.action_type})
        return kwargs


class ExportOrderValidate(FormView):
    form_class = AddExportOrderForm

    def get_form_kwargs(self):
        kwargs = super(ExportOrderValidate, self).get_form_kwargs()
        kwargs.update({"request": self.request})
        kwargs.update({"action_type": self.request.POST.get('action_type', None)})
        return kwargs

    def post(self, request, *args, **kwargs):
        tab_number = request.POST.get('tab_num', None)
        response = {}
        form = self.get_form()
        context = self.get_context_data(**kwargs)
        if form.is_valid():
            if tab_number == '1':
                form.check1()
                if form.errors:
                    response['message'] = form.errors
                    response['status'] = 'failure'
                else:
                    response['status'] = 'success'
            elif tab_number == '2':
                form.check2()
                if form.errors:
                    response['message'] = form.errors
                    response['status'] = 'failure'
                else:
                    response['status'] = 'success'
            elif tab_number == '3':
                form.check3()
                if form.errors:
                    response['message'] = form.errors
                    response['status'] = 'failure'
                else:
                    save = form.save()
                    if save == 'Y':
                        response['status'] = 'complete'
                    else:
                        response['message'] = _("Something went wrong, please try again after some time.")
                        response['status'] = 'exception'
        else:
            response['message'] = form.errors
            response['status'] = 'failure'
        return JsonResponse(response)


class CheckDistanceView(View):

    def get(self, request):
        response = dict()
        fromstationcode = request.GET.get('fromstationcode', None)
        tostationcode = request.GET.get('tostationcode', None)
        if (Distancemaster.objects.using('firebird').filter(fromstationcode=fromstationcode,
                                                            tostationcode=tostationcode).exists()):
            distance = 'Y'
        else:
            distance = 'N'
        if distance == 'N':
            if (Distancemaster.objects.using('firebird').filter(fromstationcode=tostationcode,
                                                                tostationcode=fromstationcode).exists()):
                distance = 'Y'
            else:
                distance = 'N'
        return JsonResponse({'status': 1, 'distance': distance})


class ContainerEntrySaveView(FormView):
    form_class = ContainerEntryForm

    def get(self, request):
        slno = self.request.GET.get('slno', None)
        orderreference = self.request.GET.get('orderreference', None)
        queryset = Logisticscontainerdetails.objects.using('firebird').filter(logisticreference=orderreference)
        if slno:
            edit_obj = queryset.filter(slno=int(slno)).first()
            json_data = dict()
            json_data['containertypecode'] = edit_obj.containertypecode.containertypecode
            json_data['commodityweight'] = edit_obj.commodityweight
            json_data['containerreference'] = edit_obj.containerreference
            json_data['containerseal'] = edit_obj.containerseal
            json_data['reefertemperature'] = edit_obj.reefertemperature
            json_data['gensetrequired'] = edit_obj.gensetrequired
            json_data['fueltobesupplied'] = edit_obj.fueltobesupplied
            json_data['shipperownedcontainer'] = edit_obj.shipperownedcontainer
            json_data['placeholdercontainer'] = edit_obj.placeholdercontainer
            json_data['dropoffatdestination'] = edit_obj.dropoffatdestination
            json_data['containerremarks'] = edit_obj.containerremarks
            json_data['loadtype'] = edit_obj.loadtype
            json_data['grossweight'] = edit_obj.grossweight
            json_data['containertare'] = edit_obj.containertare
            json_data['logisticreference'] = edit_obj.logisticreference
            json_data['dropoffcode'] = "" if edit_obj.dropoffcode is None else edit_obj.dropoffcode.locationcode
            json_data['dropoffdepot'] = "" if edit_obj.dropoffdepot is None else edit_obj.dropoffdepot.depotcode
            json_data['groundinginstruction'] = edit_obj.groundinginstruction
            json_data['validitydate'] = datetime.datetime.strptime(str(edit_obj.validitydate), '%Y-%m-%d'). \
                strftime('%d/%m/%Y') if edit_obj.validitydate else ""
            json_data['slno'] = edit_obj.slno
            json_data['weightinkg'] = edit_obj.weightinkg
            return JsonResponse(json_data)

        data_list = list()
        result_dict = {}
        draw = request.GET.get('draw', None)
        start = int(request.GET.get('start', 0))
        tab_length = int(request.GET.get('length', 10))
        end = start + tab_length

        coloumns = {0: 'slno', 1: 'containerreference', 2: 'containerseal', 3: 'containertypecode__containertypename',
                    4: 'containertypecode__containerweight', 5: 'commodityweight', 6: 'grossweight',
                    7: 'shipperownedcontainer', 8: 'gensetrequired', 9: 'fueltobesupplied',
                    10: 'dropoffcode__locationname', 11: 'loadingdropoffpendingqty', 12: 'dropoffdepot__depotname',
                    13: 'groundinginstruction', 14: 'validitydate'}

        for col_index in range(0, 15):
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
            row_list.append(record.slno)
            row_list.append(record.containerreference)
            row_list.append(record.containerseal)
            row_list.append(record.containertypecode.containertypename)
            row_list.append(record.containertypecode.containerweight)
            row_list.append(record.commodityweight)
            row_list.append(record.grossweight)
            row_list.append("Yes" if record.shipperownedcontainer == 'Y' else "No")
            row_list.append("Yes" if record.gensetrequired == 'Y' else "No")
            row_list.append("Yes" if record.fueltobesupplied == 'Y' else "No")
            row_list.append("" if record.dropoffcode is None else record.dropoffcode.locationname)
            row_list.append("Yes" if record.loadingdropoffpendingqty == 1 else "No")
            row_list.append("" if record.dropoffdepot is None else record.dropoffdepot.depotname)
            row_list.append(record.groundinginstruction)
            row_list.append("" if record.validitydate is None else datetime.datetime.strptime(str(record.validitydate),
                                                                                              '%Y-%m-%d').strftime(
                '%d/%m/%Y'))
            data_list.append(row_list)
        result_dict['data'] = data_list
        return JsonResponse(result_dict)

    def get_form_kwargs(self):
        kwargs = super(ContainerEntrySaveView, self).get_form_kwargs()
        kwargs.update({"request": self.request})
        return kwargs

    def post(self, request):
        response = {}
        form = self.get_form()
        if form.is_valid():
            status = form.save()
            if status:
                if status == 'Y':
                    response['message'] = _("Container entry saved succesfully")
                    response['status'] = 'success'
            else:
                response['message'] = _("Something went wrong, please try again after some time.")
                response['status'] = 'exception'
        else:
            response['message'] = form.errors
            response['status'] = 'failure'
        return JsonResponse(response)


class ContainerEntryDetailsView(View):

    def get(self, request):
        containerreference = self.request.GET.get('orderreference', None)
        queryset = Logisticscontainerdetails.objects.using('firebird').filter(logisticreference=containerreference)
        json_dict = dict()
        json_dict['quantity'] = queryset.count()
        json_dict['container_20'] = queryset.filter(
            containertypecode__containergroupcode__containergroupcode='01').count()
        json_dict['container_40'] = queryset.filter(
            containertypecode__containergroupcode__containergroupcode='02').count()
        grossweight_sum = queryset.aggregate(Sum('grossweight')).get('grossweight__sum', 0)
        grossweight_sum = 0 if grossweight_sum is None else grossweight_sum
        json_dict['tonnage'] = float(grossweight_sum)
        return JsonResponse(json_dict)


class ContainerEntryDeleteView(View):
    def post(self, request):
        orderreference = self.request.POST.get('orderreference', None)
        slno = self.request.POST.get('slno', None)
        json_dict = {}
        try:
            Logisticscontainerdetails.objects.using('firebird').filter(logisticreference=orderreference,
                                                                       slno=slno).delete()
            json_dict['status'] = 'success'
        except ObjectDoesNotExist:
            json_dict['status'] = 'fail'
        return JsonResponse(json_dict)


class ContainerUnpackSaveView(FormView):
    form_class = ContainerEntryForm

    def get(self, request):
        slno = self.request.GET.get('slno', None)
        orderreference = self.request.GET.get('orderreference', None)
        queryset = Logisticscontainerdetails.objects.using('firebird').filter(logisticreference=orderreference)

        if slno:
            edit_obj = queryset.filter(slno=int(slno)).first()
            json_data = dict()
            json_data['containertypecode'] = edit_obj.containertypecode.containertypecode
            json_data['commodityweight'] = edit_obj.commodityweight
            json_data['containerreference'] = edit_obj.containerreference
            json_data['containerseal'] = edit_obj.containerseal
            json_data['reefertemperature'] = edit_obj.reefertemperature
            json_data['gensetrequired'] = edit_obj.gensetrequired
            json_data['fueltobesupplied'] = edit_obj.fueltobesupplied
            json_data['shipperownedcontainer'] = edit_obj.shipperownedcontainer
            json_data['placeholdercontainer'] = edit_obj.placeholdercontainer
            json_data['dropoffatdestination'] = edit_obj.dropoffatdestination
            json_data['containerremarks'] = edit_obj.containerremarks
            json_data['loadtype'] = edit_obj.loadtype
            json_data['grossweight'] = edit_obj.grossweight
            json_data['containertare'] = edit_obj.containertare
            json_data['orderreference'] = edit_obj.logisticreference
            json_data['dropoffcode'] = "" if edit_obj.dropoffcode is None else edit_obj.dropoffcode.locationcode
            json_data['dropoffdepot'] = "" if edit_obj.dropoffdepot is None else edit_obj.dropoffdepot.depotcode
            json_data['groundinginstruction'] = edit_obj.groundinginstruction
            json_data['validitydate'] = datetime.datetime.strptime(str(edit_obj.validitydate), '%Y-%m-%d'). \
                strftime('%d/%m/%Y') if edit_obj.validitydate else ""
            json_data['slno'] = edit_obj.slno
            json_data['weightinkg'] = edit_obj.weightinkg
            json_data['packingname'] = edit_obj.packingname.unitcode
            json_data['bbquantity'] = edit_obj.bbquantity


            return JsonResponse(json_data)

        data_list = list()
        result_dict = {}
        draw = request.GET.get('draw', None)
        start = int(request.GET.get('start', 0))
        tab_length = int(request.GET.get('length', 10))
        end = start + tab_length

        coloumns = {0: 'slno', 1: 'containerreference', 2: 'containerseal', 3: 'containertypecode__containertypename',
                    4: 'containertypecode__containerweight', 5: 'commodityweight', 6: 'grossweight',
                    7: 'packingname__weightinkg', 8: 'bbquantity', 9: 'packingname__unitname',
                    10: 'dropoffdepot__depotname',11: 'groundinginstruction', 12: 'validitydate'}

        for col_index in range(0, 13):
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
            row_list.append(record.slno)
            row_list.append(record.containerreference)
            row_list.append(record.containerseal)
            row_list.append(record.containertypecode.containertypename)
            row_list.append(record.containertypecode.containerweight)
            row_list.append(record.commodityweight)
            row_list.append(record.grossweight)
            row_list.append(record.packingname.weightinkg if record.packingname else "")
            row_list.append(record.bbquantity)
            row_list.append(record.packingname.unitname if record.packingname else "")
            row_list.append("" if record.dropoffdepot is None else record.dropoffdepot.depotname)
            row_list.append(record.groundinginstruction)
            row_list.append("" if record.validitydate is None else datetime.datetime.strptime(str(record.validitydate),
                                                                                '%Y-%m-%d').strftime('%d/%m/%Y'))
            data_list.append(row_list)
        result_dict['data'] = data_list
        return JsonResponse(result_dict)

    def get_form_kwargs(self):
        kwargs = super(ContainerUnpackSaveView, self).get_form_kwargs()
        kwargs.update({"request": self.request})
        return kwargs

    def post(self, request):
        response = {}
        form = self.get_form()
        if form.is_valid():
            status = form.save()
            if status:
                if status == 'Y':
                    response['message'] = _("Container entry saved succesfully")
                    response['status'] = 'success'
            else:
                response['message'] = _("Something went wrong, please try again after some time.")
                response['status'] = 'exception'
        else:
            response['message'] = form.errors
            response['status'] = 'failure'
        return JsonResponse(response)



def ExportsExportListView(request):
    orderno = request.GET.get('orderno', None)
    customer = request.GET.get('customercode', None)
    origin = request.GET.get('origin', None)
    destination = request.GET.get('destination', None)
    commodity = request.GET.get('commodity', None)
    status = request.GET.get('status', None)
    cargotype = request.GET.get('cargotype', None)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    live = request.GET.get('live', None)

    if not date_from and not date_to:
        month_before = datetime.datetime.now() - datetime.timedelta(days=30)
        queryset = Logisticentry.objects.using('firebird').filter(filetype='E',
                                                                  transportercode=request.session['transporter_access'],
                                                                  orderdate__gte=month_before) \
            .exclude(logisticreference__startswith='*')
    else:
        queryset = Logisticentry.objects.using('firebird').filter(filetype='E',
                                                                  transportercode=request.session['transporter_access']) \
            .exclude(logisticreference__startswith='*')

    if orderno:
        queryset = queryset.filter(logisticreference__iexact=orderno)
    if customer:
        queryset = queryset.filter(consignorcode=customer)
    if origin:
        queryset = queryset.filter(fromstationcode=origin)
    if destination:
        queryset = queryset.filter(tostationcode=destination)
    if commodity:
        queryset = queryset.filter(commoditycode=commodity)
    if status:
        queryset = queryset.filter(statuscode=status)
    if cargotype:
        queryset = queryset.filter(cargotypecode=cargotype)
    if date_from:
        date_from = datetime.datetime.strptime(date_from, "%d/%m/%Y").date()
        queryset = queryset.filter(orderdate__gte=date_from)
    if date_to:
        date_to = datetime.datetime.strptime(date_to, "%d/%m/%Y").date()
        queryset = queryset.filter(orderdate__lte=date_to)

    headers = ['No', 'Status', 'Order Date', 'Order Owner', 'Customer', 'Consignee', 'Invoice Party', 'Shipper',
               'Client Ref', 'Origin', 'Destination', 'Loading Point', 'Offloading point', '20"', '40"',
               'Tonnage (MT)', 'Commodity', 'Cargo Type', 'Shipping Line', 'Clearing Agent',
               'Port Agent', 'Created User', 'Remarks']
    output = BytesIO()
    wb = xlsxwriter.Workbook(output)
    ws = wb.add_worksheet('Report')

    row = 0
    col = 0
    ws.write_row(row, col, headers)

    row = 1
    col = 0
    for record in queryset:
        try:
            if record.entryuser:
                created_full_name = Usermaster.objects.using('firebird').get(username=record.entryuser.strip())
            else:
                created_full_name = None
        except ObjectDoesNotExist:
            created_full_name = None
        if created_full_name:
            created_full_name = created_full_name.userfullname
        else:
            created_full_name = ""
        ws.write_row(row, col, [record.logisticreference,
                                record.statuscode.statusdescription if record.statuscode else None,
                                datetime.datetime.strptime(str(record.orderdate), '%Y-%m-%d').strftime(
                                    '%d/%m/%Y') if record.orderdate else "",
                                record.transportercode.transportername if record.transportercode else None,
                                record.consignorcode.customername if record.consignorcode else None,
                                record.consigneecode.customername if record.consigneecode else None,
                                record.invoicepartycode.customername if record.invoicepartycode else None,
                                record.consignorcode.customername if record.consignorcode else None,
                                record.clientreference,
                                record.fromstationcode.locationname if record.fromstationcode else None,
                                record.tostationcode.locationname if record.tostationcode else None,
                                record.loadingpointcode.depotname if record.loadingpointcode else None,
                                record.offloadingpointcode.depotname if record.offloadingpointcode else None,
                                record.container20,
                                record.container40,
                                record.tonnage,
                                record.cargotypecode.cargotypename if record.cargotypecode else None,
                                record.commoditycode.commodityname if record.commoditycode else None,
                                record.shippinglinecode.shippinglinename if record.shippinglinecode else None,
                                record.agentcode.agentname if record.agentcode else None,
                                record.portagentcode.agentname if record.portagentcode else None,
                                created_full_name,
                                record.descriptionofgoods, ])
        row += 1
    wb.close()
    xlsx_data = output.getvalue()
    response = HttpResponse(xlsx_data, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=LogisticExportsOrder.xlsx'
    return response


def ContainerExport(request):
    order_reference = request.GET.get('order_reference', None)
    queryset = Logisticscontainerdetails.objects.using('firebird').filter(logisticreference=order_reference)

    headers = ['Sl No.', 'Container No', 'Seal No', 'Container Type', 'Cont. Tare', 'Nett Wt', 'Gross Wt', 'SOC',
               'Genset', 'Fuel Supplied', 'Drop Off', 'Drop Off Pending', 'Container Depot', 'Grounding Instr. Ref',
               'Last DO Validity Date']

    output = BytesIO()
    wb = xlsxwriter.Workbook(output)
    ws = wb.add_worksheet('Report')

    row = 0
    col = 0
    ws.write_row(row, col, headers)

    row = 1
    col = 0
    for record in queryset:
        ws.write_row(row, col, [record.slno,
                                record.containerreference,
                                record.containerseal,
                                record.containertypecode.containertypename,
                                record.containertypecode.containerweight,
                                record.commodityweight,
                                record.grossweight,
                                "Yes" if record.shipperownedcontainer == 'Y' else "No",
                                "Yes" if record.gensetrequired == 'Y' else "No",
                                "Yes" if record.fueltobesupplied == 'Y' else "No",
                                "" if record.dropoffcode is None else record.dropoffcode.locationname,
                                "Yes" if record.loadingdropoffpendingqty == 1 else "No",
                                "" if record.dropoffdepot is None else record.dropoffdepot.depotname,
                                record.groundinginstruction,
                                "" if record.validitydate is None else datetime.datetime.
                     strptime(str(record.validitydate), '%Y-%m-%d').strftime('%d/%m/%Y')])
        row += 1
    wb.close()
    xlsx_data = output.getvalue()
    response = HttpResponse(xlsx_data, content_type='application/vnd.ms-excel')
    response['Content-Disposition'] = 'attachment; filename=ContainerExport.xlsx'
    return response


class GetDepotAddressView(View):

    def get(self, request):
        """Get method for getting loading point address"""
        loading_point = request.GET.get('loading_point')
        if loading_point:
            address1 = Depotmaster.objects.using('firebird').filter(depotcode=loading_point).values('address1')
            address2 = Depotmaster.objects.using('firebird').filter(depotcode=loading_point).values('address2')
            if address1:
                address = address1[0]['address1']
            elif address2:
                address = address2[0]['address2']
            else:
                address = ''
        else:
            address = ''
        return JsonResponse({'status': 'success', 'data': address})


class GetVoyageAjaxView(View):
    """To get the voyage detail by changing vessel """

    def get(self, request):

        shipplinglinecode = self.request.GET.get('shipplingline_code')
        vessel_code = self.request.GET.get('vessel_code')
        voyage_ref = self.request.GET.get('voyage_ref')
        str_type = self.request.GET.get('str_type')
        customercode = self.request.GET.get('customercode')

        if str_type == 'VESSEL':
            voyage_html = "<option value=''>Select A Voyage</option>"
            if vessel_code is None or vessel_code == '':
                pass
            else:
                try:
                    voyage_lst = Vesseldetails.objects.using('firebird').filter(vesselcode =vessel_code).\
                                                    exclude(Q(exportvesselvoyage='') | Q(exportvesselvoyage=None))
                    for voyage in voyage_lst:
                        voyage_html += "<option value='{0}'>{1}</option>".format(voyage.vesselreference.strip(),
                                                                                 voyage.exportvesselvoyage)
                except Exception as e:
                    pass
            result_dict = {'options_html': voyage_html}

            return JsonResponse(result_dict)

        elif str_type == 'VOYAGE':

            result_dict = {'status': -1}
            try:
                ins_vessel = Vesseldetails.objects.using('firebird').filter(vesselreference=voyage_ref).values(
                    'vesseletd', 'actualdeparture', 'stackclosing', 'exportclearancedeadline', 'shippingportstorage',
                    'shippinglinecode')
                voyage_dict = dict()
                if ins_vessel:
                    # datetime.datetime.strptime(str(ins_vessel[0]['vesseleta']), '%Y-%m-%d').strftime('%d/%m/%Y')
                    # '05/04/2021'
                    result_dict['status'] = 1
                    voyage_dict['dem_error'] = ''
                    voyage_dict['vesseletd'] = str(ins_vessel[0]['vesseletd']) if ins_vessel[0]['vesseletd'] else None
                    voyage_dict['actualdeparture'] = str(ins_vessel[0]['actualdeparture']) if ins_vessel[0][
                        'actualdeparture'] else None
                    voyage_dict['stackclosing'] = str(ins_vessel[0]['stackclosing']) if ins_vessel[0][
                        'stackclosing'] else None
                    voyage_dict['exportclearancedeadline'] = str(ins_vessel[0]['exportclearancedeadline']) if \
                        ins_vessel[0][
                            'exportclearancedeadline'] else None
                    voyage_dict['shippingportstorage'] = str(ins_vessel[0]['shippingportstorage']) if ins_vessel[0][
                        'shippingportstorage'] else None
                    q_set_shippingline_details = Shippinglinedetails.objects.using('firebird').filter(
                        shippinglinecode=ins_vessel[0]['shippinglinecode'],
                        effectivefrom__lte=datetime.datetime.now().date(),
                        effectiveto__gte=datetime.datetime.now().date())
                    if q_set_shippingline_details.filter(customercode=customercode):
                        q_set_shippingline_details = q_set_shippingline_details.filter(customercode=customercode)
                        voyage_dict['allowedfreedays'] = int(q_set_shippingline_details[0].shippingfreedayslocal)
                    elif q_set_shippingline_details.filter(customercode=None):
                        q_set_shippingline_details = q_set_shippingline_details.filter(customercode=None)
                        voyage_dict['allowedfreedays'] = int(q_set_shippingline_details[0].shippingfreedayslocal)
                    else:
                        voyage_dict['demmuragestarts'] = ''
                        voyage_dict['dem_error'] = 'Shipping Free Days Date Range Expired or Not Defined..!!'
                        voyage_dict['allowedfreedays'] = ''

                    result_dict['voyage'] = voyage_dict
                else:
                    pass

                return JsonResponse(result_dict)
            except Exception as e:
                return JsonResponse(result_dict)
        elif str_type == 'SHIPPINGLINE':
            vessel_html = "<option value=''>Select A Vessel</option>"
            if shipplinglinecode is None or shipplinglinecode == '':
                pass
            else:
                try:
                    vessel_lst = Vesseldetails.objects.using('firebird').filter(shippinglinecode =shipplinglinecode).\
                                    values('vesselcode','vesselcode__vesselname').distinct()
                    for vessel in vessel_lst:
                        vessel_html += "<option value='{0}'>{1}</option>".format(vessel['vesselcode'],vessel['vesselcode__vesselname'])
                except Exception as e:
                    pass
            result_dict = {'options_html': vessel_html}

            return JsonResponse(result_dict)
        return JsonResponse({'status': -1})


class ExportsCancelAjaxView(View):

    def post(self, request):
        if request.user.is_authenticated:
            order_ref = request.POST.get('order_ref', None)
            reason = request.POST.get('reason', None)
            try:
                order_entry = Logisticentry.objects.using('firebird').get(logisticreference=order_ref)
                if order_entry.statuscode.statuscode != '0050':
                    order_entry.statuscode = Statusmaster.objects.using('firebird').get(statuscode='0050',
                                                                                        statustype='L')
                    order_entry.cancelleduser = request.user.username
                    order_entry.cancelledtime = datetime.datetime.now()
                    order_entry.cancellationreason = reason
                    order_entry.save()
                    return JsonResponse({'status': 1})
                # else:
                # 	return JsonResponse({'status': -1, 'message': 'You cannot cancel order.Trip details found'})
                else:
                    return JsonResponse({'status': -1, 'message': 'Cannot approve cancelled order entry'})
            except ObjectDoesNotExist:
                pass
        return JsonResponse({'	status': -1})

def dateformate_DDMMYYYY(date_data):
    try:
        if date_data:
            date_str =  date_data.strftime("%d/%m/%Y, %H:%M:%S")
            return date_str
        else:
            return ""
    except Exception as e:
        return ''

class UpdateDatesAjaxView(View):

    def get(self, request):
        order_ref = request.GET.get('order_ref')
        update_type = request.GET.get('update_type')

        result_dict = {'status': -1}
        try:
            ins_logisticexport = Logisticentry.objects.using('firebird').get(logisticreference=order_ref)
        except Exception as e:
            result_dict['message'] = _("Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        if update_type == 'DOCUMENT_RECEIVED':
            if not ins_logisticexport.documentreceivedon:
                result_dict['status'] = 1
            else:
                str_msg = _("Booking Received Date Already Updated By %s at %s")
                result_dict['message'] = str_msg % (
                    str(ins_logisticexport.documentreceiveduser), dateformate_DDMMYYYY(ins_logisticexport.documentreceiveduserdate))

        return JsonResponse(result_dict)

    def post(self, request):
        order_ref = request.POST.get('order_ref')
        update_type = request.POST.get('update_type')
        str_datetoupdate = request.POST.get('datetoupdate')

        result_dict = {'status': -1}

        ins_logisticexport = Logisticentry.objects.using('firebird').filter(logisticreference=order_ref)
        if not ins_logisticexport:
            result_dict['message'] = _("Logistic Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        try:
            if not str_datetoupdate:
                result_dict['message'] = _("Please select date.")
            else:
                datetoupdate = datetime.datetime.strptime(str_datetoupdate, "%d/%m/%Y").date()
                if datetoupdate > datetime.datetime.now().date():
                    result_dict['message'] = _("Future dates are not allowed.")
                    return JsonResponse(result_dict)
                if ins_logisticexport[0].orderdate >datetoupdate:
                    result_dict['message'] = _("Date cannot be less than Order Date ")
                    return JsonResponse(result_dict)
        except Exception as e:
            result_dict['message'] = _("Some error occured.")

        if update_type == 'DOCUMENT_RECEIVED':
            try:
                username = self.request.user.username.strip()
                ins_logisticexport.update(documentreceivedon=datetoupdate,
                                          documentreceiveduser=username,
                                          documentreceiveduserdate=datetime.datetime.now(),
                                          statuscode='0040')
                result_dict['status'] = 1
            except Exception as e:
                result_dict['message'] = _("Some error occured, Please try again later")

        return JsonResponse(result_dict)


class UpdateNdeTaxedAjaxView(View):

    def get(self, request):
        # import pdb;pdb.set_trace()
        order_ref = request.GET.get('order_ref')
        update_type = request.GET.get('update_type')

        result_dict = {'status': -1}
        try:
            ins_logisticexport = Logisticentry.objects.using('firebird').get(logisticreference=order_ref)
        except Exception as e:
            result_dict['message'] = _("Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        if update_type == 'NDE_TAXED':
            if ins_logisticexport.forwardingagentcleareddate:
                if not ins_logisticexport.documenttaxed:
                    result_dict['status'] = 1
                else:
                    str_msg = _("NDE TAXED Date Already Updated By %s at %s")
                    result_dict['message'] = str_msg % (
                        str(ins_logisticexport.taxeduser), dateformate_DDMMYYYY(ins_logisticexport.taxeduserdate))
            else:
                result_dict['message'] = _("Update Forwarding Agent Cleared date first")
        return JsonResponse(result_dict)

    def post(self, request):
        # import pdb;
        # pdb.set_trace()
        order_ref = request.POST.get('order_ref')
        update_type = request.POST.get('update_type')
        str_datetoupdate = request.POST.get('datetoupdate')

        result_dict = {'status': -1}

        ins_logisticexport = Logisticentry.objects.using('firebird').filter(logisticreference=order_ref)
        if not ins_logisticexport:
            result_dict['message'] = _("Logistic Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        try:
            if not str_datetoupdate:
                result_dict['message'] = _("Please select date.")
            else:
                datetoupdate = datetime.datetime.strptime(str_datetoupdate, "%d/%m/%Y").date()
                if datetoupdate > datetime.datetime.now().date():
                    result_dict['message'] = _("Future dates are not allowed.")
                    return JsonResponse(result_dict)
        except Exception as e:
            result_dict['message'] = _("Some error occured.")

        if update_type == 'NDE_TAXED':
            if ins_logisticexport[0].forwardingagentcleareddate > datetoupdate:
                result_dict['message'] = _("Taxed Date cannot be less than Cleared Date")
            else:
                try:
                    username = self.request.user.username.strip()
                    ins_logisticexport.update(documenttaxed=datetoupdate,
                                              taxeduser=username,
                                              taxeduserdate=datetime.datetime.now(),
                                              statuscode='0043')
                    result_dict['status'] = 1
                except Exception as e:
                    result_dict['message'] = _("Some error occured, Please try again later")

        return JsonResponse(result_dict)


class UpdateWDateAjaxView(View):

    def get(self, request):
        order_ref = request.GET.get('order_ref')
        update_type = request.GET.get('update_type')

        result_dict = {'status': -1}
        try:
            ins_logisticexport = Logisticentry.objects.using('firebird').get(logisticreference=order_ref)
        except Exception as e:
            result_dict['message'] = _("Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        if update_type == 'W_DATE':
            if not ins_logisticexport.w7date:
                result_dict['status'] = 1
            else:
                str_msg = _("W7 Date Already Updated By %s at %s")
                result_dict['message'] = str_msg % (
                    str(ins_logisticexport.w7dateentryuser), dateformate_DDMMYYYY(ins_logisticexport.w7dateentrydate))

        return JsonResponse(result_dict)

    def post(self, request):
        order_ref = request.POST.get('order_ref')
        update_type = request.POST.get('update_type')
        str_datetoupdate = request.POST.get('datetoupdate')

        result_dict = {'status': -1}

        ins_logisticexport = Logisticentry.objects.using('firebird').filter(logisticreference=order_ref)
        if not ins_logisticexport:
            result_dict['message'] = _("Logistic Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        try:
            if not str_datetoupdate:
                result_dict['message'] = _("Please select date.")
            else:
                datetoupdate = datetime.datetime.strptime(str_datetoupdate, "%d/%m/%Y").date()
                if datetoupdate > datetime.datetime.now().date():
                    result_dict['message'] = _("Future dates are not allowed.")
                    return JsonResponse(result_dict)
        except Exception as e:
            result_dict['message'] = _("Some error occured.")

        if update_type == 'W_DATE':
            if ins_logisticexport[0].orderdate >datetoupdate:
                result_dict['message'] = _("W7 Date cannot be less than Order Date")
            else:
                try:
                    username = self.request.user.username.strip()
                    ins_logisticexport.update(w7date=datetoupdate,
                                              w7dateentryuser=username,
                                              w7dateentrydate=datetime.datetime.now())
                    result_dict['status'] = 1
                except Exception as e:
                    result_dict['message'] = _("Some error occured, Please try again later")

        return JsonResponse(result_dict)


class UpdateTDateAjaxView(View):

    def get(self, request):
        order_ref = request.GET.get('order_ref')
        update_type = request.GET.get('update_type')

        result_dict = {'status': -1}
        try:
            ins_logisticexport = Logisticentry.objects.using('firebird').get(logisticreference=order_ref)
        except Exception as e:
            result_dict['message'] = _("Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        if update_type == 'T8_DATE':
            if not ins_logisticexport.t8date:
                result_dict['status'] = 1
            else:
                str_msg = _("T8 Date Already Updated By %s at %s")
                result_dict['message'] = str_msg % (
                    str(ins_logisticexport.t8dateentryuser), dateformate_DDMMYYYY(ins_logisticexport.t8dateentrydate))

        return JsonResponse(result_dict)

    def post(self, request):
        order_ref = request.POST.get('order_ref')
        update_type = request.POST.get('update_type')
        str_datetoupdate = request.POST.get('datetoupdate')

        result_dict = {'status': -1}

        ins_logisticexport = Logisticentry.objects.using('firebird').filter(logisticreference=order_ref)
        if not ins_logisticexport:
            result_dict['message'] = _("Logistic Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        try:
            if not str_datetoupdate:
                result_dict['message'] = _("Please select date.")
            else:
                datetoupdate = datetime.datetime.strptime(str_datetoupdate, "%d/%m/%Y").date()
                if datetoupdate > datetime.datetime.now().date():
                    result_dict['message'] = _("Future dates are not allowed.")
                    return JsonResponse(result_dict)
        except Exception as e:
            result_dict['message'] = _("Some error occured.")

        if update_type == 'T8_DATE':
            if ins_logisticexport[0].orderdate >datetoupdate:
                result_dict['message'] = _("T8 Date cannot be less than Order Date")
            else:
                try:
                    username = self.request.user.username.strip()
                    ins_logisticexport.update(t8date=datetoupdate,
                                              t8dateentryuser=username,
                                              t8dateentrydate=datetime.datetime.now())
                    result_dict['status'] = 1
                except Exception as e:
                    result_dict['message'] = _("Some error occured, Please try again later")

        return JsonResponse(result_dict)


class UpdateKudumbaAjaxView(View):

    def get(self, request):
        order_ref = request.GET.get('order_ref')
        update_type = request.GET.get('update_type')

        result_dict = {'status': -1}
        try:
            ins_logisticexport = Logisticentry.objects.using('firebird').get(logisticreference=order_ref)
        except Exception as e:
            result_dict['message'] = _("Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        if update_type == 'KUDUMBA_DATE':
            if not ins_logisticexport.kudumbabooking:
                result_dict['status'] = 1
            else:
                str_msg = _("KUDUMBA Date Already Updated By %s at %s")
                result_dict['message'] = str_msg % (
                    str(ins_logisticexport.kudumbabookinguser), dateformate_DDMMYYYY(ins_logisticexport.kudumbabookingtime))

        return JsonResponse(result_dict)

    def post(self, request):
        order_ref = request.POST.get('order_ref')
        update_type = request.POST.get('update_type')
        str_datetoupdate = request.POST.get('datetoupdate')

        result_dict = {'status': -1}

        ins_logisticexport = Logisticentry.objects.using('firebird').filter(logisticreference=order_ref)
        if not ins_logisticexport:
            result_dict['message'] = _("Logistic Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        try:
            if not str_datetoupdate:
                result_dict['message'] = _("Please select date.")
            else:
                datetoupdate = datetime.datetime.strptime(str_datetoupdate, "%d/%m/%Y").date()
                if datetoupdate > datetime.datetime.now().date():
                    result_dict['message'] = _("Future dates are not allowed.")
                    return JsonResponse(result_dict)
        except Exception as e:
            result_dict['message'] = _("Some error occured.")

        if update_type == 'KUDUMBA_DATE':
            if ins_logisticexport[0].orderdate >datetoupdate:
                result_dict['message'] = _("KUDUMBA Date cannot be less than Order Date")
            else:
                try:
                    username = self.request.user.username.strip()
                    ins_logisticexport.update(kudumbabooking=datetoupdate,
                                              kudumbabookinguser=username,
                                              kudumbabookingtime=datetime.datetime.now())
                    result_dict['status'] = 1
                except Exception as e:
                    result_dict['message'] = _("Some error occured, Please try again later")

        return JsonResponse(result_dict)


class UpdatePortBookingAjaxView(View):

    def get(self, request):
        order_ref = request.GET.get('order_ref')
        update_type = request.GET.get('update_type')

        result_dict = {'status': -1}
        try:
            ins_logisticexport = Logisticentry.objects.using('firebird').get(logisticreference=order_ref)
        except Exception as e:
            result_dict['message'] = _("Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        if update_type == 'PORT_BOOKING':
            if not ins_logisticexport.portbooking:
                result_dict['status'] = 1
            else:
                str_msg = _("PORT BOOKING Date Already Updated By %s at %s")
                result_dict['message'] = str_msg % (
                    str(ins_logisticexport.portbookinguser), dateformate_DDMMYYYY(ins_logisticexport.portbookingtime))

        return JsonResponse(result_dict)

    def post(self, request):
        order_ref = request.POST.get('order_ref')
        update_type = request.POST.get('update_type')
        str_datetoupdate = request.POST.get('datetoupdate')

        result_dict = {'status': -1}

        ins_logisticexport = Logisticentry.objects.using('firebird').filter(logisticreference=order_ref)
        if not ins_logisticexport:
            result_dict['message'] = _("Logistic Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        try:
            if not str_datetoupdate:
                result_dict['message'] = _("Please select date.")
            else:
                datetoupdate = datetime.datetime.strptime(str_datetoupdate, "%d/%m/%Y").date()
                if datetoupdate > datetime.datetime.now().date():
                    result_dict['message'] = _("Future dates are not allowed.")
                    return JsonResponse(result_dict)
        except Exception as e:
            result_dict['message'] = _("Some error occured.")

        if update_type == 'PORT_BOOKING':
            if ins_logisticexport[0].orderdate >datetoupdate:
                result_dict['message'] = _("Port Booking Date cannot be less than Order Date")
            else:
                try:
                    username = self.request.user.username.strip()
                    ins_logisticexport.update(portbooking=datetoupdate,
                                              portbookinguser=username,
                                              portbookingtime=datetime.datetime.now())
                    result_dict['status'] = 1
                except Exception as e:
                    result_dict['message'] = _("Some error occured, Please try again later")

        return JsonResponse(result_dict)


class UpdateSobDateAjaxView(View):

    def get(self, request):
        order_ref = request.GET.get('order_ref')
        update_type = request.GET.get('update_type')

        result_dict = {'status': -1}
        try:
            ins_logisticexport = Logisticentry.objects.using('firebird').get(logisticreference=order_ref)
        except Exception as e:
            result_dict['message'] = _("Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        if update_type == 'SOB_UPDATE':
            if not ins_logisticexport.shippedonboard:
                result_dict['status'] = 1
            else:
                str_msg = _("SOB Date Already Updated By %s at %s")
                result_dict['message'] = str_msg % (
                    str(ins_logisticexport.shippedonboarduser), dateformate_DDMMYYYY(ins_logisticexport.shippedonboardtime))
        elif update_type == 'DEL_SOB':
            if ins_logisticexport.shippedonboard:
                result_dict['status'] = 1
            else:
                str_msg = _("Please Update the SOB Date first")
                result_dict['message'] = str_msg

        return JsonResponse(result_dict)

    def post(self, request):
        order_ref = request.POST.get('order_ref')
        update_type = request.POST.get('update_type')
        str_datetoupdate = request.POST.get('datetoupdate')

        result_dict = {'status': -1}

        ins_logisticexport = Logisticentry.objects.using('firebird').filter(logisticreference=order_ref)
        if not ins_logisticexport:
            result_dict['message'] = _("Logistic Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        try:
            if update_type == 'DEL_SOB':
                username = self.request.user.username.strip()
                ins_logisticexport.update(shippedonboard=None,
                                          shippedonboarduser=username,
                                          shippedonboardtime=datetime.datetime.now(),
                                          statuscode='0043')
                result_dict['status'] = 1
                return JsonResponse(result_dict)
        except Exception as e:
            result_dict['message'] = _("Some error occured.")

        if update_type == 'SOB_UPDATE':
            if not str_datetoupdate:
                result_dict['message'] = _("Please select date.")
            else:
                datetoupdate = datetime.datetime.strptime(str_datetoupdate, "%d/%m/%Y").date()
                if datetoupdate > datetime.datetime.now().date():
                    result_dict['message'] = _("Future dates are not allowed.")
                    return JsonResponse(result_dict)
            if ins_logisticexport[0].documenttaxed >datetoupdate:
                result_dict['message'] = _("Shipped on board Date cannot be less than Document Taxed date")
            else:
                try:
                    username = self.request.user.username.strip()
                    ins_logisticexport.update(shippedonboard=datetoupdate,
                                              shippedonboarduser=username,
                                              shippedonboardtime=datetime.datetime.now(),
                                              statuscode='0047')
                    result_dict['status'] = 1
                except Exception as e:
                    result_dict['message'] = _("Some error occured, Please try again later")

        return JsonResponse(result_dict)


class UpdateStackOrderAjaxView(View):

    def get(self, request):
        order_ref = request.GET.get('order_ref')
        update_type = request.GET.get('update_type')

        result_dict = {'status': -1}
        try:
            ins_logisticexport = Logisticentry.objects.using('firebird').get(logisticreference=order_ref)
        except Exception as e:
            result_dict['message'] = _("Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        if update_type == 'STACK_ORDER':
            if not ins_logisticexport.stackorder:
                result_dict['status'] = 1
            else:
                str_msg = _("Stack Order Date Already Updated By %s at %s")
                result_dict['message'] = str_msg % (
                    str(ins_logisticexport.stackorderuser), dateformate_DDMMYYYY(ins_logisticexport.stackordertime))

        return JsonResponse(result_dict)

    def post(self, request):
        order_ref = request.POST.get('order_ref')
        update_type = request.POST.get('update_type')
        str_datetoupdate = request.POST.get('datetoupdate')

        result_dict = {'status': -1}

        ins_logisticexport = Logisticentry.objects.using('firebird').filter(logisticreference=order_ref)
        if not ins_logisticexport:
            result_dict['message'] = _("Logistic Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        try:
            if not str_datetoupdate:
                result_dict['message'] = _("Please select date.")
            else:
                datetoupdate = datetime.datetime.strptime(str_datetoupdate, "%d/%m/%Y").date()
                if datetoupdate > datetime.datetime.now().date():
                    result_dict['message'] = _("Future dates are not allowed.")
                    return JsonResponse(result_dict)
        except Exception as e:
            result_dict['message'] = _("Some error occured.")

        if update_type == 'STACK_ORDER':
            if ins_logisticexport[0].orderdate >datetoupdate:
                result_dict['message'] = _("Stack order Date cannot be less than Order Date")
            else:
                try:
                    username = self.request.user.username.strip()
                    ins_logisticexport.update(stackorder=datetoupdate,
                                              stackorderuser=username,
                                              stackordertime=datetime.datetime.now())
                    result_dict['status'] = 1
                except Exception as e:
                    result_dict['message'] = _("Some error occured, Please try again later")

        return JsonResponse(result_dict)


class UpdateSubmitClearedDatesAjaxView(View):

    def get(self, request):
        order_ref = request.GET.get('order_ref')
        update_type = request.GET.get('update_type')

        result_dict = {'status': -1}
        try:
            ins_logisticexport = Logisticentry.objects.using('firebird').get(logisticreference=order_ref)
        except Exception as e:
            result_dict['message'] = _("Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        # SUBMITTED_FA
        if update_type == 'SUBMITTED_AGENT':
            if not ins_logisticexport.documentreceivedon:
                result_dict['message'] = _("Plase Update Document received Date First.")
                return JsonResponse(result_dict)
            if not ins_logisticexport.forwardingagentsubmitdate:
                fa_option_html = "<option value=''>Select A Forwarding Agent"
                q_set_fa = Forwardingagentmaster.objects.using('firebird').filter(agentblacklisted='N')
                selected_fa = ins_logisticexport.forwardingagentcode.forwardingagentcode if ins_logisticexport.forwardingagentcode else None
                for fagent in q_set_fa:
                    if selected_fa != fagent.forwardingagentcode:
                        fa_option_html += "<option value='{0}'>{1}</option>".format(fagent.forwardingagentcode.strip(),
                                                                                    fagent.forwardingagentname)
                    else:
                        fa_option_html += "<option value='{0}' selected>{1}</option>".format(
                            fagent.forwardingagentcode.strip(), fagent.forwardingagentname)
                    result_dict['fa_option_html'] = fa_option_html
                    result_dict['status'] = 1
            else:
                str_msg = _("Already Submitted to Forwarding Agent By %s at %s")
                result_dict['message'] = str_msg % (
                    str(ins_logisticexport.forwardingagentsubmituser),
                    dateformate_DDMMYYYY(ins_logisticexport.forwardingagentsubmituserdate))
        # CLEARED_FA
        elif update_type == 'CLEARED_AGENT':
            if not ins_logisticexport.forwardingagentcleareddate:
                if ins_logisticexport.forwardingagentsubmitdate:
                    result_dict['submitted_date'] = ins_logisticexport.forwardingagentsubmitdate
                    result_dict['fa_option_html'] = "<option value='{0}'>{1}</option>".format(
                        ins_logisticexport.forwardingagentcode.forwardingagentcode.strip(),
                        ins_logisticexport.forwardingagentcode.forwardingagentname)
                    result_dict['status'] = 1
                else:
                    result_dict['message'] = _("Update Forwarding Agent submitted date first")
            else:
                str_msg = _("Forwarding Agent Cleared Date Already updated By %s at %s")
                result_dict['message'] = str_msg % (
                    str(ins_logisticexport.forwardingagentsubmituser),
                    dateformate_DDMMYYYY(ins_logisticexport.forwardingagentsubmituserdate))
        return JsonResponse(result_dict)

    def post(self, request):
        order_ref = request.POST.get('order_ref')
        update_type = request.POST.get('update_type')
        str_datetoupdate = request.POST.get('datetoupdate')
        str_fa_code = request.POST.get('forwading_agentcode')
        result_dict = {'status': -1}

        ins_logisticexport = Logisticentry.objects.using('firebird').filter(logisticreference=order_ref)
        if not ins_logisticexport:
            result_dict['message'] = _("Logistic Order with the orderreference doesn't exists.")
            return JsonResponse(result_dict)
        try:
            if not str_datetoupdate:
                result_dict['message'] = _("Please select date.")
            else:
                datetoupdate = datetime.datetime.strptime(str_datetoupdate, "%d/%m/%Y").date()
                if datetoupdate > datetime.datetime.now().date():
                    result_dict['message'] = _("Future dates are not allowed.")
                    return JsonResponse(result_dict)
        except Exception as e:
            result_dict['message'] = _("Some error occured.")
        username = self.request.user.username.strip()

        # SUBMITTED_FA
        if update_type == 'SUBMITTED_AGENT':
            if str_fa_code != '':
                if ins_logisticexport[0].documentreceivedon > datetoupdate:
                    result_dict['message'] = _("Submitted Date cannot be less than Document Received Date")
                else:
                    if ins_logisticexport[0].forwardingagentcode and ins_logisticexport[
                        0].forwardingagentcode.forwardingagentcode == str_fa_code:
                        ins_logisticexport.update(forwardingagentsubmitdate=datetoupdate,
                                                  forwardingagentsubmituser=username,
                                                  forwardingagentsubmituserdate=datetime.datetime.now(),
                                                  statuscode='0041')
                        result_dict['status'] = 1
                    else:
                        try:
                            ins_fa = Forwardingagentmaster.objects.using('firebird').get(
                                forwardingagentcode=str_fa_code, agentblacklisted='N')
                        except Exception as e:
                            result_dict['message'] = _("Forwading Agent Does not Exists.")
                        try:
                            ins_logisticexport.update(forwardingagentcode=ins_fa,
                                                      forwardingagentuser=username,
                                                      forwardingagentuserdate=datetime.datetime.now(),
                                                      forwardingagentsubmitdate=datetoupdate,
                                                      forwardingagentsubmituser=username,
                                                      forwardingagentsubmituserdate=datetime.datetime.now(),
                                                      statuscode='0041')
                            result_dict['status'] = 1
                        except Exception as e:
                            result_dict['message'] = _("Some error occured, Please try again later")
            else:
                result_dict['message'] = _("Select Forwarding Agent")
        # CLEARED_FA
        elif update_type == 'CLEARED_AGENT':
            if ins_logisticexport[0].forwardingagentsubmitdate > datetoupdate:
                result_dict['message'] = _("Cleared Date cannot be less than Submitted Date")
            else:
                try:
                    ins_logisticexport.update(forwardingagentcleareddate=datetoupdate,
                                              forwardingagentcleareduser=username,
                                              forwardingagentcleareduserdate=datetime.datetime.now(),
                                              statuscode='0042')
                    result_dict['status'] = 1
                except Exception as e:
                    result_dict['message'] = _("Some error occured, Please try again later")

        return JsonResponse(result_dict)


class ShowAlldataAjaxView(View):

    def get(self, request):
        # import pdb;pdb.set_trace()
        order_ref = request.GET.get('order_ref', None)
        ins_logisticexport = Logisticentry.objects.using('firebird').filter(logisticreference=order_ref)
        ins_logisticexport_data = ins_logisticexport.values()
        ins_logisticexport_fk_data = ins_logisticexport. \
            values('transportercode__transportername', 'consignorcode__customername',
                   'consigneecode__customername', 'invoicepartycode__customername',
                   'fromstationcode__locationname', 'loadingpointcode__depotname',
                   'tostationcode__locationname', 'offloadingpointcode__depotname',
                   'commoditycode__commodityname', 'bordercode__bordername',
                   'agentcode__agentname', 'cargotypecode__cargotypename', 'shippinglinecode__shippinglinename',
                   'vesselcode__vesselname', 'forwardingagentcode__forwardingagentname',
                   'statuscode__statusdescription', 'portagentcode__agentname', 'unitcode__unitname',
                   'statuscode__statuscode')
        # select_related('transportercode','consignorcode','consigneecode','invoicepartycode',
        # 	'fromstationcode','loadingpointcode','tostationcode','offloadingpointcode',
        # 	'commoditycode','bordercode','agentcode','shippinglinecode','vesselcode',
        # 	'forwardingagentcode','statuscode','portagentcode','unitcode')
        result_dict = {'status': -1}
        if ins_logisticexport and ins_logisticexport_data:
            logisticexport_data = ins_logisticexport_data[0]
            logisticexport_data.update(ins_logisticexport_fk_data[0])
            result_dict['status'] = 1
            result_dict['order_data'] = logisticexport_data
        else:
            result_dict['message'] = _("Not found")
        return JsonResponse(result_dict)
