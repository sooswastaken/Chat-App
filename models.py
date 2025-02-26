from enum import Enum

from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class User(models.Model):
    id = fields.CharField(pk=True, unique=True, max_length=255)
    username = fields.CharField(max_length=255, unique=True)
    password = fields.CharField(max_length=255)  # Consider hashing passwords in practice
    name = fields.CharField(max_length=255)

    class Meta:
        table = "users"

    def json(self):
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name
        }


# Define an Enum for Channel Types
class ChannelType(Enum):
    DM = 'dm'
    GROUP_CHAT = 'group_chat'
    PUBLIC_CHAT = 'public_chat'


# Model Definition
class Channel(models.Model):
    name = fields.CharField(max_length=255)
    id = fields.CharField(pk=True, unique=True, max_length=255)
    type = fields.CharEnumField(enum_type=ChannelType, default=ChannelType.PUBLIC_CHAT)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "channels"

    def json(self):
        return {
            "name": self.name,
            "id": self.id,
            "type": self.type,
            "created_at": int(self.created_at.timestamp())
        }


class ChannelMember(models.Model):
    user = fields.ForeignKeyField('models.User', related_name='channel_membership')
    channel = fields.ForeignKeyField('models.Channel', related_name='user_membership')

    class Meta:
        table = "channel_members"

    def json(self):
        return {
            "user": self.user.id,
            "channel_name": self.channel.name,
            "channel_id": self.channel.id
        }


class Message(models.Model):
    id = fields.CharField(pk=True, unique=True, max_length=255)
    content = fields.TextField()
    author = fields.ForeignKeyField('models.User', related_name='messages')
    channel = fields.ForeignKeyField('models.Channel', related_name='messages')
    created_at = fields.DatetimeField(auto_now_add=True)

    def json(self):
        return {
            "id": self.id,
            "content": self.content,
            "author": self.author.id,
            "author_name": self.author.name,
            "channel_id": self.channel.id,
            "created_at": int(self.created_at.timestamp())
        }

    class Meta:
        table = "messages"


# Pydantic models for data validation
User_Pydantic = pydantic_model_creator(User, name="User")
UserIn_Pydantic = pydantic_model_creator(User, name="UserIn", exclude_readonly=True)
Message_Pydantic = pydantic_model_creator(Message, name="Message")
MessageIn_Pydantic = pydantic_model_creator(Message, name="MessageIn", exclude_readonly=True)
