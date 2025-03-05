import requests, aiohttp, asyncio, random, base64, json
from django.shortcuts import render
# from rest_framework.views import APIView
from adrf.views import APIView
from asgiref.sync import sync_to_async, async_to_sync
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import *
from smerg_chat.models import *
from .serializers import *
from django.utils import timezone
from django.contrib.auth import authenticate
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q
from dateutil.relativedelta import relativedelta
from django.core.files.base import ContentFile
from django.contrib.auth.hashers import check_password
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from django.db.models import Count, Sum, Avg
from django.db.models.functions import ExtractMonth
from django.core.cache import cache
from .utils.twilio_utils import *
from .utils.razorpay_utils import *
from .utils.async_serial_utils import *
from rest_framework import status
from .utils.check_utils import *
from datetime import datetime, timedelta
from django.conf import settings

# Login
class LoginView(APIView):
    @swagger_auto_schema(operation_description="Login authentication using username and password, and return token",
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT,required=['username', 'password'],
    properties={'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username for authentication'),'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password for authentication'),},),
    responses={200: '{"status": true,"token": "d08dcdfssd38ffaaa0d974fb7379e05ec1cd5b95"}',400:'{"status": false,"message": "Invalid credentials"}'})
    async def post(self,request):
        exists, user = await check_exists(request.data.get('phone'))
        if exists:
            if check_password(request.data.get('password'), user.password):
                if not user.block and not user.deactivate:
                    token = await Token.objects.aget(user=user)
                    device = None
                    if request.data.get('mobile_device') and user.mobile_device != request.data.get('mobile_device'):
                        user.mobile_device = request.data.get('mobile_device')
                        device = user.mobile_device
                    elif request.data.get('web_device') and user.web_device != request.data.get('web_device'):
                        user.web_device = request.data.get('web_device')
                        device = user.web_device
                    if device:
                        variables = {
                            "1": user.first_name,
                            "2": device,
                            "3": datetime.now().strftime("%I:%M %p").lower()
                        }
                        await sync_to_async(send_updates)(body=variables, number=user.username)
                        await user.asave()
                    return Response({'status':True, 'token':token.key}, status=status.HTTP_200_OK)
                return Response({'status':False,'message': 'User Blocked/ Account deactivated'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'status':False,'message': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

# Social Implementation for verifying login
class Social(APIView):
    @swagger_auto_schema(operation_description="Verify if user is in DB using social media",request_body=openapi.Schema(type=openapi.TYPE_OBJECT,required=['username'],
    properties={'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username/ Email for authentication'),},),
    responses={200: "{'status':True,'message': 'Verify if user is in DB using social media successfully'}",400:"Passes an error message"})
    async def post(self,request):
        exists, user = await check_email(request.data.get('username'))
        if exists:
            if not user.block and not user.deactivate:
                token = await Token.objects.aget(user=user)
                return Response({'status':True,'token':token.key}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User Blocked/ Account deactivated'}, status=status.HTTP_403_FORBIDDEN)
        return Response({'status':False,'message':'Register to continue'}, status=status.HTTP_400_BAD_REQUEST)

# Registration OTP
class RegisterOtp(APIView):
    @swagger_auto_schema(operation_description="Sending OTP for registration using whatsapp, twilio and phone number, and return a response",
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT,required=['username','email'],
    properties={'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username for authentication'),'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email for authentication'),},),
    responses={200: "{'status':True}",400:"{'status':False,'message': 'User with same phone number/email id already exist'}"})
    async def post(self,request):
        if request.data.get('phone') and request.data.get('email'):
            exists, user = await check_exists(request.data.get('phone'))
            email_exists, user = await check_email(request.data.get('email'))
            if exists or email_exists:
                return Response({'status':False,'message': 'User with same phone number/email id already exist'}, status=status.HTTP_403_FORBIDDEN)
            otp = random.randint(1111,9999)
            key = f'otp_{request.data.get('phone')}'
            cache_value = await sync_to_async(cache.get)(key)
            if not cache_value:
                await sync_to_async(cache.set)(key, f"{otp:04d}", timeout=30)
                await twilio_int(f"{otp:04d}", request.data.get('phone'))
            return Response({'status':True}, status=status.HTTP_200_OK)
        return Response({'status':False,'message':"Phone number/ Email not found"}, status=status.HTTP_400_BAD_REQUEST)

# User registration
class RegisterView(APIView):
    @swagger_auto_schema(operation_description="User creation for an organisation",request_body=UserSerial,
    responses={200: "{'status':True,'message': 'User created successfully'}",400:"Passes an error message"})
    async def post(self,request):
        key = f'otp_{request.data.get('phone')}'
        @sync_to_async()
        def get_cache_value(key):
            return cache.get(key)

        stored_otp = await get_cache_value(key)
        if stored_otp:
            if int(stored_otp) == int(request.data.get('otp')):
                await sync_to_async(cache.delete)(key)
                exists, user = await check_exists(request.data.get('phone'))
                email_exists, user = await check_email(request.data.get('email'))
                if exists or email_exists:
                    return Response({'status':False,'message': 'User already exists'}, status=status.HTTP_403_FORBIDDEN)
                request.data['username'] = request.data.get('phone')

                # Make random password for Social Login
                if request.data.get('password') == "":
                    password = UserProfile.objects.make_random_password()
                    request.data['password'] = password
                saved, user = await create_serial(UserSerial, request.data)
                if saved:
                    token = await Token.objects.acreate(user=user)
                    await sync_to_async(user.set_password)(request.data['password'])
                    user.first_name = request.data.get('name')
                    await user.asave()

                    if request.data.get('images') is not None:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(request.data.get('images')) as response:
                                if response.status == 200:
                                    content = await response.read()
                                    await sync_to_async(user.image.save)(f'{user.username}_profile.jpg', ContentFile(content))
                    return Response({'status':True,'token':token.key}, status=status.HTTP_201_CREATED)
                return Response(user)
            return Response({'status':False,'message': 'Incorrect OTP'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'OTP has expired'}, status=status.HTTP_408_REQUEST_TIMEOUT)

# Forgot password
class ForgotPwd(APIView):
    @swagger_auto_schema(operation_description="Forgot password api, where an otp is sended to user's whatsapp",
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT,required=['number'],
    properties={'number': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number for authentication')}),
    responses={200: "{'status':True}",400:"{'status':False}"})
    async def post(self,request):
        exists, user = await check_exists(request.data.get('number'))
        if exists and not user.block:
            otp = random.randint(0000,9999)
            key = f'otp_{request.data.get('number')}'
            cache_value = await sync_to_async(cache.get)(key)
            if not cache_value:
                await sync_to_async(cache.set)(key, f"{otp:04d}", timeout=30)
                await twilio_int(f"{otp:04d}", request.data.get('number'))
            return Response({'status':True}, status=status.HTTP_200_OK)
        return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)

# Confirm OTP
class OTPConfirm(APIView):
    @swagger_auto_schema(operation_description="Confirm OTP api, where an otp is sended to user's whatsapp",
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT,required=['phone'],
    properties={'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number for authentication')}),
    responses={200: "{'status':True}",400:"{'status':False}"})
    async def post(self,request):
        exists, user = await check_exists(request.data.get('phone'))
        if exists and not user.block:
            key = f'otp_{request.data.get('phone')}'
            stored_otp = await cache.aget(key)
            if stored_otp:
                if int(stored_otp) == int(request.data.get('otp')):
                    return Response({'status':True}, status=status.HTTP_200_OK)
                return Response({'status':False,'message': 'Incorrect OTP'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'status':False,'message': 'OTP has expired'}, status=status.HTTP_408_REQUEST_TIMEOUT)
        return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_404_NOT_FOUND)

# Change Password
class ChangePwd(APIView):
    @swagger_auto_schema(operation_description="Forgot password api, where an otp is sended to user's whatsapp",request_body=openapi.Schema(type=openapi.TYPE_OBJECT,required=['username'],
    properties={'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username for authentication'),'password': openapi.Schema(type=openapi.TYPE_STRING, description='Password for authentication'),},),
    responses={200: "{'status':True,'message': 'User password changed successfully'}",400:"Passes an error message"})
    async def post(self,request):
        password = request.data.get('password')
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
        else:
            exists, user = await check_exists(request.data.get('username'))
        if exists:
            if check_password(password, user.password):
                return Response({'status':False}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
            await sync_to_async(user.set_password)(password)
            await user.asave()
            return Response({'status':True}, status=status.HTTP_200_OK)
        return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)

