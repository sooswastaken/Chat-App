from enum import Enum

from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator


class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=255, unique=True)
    password = fields.CharField(max_length=255)  # Consider hashing passwords in practice
    name = fields.CharField(max_length=255)

    class Meta:
        table = "users"


# Define an Enum for Channel Types
class ChannelType(Enum):
    DM = 'dm'
    GROUP_CHAT = 'group_chat'
    PUBLIC_CHAT = 'public_chat'


# Model Definition
class Channel(models.Model):
    id = fields.IntField(pk=True)
    type = fields.CharEnumField(enum_type=ChannelType, default=ChannelType.PUBLIC_CHAT)
    members = fields.ManyToManyField('models.User', related_name='channels', through='channel_members')

    class Meta:
        table = "channels"


class ChannelMember(models.Model):
    user = fields.ForeignKeyField('models.User', related_name='channel_membership')
    channel = fields.ForeignKeyField('models.Channel', related_name='user_membership')

    class Meta:
        table = "channel_members"


class Message(models.Model):
    id = fields.IntField(pk=True)
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
            "channel": self.channel.id,
            "created_at": int(self.created_at.timestamp())
        }

    class Meta:
        table = "messages"


# Pydantic models for data validation
User_Pydantic = pydantic_model_creator(User, name="User")
UserIn_Pydantic = pydantic_model_creator(User, name="UserIn", exclude_readonly=True)
Message_Pydantic = pydantic_model_creator(Message, name="Message")
MessageIn_Pydantic = pydantic_model_creator(Message, name="MessageIn", exclude_readonly=True)
