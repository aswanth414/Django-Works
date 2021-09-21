from django.conf.urls import url
#from fms.utils.decorators import transporter_login_required,
from django.contrib.auth.decorators import login_required
from apps.customer_management import views

app_name = 'customer_management'

urlpatterns = [
    url(r'^$', login_required(views.CustomerManagementView.as_view()), name='customer_management-list'),
    url(r'^customer_management_grid/$', login_required(views.customerManagementGrid.as_view()), name='customer_management_grid'),

]