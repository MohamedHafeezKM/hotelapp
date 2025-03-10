from django.shortcuts import render
from django.http import HttpResponse
from datetime import date,datetime
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
from rest_framework.parsers import JSONParser
from api.serializers import UserSerializer,ItemSerializer,ItemVarientSerializer,CartItemSerializer,OrderItemSerializer,OrderSerializer
from api.models import ItemModel,ItemVariantModel,CartItemModel,OrderItemModel,OrderModel
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4,A7
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER 
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from io import BytesIO


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
        print(request.POST)
        print(request.content_type)
        
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
    

    @action(methods=['post'],detail=True,parser_classes=[JSONParser])
    def add_varient(self,request,*args,**kwargs):
        print("Content-Type:", request.content_type)  # Log the received Content-Type
        print("Request Data:", request.data) 
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
           
            serving_mode='Takeaway' if request.data.get('takeaway') == True else 'Dine in'
            order=OrderModel.objects.create(created_by=request.user,table_no=request.data.get('table_no') if request.data.get('table_no') else None,serving_mode=serving_mode)
            total_price=0
            for each in request.user.cart_user.cart_items.all():
                OrderItemModel.objects.create(order=order,item=each.item,quantity=each.quantity,price=each.price,total_item_price=each.total_item_price)
                total_price+=each.total_item_price
            order.total_price=total_price
            order.save()
            qs=OrderItemModel.objects.filter(order=order)
            deserialier=OrderItemSerializer(qs,many=True)
            CartItemModel.objects.filter(cart__user=request.user).delete()


            #websocket for front-end for componnets to update in two windows, servers, cook
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "orders",
                {
                    "type": "order_update",
                    "message": {
                        'department': 'kitchen',
                        'message':f"New order created: {order.id}"
                    }
                }
            )
            return Response(data=deserialier.data)


    def list(self,request,*args,**kwargs):
        qs=OrderModel.objects.all().order_by('-created_at')
        if request.query_params.get('date')=='today':
            qs=qs.filter(created_at__date=date.today())
       

        page=self.paginate_queryset(qs)
        if page is not None:
            deserializer=OrderSerializer(page,many=True)
            return self.get_paginated_response(deserializer.data)
        # deserializeer=OrderSerializer(qs,many=True)
        # return Response(data=deserializeer.data)


    def update(self,request,*args,**kwargs):
        print(request.data)
        id=kwargs.get('pk')
        order=OrderModel.objects.get(id=id)
        order.order_status='Confirmed'
        order.save()
        item_varient_id=int(request.data.get('item_var_id'))
        quantity=int(request.data.get('quantity'))
     
     
        item_varient=ItemVariantModel.objects.get(id=item_varient_id)
        total_item_price=item_varient.price*quantity
        order_item=OrderItemModel.objects.create(order=order,item=item_varient,price=item_varient.price,quantity=quantity,total_item_price=total_item_price)
        order.total_price+=total_item_price
        order.save()

        deserlaizer=OrderSerializer(order)
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "orders",
            {
                "type": "order_update",
                "message": {
                    "department":'kitchen',
                    'message':f"{quantity} quantity of Item {item_varient.name} - {item_varient.item.name} added to Order ID:{order.id}"
                }
            }
        )
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
            order.cooked_by=request.user
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
                cancelled_items=0
                for each in all_order_items:
                  if each.order_item_status=='Canceled':
                      cancelled_items+=1
                    
                if cancelled_items==len(all_order_items):
                    order.order_status='Canceled'
                    order.save()
                    
        
        else:
            order_item.order_item_status=status
            order_item.save()
            order.order_status=status
            order.save()


        
        qs=order_item
        deserializer=OrderItemSerializer(qs)

        statement=''
        if order.table_no:
            statement=f"For table no: {order.table_no}"
        elif order.serving_mode=='Takeaway':
            statement='For Takeaway'
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "orders",
            {
                "type": "order_update",
                "message": {
                    "department":'menu',
                    'message':f"Order ID:{order.id} Ready {statement},items- {[each.item.item.name for each in all_order_items]}" if order.order_status=='Ready' else ""
                }
            }
        )
        return Response(data=deserializer.data)

    @action(methods=['get'],detail=True)
    def order_item_details(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        order_items=OrderItemModel.objects.filter(order_id=id)
        deserializer=OrderItemSerializer(order_items,many=True)
        return Response(data=deserializer.data)
    
    @action(methods=['get'],detail=True)
    def invoice(self,request,*args,**kwargs):
        id=kwargs.get('pk')
        order=OrderModel.objects.get(id=id)
        order_items=OrderItemModel.objects.filter(order_id=id)


               # Create a PDF document
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'
        width, height = A7
        styles = getSampleStyleSheet()
        styleN = styles["BodyText"]
        styleN.alignment = TA_LEFT
        styleBH = styles["Normal"]
        styleBH.alignment = TA_CENTER

        def coord(x, y, unit=1):
            x, y = x * unit, height - y * unit
            return x, y

      

        buffer = BytesIO()

        p = canvas.Canvas(buffer, pagesize=A7)
        

        
        data = [['Description','Unit Price', 'Qty', 'Total MRP','Tax Amount','Total']]
        sub_total=0
        
        gst_rate_lists=[]
        sl_no=0
        sub_tax_total=order.tax_amount
        #single orders/mixed orders idea and formula starts here!
        for eachorder in order_items:
       
    
            sl_no+=1
            no=str(sl_no)    
            
            product_name = Paragraph(str(no+') '+eachorder.item.item.name+'-'+eachorder.item.name), styleN)
            mrp = Paragraph(str(eachorder.price), styleN)
            quantity = Paragraph(str(eachorder.quantity), styleN)
            total_mrp = Paragraph(str(eachorder.total_item_price), styleN)
            # discount = Paragraph(str(price_list[2]), styleN)
            # net_price=Paragraph(str(price_list[3]), styleN)
            

            tax_amount=eachorder.tax_amount//2
            tax_type=Paragraph(' CGST '+str(tax_amount)+' SGST '+str(tax_amount), styleN)
         
            total_item_price = Paragraph(str(eachorder.total_tax_price), styleN)
            sub_total+=eachorder.total_tax_price
            data.append([product_name,mrp,quantity,total_mrp,tax_type,total_item_price])
    
    
   

        #total
        sub_total=Paragraph(str(sub_total), styleN)
        sub_tax_total=round(sub_tax_total,2)
        sub_tax_total=Paragraph(str(sub_tax_total), styleN)
        total=order.total_price
        data.append(['SUB TOTAL:','','',total,sub_tax_total,sub_total])


        table = Table(data, colWidths=[5 * cm,2 * cm, 1 * cm, 2 * cm, 2.8 * cm, 2 * cm])

        table.setStyle(TableStyle([
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ]))
        table.wrapOn(p, width, height)
        table.wrapOn(p, width, height)
        table.drawOn(p, *coord(0.5, 23, cm))

        id = Paragraph(str(order.id), styleN)
        date = Paragraph(str(order.created_at.strftime('%b %d, %Y %H:%M:%S')), styleN)
    
        status = Paragraph(order.order_status, styleN)

        data2=[['Order ID','Date','Order Status'],[id,date,status]]

        table2 =  Table(data2, colWidths=[2 * cm, 8 * cm, 3 * cm, 6 * cm])
        table2.setStyle(TableStyle([
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
        ]))
        table2.wrapOn(p, width, height)
        table2.wrapOn(p, width, height)
        table2.drawOn(p, *coord(0.5, 25, cm))


        y = 700
        # if admin.brand_logo:
        #     p.drawImage(f'media/{admin.brand_logo}', *coord(0.5, 3.5, cm), width=100,height=100)

        # else:
        #     p.drawImage(f'Products/static/images/empty.png', *coord(0.5, 3.5, cm), width=100,height=100)
        
        p.drawCentredString(300, y + 70, f"Invoice")
        p.setFont("Helvetica", 10)
        # p.drawRightString(580, y - 80, f"Billing and Shipping Address:")
        # p.drawRightString(580, y - 100, f"{order.customer.full_name}")
        # p.drawRightString(580, y - 120, f"{order.customer.complete_address}")
        # p.drawRightString(580, y - 140, f"{order.customer.city}")
        # p.drawRightString(580, y - 160, f"{order.customer.state}")
        # p.drawRightString(580, y - 180, f"{order.customer.pincode}")
        # p.drawRightString(580, y - 200, f"{order.customer.phone_number}")
        # p.drawRightString(580, y - 220, f"{order.customer.user.email}")
        # p.drawRightString(580, y + 10, f"Place of supply: {admin.state}")
        # p.drawRightString(580, y - 10, f"Place of delivery: {order.customer.state}")
        

        # p.drawString(20, y + 10, f"Sold By:")
        # p.drawString(20, y - 10, f"{admin.brand_name}")
        # p.drawString(20, y - 30, f"{admin.brand_address}")
        # p.drawString(20, y - 50, f"Phone: {admin.brand_contact}")
        # p.drawString(20, y - 70, f"Email: { admin.notification_email}")
        # if admin.gst_number:
        #     p.drawString(20, y - 130, f"GST No: {admin.gst_number}")
        
        
        p.drawCentredString(300, y - 680, f"This is a computer generated invoice, Report generated at " + datetime.now().strftime('%b %d, %Y %H:%M:%S'))
        p.drawCentredString(300, y - 695, f"Developed with \u2665 by Haze Tech")
        # p.drawString(350, y - 600, f"Authorized Signature for {admin.brand_name}")

        # if admin.signature:
        #     p.drawImage(f'media/{admin.signature}', *coord(15, 28, cm), width=100,height=50)
        # else:
        #     p.drawImage(f'Products/static/images/empty.png', *coord(15, 28, cm), width=100,height=50)

        
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response


class FileUploadDebugView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        print("Request Data:", request.data)
        print("Request FILES:", request.FILES)

        if not request.FILES:
            return Response({"error": "No files detected"}, status=400)

        return Response({"message": "File upload successful", "file_name": request.FILES['image'].name})