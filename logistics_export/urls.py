from django.conf.urls import url, include
from fms.utils.decorators import transporter_login_required
from apps.logistics.logistics_export import views

app_name = 'logisticsexport'

urlpatterns = [
    url(r'^export/$', transporter_login_required(views.ExportOrderListView.as_view()), name='export-list'),
    url(r'^export-grid/$', transporter_login_required(views.ExportOrderGridView.as_view()), name='export-grid'),
    url(r'^export-add/$', transporter_login_required(views.ExportOderCreateView.as_view()), name='add-export-order'),
    url(r'^export-edit/$', transporter_login_required(views.ExportOrderEditView.as_view()), name='edit-export-order'),
    url(r'^order-validate/$', transporter_login_required(views.ExportOrderValidate.as_view()),name='export_order-validate'),
    url(r'^check-distance/$', transporter_login_required(views.CheckDistanceView.as_view()), name='check-distance'),
    url(r'^customers-list/$', transporter_login_required(views.CustomerAjaxListView.as_view()), name='customers-list'),
    url(r'^container-details/$', transporter_login_required(views.ContainerEntryDetailsView.as_view()),name='container-details'),
    url(r'^container-entry-endpoint/$', transporter_login_required(views.ContainerEntrySaveView.as_view()),name='container-entry-endpoint'),

    url(r'^container-entry-delete/$', transporter_login_required(views.ContainerEntryDeleteView.as_view()),name='container-entry-delete'),
    url(r'^container-export/$', transporter_login_required(views.ContainerExport), name='container-export'),
    # container unpacking
    url(r'^containerunpack-entry-endpoint/$', transporter_login_required(views.ContainerUnpackSaveView.as_view()), name='containerunpack-entry-endpoint'),

    url(r'^logisticsexports-export/$', transporter_login_required(views.ExportsExportListView),name='logisticsexports-export'),
    url(r'^get_depot_address/', transporter_login_required(views.GetDepotAddressView.as_view()),name='get_depot_address'),

    url(r'^get-vessel-voyage/$', transporter_login_required(views.GetVoyageAjaxView.as_view()),name='get-vessel-voyage'),
    url(r'^logisticsexports-cancel/$', transporter_login_required(views.ExportsCancelAjaxView.as_view()),name='logisticsexports-cancel'),

    url(r'^logisticsexports_book_rec_date/$', transporter_login_required(views.UpdateDatesAjaxView.as_view()),name='logisticsexports_book_rec_date'),
    url(r'^logisticsexports_nde_taxed_date/$', transporter_login_required(views.UpdateNdeTaxedAjaxView.as_view()),name='logisticsexports_nde_taxed_date'),
    url(r'^logisticsexports_w7_date/$', transporter_login_required(views.UpdateWDateAjaxView.as_view()),name='logisticsexports_w7_date'),
    url(r'^logisticsexports_t8_date/$', transporter_login_required(views.UpdateTDateAjaxView.as_view()),name='logisticsexports_t8_date'),
    url(r'^logisticsexports_kudumba_date/$', transporter_login_required(views.UpdateKudumbaAjaxView.as_view()),name='logisticsexports_kudumba_date'),
    url(r'^logisticsexports_port_booking/$', transporter_login_required(views.UpdatePortBookingAjaxView.as_view()),name='logisticsexports_port_booking'),
    url(r'^logisticsexports_sob_date/$', transporter_login_required(views.UpdateSobDateAjaxView.as_view()),name='logisticsexports_sob_date'),
    url(r'^logisticsexports_stack_order/$', transporter_login_required(views.UpdateStackOrderAjaxView.as_view()),name='logisticsexports_stack_order'),
    url(r'^logisticsexports_sub_clr/$', transporter_login_required(views.UpdateSubmitClearedDatesAjaxView.as_view()),name='logisticsexports_sub_clr'),
    url(r'^view_import_details/$', transporter_login_required(views.ShowAlldataAjaxView.as_view()),name='view_import_details'),

]
