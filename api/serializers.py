from rest_framework import serializers
from django.contrib.auth.models import User
from api.models import ItemModel,ItemVariantModel,OrderModel,OrderItemModel,CartItemModel

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['id','username','password','email']

        read_only_fields=['id']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model=ItemModel
        fields=['id','name','image','category','is_available','is_non_veg','is_variable']

        read_only_fields=['id','created_by']

        extra_kwargs = {
            'name': {'required': False},
            'image': {'required': False},
            'category': {'required': False},
            'is_available': {'required': False},
            'is_non_veg': {'required': False},
            'is_variable': {'required': False},
        }


class ItemVarientSerializer(serializers.ModelSerializer):
    item=ItemSerializer(read_only=True)
    class Meta:
        model=ItemVariantModel
        fields=['id','price','item','name']

        read_only_fields=['id','created_at']

class CartItemSerializer(serializers.ModelSerializer):
    item=ItemVarientSerializer(read_only=True)
    class Meta:
        model=CartItemModel
        fields='__all__'
        read_only_fields=['id','cart','item','quantity','total_item_price']


class OrderSerializer(serializers.ModelSerializer):
    cooked_user=serializers.StringRelatedField()
    created_user=serializers.StringRelatedField()
    class Meta:
        model=OrderModel
        fields='__all__'
        read_only_fields=['id','order_status','total_price','serving_mode','cooked_by','created_by','created_user','cooked_user']


class OrderItemSerializer(serializers.ModelSerializer):
    item=ItemVarientSerializer(read_only=True)
    # order=OrderSerializer(read_only=True)
    class Meta:
        model=OrderItemModel
        fields="__all__"
        read_only_fields=['order','item','quantity','price','total_item_price','order_item_status']

