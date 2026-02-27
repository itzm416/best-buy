from django.contrib import admin

from shop.models import CustomerInformation, Product, Cart, OrderPlaced, OrderItem

# Register your models here.
admin.site.register(OrderItem)

@admin.register(CustomerInformation)
class CustomerModelAdmin(admin.ModelAdmin):
    list_display=['user_email','name','mobile_number','locality','city','zipcode','state']

@admin.register(Product)
class ProductModelAdmin(admin.ModelAdmin):
    list_display=['title','selling_price','discounted_price','description','brand','category','product_image']

@admin.register(Cart)
class CartModelAdmin(admin.ModelAdmin):
    list_display=['user','product','quantity']


@admin.register(OrderPlaced)
class OrderPlacedModelAdmin(admin.ModelAdmin):
    list_display=['user','customer_information','ordered_date','status','total_amount','is_paid']
