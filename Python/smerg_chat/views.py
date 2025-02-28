from django.shortcuts import render
from .models import *
from .serializers import *
# from rest_framework.views import APIView
from adrf.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from .utils.enc_utils import *
from smerg_app.utils.async_serial_utils import *
from smerg_app.utils.check_utils import *
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone

# Rooms
class Rooms(APIView):
    @swagger_auto_schema(operation_description="Get a list of all chat rooms for the authenticated user.",
    responses={200: "List of chat rooms retrieved successfully.",404: "User does not exist.",400: "Token is not passed."})
    async def get(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                rooms = [room async for room in Room.objects.filter(Q(first_person=user) | Q(second_person=user)).order_by('-updated')] 
                serialized_data = await serialize_data(rooms, RoomSerial)
                return Response(serialized_data)
            return Response({'status':False,'message': 'User doesnot exist'})
        return Response({'status':False,'message': 'Token is not passed'})

    @swagger_auto_schema(operation_description="Create a new chat room or retrieve an existing one between two users.",request_body=openapi.Schema(type=openapi.TYPE_OBJECT,
    properties={'receiverId': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the receiver's SaleProfile."),},required=['receiverId'],),
    responses={200: "Chat room created or retrieved successfully.",404: "User does not exist.",400: "Token is not passed."})
    async def post(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                reciever = await SaleProfiles.objects.aget(id=request.data.get('receiverId'))
                recieved_user = await sync_to_async(lambda: reciever.user)()
                if user == recieved_user:
                    return Response({'status':False,'message': 'You cannot chat with yourself'},  status=status.HTTP_403_FORBIDDEN)
                recieved_name = await sync_to_async(lambda: reciever.name)()
                recieved_image = await sync_to_async(lambda: reciever.user.image)()
                if recieved_image:
                    image = recieved_image.url 
                else: 
                    image = None
                enquiry = None
                if not await Enquiries.objects.filter(user=user, post=reciever).aexists():
                    enquiry = await Enquiries.objects.acreate(user=user, post=reciever, created=timezone.now())
                if await Room.objects.filter(Q(first_person=user, second_person=recieved_user) | Q(second_person=user, first_person=recieved_user), post=reciever).aexists():
                    room = await Room.objects.aget(Q(first_person=user, second_person=recieved_user) | Q(second_person=user, first_person=recieved_user), post=reciever)
                    room_id = await sync_to_async(lambda: room.id)()
                    if enquiry:
                        enquiry.room_id = room_id
                        await enquiry.asave()
                    return Response({'status':True, 'name': recieved_name, 'image':image, 'roomId': room_id, 'post': {"id": reciever.id, "title": reciever.title, "image": image}})
                room = await Room.objects.acreate(first_person=user, second_person=recieved_user, post=reciever, last_msg=encrypt_message("Tap to send message"))
                if enquiry:
                    enquiry.room_id = room.id
                    await enquiry.asave()
                return Response({'status':True,'name': recieved_name, 'image': image, 'roomId':room.id, 'post': {"id": reciever.id, "title": reciever.title, "image": image}})
            return Response({'status':False,'message': 'User doesnot exist'})
        return Response({'status':False,'message': 'Token is not passed'})

# Chat of 2 users
class Chat(APIView):
    @swagger_auto_schema(operation_description="Fetch chat messages for a specific room.",
    manual_parameters=[openapi.Parameter('roomId', openapi.IN_QUERY, type=openapi.TYPE_INTEGER,description="ID of the chat room.")],
    responses={200: "Chat messages retrieved successfully.",404: "User does not exist.",400: "Token is not passed."})
    async def get(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                chats = [chat async for chat in ChatMessage.objects.filter(room__id = request.GET.get('roomId')).order_by('-id')] 
                serialized_data = await serialize_data(chats, ChatSerial)
                room   = await Room.objects.select_related('first_person', 'second_person').aget(id = request.GET.get('roomId'))
                if user.id == room.first_person.id:
                    number = room.second_person.username
                else:
                    number = room.first_person.username
                return Response({'messages': serialized_data, 'number': number })
            return Response({'status':False,'message': 'User doesnot exist'})
        return Response({'status':False,'message': 'Token is not passed'})