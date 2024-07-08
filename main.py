from sanic import Sanic, response
from sanic.request import Request
from tortoise import Tortoise
from tortoise.contrib.sanic import register_tortoise
import bcrypt
from models import User, Channel, ChannelType, ChannelMember, Message
import uuid

app = Sanic("ChatApp")


async def check_user_exists(username: str) -> bool:
    return await User.filter(username=username).exists()


async def verify_credentials(username: str, password: str) -> bool:
    user = await User.filter(username=username).first()
    if not user:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8'))


async def user_has_access_to_channel(user_id: int, channel_id: int) -> bool:
    # Retrieve the channel type and members
    channel = await Channel.filter(id=channel_id).prefetch_related("members").first()

    if not channel:
        return False  # Channel not found

    if channel.type == ChannelType.PUBLIC_CHAT:
        return True  # All users have access to public chats

    if channel.type in (ChannelType.DM, ChannelType.GROUP_CHAT):
        # Check if user is in the list of members
        return await ChannelMember.filter(user_id=user_id, channel_id=channel_id).exists()

    return False


async def init_db():
    # Ensure at least one public chat exists
    if not await Channel.filter(type=ChannelType.PUBLIC_CHAT.value).exists():
        await Channel.create(type=ChannelType.PUBLIC_CHAT)
        print("Public chat channel created.")
    else:
        print("Public chat channel already exists.")


@app.listener('after_server_start')
async def setup_db(_, __):
    await init_db()  # Initialize the database and check for required initial data


# Utility function for password hashing
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


@app.route("/")
async def index(request):
    return response.json({'state': 'running'})


@app.post('/sign-up')
async def sign_up(request):
    print(request.json)
    data = request.json
    if not all(key in data for key in ('username', 'password', 'name')):
        return response.json({'state': 'missing-fields'}, status=400)
    if await User.filter(username=data.username).exists():
        return response.json({'state': 'user-already-exists'}, status=400)
    data.password = hash_password(data.password)
    user_obj = await User.create(id=uuid.uuid4(), **data)
    return response.json({'state': 'user-created', 'user_id': user_obj.id})


@app.post('/login-in')
async def login(request):
    username = request.json.get('username')
    password = request.json.get('password')
    if not await check_user_exists(username):
        return response.json({'state': 'email-not-registered'}, status=404)
    if not await verify_credentials(username, password):
        return response.json({'state': 'wrong-password'}, status=403)
    return response.json({'state': 'correct-credentials'})


@app.post('/get-messages/<channel_id:int>')
async def get_messages(request, channel_id):
    username = request.json.get('username')
    password = request.json.get('password')
    if not await verify_credentials(username, password):
        return response.json({'state': 'wrong-credentials'}, status=403)
    if not await user_has_access_to_channel(username, channel_id):
        return response.json({'state': 'no-access'}, status=403)

    messages = await Message.filter(channel_id=channel_id).order_by('created_at')
    return response.json({'messages': [msg.to_dict() for msg in messages]})


@app.post('/send-message/<channel_id:int>')
async def send_message(request, channel_id):
    username = request.json.get('username')
    password = request.json.get('password')
    message_text = request.json.get('message')
    if not await verify_credentials(username, password):
        return response.json({'state': 'wrong-credentials'}, status=403)

    if not await user_has_access_to_channel(username, channel_id):
        return response.json({'state': 'no-access'}, status=403)

    message_obj = await Message.create(content=message_text, author_id=username, channel_id=channel_id)
    return response.json({'state': 'message-sent', 'message_id': message_obj.id})


register_tortoise(
    app,
    db_url='sqlite://database.db',  # Adjust the database URL as needed
    modules={"models": ["models"]},  # Adjust the path to your model module
    generate_schemas=True
)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
