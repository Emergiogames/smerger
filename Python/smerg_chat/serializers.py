from rest_framework import serializers
from .models import *
from smerg_app.serializers import *
from .utils.enc_utils import decrypt_message
from html import unescape

class RoomSerial(serializers.ModelSerializer):
    last_msg = serializers.SerializerMethodField()
    first_person = UserSerial(read_only=True)
    second_person = UserSerial(read_only=True)
    post = SaleProfilesSerial(read_only=True)

    class Meta:
        model = Room
        fields = '__all__'

    def get_last_msg(self, obj):
        return decrypt_message(obj.last_msg)

class ChatSerial(serializers.ModelSerializer):
    message = serializers.SerializerMethodField()
    sended_by = UserSerial(read_only=True)
    sended_to = UserSerial(read_only=True)

    class Meta:
        model = ChatMessage
        fields = '__all__'

    def get_message(self, obj):
        return decrypt_message(obj.message)