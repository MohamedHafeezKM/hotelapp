from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_delete,post_save
from django.dispatch.dispatcher import receiver
# Create your models here.


class ItemModel(models.Model):
    name=models.TextField()
    image=models.ImageField(upload_to='food_images',null=True)
    category_option=(('main dish','main dish'),('side dish','side dish'),("snack","snack"),("beverage","beverage"),("dessert","dessert"),("curry","curry"),)
    category=models.CharField(max_length=50,choices=category_option)
    created_by=models.ForeignKey(User,related_name='dish_by',on_delete=models.SET_NULL,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    is_available=models.BooleanField()
    is_non_veg=models.BooleanField()
    is_variable=models.BooleanField()

    def remove_on_image_update(self):
        try:
            # is the object in the database yet?
            obj = ItemModel.objects.get(id=self.id)
        except ItemModel.DoesNotExist:
            # object is not in db, nothing to worry about
            return
        # is the save due to an update of the actual image file?
        if obj.image and self.image and obj.image != self.image:
            # delete the old image file from the storage in favor of the new file
            obj.image.delete()




    def __str__(self):
        return self.name
    
@receiver(pre_delete, sender=ItemModel)
def mymodel_delete(sender, instance, **kwargs):
    # Pass false so FileField doesn't save the model.
       instance.image.delete(False) 
    
def create_non_variant_item(sender,instance,created,**kwargs):
    if created:
        if not instance.is_variable:
            ItemVariantModel.objects.create(item=instance,name=instance.name)

post_save.connect(create_non_variant_item,sender=ItemModel)


class ItemVariantModel(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    price=models.FloatField(default=1)
    item=models.ForeignKey(ItemModel,on_delete=models.CASCADE,related_name='variant',null=True)
    name=models.TextField()


class CartModel(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    user=models.OneToOneField(User,on_delete=models.CASCADE,related_name='cart_user')


def create_cart(sender,instance,created,**kwargs):
    if created:
        CartModel.objects.create(user=instance)

post_save.connect(create_cart,sender=User)
    
class CartItemModel(models.Model):
    cart=models.ForeignKey(CartModel,on_delete=models.CASCADE,related_name='cart_items')
    item=models.ForeignKey(ItemVariantModel,on_delete=models.SET_NULL,null=True,related_name='cart_items')
    quantity=models.PositiveIntegerField(default=1)
    price=models.FloatField(default=0)
    total_item_price=models.FloatField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)





    

class OrderModel(models.Model):
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    options=(('Confirmed','Confirmed'),
             ('Processing','Processing'),
             ('Ready','Ready'),
             ('Canceled','Canceled'),
             )
    order_status=models.CharField(max_length=30,choices=options,default='Confirmed')
    total_price=models.FloatField(default=1)
    created_by=models.ForeignKey(User,related_name='server',on_delete=models.SET_NULL,null=True)
    cooked_by=models.ForeignKey(User,related_name='chef',on_delete=models.SET_NULL,null=True)
    mode=(('Dine in','Dine in'),('Takeaway','Takeaway'))
    serving_mode=models.CharField(max_length=50,choices=mode,default='Dine in')
    table_no=models.TextField(null=True,blank=True)


class OrderItemModel(models.Model):
    order=models.ForeignKey(OrderModel,on_delete=models.CASCADE,related_name='orderitems')
    item=models.ForeignKey(ItemVariantModel,on_delete=models.SET_NULL,null=True,related_name='items')
    quantity=models.PositiveIntegerField(default=1)
    price=models.FloatField(default=0)
    total_item_price=models.FloatField(default=0)
    options=(('Confirmed','Confirmed'),
             ('Processing','Processing'),
             ('Ready','Ready'),
             ('Canceled','Canceled'),
             )
    order_item_status=models.CharField(max_length=30,choices=options,default='Confirmed')