# class Profiles(APIView):
#     @swagger_auto_schema(operation_description="Fetch profiles based on type and user subscription.",
#         manual_parameters=[openapi.Parameter('type', openapi.IN_QUERY,description="Type of the profile to fetch",type=openapi.TYPE_STRING, required=True),openapi.Parameter('show_all', openapi.IN_QUERY, 
#         description="Set to 'true' to fetch all profiles of the given type; otherwise, fetch the user's latest profile.",type=openapi.TYPE_BOOLEAN, default=False),],
#         responses={200: "Returns a serialized profile or list of profiles.",404: "{'status': False, 'message': 'No profiles found'}",403: "{'status': False, 'message': 'User does not exist'}"})
#     async def get(self,request):
#         if request.headers.get('token'):
#             exists, user = await check_user(request.headers.get('token'))
#             if exists:
#                 if request.GET.get('show_all'):
#                     profiles = [profile async for profile in Profile.objects.filter(type=request.GET.get('type')).order_by('-id')]
#                 else:
#                     profiles = [profile async for profile in Profile.objects.filter(user=user, type=request.GET.get('type')).order_by('-id')]
#                 serialized_data = await serialize_data(profiles, ProfileSerial)
#                 return Response(serialized_data)
#             return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
#         return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

#     @swagger_auto_schema(operation_description="create profiles",request_body=ProfileSerial,
#     responses={200: "{'status':True,'message': 'created successfully'}",400:"Passes an error message"})
#     async def post(self, request):
#         if request.headers.get('token'):
#             exists, user = await check_user(request.headers.get('token'))
#             if exists:
#                 profile_exist = await Profile.objects.filter(user=user, type=request.data.get('type')).aexists()
#                 subscription = await Subscription.objects.filter(user=user, plan__type=request.data.get('type')).aexists()
#                 if not profile_exist and subscription:
#                     data = request.data
#                     data['user'] = user.id
#                     if await AadhaarDetails.objects.filter(user=user).aexists():
#                         details = await AadhaarDetails.objects.aget(user=user)
#                         name = await sync_to_async(lambda: details.name)()
#                         if data["name"].lower() != name.lower():
#                             return Response({'status': False, 'message': 'Data not matching'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
#                         data['aadhar_verified'] = True
#                     saved, resp = await create_serial(ProfileSerial, data)
#                     if saved:
#                         if not await AadhaarDetails.objects.filter(user=user).aexists():
#                             return Response({'status': True, 'message': 'Profile created successfully but aadhar details not found'}, status=status.HTTP_206_PARTIAL_CONTENT)
#                         return Response({'status': True, 'message': 'Profile created successfully'}, status=status.HTTP_201_CREATED)
#                     return Response(resp)
#                 return Response({'status': False, 'message': 'Subscription with specified plan type does not exist'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
#             return Response({'status': False, 'message': 'User already has a profile'}, status=status.HTTP_400_BAD_REQUEST)
#         return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

#     @swagger_auto_schema(operation_description="Update an existing profile's details.",
#         request_body=openapi.Schema(type=openapi.TYPE_OBJECT,properties={'field_to_update': openapi.Schema(type=openapi.TYPE_STRING, description="Field to update"),},),
#         responses={200: "{'status': True}",400: "Returns validation errors.",404: "{'status': False, 'message': 'Profile not found'}",403: "{'status': False, 'message': 'User does not exist'}",})
#     async def patch(self,request,id):
#         if request.headers.get('token'):
#             exists, user = await check_user(request.headers.get('token'))
#             if exists:
#                 profile = await  Profile.objects.aget(id=id)
#                 saved, resp = await update_serial(ProfileSerial, request.data, profile)
#                 if saved:
#                     return Response({'status':True}, status=status.HTTP_201_CREATED)
#                 return Response(resp)
#             return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
#         return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

#     @swagger_auto_schema(operation_description="Delete a profile and related SaleProfiles.",responses={200: "{'status': True, 'message': 'Profile deleted successfully'}",
#             404: "{'status': False, 'message': 'Profile not found'}",403: "{'status': False, 'message': 'User does not exist'}",})
#     async def delete(self,request,id):
#         if request.headers.get('token'):
#             exists, user = await check_user(request.headers.get('token'))
#             if exists:
#                 profiles = await Profile.objects.aget(user=user, type=request.GET.get("type"))
#                 await SaleProfiles.objects.filter(user = user, entity_type=profiles.type).adelete()
#                 await profiles.adelete()
#                 return Response({'status':True}, status=status.HTTP_200_OK)
#             return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
#         return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Single Post
class SinglePostDetails(APIView):
    @swagger_auto_schema(operation_description="Fetch a post using id passed as query param",
        responses={200: "Returns a serialized list of business posts.", 404: "{'status': False, 'message': 'Post does not exist'}", 400: "{'status': False, 'message': 'Token is not passed'}",},
        manual_parameters=[openapi.Parameter('id', openapi.IN_PATH,description=" fetch posts based on id.",type=openapi.TYPE_INTEGER, required=True),])
    async def get(self, request):
        id = request.GET.get('id')
        if await SaleProfiles.objects.filter(id=id).aexists():
            post = await SaleProfiles.objects.aget(id=id)
            serialized_data = await get_serialize_data(post, SaleProfilesSerial)
            return Response(serialized_data)
        return Response({'status': False, 'message': 'Post doesnot exist'}, status=status.HTTP_404_NOT_FOUND)

