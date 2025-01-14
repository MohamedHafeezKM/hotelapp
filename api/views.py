from django.shortcuts import render
from datetime import date
# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ViewSet,ModelViewSet
from rest_framework import authentication,permissions,pagination
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.parsers import FileUploadParser,MultiPartParser,FormParser
from rest_framework.generics import GenericAPIView
from rest_framework.decorators import action
from rest_framework.serializers import ValidationError
from api.serializers import UserSerializer,ItemSerializer,ItemVarientSerializer,CartItemSerializer,OrderItemSerializer,OrderSerializer
from api.models import ItemModel,ItemVariantModel,CartItemModel,OrderItemModel,OrderModel

class RegisterView(APIView):
    def post(self,request,*args,**kwargs):
        serializer=UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data,status=status.HTTP_201_CREATED)
        
        else:
            return Response(data=serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
class SetPagination(pagination.PageNumberPagination):
    #setting 20 users per page
    page_size=10
    page_query_param = 'page'
    page_size_query_param = 'page_size'
    max_page_size = 10


class ItemView(ViewSet,GenericAPIView):
    authentication_classes=[JWTAuthentication]
    permission_classes=[permissions.IsAuthenticated]
    parser_classes =  [MultiPartParser]
    pagination_class=SetPagination

    def create(self,request,*args,**kwargs):
        serializer=ItemSerializer(data=request.data)
        print(request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            if request.data.get('price') and request.data.get('is_variable')=='false':
                ItemVariantModel.objects.filter(item__id=serializer.data.get('id')).update(price=request.data.get('price'))
            return Response(data=serializer.data)
        else:
            return Response(data=serializer.errors)
        

    def list(self,request,*args,**kwargs):
        qs=ItemModel.objects.all()
        # deserializer=ItemSerializer(qs,many=True)
        page=self.paginate_queryset(qs)
        if page is not None:
            deserializer=ItemSerializer(page,many=True)
            return self.get_paginated_response(deserializer.data)

        deserializer=ItemSerializer(qs,many=True)
        return Response(data=deserializer.data)
    
    def retrieve(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        item=ItemModel.objects.get(id=id)
        deserializer=ItemSerializer(item)
        return Response(data=deserializer.data)
    
    def update(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        item=ItemModel.objects.get(id=id)
        serialize=ItemSerializer(data=request.data,instance=item)
        if serialize.is_valid():
            serialize.save()
            return Response(data=serialize.data)
        else:
            return Response(data=serialize.errors)
        
    def destroy(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        item=ItemModel.objects.get(id=id).delete()
        return Response(data={'message':'This item has been deleted'})
    

    @action(methods=['post'],detail=True)
    def add_varient(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        item=ItemModel.objects.get(id=id)
        serilizer=ItemVarientSerializer(data=request.data)
        if serilizer.is_valid():
            serilizer.save(item=item)
            return Response(data=serilizer.data)
        else:
            return Response(data=serilizer.errors)
        
    @action(methods=['get'],detail=True)
    def get_varient(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        item=ItemModel.objects.get(id=id)
        itemvariants=ItemVariantModel.objects.filter(item=item)
        deserilizer=ItemVarientSerializer(itemvariants,many=True)
        return Response(data=deserilizer.data)
     

    


class ItemVarientView(ViewSet):
    authentication_classes=[JWTAuthentication]
    permission_classes=[permissions.IsAuthenticated]
     
    @action(methods=['post'],detail=True)
    def add_to_cart(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        quantity=int(request.data.get('quantity',1))
        preexist_cart=list(CartItemModel.objects.filter(cart__user=request.user).values_list('item',flat=True))
        if int(id) in preexist_cart:
            instance=CartItemModel.objects.get(cart__user=request.user,item__id=id)
            instance.quantity=quantity
            total_item_price=instance.price*quantity
            instance.total_item_price=total_item_price
            instance.save()
            deserializer=CartItemSerializer(instance)
            return Response(data=deserializer.data,status=status.HTTP_202_ACCEPTED)

        else:
            itemvariant=ItemVariantModel.objects.get(id=id)
            price=itemvariant.price
            total_item_price=quantity*price
            cart_object=CartItemModel.objects.create(cart=request.user.cart_user,item=itemvariant,quantity=quantity,price=price,total_item_price=total_item_price)
            deserializer=CartItemSerializer(cart_object)
            return Response(data=deserializer.data,status=status.HTTP_201_CREATED)

    @action(methods=['delete'],detail=True)
    def remove_from_cart(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        try:
            CartItemModel.objects.get(cart__user=request.user,item__id=id).delete()
        except:
            pass
      
        return Response(status=status.HTTP_204_NO_CONTENT)
        


    def destroy(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        ItemVariantModel.objects.get(id=id).delete()
        return Response(data={'message':'Item varient has been deleted'},status=status.HTTP_200_OK)

class CartView(APIView):
    authentication_classes=[JWTAuthentication]
    permission_classes=[permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        qs=CartItemModel.objects.filter(cart__user=request.user)
        deserializer=CartItemSerializer(qs,many=True)
        return Response(data=deserializer.data)


class OrderView(ViewSet,GenericAPIView):
    authentication_classes=[JWTAuthentication]
    permission_classes=[permissions.IsAuthenticated]
    pagination_class=SetPagination

    def create(self,request,*args,**kwargs):
        if list(request.user.cart_user.cart_items.all())==[]:
            raise ValidationError('The cart is empty, fill cart and process order')
        
        else:
            order=OrderModel.objects.create(created_by=request.user,table_no=request.data.get('table_no') if request.data.get('table_no') else None)
            total_price=0
            for each in request.user.cart_user.cart_items.all():
                OrderItemModel.objects.create(order=order,item=each.item,quantity=each.quantity,price=each.price,total_item_price=each.total_item_price)
                total_price+=each.total_item_price
            order.total_price=total_price
            order.save()
            qs=OrderItemModel.objects.filter(order=order)
            deserialier=OrderItemSerializer(qs,many=True)
            CartItemModel.objects.filter(cart__user=request.user).delete()
            return Response(data=deserialier.data)


    def list(self,request,*args,**kwargs):
        qs=OrderModel.objects.all()
        if request.query_params.get('date')=='today':
            qs=qs.filter(created_at__date=date.today())
       

        page=self.paginate_queryset(qs)
        if page is not None:
            deserializer=OrderSerializer(page,many=True)
            return self.get_paginated_response(deserializer.data)
        # deserializeer=OrderSerializer(qs,many=True)
        # return Response(data=deserializeer.data)


    def update(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        order=OrderModel.objects.get(id=id)
        order.order_status='Confirmed'
        order.save()
        item_varient_id=request.data.get('item_var_id')
        quantity=int(request.data.get('quantity'))
     
     
        item_varient=ItemVariantModel.objects.get(id=item_varient_id)
        total_item_price=item_varient.price*quantity
        order_item=OrderItemModel.objects.create(order=order,item=item_varient,price=item_varient.price,quantity=quantity,total_item_price=total_item_price)
        order.total_price+=total_item_price
        order.save()

        deserlaizer=OrderSerializer(order)
        return Response(data=deserlaizer.data)
    
    @action(methods=['put'],detail=True)
    def order_item_status_change(self,request,*args,**kwargs):
        status=request.data.get('order_item_status')
        id=kwargs.get('pk')
        order_item=OrderItemModel.objects.get(id=id)
        if order_item.order_item_status=='Canceled':
            raise ValidationError('This item has been cancelled before! Cannot change status')
        order_id=order_item.order.id
        order=OrderModel.objects.get(id=order_id)
        all_order_items=OrderItemModel.objects.filter(order=order)
        if status=='Processing':
            order.order_status='Processing'
            order.save()
            order_item.order_item_status='Processing'
            order_item.save()
        
        elif status=='Ready':
            order_item.order_item_status='Ready'
            order_item.save()
            all_order_ready=True
            
            for each in all_order_items:
                if each.order_item_status=='Canceled':
                    pass
                elif each.order_item_status!='Ready':
                    all_order_ready=False
                    break
            if all_order_ready:
                order.order_status='Ready'
                order.save()

        elif status=='Canceled':
            order.total_price-=order_item.total_item_price
            order.save()
            order_item.order_item_status='Canceled'
            order_item.total_item_price=0
            order_item.price=0
            order_item.save()
            if len(all_order_items)==1:
                order.order_status='Canceled'
                order.save()
        
        else:
            order_item.order_item_status=status
            order_item.save()
            order.order_status=status
            order.save()


        
        qs=order_item
        deserializer=OrderItemSerializer(qs)
        return Response(data=deserializer.data)



class FileUploadDebugView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        print("Request Data:", request.data)
        print("Request FILES:", request.FILES)

        if not request.FILES:
            return Response({"error": "No files detected"}, status=400)

        return Response({"message": "File upload successful", "file_name": request.FILES['image'].name})