from django import forms
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse_lazy
from fms.utils.fb_connect import get_fb_conn
from apps.fms_db.models import (Currencymaster, Locationmaster, Cargotypemaster, Commoditymaster, Unitofmeasurement,
                                Shippinglinemaster, Vesselmaster, Agentmaster, Ordercontainerdetails,
                                Forwardingagentmaster, Logisticscontainerdetails, Logisticentry,Brokermaster)
import datetime
import re


class AddExportOrderForm(forms.Form):
    # Main Entry Details.

    # imp_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control',
    # 'oninput': 'this.value=this.value.toUpperCase();'}))
    entry_date = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                                 initial=datetime.datetime.now().strftime("%d/%m/%Y"),
                                 widget=forms.DateInput(attrs={'class': 'form-control pull-right',
                                                               'data-date-format': "dd/mm/yyyy"}))
    order_owner = forms.CharField(required=False)

    customer_name = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control',
               'oninput': 'this.value=this.value.toUpperCase();'}))

    customercode = forms.CharField(required=False)

    consignee_name = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control',
               'oninput': 'this.value=this.value.toUpperCase();'}))

    consigneecode = forms.CharField(required=False)
    invoice_party_name = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control',
               'oninput': 'this.value=this.value.toUpperCase();'}))

    invoice_partycode = forms.CharField(required=False)

    # invoice_currency = forms.ModelChoiceField(required=False, queryset=Currencymaster.objects.using('firebird').
    # filter(activecurrency='Y'),
    # widget=forms.Select(attrs={'class': 'form-control'}, ),
    # empty_label="Select a currency")
    origin = forms.ModelChoiceField(required=False, queryset=Locationmaster.objects.using('firebird').
                                    filter(activelocation='Y').order_by('locationname'),
                                    widget=forms.Select(attrs={'class': 'form-control',
                                                               'data-url': reverse_lazy('orders:loading-points-html'),
                                                               'data-border-agent-url': reverse_lazy(
                                                                   'orders:border-agent-html')}),
                                    empty_label="Select a origin")
    loading_point = forms.CharField(required=False, widget=forms.Select(attrs={'class': 'form-control'}), )

    destination = forms.ModelChoiceField(required=False, queryset=Locationmaster.objects.using('firebird').
                                         filter(activelocation='Y').order_by('locationname'),
                                         widget=forms.Select(attrs={'class': 'form-control',
                                                                    'data-url': reverse_lazy(
                                                                        'orders:loading-points-html'),
                                                                    'data-border-agent-url': reverse_lazy(
                                                                        'orders:border-agent-html')}),
                                         empty_label="Select a destination")

    offloading_point = forms.CharField(required=False, widget=forms.Select(attrs={'class': 'form-control'}), )

    commodity = forms.ModelChoiceField(required=False, queryset=Commoditymaster.objects.using('firebird').filter(
        activecommodity='Y').exclude(commoditycode='000001').order_by('commodityname'),
                                       widget=forms.Select(attrs={'class': 'form-control'}),
                                       empty_label="Select a commodity")

    cargo_type = forms.ModelChoiceField(required=False, queryset=Cargotypemaster.objects.using('firebird').filter(activecargotype='Y'),
                                        widget=forms.Select(attrs={'class': 'form-control'}),
                                        empty_label="Select a cargo type")
    blnumber = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'BL NUMBER IS IMPORTANT',
               'oninput': "this.value=this.value.toUpperCase();"}))

    client_reference = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control',
               'oninput': "this.value=this.value.toUpperCase();"}))

    container_20 = forms.IntegerField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'readonly': True}), )

    container_40 = forms.IntegerField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'readonly': True}), )
    packing_unit = forms.ModelChoiceField(required=False,
                                          queryset=Unitofmeasurement.objects.using('firebird').filter(activeunit='Y'),
                                          widget=forms.Select(attrs={'class': 'form-control',
                                                                     'data-url': reverse_lazy(
                                                                         'orders:packing-unit-html')}),
                                          empty_label="")
    weight = forms.IntegerField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'readonly': True}), )

    quantity = forms.IntegerField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control'}), )

    tonnage = forms.DecimalField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'readonly': True}), )

    cargo_details_ref = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'oninput': "this.value=this.value.toUpperCase();"}))

    declaration_no = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'oninput': "this.value=this.value.toUpperCase();"}))

    report_comments = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'oninput': "this.value=this.value.toUpperCase();"}))

    border_entry = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'oninput': 'this.value=this.value.toUpperCase();'}))

    clearing_agent = forms.CharField(required=False,
                                     widget=forms.Select(attrs={'class': 'form-control', 'required': ''}))

    port_of_entry = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'oninput': 'this.value=this.value.toUpperCase();'}))

    port_agent = forms.ModelChoiceField(required=False, queryset=Agentmaster.objects.using('firebird').
                                        filter(Q(activeagent='Y') & (Q(agenttype='P') | Q(agenttype='B'))),
                                        widget=forms.Select(attrs={'class': 'form-control'}),
                                        empty_label="Select a Port Agent")
    broker = forms.ModelChoiceField(required=False, queryset=Brokermaster.objects.using('firebird').
                    filter(Q(blacklisted='N')),
                    widget=forms.Select(attrs={'class': 'form-control'}),
                    empty_label="Select a Broker")
    remarks = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'class': 'form-control', 'oninput': 'this.value=this.value.toUpperCase();'}))

    # SHIPPING LINE AND VESSEL DETAILS

    # mode_of_transportation = forms.CharField(required=False, widget=forms.Select(attrs={'class': 'form-control'}))

    shippingline_name = forms.ModelChoiceField(required=False,
                                               queryset=Shippinglinemaster.objects.using('firebird').all().order_by(
                                                   'shippinglinename'),
                                               widget=forms.Select(attrs={'class': 'form-control',
                                                                          'data-url': reverse_lazy(
                                                                              'logisticsexport:get-vessel-voyage')}),
                                               empty_label="Select a Shipping Line")

    allowed_free_days = forms.CharField(required=False,
                                        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))

    vessel = forms.CharField(required=False, widget=forms.Select(attrs={'class': 'form-control',
                                                                        'data-url': reverse_lazy(
                                                                            'logisticsexport:get-vessel-voyage')}))

    voyage = forms.CharField(required=False, widget=forms.Select(attrs={'class': 'form-control',
                                                                        'data-url': reverse_lazy(
                                                                            'logisticsexport:get-vessel-voyage')}))
    etd = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                          widget=forms.DateInput(attrs={'class': 'odate form-control pull-right vesseldates',
                                                        'data-date-format': "dd/mm/yyyy", 'disabled': 'disabled'}))
    # cm_date = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
    # widget=forms.DateInput(attrs={'class': 'form-control pull-right',
    # 'data-date-format': "dd/mm/yyyy"}))
    actual_departure = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                                       widget=forms.DateInput(
                                           attrs={'class': 'odate form-control pull-right vesseldates',
                                                  'data-date-format': "dd/mm/yyyy", 'disabled': 'disabled'}))
    stack_closing = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                                    widget=forms.DateInput(attrs={'class': 'odate form-control pull-right vesseldates',
                                                                  'data-date-format': "dd/mm/yyyy",
                                                                  'disabled': 'disabled'}))
    clearance_deadline = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                                         widget=forms.DateInput(
                                             attrs={'class': 'odate form-control pull-right vesseldates',
                                                    'data-date-format': "dd/mm/yyyy", 'disabled': 'disabled'}))
    port_storage_starts = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                                          widget=forms.DateInput(
                                              attrs={'class': 'odate form-control pull-right vesseldates',
                                                     'data-date-format': "dd/mm/yyyy", 'disabled': 'disabled'}))
    # Document Details

    booking_received = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                                       initial=datetime.datetime.now().strftime("%d/%m/%Y"),
                                       widget=forms.DateInput(attrs={'class': 'odate form-control pull-right',
                                                                     'data-date-format': "dd/mm/yyyy"}))

    forwarding_agent = forms.ModelChoiceField(required=False, queryset=Forwardingagentmaster.objects.using('firebird').
                                              filter(agentblacklisted='N'),
                                              widget=forms.Select(attrs={'class': 'form-control'}),
                                              empty_label="Select Forwarding Agent")

    submitted_fa = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                                   initial=datetime.datetime.now().strftime("%d/%m/%Y"),
                                   widget=forms.DateInput(attrs={'class': 'odate form-control pull-right',
                                                                 'data-date-format': "dd/mm/yyyy"}))
    cleared_agent_name = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                                         initial=datetime.datetime.now().strftime("%d/%m/%Y"),
                                         widget=forms.DateInput(attrs={'class': 'odate form-control pull-right',
                                                                       'data-date-format': "dd/mm/yyyy"}))
    nde_tax = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS,
                              initial=datetime.datetime.now().strftime("%d/%m/%Y"),
                              widget=forms.DateInput(attrs={'class': 'odate form-control pull-right',
                                                            'data-date-format': "dd/mm/yyyy"}))
    edit_orderreference = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        self.action_type = kwargs.pop("action_type", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(AddExportOrderForm, self).clean()

        return self.cleaned_data

    # Main Entry Details.

    def check1(self):
        cleaned_data = super(AddExportOrderForm, self).clean()

        entry_date = cleaned_data.get('entry_date')
        customer_name = cleaned_data.get('customer_name')
        invoice_party_name = cleaned_data.get('invoice_party_name')
        # invoice_currency = cleaned_data.get('invoice_currency')
        origin = cleaned_data.get('origin')
        loading_point = cleaned_data.get('loading_point')
        destination = cleaned_data.get('destination')
        commodity = cleaned_data.get('commodity')
        cargo_type = cleaned_data.get('cargo_type')
        packing_unit = cleaned_data.get('packing_unit')
        quantity = cleaned_data.get('quantity')
        clearing_agent = cleaned_data.get('clearing_agent')
        port_agent = cleaned_data.get('port_agent')
        broker = cleaned_data.get('broker')
        username = self.request.user.username
        temp_container_reference = "*" * (14 - len(username)) + "{0}".format(username)

        if entry_date and entry_date > datetime.datetime.now().date():
            raise forms.ValidationError({'entry_date': "Cannot select future date."})

        if not customer_name:
            self.add_error('customer_name', _('Please select a Customer.'))

        if not invoice_party_name:
            self.add_error('invoice_party_name', _('Please select an Invoice Party.'))

        # if not invoice_currency:
        # self.add_error('invoice_currency', _('Please select currency.'))

        if not origin:
            self.add_error('origin', _('Please select Origin.'))

        if not loading_point:
            self.add_error('loading_point', _('Please select Loading Point.'))

        if not destination:
            self.add_error('destination', _('Please select Destination.'))

        if destination and origin and destination == origin:
            if origin.locationcode != '000000' or destination.locationcode != '000000':
                self.add_error('origin',
                               _('ORIGIN and DESTINATION should not be the same, please select another Origin.'))
                self.add_error('destination_',
                               _('ORIGIN and DESTINATION should not be the same, please select another Destination.'))

        if not commodity:
            self.add_error('commodity', _('Please select a Commodity.'))

        if not cargo_type:
            self.add_error('cargo_type', _('Please select Cargo Type.'))
        if not clearing_agent:
          self.add_error('clearing_agent',_('Please select Border Clearing Agent'))
        if not port_agent:
          self.add_error('port_agent',_('Please select Port Agent'))

        if not broker:
          self.add_error('broker',_('Please select Broker'))
        # else:
        #   if broker.effectiveto < datetime.datetime.now().date():
        #     self.add_error('broker',_('Broker validity Expired'))

        if cargo_type and cargo_type.cargotypecode == 1:
            containers = Logisticscontainerdetails.objects.using('firebird').filter(
                logisticreference=temp_container_reference)
        # if not containers.exists():
        # self.add_error('cargo_type', _('Please add atleast 1 container.'))

        if cargo_type and cargo_type.cargotypecode == 4:
            if commodity and (commodity.liquidtype == 'N' and commodity.mixedload == 'N'):
                self.add_error('commodity', _('Please select liquid type commodity or mixed load.'))

        if cargo_type and cargo_type.cargotypecode == 2:
            if not packing_unit:
                self.add_error('packing_unit', _('Please select a packing unit.'))
            if quantity and quantity <= 0:
                self.add_error('quantity', _('Please enter the quantity.'))
            if commodity.commoditycode == '000002':
                self.add_error('commodity', _('You cannot select container commodity in Breakbulk cargo.'))

        return self.cleaned_data

    # SHIPPING LINE AND VESSEL DETAILS

    def check2(self):
        cleaned_data = super(AddExportOrderForm, self).clean()
        shippingline_name = cleaned_data.get('shippingline_name')
        vessel = cleaned_data.get('vessel')
        voyage = cleaned_data.get('voyage')
        etd = cleaned_data.get('etd')
        actual_departure = cleaned_data.get('actual_departure')
        stack_closing = cleaned_data.get('stack_closing')
        clearance_deadline = cleaned_data.get('clearance_deadline')

        if not shippingline_name:
            self.add_error('shippingline_name', _('Please select a Shipping Line.'))

        if not vessel:
            self.add_error('vessel', _('Please select a Vessel.'))

        if not voyage:
            self.add_error('voyage', _('Please select Voyage date.'))

        if not etd:
            self.add_error('etd', _('Please select ETD.'))

        if not actual_departure:
            self.add_error('actual_departure', _('Please select Actual departure.'))

        if not stack_closing:
            self.add_error('stack_closing', _('Please select Stack closing.'))

        if not clearance_deadline:
            self.add_error('clearance_deadline', _('Please select Clearance Deadline.'))

        return self.cleaned_data

    # Document Details

    def check3(self):
        cleaned_data = super(AddExportOrderForm, self).clean()
        entry_date = cleaned_data.get('entry_date')
        booking_received = cleaned_data.get('booking_received')
        forwarding_agent = cleaned_data.get('forwarding_agent')
        submitted_fa = cleaned_data.get('submitted_fa')
        cleared_agent_name = cleaned_data.get('cleared_agent_name')
        document_taxed = cleaned_data.get('nde_tax')
        duty_confirmed = cleaned_data.get('cleared_agent_name')
        # import pdb;pdb.set_trace()
        if booking_received and booking_received > datetime.datetime.now().date():
          self.add_error('booking_received', _('Future ates are not allowed'))
        if booking_received and entry_date > booking_received:
          self.add_error('booking_received', _('Booking received date cannot be less than Order date'))

        if submitted_fa and not forwarding_agent:
          self.add_error('forwarding_agent', _('Please select a Forwarding Agent.'))
        if forwarding_agent and not submitted_fa:
          self.add_error('forwarding_agent', _('Please select Forwarding Agent submitted date.'))

        if submitted_fa and not booking_received:
          self.add_error('submitted_fa', _('Plase Update Document received Date First.'))

        if booking_received and submitted_fa and booking_received  > submitted_fa:
          self.add_error('submitted_fa', _('Submitted date cannot be less than Document received Date.'))

        if cleared_agent_name and not submitted_fa:
          self.add_error('cleared_agent_name', _('Plase Update Submitted Date First.'))

        if submitted_fa and cleared_agent_name and submitted_fa  > cleared_agent_name:
          self.add_error('cleared_agent_name', _('Cleared date cannot be less than Submitted received Date.'))

        if document_taxed and not cleared_agent_name:
          self.add_error('nde_tax', _('Plase Update Cleared Date First.'))

        if cleared_agent_name and document_taxed and cleared_agent_name  > document_taxed:
          self.add_error('nde_tax', _('Taxed date cannot be less than Cleared Date.'))

        return self.cleaned_data

    def save(self):
        data = self.cleaned_data
        con = get_fb_conn()
        cur = con.cursor()
        status_code = '0039'
        transporter_code = self.request.session['transporter_access']
        username = self.request.user.username
        temp_order_reference = "*" * (14 - len(username)) + "{0}".format(username)

        # Main Entry Details.
        # lst_p = (temp_order_reference,data['entry_date'],'1',transporter_code,data['customercode'],data['consigneecode'],data['invoice_partycode'],data['origin'].locationcode,data['loading_point'],data['destination'].locationcode,data['offloading_point'],data['commodity'].commoditycode,None if data['remarks'] == '' else data['remarks'],None if data['client_reference'] == '' else data['client_reference'],None if data['blnumber'] == '' else data['blnumber'],int(data['cargo_type'].cargotypecode),0 if data['container_20'] is None else int(data['container_20']),0 if data['container_40'] is None else int(data['container_40']),0 if data['weight'] is None else data['weight'],0 if data['tonnage'] is None else data['tonnage'],None if data['cargo_details_ref'] == '' else data['cargo_details_ref'],None if data['report_comments'] == '' else data['report_comments'],None if data['border_entry'] == '' else data['border_entry'],None,None,data['port_of_entry'] if data['port_of_entry']  else None,'N',None,None,None,None,'N',data['clearing_agent'] if data['clearing_agent'] else None,None,None,data['shippingline_name'].shippinglinecode if data['shippingline_name'] else None,data['vessel'],int(data['allowed_free_days']) if data['allowed_free_days'] else 0,str(data['voyage']),None,None,None,None,None,None,data['booking_received'],username if data['booking_received'] else None,datetime.datetime.now() if data['booking_received'] else None,None,None,None,None,None,None,None,None,None,data['forwarding_agent'].forwardingagentcode if data['forwarding_agent']  else None,username if data['forwarding_agent'] else None,datetime.datetime.now() if data['forwarding_agent'] else None,username if data['submitted_fa'] else None,datetime.datetime.now() if data['submitted_fa'] else None,data['cleared_agent_name'] if data['cleared_agent_name'] else None,username if data['cleared_agent_name'] else None,datetime.datetime.now() if data['cleared_agent_name'] else None,data['nde_tax'] if data['nde_tax'] else None ,username if data['nde_tax'] else None,datetime.datetime.now() if data['nde_tax'] else None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,status_code,username,username,datetime.datetime.now().date(),'0','0','N',None,None,None,None,None,None,'N','N',username if status_code else None,datetime.datetime.now() if status_code else None,username if data['cargo_details_ref'] else None,datetime.datetime.now() if data['cargo_details_ref'] else None,username if data['report_comments'] else None,datetime.datetime.now() if data['report_comments'] else None,username,'E',data['port_agent'].agentcode if data['port_agent'] else None,data['packing_unit'].unitcode if data['packing_unit'] else None,data['submitted_fa'] if data['submitted_fa'] else None,data['etd'] if data['etd'] else None,data['actual_departure'] if data['actual_departure'] else None,data['stack_closing'] if data['stack_closing'] else None,data['clearance_deadline'] if data['clearance_deadline'] else None,data['declaration_no'],data['broker'].brokercode if data['broker'] else None,self.action_type,data['edit_orderreference'])
        if data['booking_received']:
          status_code = '0040'
        if data['submitted_fa']:
          status_code = '0041'
        if data['cleared_agent_name']:
          status_code = '0042'
        if data['nde_tax']:
          status_code = '0043'
        cur.callproc("DBPROCSAVELOGISTICSENTRY",
                     (temp_order_reference,
                         data['entry_date'],
                         '1',
                         transporter_code,
                         data['customercode'],
                         data['consigneecode'],
                         data['invoice_partycode'],
                         data['origin'].locationcode,
                         data['loading_point'],
                         data['destination'].locationcode,
                         data['offloading_point'],
                         data['commodity'].commoditycode,
                         None if data['remarks'] == '' else data['remarks'],
                         None if data['client_reference'] == '' else data['client_reference'],
                         None if data['blnumber'] == '' else data['blnumber'],
                         int(data['cargo_type'].cargotypecode),
                         0 if data['container_20'] is None else int(data['container_20']),
                         0 if data['container_40'] is None else int(data['container_40']),
                         0 if data['weight'] is None else data['weight'],
                         0 if data['tonnage'] is None else data['tonnage'],
                         None if data['cargo_details_ref'] == '' else data['cargo_details_ref'],
                         None if data['report_comments'] == '' else data['report_comments'],
                         None if data['border_entry'] == '' else data['border_entry'],
                         None,
                         None,
                         data['port_of_entry'] if data['port_of_entry']  else None,
                         'N',
                         None,
                         None,
                         None,
                         None,
                         'N',
                         data['clearing_agent'] if data['clearing_agent'] else None,
                         None,
                         None,
                         data['shippingline_name'].shippinglinecode if data['shippingline_name'] else None,
                         data['vessel'],
                         int(data['allowed_free_days']) if data['allowed_free_days'] else 0,
                         str(data['voyage']),
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         data['booking_received'],
                         username if data['booking_received'] else None,
                         datetime.datetime.now() if data['booking_received'] else None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         data['forwarding_agent'].forwardingagentcode if data['forwarding_agent']  else None,
                         username if data['forwarding_agent'] else None,
                         datetime.datetime.now() if data['forwarding_agent'] else None,
                         username if data['submitted_fa'] else None,
                         datetime.datetime.now() if data['submitted_fa'] else None,
                         data['cleared_agent_name'] if data['cleared_agent_name'] else None,
                         username if data['cleared_agent_name'] else None,
                         datetime.datetime.now() if data['cleared_agent_name'] else None,
                         data['nde_tax'] if data['nde_tax'] else None ,
                         username if data['nde_tax'] else None,
                         datetime.datetime.now() if data['nde_tax'] else None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         status_code,
                         username,
                         username,
                         datetime.datetime.now().date(),
                         '0',
                         '0',
                         'N',
                         None,
                         None,
                         None,
                         None,
                         None,
                         None,
                         'N',
                         'N',
                         username if status_code else None,
                         datetime.datetime.now() if status_code else None,
                         username if data['cargo_details_ref'] else None,
                         datetime.datetime.now() if data['cargo_details_ref'] else None,
                         username if data['report_comments'] else None,
                         datetime.datetime.now() if data['report_comments'] else None,
                         username,
                         'E',
                         data['port_agent'].agentcode if data['port_agent'] else None,
                         data['packing_unit'].unitcode if data['packing_unit'] else None,
                         data['submitted_fa'] if data['submitted_fa'] else None,
                         data['etd'] if data['etd'] else None,
                         data['actual_departure'] if data['actual_departure'] else None,
                         data['stack_closing'] if data['stack_closing'] else None,
                         data['clearance_deadline'] if data['clearance_deadline'] else None,
                         data['declaration_no'],
                         data['broker'].brokercode if data['broker'] else None,
                         self.action_type,
                         data['edit_orderreference']
                     )
                     )
        outputParams = cur.fetchone()
        con.commit()
        return outputParams[0] if outputParams else None

    # Container Entry


class ContainerEntryForm(forms.Form):
    order_number = forms.CharField(required=True)
    container_type = forms.IntegerField(required=True)
    container_tare = forms.DecimalField(required=True)
    quantity = forms.IntegerField(required=True)
    net_weight = forms.DecimalField(required=True)
    gross_weight = forms.DecimalField(required=True, min_value=0.01)
    load_type = forms.CharField(required=True)
    container_no = forms.CharField(required=True)
    seal_no = forms.CharField(required=False)
    reefer_temp = forms.CharField(required=False)
    genset_required = forms.CharField(required=False)
    fuel_supply = forms.CharField(required=False)
    dropoffatdestination = forms.CharField(required=False)
    shipper_owned = forms.CharField(required=False)
    remarks = forms.CharField(required=False)
    empty_dropoff = forms.CharField(required=False)
    empty_depot = forms.CharField(required=False)
    grounding_reference = forms.CharField(required=False)
    validity_date = forms.DateField(required=False, input_formats=settings.DATE_INPUT_FORMATS)
    place_holder = forms.CharField(required=False)
    action_type = forms.CharField(required=True)
    slno = forms.IntegerField(required=True)
    soc = forms.CharField(required=False)
    weightinkg = forms.CharField(required=False)
    edit_order_ref = forms.CharField(widget=forms.HiddenInput(), required=False)
    created_tostation = forms.CharField(widget=forms.HiddenInput(), required=False)
    created_tostation_depot = forms.CharField(widget=forms.HiddenInput(), required=False)
    commodity_code = forms.CharField(widget=forms.HiddenInput(), required=False)

    # conatiner unpack fields
    packingname = forms.CharField(required=False)
    cargotypecode = forms.CharField(required=True)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(ContainerEntryForm, self).clean()
        container_no = cleaned_data.get('container_no')
        type = cleaned_data.get('action_type')
        edit_order_ref = cleaned_data.get('edit_order_ref')
        place_holder = cleaned_data.get('place_holder')
        load_type = cleaned_data.get('load_type')
        Shipperowned = cleaned_data.get('dropoffatdestination')
        soc = cleaned_data.get('soc')
        remarks = cleaned_data.get('remarks')
        empty_dropoff = cleaned_data.get('empty_dropoff')
        net_weight = cleaned_data.get('net_weight')
        grossweight = cleaned_data.get('gross_weight')
        created_tostation = cleaned_data.get('created_tostation')
        created_tostation_depot = cleaned_data.get('created_tostation_depot')
        commodity_code = cleaned_data.get('commodity_code')

        username = self.request.user.username.strip()
        temp_order_reference = "*" * (14 - len(username)) + "{0}".format(username)
        if type == 'I':
            if Shipperowned != 'Y' and soc != 'Y':
                if created_tostation == empty_dropoff:
                    raise forms.ValidationError({'remarks': _(
                        'Selected Container Drop off point is order destination. Please mark either SOC or Dropoff at destination')})
            if not place_holder:
                if (Logisticscontainerdetails.objects.using('firebird').filter(logisticreference=temp_order_reference,
                                                                               containerreference=container_no).exists()):
                    raise forms.ValidationError({'remarks': _('Container number already exists.Please check ')})
        if type == 'E':
            if Shipperowned != 'Y' and soc != 'Y':
                if created_tostation == empty_dropoff:
                    raise forms.ValidationError({'remarks': _(
                        'Selected Container Drop off point is order destination. Please mark either SOC or Dropoff at destination')})
            if not place_holder:
                if (Logisticscontainerdetails.objects.using('firebird').filter(logisticreference=temp_order_reference,
                                                                               containerreference=container_no).count() > 1):
                    raise forms.ValidationError({'remarks': _('Container number already exists.Please check ')})
        if edit_order_ref:
            if not place_holder:
                if (Logisticscontainerdetails.objects.using('firebird').filter(logisticreference=edit_order_ref,
                                                                               containerreference=container_no).exists()):
                    raise forms.ValidationError({'remarks': _('Container number already exists.Please check ')})
            temptostationcode = Logisticentry.objects.using('firebird').filter(logisticreference=edit_order_ref)[
                0].tostationcode.locationcode
            if Shipperowned != 'Y' and soc != 'Y':
                if temptostationcode == empty_dropoff:
                    raise forms.ValidationError({'remarks': _(
                        'Selected Container Drop off point is order destination. Please mark either SOC or Dropoff at destination')})
        if load_type == 'CO-LOAD' and remarks == '':
            raise forms.ValidationError({'remarks': _('Remarks is mandatory for CO-LOAD')})
        if (commodity_code != '000002' and net_weight == 0):
            raise forms.ValidationError({'net_weight': _('Net weight cannot be 0')})
        if grossweight > 32:
            raise forms.ValidationError({'remarks': _('You cannot add container having more than 32 ton gross weight')})
        if not place_holder:
            if not re.match(r"^[A-Z]{4}\d{7}$", container_no):
                raise forms.ValidationError(
                    {'container_no': _('Container number should start with 4 Capital letters and end with 7 digits')})
            if container_no.startswith('YYYY'):
                raise forms.ValidationError(
                    {'container_no': _('Container number should not start with place holder prefix (YYYY)')})
        else:
            cleaned_data['container_no'] = ' '
        return self.cleaned_data

    def save(self):
        data = self.cleaned_data
        con = get_fb_conn()
        cur = con.cursor()
        username = self.request.user.username.strip()
        temp_order_reference = "*" * (14 - len(username)) + "{0}".format(username)

        cur.callproc("DBPROCSAVELOGISTICSCONTDETAILS",
                     (temp_order_reference,
                      self.request.session['transporter_access'],
                      data['container_type'],
                      data['container_no'],
                      data['quantity'],
                      data['container_tare'],
                      data['net_weight'],
                      data['gross_weight'],
                      None if data['empty_dropoff'] == '' else data['empty_dropoff'],
                      None if data['empty_depot'] == '' else data['empty_depot'],
                      0 if data['soc'] == 'Y' or data['dropoffatdestination'] == 'Y' else 1,
                      data['load_type'],
                      data['seal_no'],
                      data['reefer_temp'],
                      'N' if data['genset_required'] == '' else data['genset_required'],
                      'N' if data['fuel_supply'] == '' else data['fuel_supply'],
                      'N' if data['soc'] == '' else data['soc'],
                      data['grounding_reference'],
                      data['validity_date'],
                      data['remarks'],
                      data['place_holder'],
                      username,
                      data['action_type'],
                      data['slno'],
                      'N' if data['dropoffatdestination'] == '' else data['dropoffatdestination'],
                      data['weightinkg'],
                      data['packingname'],
                      data['cargotypecode']
                      )
                     )
        outputParams = cur.fetchone()
        con.commit()
        return outputParams[0] if outputParams else None
