from django.shortcuts import render, redirect
from shop.models import Product, Cart, CustomerInformation, OrderPlaced, OrderItem
from authenticationapp.models import User
from shop.forms import CustomerInformationForm
import razorpay
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
import json
from django.contrib.auth.decorators import login_required

client=razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def home(request):

    category_list = [
        ('Mobiles', '/static/images/categories/mobile.jpg'),
        ('Laptops', '/static/images/categories/laptop.jpg'),
        ('Accessories', '/static/images/categories/accessories.jpg'),
        ('Electronics', '/static/images/categories/electronics.jpg'),
        # ('Fashion', '/static/images/categories/fashion.jpg'),
        # ('Beauty', '/static/images/categories/beauty.jpg'),
    ]

    # Prepare a dictionary to hold random products for each category
    category_products = {}
    for category, img in category_list:
        products = Product.objects.filter(category=category).order_by('?')[:5]  # random 5 products
        category_products[category] = products

    context={
        'category_list': category_list,
        'category_products': category_products
    }

    return render(request, 'home.html', context)

def product_detail(request,slug):
    try:
        product=Product.objects.get(slug=slug)

        # Get related products in the same category, excluding the current product, random order
        related_products = Product.objects.filter(
        category=product.category
        ).exclude(id=product.id).order_by('?')[:4]  # limit to 4 random products

    except Exception as e:
        pass

    context={
        'product':product,
        'related_products':related_products
    }
    return render(request, 'product.html', context)

def category_products(request, category):
    # Start with all products of this category
    products = Product.objects.filter(category=category)

    # Filter by brand if user clicked a brand
    selected_brand = request.GET.get('brand')
    if selected_brand:
        products = products.filter(brand=selected_brand)

    # Filter by price if user clicked a price range
    selected_price = request.GET.get('price')
    if selected_price:
        min_price, max_price = map(int, selected_price.split('-'))
        products = products.filter(discounted_price__gte=min_price, discounted_price__lte=max_price)

    # For filter buttons: unique brands in this category
    brands = Product.objects.filter(category=category).values_list('brand', flat=True).distinct()
    # Define price ranges in view
    price_ranges = [
        '0-1000',
        '1000-10000',
        '10000-20000',
        '20000-30000',
    ]

    context = {
        'products': products,
        
        'brands': brands,
        'price_ranges': price_ranges,

        'selected_brand': selected_brand,
        'selected_price': selected_price,
    }
    return render(request, 'category_products.html', context)

@login_required
def add_to_cart(request):
    # If any query parameters exist → remove them
    user=User.objects.get(email=request.user.email)
    
    check_slug = request.GET.get('slug')
    if check_slug:
        product=Product.objects.get(slug=check_slug)
        cart=Cart(user=user,product=product)
        cart.save()

    if request.GET:
        return redirect('add_to_cart')
    
    # Calculate Total Amount
    cart_items= Cart.objects.filter(user=user)
    total_amount = 0
    for item in cart_items:
        total_amount += item.product.discounted_price * item.quantity

    context={
        'cart_items':cart_items,
        'total_amount': total_amount
    }

    return render(request, 'cart.html', context)

@login_required
def update_quantity(request, cart_id):
    user=User.objects.get(email=request.user.email)
    cart_item= Cart.objects.get(id=cart_id,user=user)

    action = request.GET.get('action')

    if action == 'increase':
        cart_item.quantity += 1

    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1

    cart_item.save()
    return redirect('add_to_cart')  # redirect back to cart pag

@login_required
def delete_item(request, cart_id):
    user=User.objects.get(email=request.user.email)
    cart_item= Cart.objects.get(id=cart_id,user=user)
    cart_item.delete()
    return redirect('add_to_cart')  # redirect back to cart pag

@login_required
@csrf_exempt
def checkout(request):
    user = request.user
    # Get saved addresses of logged-in user
    customer_info = CustomerInformation.objects.filter(user_email=user)
    cart_items = Cart.objects.filter(user=user)

    # Calculate total amount
    total_amount = 0
    for item in cart_items:
        total_amount += item.product.discounted_price * item.quantity

    if request.method == "POST":
        data = json.loads(request.body)
        customer_id = data.get("customer_id")
        checkout_customer=CustomerInformation.objects.get(pk=customer_id)

        order_data={
            "amount":int(total_amount*100),
            "currency":"INR",
            "payment_capture":"1",
             # Optional but very useful
            "notes": {
            "customer_id": checkout_customer.id,
            "user_email": "user@gmail.com",
            }
        }
        razorpay_order=client.order.create(order_data)

        place_order = OrderPlaced(
        user=request.user,
        customer_information=checkout_customer,
        status='Pending',
        total_amount=total_amount,
        razorpay_order_id=razorpay_order['id'],
        )

        place_order.save()
        order_id = place_order
        
        for item in cart_items:
            item_amount=item.product.discounted_price*item.quantity
            OrderItem.objects.create(order=order_id,product=item.product,quantity=item.quantity,amount=item_amount)
        
        return JsonResponse({
            "order_id":razorpay_order["id"],
            "razorpay_key_id":settings.RAZORPAY_KEY_ID,
            "user_email":request.user.email,
            "amount":order_data["amount"],
            "razorpay_callback_url":settings.RAZORPAY_CALLBACK_URL
        })


    context = {
        "customer_info": customer_info,
        "cart_items": cart_items,
        "total_amount": total_amount,
    }

    return render(request, 'checkout.html', context)

@login_required
@csrf_exempt
def payment_callback(request):
    if request.method == "POST":
        if "razorpay_signature" in request.POST:
            order_id = request.POST.get("razorpay_order_id")
            payment_id = request.POST.get("razorpay_payment_id")
            signature = request.POST.get("razorpay_signature")

            order=get_object_or_404(OrderPlaced,razorpay_order_id=order_id)

            if client.utility.verify_payment_signature({
                'razorpay_order_id':order_id,
                'razorpay_payment_id':payment_id,
                'razorpay_signature':signature
            }):
                order.razorpay_payment_id=payment_id
                order.razorpay_signature=signature
                order.is_paid=True
                order.save()
                return render(request, "payment_verified.html", {"order": order})
            else:
                order.is_paid=False
                order.save()
                return render(request, "payment_failed.html", {"order": order})
    return redirect('home')

@login_required
def add_customer_information(request):
    if request.method == "POST":
        form = CustomerInformationForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.user_email = request.user  # auto assign user
            customer.save()
            return redirect("checkout")  # change as needed
    else:
        form = CustomerInformationForm()

    return render(request, "customer_information.html", {"form": form})



