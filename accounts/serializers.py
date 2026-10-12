from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}, 'email': {'required': True, 'allow_blank': False}}

    def validate(self, attrs):
        try:
            validate_password(attrs['password'], User(username=attrs['username'], email=attrs['email']))
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': e.messages})  # shown under the password field
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)  # hashes the password