# Business
class BusinessList(APIView):
    @swagger_auto_schema(operation_description="Fetch business posts. If `id` is 0, fetch all business posts; otherwise, fetch posts created by the logged-in user.",
        responses={200: "Returns a serialized list of business posts.",403: "{'status': False, 'message': 'User does not exist'}",400: "{'status': False, 'message': 'Token is not passed'}",},
        manual_parameters=[openapi.Parameter('id', openapi.IN_PATH,description="0 to fetch all business posts; otherwise, fetch user's business posts.",type=openapi.TYPE_INTEGER, required=True),])
    async def get(self,request,id):
        if id == 0:
            businesses = [posts async for posts in SaleProfiles.objects.filter(entity_type='business', block=False, verified=True, subscribed=True).order_by('-id')]
        else:
            exists, user = await check_user(request.headers.get('token'))
            if not exists:
                return Response({'status': False, 'message': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            businesses = [posts async for posts in SaleProfiles.objects.filter(entity_type='business', user=user, block=False).order_by('-id')]
        serialized_data = await serialize_data(businesses, SaleProfilesSerial)
        return Response(serialized_data)

    @swagger_auto_schema(operation_description="Create a new business post. Requires a valid subscription with remaining posts.",
        request_body=SaleProfilesSerial,responses={201: "{'status': True, 'message': 'Business created successfully'}",
        403: "{'status': False, 'message': 'No valid subscription or remaining posts'}",400: "Returns validation errors or {'status': False, 'message': 'Token is not passed'}",})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                data = request.data.copy()
                data['user'] = user.id
                data['entity_type'] = 'business'
                industry = data.get('industry', 'industry')
                sale = data.get('type_sale', 'sale')
                city = data.get('city', '...')
                state = data.get('state', '...')
                data['title'] = f'{industry} for {sale} in {city}, {state}'
                subscribed = await check_subscription(user, "business")
                if subscribed:
                    data['subscribed'] = True
                saved, resp = await create_serial(SaleProfilesSerial, data)
                if saved:
                    return Response({'status':True}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Update an existing business post.",
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT,properties={'field_to_update': openapi.Schema(type=openapi.TYPE_STRING, description="Field to update"),},),
        responses={200: "{'status': True}",400: "Returns validation errors or {'status': False, 'message': 'Token is not passed'}",
        403: "{'status': False, 'message': 'User does not exist'}",404: "{'status': False, 'message': 'Business not found'}",})
    async def patch(self,request,id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                business = await SaleProfiles.objects.aget(id=id)
                update_fields = []
                print(request.data)
                for field, value in request.data.items():
                    if hasattr(business, field):
                        field_object = getattr(business.__class__, field).field
                        if isinstance(field_object, models.FileField) and value == "null":
                            existing_file = getattr(business, field)
                            if existing_file:
                                await sync_to_async(existing_file.delete)(save=False)
                            setattr(business, field, None)
                            print("File deleted")
                        elif (isinstance(field_object, (models.FileField, models.CharField, models.IntegerField)) and value == ""):
                            setattr(business, field, None)
                            print("Field Changed")
                        else:
                            setattr(business, field, value)
                            print("Field updated")
                        update_fields.append(field)
                
                if update_fields:
                    await business.asave(update_fields=update_fields)
                return Response({'status': True}, status=status.HTTP_201_CREATED)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Delete a business post by ID. If `id` is 0, delete all business posts of the logged-in user.",
        responses={200: "{'status': True, 'message': 'Business deleted successfully'}",403: "{'status': False, 'message': 'User does not exist'}",
        400: "{'status': False, 'message': 'Token is not passed'}",404: "{'status': False, 'message': 'Business not found'}",},
        manual_parameters=[openapi.Parameter('id', openapi.IN_PATH, description="ID of the business post to delete. Use 0 to delete all posts of the logged-in user.", type=openapi.TYPE_INTEGER, required=True),])
    async def delete(self,request,id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if id == 0:
                    async for profile in SaleProfiles.objects.filter(user=user, entity_type='business'):
                        await profile.adelete()
                else:
                    profiles = await SaleProfiles.objects.aget(id=id)
                    await profiles.adelete()
                return Response({'status':True}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Investor
class InvestorList(APIView):
    @swagger_auto_schema(operation_description="Fetch investor profiles. If `id` is 0, fetch all verified investor profiles; otherwise, fetch investor profiles created by the logged-in user.",
        responses={200: "Returns a serialized list of investor profiles.",
        403: "{'status': False, 'message': 'User does not exist'}",400: "{'status': False, 'message': 'Token is not passed'}",},
        manual_parameters=[openapi.Parameter('id', openapi.IN_PATH,description="0 to fetch all verified investor profiles; otherwise, fetch user's investor profiles.", type=openapi.TYPE_INTEGER, required=True),])
    async def get(self,request,id):
        if id == 0:
            investor = [posts async for posts in SaleProfiles.objects.filter(entity_type='investor', block=False, verified=True, subscribed=True).order_by('-id')]
        else:
            exists, user = await check_user(request.headers.get('token'))
            if not exists:
                return Response({'status': False, 'message': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            investor = [posts async for posts in SaleProfiles.objects.filter(entity_type='investor', user=user, block=False).order_by('-id')]
        serialized_data = await serialize_data(investor, SaleProfilesSerial)
        return Response(serialized_data)

    @swagger_auto_schema(operation_description="Create a new investor profile. Requires a valid subscription with remaining posts.",
        request_body=SaleProfilesSerial,responses={201: "{'status': True, 'message': 'Investor created successfully'}",
        403: "{'status': False, 'message': 'No valid subscription or remaining posts'}",400: "Returns validation errors or {'status': False, 'message': 'Token is not passed'}",})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                data = request.data.copy()
                data['user'] = user.id
                data['entity_type'] = 'investor'
                industry = data.get('industry', 'industry')
                sale = data.get('type_sale', 'sale')
                city = data.get('city', '...')
                state = data.get('state', '...')
                preference_list = json.loads(data.get("preference"))
                first_preference = preference_list[0] if preference_list else "Investment"
                data["title"] = f"{industry}, {first_preference}, {city}, {state}"
                data["single_desc"] = f'{first_preference} in {city}, {state}'
                subscribed = await check_subscription(user, "investor")
                if subscribed:
                    data['subscribed'] = True
                saved, resp = await create_serial(SaleProfilesSerial, data)
                if saved:
                    return Response({'status':True}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Update an existing investor profile by ID.",
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT,properties={'field_to_update': openapi.Schema(type=openapi.TYPE_STRING, description="Field to update"),},),
        responses={200: "{'status': True}",400: "Returns validation errors or {'status': False, 'message': 'Token is not passed'}",
        403: "{'status': False, 'message': 'User does not exist'}",404: "{'status': False, 'message': 'Investor not found'}",})
    async def patch(self,request,id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                investor = await SaleProfiles.objects.aget(id=id)
                saved, resp = await update_serial(SaleProfilesSerial, request.data, investor)
                if saved:
                    return Response({'status':True}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Delete an investor profile by ID. If `id` is 0, delete all investor profiles of the logged-in user.",
        responses={200: "{'status': True, 'message': 'Investor deleted successfully'}",403: "{'status': False, 'message': 'User does not exist'}",
        400: "{'status': False, 'message': 'Token is not passed'}",404: "{'status': False, 'message': 'Investor not found'}",},
        manual_parameters=[openapi.Parameter('id', openapi.IN_PATH,description="ID of the investor profile to delete. Use 0 to delete all profiles of the logged-in user.", type=openapi.TYPE_INTEGER, required=True),])
    async def delete(self,request,id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if id == 0:
                    async for profile in SaleProfiles.objects.filter(user=user, entity_type='investor'):
                        await profile.adelete()
                else:
                    profiles = await SaleProfiles.objects.aget(id=id)
                    await profiles.adelete()
                return Response({'status':True}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Franchise
class FranchiseList(APIView):
    @swagger_auto_schema(operation_description="Fetch franchise profiles. If `id` is 0, fetch all verified franchise profiles; otherwise, fetch franchise profiles created by the logged-in user.",
        responses={200: "Returns a serialized list of franchise profiles.",
        403: "{'status': False, 'message': 'User does not exist'}",400: "{'status': False, 'message': 'Token is not passed'}",},
        manual_parameters=[openapi.Parameter('id', openapi.IN_PATH, description="0 to fetch all verified franchise profiles; otherwise, fetch user's franchise profiles.", type=openapi.TYPE_INTEGER, required=True),])
    async def get(self,request,id):
        if id == 0:
            businesses = [posts async for posts in SaleProfiles.objects.filter(entity_type='franchise', block=False, verified=True, subscribed=True).order_by('-id')]
        else:
            exists, user = await check_user(request.headers.get('token'))
            if not exists:
                return Response({'status': False, 'message': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            businesses = [posts async for posts in SaleProfiles.objects.filter(entity_type='franchise', user=user, block=False).order_by('-id')]
        serialized_data = await serialize_data(businesses, SaleProfilesSerial)
        return Response(serialized_data)

    @swagger_auto_schema(operation_description="Create a new franchise profile. Requires a valid subscription with remaining posts.",
        request_body=SaleProfilesSerial,responses={201: "{'status': True, 'message': 'Franchise created successfully'}",
        403: "{'status': False, 'message': 'No valid subscription or remaining posts'}",400: "Returns validation errors or {'status': False, 'message': 'Token is not passed'}",})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                data = request.data.copy()
                data['user'] = user.id
                data['entity_type'] = 'franchise'
                industry = data.get('industry', 'industry')
                state = data.get('state', '...')
                offering = data.get('offering', 'Offering')
                data['title'] = f'{industry} {offering} in {state}'
                data['single_desc'] = f'{data.get("company", "Company")}, Established in {data.get("establish_yr", "2000")}, {data.get("total_outlets", "1")} Franchises, {state}'
                subscribed = await check_subscription(user, "franchise")
                if subscribed:
                    data['subscribed'] = True
                saved, resp = await create_serial(SaleProfilesSerial, data)
                print(resp)
                if saved:
                    return Response({'status':True, "message": "Franchise added successfully"}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Update an existing franchise profile by ID.",
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT,properties={'field_to_update': openapi.Schema(type=openapi.TYPE_STRING, description="Field to update"),},),
        responses={200: "{'status': True}",400: "Returns validation errors or {'status': False, 'message': 'Token is not passed'}",
        403: "{'status': False, 'message': 'User does not exist'}",404: "{'status': False, 'message': 'Franchise not found'}",})
    async def patch(self,request,id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                franchise = await SaleProfiles.objects.aget(id=id)
                saved, resp = await update_serial(SaleProfilesSerial, request.data, franchise)
                if saved:
                    return Response({'status':True}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Delete a franchise profile by ID. If `id` is 0, delete all franchise profiles of the logged-in user.",
        responses={200: "{'status': True, 'message': 'Franchise deleted successfully'}",403: "{'status': False, 'message': 'User does not exist'}",
        400: "{'status': False, 'message': 'Token is not passed'}",404: "{'status': False, 'message': 'Franchise not found'}",},
        manual_parameters=[openapi.Parameter('id', openapi.IN_PATH,description="ID of the franchise profile to delete. Use 0 to delete all profiles of the logged-in user.", type=openapi.TYPE_INTEGER, required=True),])
    async def delete(self,request,id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if id == 0:
                    async for profile in SaleProfiles.objects.filter(user=user, entity_type='franchise'):
                        await profile.adelete()
                else:
                    profiles = await SaleProfiles.objects.aget(id=id)
                    await profiles.adelete()
                return Response({'status':True}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Advisor
class AdvisorList(APIView):
    @swagger_auto_schema(operation_description="Advisor fetching",
    responses={200: "Advisor Details fetched succesfully",400:"Passes an error message"})
    async def get(self, request, id):
        if id == 0:
            advisor = [posts async for posts in SaleProfiles.objects.filter(entity_type='advisor', block=False, verified=True, subscribed=True).order_by('-id')]
        else:
            exists, user = await check_user(request.headers.get('token'))
            if not exists:
                return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
            advisor = [posts async for posts in SaleProfiles.objects.filter(entity_type='advisor', user=user, block=False).order_by('-id')]
        serialized_data = await serialize_data(advisor, SaleProfilesSerial)
        rate = await sync_to_async(lambda: {advisor_.id: (Testimonial.objects.filter(advisor=advisor_).aggregate(Avg('rate')) or 0) for advisor_ in advisor})()
        for advisor in serialized_data:
            advisor['average_rating'] = round(rate.get(advisor['id'])['rate__avg'], 1) if rate.get(advisor['id'])['rate__avg'] else 0
        return Response(serialized_data)

    @swagger_auto_schema(operation_description="Advisor creation",request_body=SaleProfilesSerial,
    responses={200: "{'status':True,'message': 'Advisor created successfully'}",400:"Passes an error message"})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                data = request.data.copy()
                data['user'] = user.id
                data['entity_type'] = 'advisor'
                city = data.get('city', '...')
                state = data.get('state', '...')
                data['title'] = f"{data.get('designation', 'Advisor')}, Financial Advisor, {data.get('city', '...')}, {data.get('state', '...')}"
                data['single_desc'] = f'Advisor in {data.get("city", "...")}, {data.get("state", "...")}'
                subscribed = await check_subscription(user, "advisor")
                if subscribed:
                    data['subscribed'] = True
                saved, resp = await create_serial(SaleProfilesSerial, data)
                if saved:
                    return Response({'status':True}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Advisor updation",request_body=SaleProfilesSerial,
    responses={200: "{'status':True,'message': 'Advisor updated successfully'}",400:"Passes an error message"})
    async def patch(self,request,id):
        if request.headers.get('token'): 
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                advisor = await SaleProfiles.objects.aget(id=id)
                saved, resp = await update_serial(SaleProfilesSerial, request.data, advisor)
                if saved:
                    return Response({'status':True}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Advisor deletion",request_body=SaleProfilesSerial,
    responses={200: "{'status':True,'message': 'Advisor deleted successfully'}",400:"Passes an error message"})
    async def delete(self,request,id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if id == 0:
                    async for profile in SaleProfiles.objects.filter(user=user, entity_type='advisor'):
                        await profile.adelete()
                else:
                    profiles = await SaleProfiles.objects.aget(id=id)
                    await profiles.adelete()
                return Response({'status':True}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Update Posts
class EditPosts(APIView):
    @swagger_auto_schema(operation_description="Update an existing post.",
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT,properties={'field_to_update': openapi.Schema(type=openapi.TYPE_STRING, description="Field to update"),},),
        responses={200: "{'status': True}",400: "Returns validation errors or {'status': False, 'message': 'Token is not passed'}",
        403: "{'status': False, 'message': 'User does not exist'}",404: "{'status': False, 'message': 'Business not found'}",})
    async def patch(self,request,id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                posts = await SaleProfiles.objects.aget(id=id)
                update_fields = []
                print(request.data)
                for field, value in request.data.items():
                    if hasattr(posts, field):
                        field_object = getattr(posts.__class__, field).field
                        if isinstance(field_object, models.FileField) and value == "null":
                            existing_file = getattr(posts, field)
                            if existing_file:
                                await sync_to_async(existing_file.delete)(save=False)
                            setattr(posts, field, None)
                            print("File deleted")
                        elif (isinstance(field_object, (models.FileField, models.CharField, models.IntegerField)) and value == ""):
                            setattr(posts, field, None)
                            print("Field Changed")
                        else:
                            setattr(posts, field, value)
                            print("Field updated")
                        update_fields.append(field)
                if update_fields:
                    await business.asave(update_fields=update_fields)
                return Response({'status': True}, status=status.HTTP_201_CREATED)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)


# User information
class UserView(APIView):
    @swagger_auto_schema(operation_description="Fetch details of the logged-in user based on the provided token.",
        responses={200: "User details are successfully retrieved.",403: "{'status': False, 'message': 'User does not exist'}",400: "{'status': False, 'message': 'Token is not passed'}",},
        manual_parameters=[openapi.Parameter('token', openapi.IN_HEADER,description="Authentication token of the logged-in user.",type=openapi.TYPE_STRING, required=True)])
    async def get(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                serialized_data = await get_serialize_data(user, UserSerial)
                return Response(serialized_data)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Update details of the logged-in user.",
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT,properties={'username': openapi.Schema(type=openapi.TYPE_STRING, description="Updated username of the user"),'email': openapi.Schema(type=openapi.TYPE_STRING, description="Updated email of the user"),
    'other_field': openapi.Schema(type=openapi.TYPE_STRING, description="Other fields as required"),}),
    responses={200: "{'status': True, 'message': 'User updated successfully'}",403: "{'status': False, 'message': 'User does not exist'}",400: "Returns validation errors or {'status': False, 'message': 'Token is not passed'}",})
    async def patch(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                already_exists = await UserProfile.objects.filter(Q(username=request.data.get('phone'))|Q(email=request.data.get('email'))& ~Q(id=user.id)).aexists() 
                if already_exists:
                    return Response({'status':False,'message': 'User with same details already exists'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                data = request.data.copy()
                if await AadhaarDetails.objects.filter(user=user).aexists():
                    details = await AadhaarDetails.objects.aget(user=user)
                    name = await sync_to_async(lambda: details.name)()
                    if data["first_name"].lower() != name.lower():
                        return Response({'status': False, 'message': 'Data not matching'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                    data['verified'] = True
                saved, resp = await update_serial(UserSerial, data, user)
                if saved:
                    return Response({'status':True,'message': 'User updated successfully'}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(
        operation_description="Delete the logged-in user's account.",
        responses={200: "{'status': True, 'message': 'User deleted successfully'}",403: "{'status': False, 'message': 'User does not exist'}",400: "{'status': False, 'message': 'Token is not passed'}",},
        manual_parameters=[openapi.Parameter('token', openapi.IN_HEADER,description="Authentication token of the logged-in user.", type=openapi.TYPE_STRING, required=True)])
    async def delete(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                user.deactivate = True
                user.deactivated_on = datetime.now().date()
                await user.asave()
                return Response({'status':True}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Search based on query and filtering
class Search(APIView):
    @swagger_auto_schema(operation_description="Search query fetching",
    responses={200: "Search query details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if request.GET.get('filter') == "false":
                    search = [posts async for posts in SaleProfiles.objects.filter(Q(title__icontains=request.GET.get('query')) | Q(single_desc__icontains=request.GET.get('query')), verified=True, subscribed=True)]
                else:
                    query = Q()
                    query = Q(name__icontains=request.GET.get('query')) | Q(company__icontains=request.GET.get('query')) & Q(verified=True)
                    if request.GET.get('city'):
                        query &= Q(city__icontains=request.GET.get('city'))
                    if request.GET.get('state'):
                        query &= Q(state__icontains=request.GET.get('state'))
                    if request.GET.get('industry'):
                        intustry_list = request.GET.get('industry') if isinstance(request.GET.get('industry'), list) else [request.GET.get('industry')]
                        query &= Q(industry__in=intustry_list)
                    if request.GET.get('entity_type'): 
                        entity_type_list = request.GET.get('entity_type') if isinstance(request.GET.get('entity_type'), list) else [request.GET.get('entity_type')]
                        query &= Q(entity_type__in=entity_type_list)
                    if request.GET.get('establish_from') and request.GET.get('establish_to'):
                        query &= Q(establish_yr__range=[request.GET.get('establish_from'),request.GET.get('establish_to')])
                    if request.GET.get('range_starting'):
                        query &= Q(range_starting__gte=float(request.GET.get('range_starting')))
                    if request.GET.get('range_ending'):
                        query &= Q(range_ending__lte=float(request.GET.get('range_ending')))
                    if request.GET.get('ebitda'):
                        query &= Q(ebitda__icontains=request.GET.get('ebitda'))
                    if request.GET.get('preference'):
                        query &= Q(preference__contains=request.GET.get('preference '))
                    if request.GET.get('top_selling'):
                        query &= Q(top_selling__icontains=request.GET.get('top_selling'))
                    search = [posts async for posts in SaleProfiles.objects.filter(query).exclude(subscribed=False)]
                serialized_data = await serialize_data(search, SaleProfilesSerial)
                return Response({'status':True,'data':serialized_data}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Wishlist
class Wishlists(APIView):
    @swagger_auto_schema(operation_description="Wishlist fetching",
    responses={200: "Wishlist Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                data = []
                async for posts in Wishlist.objects.filter(user=user).order_by('-id'):
                    product = await sync_to_async(lambda: posts.product)()
                    data.append(product)
                serialized_data = await serialize_data(data, SaleProfilesSerial)
                return Response(serialized_data)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Wishlist creation",request_body=SaleProfilesSerial,
    responses={200: "{'status':True,'message': 'Wishlist created successfully'}",400:"{'status':False,'error':'Already exists in wishlist'}"})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                # request.data['user'] = user.id
                # request.data['product'] = request.data.get('productId')
                data = request.data
                data['user'] = user.id
                data['product'] = request.data.get('productId')
                product = await SaleProfiles.objects.aget(id=request.data.get('productId'))
                already_exists = await Wishlist.objects.filter(user=user, product=product).aexists()
                if already_exists:
                    return Response({'status':False,'error':'Already exists in wishlist'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                saved, resp = await create_serial(WishlistSerial, data)
                if saved:
                    return Response({'status':True}, status=status.HTTP_201_CREATED)
                return Response(serializer.errors)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Wishlist deletion",request_body=SaleProfilesSerial,
    responses={200: "{'status':True,'message': 'Wishlist deleted successfully'}",400:"Passes an error message"})
    async def delete(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                lists = await Wishlist.objects.aget(user=user, product__id=request.GET.get('productId'))
                await lists.adelete()
                return Response({'status':True}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Recent Activities
class RecentActs(APIView):
    @swagger_auto_schema(operation_description="Recent Activity fetching",
    responses={200: "Recent Activity Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                data = []
                async for posts in RecentActivity.objects.filter(user=user).order_by('-id'):
                    product = await sync_to_async(lambda: posts.product)()
                    data.append(product)
                serialized_data = await serialize_data(data, SaleProfilesSerial)
                return Response(serialized_data)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Recent Activity creation",request_body=RecentSerial,
    responses={200: "{'status':True,'message': 'Recent Activity created successfully'}",400:"Passes an error message"})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                product = await SaleProfiles.objects.aget(id=request.data.get('productId'))
                product_user = await sync_to_async(lambda: product.user)()
                if user == product_user:
                    return Response({'status':False,'message': 'User cant add'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                if product.entity_type == "Advisor":
                    return Response({'status':False,'message': 'Advisor cant add'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                # request.data['user'] = user.id
                # request.data['product'] = request.data.get('productId')
                data = request.data
                data['user'] = user.id
                data['product'] = request.data.get('productId')

                ## Deleting and updating to front if the data is already in DB
                already_exists = await RecentActivity.objects.filter(user=user, product=product).aexists()
                if already_exists:
                    recent = await RecentActivity.objects.filter(user=user,product=product).adelete()
                    product.impressions -= 1
                saved, resp = await create_serial(RecentSerial, data)
                if saved:
                    product.impressions += 1
                    await product.asave()
                    return Response({'status':True}, status=status.HTTP_200_OK)
                return Response(serializer.errors)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Suggestions
class Suggests(APIView):
    @swagger_auto_schema(operation_description="Suggestion creation",request_body=SuggestSerial,
    responses={200: "{'status':True,'message': 'Suggestion created successfully'}",400:"Passes an error message"})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                # request.data['user'] = user.id
                data = request.data
                data['user'] = user.id
                saved, resp = await create_serial(SuggestSerial, data)
                if saved:
                    return Response({'status':True}, status=status.HTTP_200_OK)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Testimonials
class Testimonials(APIView):
    @swagger_auto_schema(operation_description="Testimonial fetching",
    responses={200: "Testimonial Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                # if request.GET.get('userId'):
                #     user = await UserProfile.objects.aget(id=request.GET.get('userId'))
                tests = [test async for test in Testimonial.objects.filter(advisor__id=request.GET.get('advisorId')).order_by('-id')]
                rate = await sync_to_async(lambda: Testimonial.objects.filter(advisor__id=request.GET.get('advisorId')).aggregate(Avg('rate')))()
                serialized_data = await serialize_data(tests, TestSerial)
                return Response({'data': serialized_data, 'avg_rating': rate['rate__avg']})
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Testimonial creation",request_body=TestSerial,
    responses={200: "{'status':True,'message': 'Testimonial created successfully'}",400:"Passes an error message"})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                # request.data['user'] = user.id
                data = request.data
                if request.data.get('advisorId') and await SaleProfiles.objects.filter(id=request.data.get('advisorId')).aexists():
                    advisor = await SaleProfiles.objects.aget(id=request.data.get('advisorId'))
                    user_id = await sync_to_async(lambda: advisor.user.id)()
                    if user_id == user.id:
                        return Response({'status':False,'message': 'User cant add'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                    room = [i async for i in Room.objects.filter(Q(first_person=user, second_person=user_id) | Q(first_person=user_id, second_person=user))]
                    print(room)
                    if not room:
                        return Response({'status':False,'message': 'Chat not done'}, status=status.HTTP_406_NOT_ACCEPTABLE)
                    messages = 0
                    for i in room:
                        messages += await ChatMessage.objects.filter(room=i).acount()
                    if messages < 5:
                        return Response({'status':False,'message': 'Chat not done'}, status=status.HTTP_406_NOT_ACCEPTABLE)
                    await Testimonial.objects.acreate(user=user, advisor=advisor, rate=request.data.get('rate'), testimonial=request.data.get('testimonial'))
                    return Response({'status':True}, status=status.HTTP_200_OK)
                return Response({'status':False,'message': 'Advisor doesnot exist'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Testimonial deletion",request_body=TestSerial,
    responses={200: "{'status':True,'message': 'Testimonial deleted successfully'}",400:"Passes an error message"})
    async def delete(self,request,id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                test = await Testimonial.objects.aget(id=id)
                await test.adelete()
                return Response({'status':True}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Recent Transactions
class Transactions(APIView):
    @swagger_auto_schema(operation_description="Transactions (Recent Updations) fetching",
    responses={200: "Transaction Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                activity_logs =[logs async for logs in ActivityLog.objects.all().order_by('-id')[:10]]
                serialized_data = await serialize_data(activity_logs, TransSerial)
                return Response(serialized_data)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Preferences
class Prefer(APIView):
    @swagger_auto_schema(operation_description="Get preference details for the user", 
    responses={200: "Preference details fetched successfully", 400: "Error message"})
    async def get(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                pref_exists = await Preference.objects.filter(user=user).aexists()
                if pref_exists:
                    preference = await Preference.objects.aget(user=user)
                    serialized_data = await get_serialize_data(preference, PrefSerial)
                    return Response(serialized_data)
                return Response({'status': False, 'message': 'Preference does not exist'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Preference details creation",request_body=PrefSerial,
    responses={200: "{'status':True,'message': 'Preference details created successfully'}",400:"Passes an error message"})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                already_exists = await Preference.objects.filter(user=user).aexists()
                if already_exists:
                    return Response({'status':True,'message': 'Preference already exist'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                # request.data['user'] = user.id
                data = request.data
                data['user'] = user.id
                saved, resp = await create_serial(PrefSerial, data)
                if saved:
                    return Response({'status':True}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Partially update preference details",
    request_body=PrefSerial,responses={200: "Preference details updated successfully",400: "Error message"})
    async def patch(self, request, id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                prefer = await Preference.objects.aget(id=id)
                saved, resp = await update_serial(PrefSerial, request.data, prefer)
                if saved:
                    return Response({'status':True,'message': 'Preference updated successfully'}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Delete preference details", 
    responses={200: "Preference details deleted successfully", 400: "Error message"})
    async def delete(self, request, id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                prefer = await Preference.objects.aget(id=id)
                await prefer.adelete()
                return Response({'status':True}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)																								   

# Recommended Posts
class Recommended(APIView):
    @swagger_auto_schema(operation_description="Recommended fetching using a users preference",
    responses={200: "Recommended Details using a users preference fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                preference = await Preference.objects.filter(user = user).aexists()
                if preference:
                    preference = await Preference.objects.aget(user = user)
                    query = Q()
                    if preference.industries:
                        query |= Q(industry__in=preference.industries)
                    # if preference.profile:
                    #     query |= Q(entity_type__in=preference.profile)
                    if request.GET.get('type') != "advisor":
                        if preference.price_starting is not None:
                            query |= Q(range_starting__gte=preference.price_starting)
                        if preference.price_starting is not None:
                            query |= Q(range_ending__lte=preference.price_ending)
                    if request.GET.get('type'):
                        query &= Q(entity_type=request.GET.get('type'), verified=True, subscribed=True)
                        products = [posts async for posts in SaleProfiles.objects.filter(query).order_by('-id')]
                        serialized_data = await serialize_data(products, SaleProfilesSerial)
                    else:
                        query &= Q(verified=True, subscribed=True)
                        products = [posts async for posts in SaleProfiles.objects.filter(query).order_by('-id')]
                        serialized_data = await serialize_data(products, SaleProfilesSerial)
                else:
                    products = [posts async for posts in SaleProfiles.objects.filter(verified=True, subscribed=True).order_by('-id')[:10]]
                    serialized_data = await serialize_data(products, SaleProfilesSerial)
                if request.GET.get('type') == "advisor":
                    rate = await sync_to_async(lambda: {advisor_.id: (Testimonial.objects.filter(advisor=advisor_).aggregate(Avg('rate')) or 0) for advisor_ in products})()
                    for advisor in serialized_data:
                        advisor['average_rating'] = round(rate.get(advisor['id'])['rate__avg'], 1) if rate.get(advisor['id'])['rate__avg'] else 0
                return Response(serialized_data)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Banner Passing
class Banners(APIView):
    @swagger_auto_schema(operation_description="Banner fetching",
    responses={200: "Banner Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if not request.GET.get('type'):
            banners = [banner async for banner in Banner.objects.filter(validity_date__gte=timezone.now()).order_by('-id')[:5]]
        else:
            banners = [banner async for banner in Banner.objects.filter(type=request.GET.get('type'), validity_date__gte=timezone.now()).order_by('-id')[:5]]
        serialized_data = await serialize_data(banners, BannerSerial)
        return Response(serialized_data)

# Plans
class Plans(APIView):
    @swagger_auto_schema(operation_description="Plans fetching", 
    responses={200: "Plans Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if request.GET.get('type'):
            plan = [plans async for plans in Plan.objects.filter(type=request.GET.get('type')).order_by('-id')]
        else:
            plan = [plans async for plans in Plan.objects.all().order_by('-id')]
        serialized_data = await serialize_data(plan, PlanSerial)
        for i in serialized_data:
            i['key'] = settings.RAZORPAY_API_KEY
        return Response(serialized_data)

# Razorpay Order data fetching
class RazorOrder(APIView):
    @swagger_auto_schema(operation_description="Order data fetching", 
    responses={200: "Order data fetching",400: "Passes an error message"})
    async def get(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if await Plan.objects.filter(id=request.GET.get('id')).aexists():
                    plan = await Plan.objects.aget(id=request.GET.get('id'))
                    order_amount = await sync_to_async(lambda: plan.rate)()
                    order_data = await sync_to_async(create_order)(order_amount)
                    return Response(order_data)
                return Response({'status':False,'message': 'Plan doesnot exist'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Check subscriptions
class Subscribe(APIView):
    @swagger_auto_schema(operation_description="Subscription fetching",
    responses={200: "Subscription Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if request.GET.get('type'):
                    if await Subscription.objects.filter(user=user, plan__type=request.GET.get('type')).aexists():
                        subscription = await Subscription.objects.aget(user=user, plan__type=request.GET.get('type'))
                        remaining_posts = await sync_to_async(lambda: subscription.remaining_posts)()
                        expiry_date = await sync_to_async(lambda: subscription.expiry_date)()
                        if subscription.remaining_posts != 0 and subscription.expiry_date >= timezone.now().date():
                            plan = await sync_to_async(lambda: subscription.plan)()
                            plan_data = await sync_to_async(lambda: PlanSerial(plan).data)()
                            plan_id = await sync_to_async(lambda: subscription.plan.id)()
                            return Response({'status':True, 'id':plan_id, 'posts':remaining_posts, "expiry":expiry_date, 'plan':plan_data})
                    return Response({'status':False,'message': 'Subscription doesnot exist'}, status=status.HTTP_404_NOT_FOUND)
                else:
                    if await Subscription.objects.filter(user=user).aexists():
                        return Response({'status':True})
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Subscrided plan details creation",request_body=SubscribeSerial,
    responses={200: "{'status':True,'message': 'Subscrided plan details created successfully'}",400:"Passes an error message"})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if await Plan.objects.filter(id=request.data.get('id')).aexists():
                    plan = await Plan.objects.aget(id=request.data.get('id'))
                    print(plan)
                    order_amount = await sync_to_async(lambda: plan.rate)()
                    print(order_amount)
                    verified, payment_details = await sync_to_async(verify_payment)(request.data.get('transaction_id'), order_amount)
                    if verified:
                        if not await Subscription.objects.filter(user=user, plan__type=plan.type).aexists():
                            data = request.data
                            data['user'] = user.id
                            data['expiry_date'] = (timezone.now() + relativedelta(months=plan.time_period)).strftime('%Y-%m-%d')
                            data['remaining_posts'] = plan.post_number
                            data['plan'] = plan.id
                            saved, resp = await create_serial(SubscribeSerial, data)
                            if saved:
                                return Response({'status':True}, status=status.HTTP_200_OK)
                            return Response(resp)
                        subscribe = await Subscription.objects.aget(user=user, plan__type=plan.type)
                        subscribe.plan = plan
                        subscribe.expiry_date = (timezone.now() + relativedelta(months=plan.time_period)).date()
                        subscribe.remaining_posts = plan.post_number
                        await subscribe.asave()
                        return Response({'status':True}, status=status.HTTP_200_OK)
                    else:
                        return Response({'status':False,'message': f'Transaction not found {payment_details}' })
                return Response({'status':False,'message': 'Plan doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Featured Posts
class Featured(APIView):
    @swagger_auto_schema(operation_description="Featured fetching",
    responses={200: "Featured Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        data = []
        if request.GET.get('type'):
            product = SaleProfiles.objects.filter(entity_type=request.GET.get('type'), verified=True, subscribed=True).order_by('-id')
            serial = SaleProfilesSerial
        else:
            product = SaleProfiles.objects.filter(verified=True, subscribed=True)
            serial = SaleProfilesSerial
        async for i in product:
            user_id = await sync_to_async(lambda: i.user)()
            if await Subscription.objects.filter(user=user_id, plan__type=request.GET.get('type')).aexists():
                subscribed = await Subscription.objects.aget(user=user_id, plan__type=request.GET.get('type'))
                plan_id = await sync_to_async(lambda: subscribed.plan.id)()
                plan = await Plan.objects.aget(id = plan_id)
                if plan.feature:
                    data.append(i)
        serialized_data = await serialize_data(data, serial)
        if request.GET.get('type') == "advisor":
            rate = await sync_to_async(lambda: {advisor_.id: (Testimonial.objects.filter(advisor=advisor_).aggregate(Avg('rate')) or 0) for advisor_ in product})()
            for advisor in serialized_data:
                advisor['average_rating'] = round(rate.get(advisor['id'])['rate__avg'], 1) if rate.get(advisor['id'])['rate__avg'] else 0
        return Response(serialized_data)

# Latest Posts
class Latest(APIView):
    @swagger_auto_schema(operation_description="Latest Posts fetching",
    responses={200: "Latest Posts Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if request.GET.get('type'):
            product = [post async for post in SaleProfiles.objects.filter(entity_type=request.GET.get('type'), verified=True, subscribed=True).order_by('-id')[:10]]
            serial = SaleProfilesSerial
        else:
            product = [post async for post in SaleProfiles.objects.filter(verified=True, subscribed=True).order_by('-id')[:10]]
            serial = SaleProfilesSerial
        serialized_data = await serialize_data(product, serial)
        if request.GET.get('type') == "advisor":
            rate = await sync_to_async(lambda: {advisor_.id: (Testimonial.objects.filter(advisor=advisor_).aggregate(Avg('rate')) or 0) for advisor_ in product})()
            for advisor in serialized_data:
                advisor['average_rating'] = round(rate.get(advisor['id'])['rate__avg'], 1) if rate.get(advisor['id'])['rate__avg'] else 0
        return Response(serialized_data)

# Notification
class Notifications(APIView):
    @swagger_auto_schema(operation_description="Notifications fetching",
    responses={200: "Notifications Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                noti = [item async for item in user.notifications.all().order_by('-id')]
                serialized_data = await serialize_data(noti, NotiSerial)
                return Response(serialized_data)
            return Response({'status':False, 'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False, 'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Read notification",
    responses={200: "Notifications Details fetched succesfully",400:"Passes an error message"})
    async def patch(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:

                @sync_to_async
                def update_notification(user):
                    for item in user.notifications.all():
                        item.read_by.add(user)
                        item.save()

                await update_notification(user)

                return Response({'status':True}, status=status.HTTP_200_OK)
            return Response({'status':False, 'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False, 'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Notification deletion",request_body=NotiSerial,
    responses={200: "{'status':True,'message': 'Notification deleted successfully'}",400:"Passes an error message"})
    async def delete(self,request,id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                noti = await Notification.objects.aget(id=id)
                await noti.user.aremove(user)
                return Response({'status':True}, status=status.HTTP_200_OK)
            return Response({'status':False, 'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False, 'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Graph details passing
class Graph(APIView):
    @swagger_auto_schema(operation_description="Graph data fetching",
    responses={200: "Graph Details fetched succesfully",400:"Passes an error message"})
    async def get(self,request):
        businessData = SaleProfiles.objects.filter(entity_type='business', verified=True, subscribed=True).annotate(month=ExtractMonth("listed_on")).values("month").annotate(total_rate=Sum("range_starting")).values("month", "total_rate")[:5]
        investorData = SaleProfiles.objects.filter(entity_type='investor', verified=True, subscribed=True).annotate(month=ExtractMonth("listed_on")).values("month").annotate(total_rate=Sum("range_starting")).values("month", "total_rate")[:5]
        franchiseData = SaleProfiles.objects.filter(entity_type='franchise', verified=True, subscribed=True).annotate(month=ExtractMonth("listed_on")).values("month").annotate(total_rate=Sum("range_starting")).values("month", "total_rate")[:5]
        investAmount=0
        totalAmount = 0
        async for i in investorData:
            if i['total_rate'] != None:
                investAmount += int(i['total_rate'])
        async for i in businessData:
            if i['total_rate'] != None:
                totalAmount += int(i['total_rate'])
        async for i in investorData:
            if i['total_rate'] != None:
                totalAmount += int(i['total_rate'])
        totalAmount += investAmount
        return Response({"business":businessData,"investor":investorData,"franchise":franchiseData,"total":totalAmount,"invest":investAmount}, status=status.HTTP_200_OK)

# Contact Us
class Contact(APIView):
    @swagger_auto_schema(operation_description="Business creation",request_body=ContactSerial,
    responses={200: "{'status':True,'message': 'Contact created successfully'}",400:"Passes an error message"})
    async def post(self,request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                saved, resp = await create_serial(ContactSerial, request.data)
                if saved:
                    return Response({'status':True}, status=status.HTTP_201_CREATED)
                return Response(resp)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Check userid of logged user
class User(APIView):
    @swagger_auto_schema(operation_description="Fetch the User ID based on the authentication token.",
    manual_parameters=[openapi.Parameter('token', openapi.IN_HEADER,description="Authentication token of the logged-in user.",type=openapi.TYPE_STRING,required=True)],
    responses={200: openapi.Response(description="User ID fetched successfully."),403: openapi.Response(description="User does not exist or is blocked."),400: openapi.Response(description="Token is not passed."),})
    async def get(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                return Response({'status': True, 'userId': user.id}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Update onesignal id of a user after login
class OneSignal(APIView):
    @swagger_auto_schema(operation_description="Update the user's OneSignal ID based on the authentication token.",
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT,properties={'onesignal_id': openapi.Schema(type=openapi.TYPE_STRING, description='The new OneSignal ID to be updated.')},
    required=['onesignal_id']),
    responses={200: openapi.Response(description="OneSignal ID updated successfully."),400: openapi.Response(description="Invalid request or missing token."),
    403: openapi.Response(description="User does not exist or is blocked."),409: openapi.Response(description="OneSignal ID already exists."),})
    async def post(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if user.onesignal_id != request.data.get('onesignal_id'):
                    user.onesignal_id = request.data.get('onesignal_id')
                    await user.asave()
                    return Response({'status': True}, status=status.HTTP_200_OK)
                return Response({'status':False,'message': 'Onesignal id already exist'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Popular searched items
class Popularsearch(APIView):
    @swagger_auto_schema(operation_description="Fetching popular searched items", responses={200: "Featured Details fetched successfully", 400: "Passes an error message"})
    async def get(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                popular_searches = [act async for act in Activity.objects.all().order_by('-count')[:10]]
                serialized_data = await serialize_data(popular_searches, ActivitySerial)
                return Response(serialized_data)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Record or increment count of a searched item", request_body=ActivitySerial, responses={201: "Interaction recorded successfully", 400: "Error message"})
    async def post(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if await SaleProfiles.objects.filter(id=request.data.get('post_id'), verified=True).aexists():
                    post = await SaleProfiles.objects.aget(id=request.data.get('post_id'), verified=True)
                    if not await Activity.objects.filter(post=post).aexists():
                        created = await Activity.objects.acreate(post=post, count=1)
                    else:
                        activity = await Activity.objects.aget(post=post)
                        activity.count += 1
                        await activity.asave()
                    return Response({'status': True, 'message': 'Interaction recorded successfully'}, status=status.HTTP_201_CREATED)
                return Response({'status':False,'message': 'Posts doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

    @swagger_auto_schema(operation_description="Delete a specific activity", responses={200: "Activity deleted successfully", 400: "Error message"})
    async def delete(self, request, id):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                activity = await Activity.objects.aget(id=id)
                await activity.adelete()
                return Response({'status': True, 'message': 'Activity deleted successfully'}, status=status.HTTP_200_OK)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Recent searched Items
# class RecentSearchview(APIView):
#     @swagger_auto_schema(operation_description="Fetching Recently viewed items", responses={200: "Fetched successfully", 400: "Passes an error message"})
#     async def get(self, request):
#         if request.headers.get('token'):
#             exists, user = await check_user(request.headers.get('token'))
#             if exists:
#                 recent_views = [acts async for acts in Activity.objects.filter(user=user).order_by('-created')[:10]]
#                 serialized_data = await serialize_data(recent_views, ActivitySerial)
#                 return Response(serialized_data)
#             return Response({'status': False, 'message': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
#         return Response({'status': False, 'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

#     @swagger_auto_schema(operation_description="Record or increment count of a viewed item", request_body=ActivitySerial, responses={201: "Interaction recorded successfully", 400: "Error message"})
#     async def post(self, request):
#         if request.headers.get('token'):
#             exists, user = await check_user(request.headers.get('token'))
#             if exists:
#                 post = await SaleProfiles.objects.aget(id=request.data.get('post_id'))
#                 if await Activity.objects.filter(user=user, post=post).aexists():
#                     activity = await Activity.objects.aget(user=user, post=post)
#                     await activity.adelete()
#                 activity = await Activity.objects.acreate(user=user, post=post)
#                 await activity.asave()
#                 return Response({'status': True, 'message': 'Interaction recorded successfully'}, status=status.HTTP_201_CREATED)
#                 return Response({'status': False, 'message': 'Interaction already exists'}, status=status.HTTP_201_CREATED)
#             return Response({'status': False, 'message': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
#         return Response({'status': False, 'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

#     @swagger_auto_schema(operation_description="Delete a specific activity", responses={200: "Activity deleted successfully", 400: "Error message"})
#     async def delete(self, request, id):
#         if request.headers.get('token'):
#             exists, user = await check_user(request.headers.get('token'))
#             if exists:
#                 activity = await Activity.objects.aget(id=id, user=user)
#                 await activity.adelete()
#                 return Response({'status': True, 'message': 'Activity deleted successfully'}, status=status.HTTP_200_OK)
#             return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
#         return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Report a Post
class ReportPost(APIView):
    @swagger_auto_schema(operation_description="Report a post or profile",
    request_body=openapi.Schema(type=openapi.TYPE_OBJECT, required=['id', 'reason', 'reason_type'],
    properties={'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID of the post or profile to report'),
    'reason': openapi.Schema(type=openapi.TYPE_STRING, description='Reason for reporting'),
    'reason_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of reason (e.g., "spam", "harassment")'),}),
    responses={200: "{'status':True,'message': 'Reported successfully'}", 400: "{'status':False,'message': 'Invalid ID, reason, or reason type'}"})
    async def post(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if request.data.get('id') or request.data.get('reason_type'):
                    reason = None
                    if request.data.get('reason'):
                        reason = request.data.get('reason')

                    # Check if the post is reporting
                    if await SaleProfiles.objects.filter(id=request.data.get('id')).aexists():
                        report_post = await SaleProfiles.objects.aget(id=request.data.get('id'))
                        report = Report(report_post=report_post, reason=reason, reason_type=request.data.get('reason_type'), reported_by=user, report_type='post')
                        await report.asave()
                        return Response({'status': True, 'message': 'Post reported successfully'}, status=status.HTTP_200_OK)

                    # # Check if the profile is reporting
                    # elif await Profile.objects.filter(id=request.data.get('id')).aexists():
                    #     reported_profile = await Profile.objects.aget(id=request.data.get('id'))
                    #     report = Report(reported_profile=reported_profile, reason=reason, reason_type=request.data.get('reason_type'), reported_by=user, report_type='profile')
                    #     await report.asave()
                    #     return Response({'status': True, 'message': 'Profile reported successfully'}, status=status.HTTP_200_OK)
                return Response({'status': False, 'message': 'Invalid ID, reason, type(Post or Profile) or reason type'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Recently made enquiries
class RecentEnquiries(APIView):
    @swagger_auto_schema(operation_description="Fetch recent enquiries", responses={200: "{'status':True,'message': 'Fetched successfully'}"})
    async def get(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                if request.GET.get('id'):
                    user_posts = await SaleProfiles.objects.filter(user=user, id=request.GET.get('id')).aexists()
                    if user_posts:
                        recent_enqs = [enqs async for enqs in Enquiries.objects.filter(post__id=request.GET.get('id')).order_by('-created')[:10]]
                        serialized_data = await serialize_data(recent_enqs, EnqSerial)
                        user_data = await sync_to_async(lambda: {enq.id: enq.post.user.id for enq in recent_enqs})()
                        for enq in serialized_data:
                            enq['user_id'] = user_data.get(enq['id'])
                        return Response(serialized_data)
                    return Response({'status': False, 'message': 'No post found'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                return Response({'status': False, 'message': 'Post type param not found'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Count of enquiries
class EnquiriesCounts(APIView):
    @swagger_auto_schema(operation_description="Fetch enquiries counts", responses={200: "{'status':True,'message': 'Fetched successfully'}"})
    async def get(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            impression = 0
            if exists:
                if request.GET.get('id'):
                    user_posts = await SaleProfiles.objects.filter(user=user, id=request.GET.get('id')).aexists()
                    if user_posts:
                        async for posts in SaleProfiles.objects.filter(user=user, id=request.GET.get('id')):
                            impression += posts.impressions
                        today = timezone.localtime()
                        yesterday = today - timedelta(days=1)
                        today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
                        today_end = today_start + timedelta(days=1)
                        
                        # Get start and end of yesterday
                        yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
                        yesterday_end = yesterday_start + timedelta(days=1)
                        yesterday_enqs = await Enquiries.objects.filter(post__id=request.GET.get('id'), created__gte=yesterday_start, created__lt=yesterday_end).acount()
                        today_enqs = await Enquiries.objects.filter(post__id=request.GET.get('id'), created__gte=today_start, created__lt=today_end).acount()
                        total_enqs = await Enquiries.objects.filter(post__id=request.GET.get('id')).acount()
                        return Response({'status': True, 'impressions':impression, 'today_count': today_enqs, 'yesterday_count': yesterday_enqs, 'total_count': total_enqs})
                    return Response({'status': False, 'message': 'User has not added any posts in the requested type'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                return Response({'status': False, 'message': 'Post type param not found'}, status=status.HTTP_404_NOT_FOUND)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Filter data from posts
class FilterPosts(APIView):
    @swagger_auto_schema(operation_description="Filtering posts", responses={200: "{'status':True,'message': 'Filtering posts'}"})
    async def get(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                query = Q()
                if request.GET.get('entity_type'):
                    query = Q(entity_type__icontains=request.GET.get('entity_type')) & Q(verified=True)
                    if request.GET.get('city'):
                        query &= Q(city__icontains=request.GET.get('city'))
                    if request.GET.get('industry'):
                        query &= Q(industry__icontains=request.GET.get('industry'))
                    if request.GET.get('entity'):
                        query &= Q(entity__icontains=request.GET.get('entity'))
                    if request.GET.get('ebitda'):
                        query &= Q(ebitda__range=(0, request.GET.get('ebitda')))
                    if request.GET.get('preference'):
                        query &= Q(preference__in=request.GET.get('preference'))
                    if request.GET.get('year_starting') and request.GET.get('year_ending'):
                        query &= Q(establish_yr__range=(request.GET.get('year_starting'), request.GET.get('year_ending')))
                    if request.GET.get('range_starting') and request.GET.get('range_ending'):
                        query &= Q(range_starting__gte=float(request.GET.get('range_starting'))) & Q(range_ending__lte=float(request.GET.get('range_ending')))
                    search = [posts async for posts in SaleProfiles.objects.filter(query)]
                    serialized_data = await serialize_data(search, SaleProfilesSerial)
                    return Response({'status':True,'data':serialized_data}, status=status.HTTP_200_OK)
                return Response({'status':False,'message': 'Entity type not passed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)

# Aadhaar Details
class AadharInfo(APIView):
    @swagger_auto_schema(operation_description="save aadhar data",request_body=AadhaarSerial,
    responses={200: "{'status':True,'message': 'saved successfully'}",400:"Passes an error message"})
    async def post(self, request):
        if request.headers.get('token'):
            exists, user = await check_user(request.headers.get('token'))
            if exists:
                data = request.data
                data['user'] = user.id
                profile = data['profile_image']
                decoded_file = base64.b64decode(profile)
                file = ContentFile(decoded_file, name=f"aadhar_profile_{user.username}.jpg")
                data['profile_image'] = file
                print(data)
                if not await AadhaarDetails.objects.filter(user=user).aexists():
                    saved, resp = await create_serial(AadhaarSerial, data)
                    if saved:
                        aadhar_name = resp.name
                if data['name'].lower() != user.first_name.lower():
                    return Response({'status': False, 'message': 'Data not matching'}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                user.verified = True
                await user.asave()
                return Response({'status': True, 'message': 'Aadhaar data saved successfully'}, status=status.HTTP_201_CREATED)
            return Response({'status':False,'message': 'User doesnot exist'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status':False,'message': 'Token is not passed'}, status=status.HTTP_401_UNAUTHORIZED)