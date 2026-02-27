from django.db import models
from authenticationapp.models import User
from autoslug import AutoSlugField

# Lookup = O(log n) (fast)
# Without index = O(n) (slow scan)
# Now database creates a B-Tree index (like a sorted lookup table).
# fast filtering

STATE_CHOICES = (
    ('AN', 'Andaman and Nicobar Islands'),
    ('AP', 'Andhra Pradesh'),
    ('AR', 'Arunachal Pradesh'),
    ('AS', 'Assam'),
    ('BR', 'Bihar'),
    ('CG', 'Chhattisgarh'),
    ('CH', 'Chandigarh'),
    ('DN', 'Dadra and Nagar Haveli and Daman and Diu'),
    ('DL', 'Delhi'),
    ('GA', 'Goa'),
    ('GJ', 'Gujarat'),
    ('HR', 'Haryana'),
    ('HP', 'Himachal Pradesh'),
    ('JK', 'Jammu and Kashmir'),
    ('JH', 'Jharkhand'),
    ('KA', 'Karnataka'),
    ('KL', 'Kerala'),
    ('LA', 'Ladakh'),
    ('LD', 'Lakshadweep'),
    ('MP', 'Madhya Pradesh'),
    ('MH', 'Maharashtra'),
    ('MN', 'Manipur'),
    ('ML', 'Meghalaya'),
    ('MZ', 'Mizoram'),
    ('NL', 'Nagaland'),
    ('OR', 'Odisha'),
    ('PB', 'Punjab'),
    ('PY', 'Puducherry'),
    ('RJ', 'Rajasthan'),
    ('SK', 'Sikkim'),
    ('TN', 'Tamil Nadu'),
    ('TG', 'Telangana'),
    ('TR', 'Tripura'),
    ('UP', 'Uttar Pradesh'),
    ('UK', 'Uttarakhand'),
    ('WB', 'West Bengal'),
)



class CustomerInformation(models.Model):
    user_email = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    mobile_number = models.CharField(max_length=15)
    locality = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    zipcode = models.IntegerField()
    state = models.CharField(max_length=2, choices=STATE_CHOICES)

    def __str__(self):
        return str(self.name)

CATEGORY_CHOICE = (
    ('Mobiles', 'Mobiles'),
    ('Laptops', 'Laptops'),
    ('Accessories', 'Accessories'),
    ('Electronics', 'Electronics'),
    ('Fashion', 'Fashion'),
    ('Beauty', 'Beauty'),
)

class Product(models.Model):
    title = models.CharField(max_length=100, db_index=True)

    slug = AutoSlugField(
        populate_from='title',
        unique=True,
        always_update=False,
        db_index=True
    )

    selling_price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2)

    description = models.TextField()
    brand = models.CharField(max_length=100, db_index=True)

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICE,
        db_index=True    
    )

    product_image = models.ImageField(upload_to='productimg')
    created_at = models.DateTimeField(auto_now_add=True)  # good for sorting
    
    def __str__(self):
        return self.title

class Cart(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    product=models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity=models.PositiveIntegerField(default=1)

    def __str__(self):
        return str(self.id)


STATUS_CHOICE=(
    ('Accepted','Accepted'),
    ('Packed','Packed'),
    ('Pending','Pending'),
    ('On The Way','On The Way'),
    ('Delivered','Delivered'),
    ('Cancel','Cancel')
)

class OrderPlaced(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    customer_information=models.ForeignKey(CustomerInformation, on_delete=models.CASCADE)
    ordered_date=models.DateTimeField(auto_now_add=True)
    
    status=models.CharField(max_length=50,choices=STATUS_CHOICE)
    total_amount=models.DecimalField(max_digits=10, decimal_places=2)
    
    razorpay_order_id=models.CharField(max_length=255,blank=True, null=True)
    razorpay_payment_id=models.CharField(max_length=255,blank=True, null=True)
    razorpay_signature=models.CharField(max_length=255,blank=True, null=True)
    
    is_paid=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.user)

class OrderItem(models.Model):
    order = models.ForeignKey(OrderPlaced, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.title} - {self.quantity}"
