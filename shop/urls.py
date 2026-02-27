from shop import views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<slug:slug>/', views.product_detail, name='product'),
    path('category-products/<str:category>/', views.category_products, name='category-products'),
    path('cart/', views.add_to_cart, name='add_to_cart'),
    path('update-quantity/<int:cart_id>/', views.update_quantity, name='update_quantity'),
    path('delete-item/<int:cart_id>/', views.delete_item, name='delete_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment-verify/', views.payment_callback, name='paymengt_verify'),
    path('customer-info/', views.add_customer_information, name='customer_info'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
