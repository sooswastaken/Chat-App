import asyncio
import json

from sanic import Sanic, response, Websocket
from tortoise.contrib.sanic import register_tortoise
import bcrypt
from models import User, Channel, ChannelType, ChannelMember, Message
import uuid
from sanic_cors import CORS

app = Sanic("ChatApp")
CORS(app)


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
        await Channel.create(type=ChannelType.PUBLIC_CHAT, id=uuid.uuid4().int % (2 ** 63 - 1))
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
    print(data)
    if not all(key in data for key in ('username', 'password', 'name')):
        return response.json({'state': 'missing-fields'}, status=400)
    if await User.filter(username=data["username"]).exists():
        return response.json({'state': 'user-already-exists'}, status=400)
    data["password"] = hash_password(data["password"])
    print(uuid.uuid4().int % (2 ** 63 - 1))
    user_obj = await User.create(id=uuid.uuid4().int % (2 ** 63 - 1), **data)
    return response.json({'state': 'user-created', 'user_id': user_obj.id})


@app.post('/login')
async def login(request):
    username = request.json.get('username')
    password = request.json.get('password')
    if not await check_user_exists(username):
        return response.json({'state': 'email-not-registered'}, status=404)
    if not await verify_credentials(username, password):
        return response.json({'state': 'wrong-password'}, status=403)
    return response.json({'state': 'correct-credentials'})


@app.post('/get-messages/<channel_id>')
async def get_messages(request, channel_id):
    username = request.json.get('username')
    password = request.json.get('password')
    if not await verify_credentials(username, password):
        return response.json({'state': 'wrong-credentials'}, status=403)

    if channel_id == "public-chat":
        channel = await Channel.filter(type=ChannelType.PUBLIC_CHAT.value).first()
        messages = await Message.filter(channel=channel).order_by('created_at').prefetch_related('author',
                                                                                                 'channel').all()
        return response.json({'messages': [msg.json() for msg in messages]})
    else:
        channel_id = int(channel_id)
    if not await user_has_access_to_channel(username, channel_id):
        return response.json({'state': 'no-access'}, status=403)

    messages = await Message.filter(channel_id=channel_id).order_by('created_at')
    return response.json({'messages': [msg.to_dict() for msg in messages]})


@app.post('/send-message/<channel_id>')
async def send_message(request, channel_id):
    username = request.json.get('username')
    password = request.json.get('password')
    message_text = request.json.get('message')
    if not await verify_credentials(username, password):
        return response.json({'state': 'wrong-credentials'}, status=403)

    user = await User.filter(username=username).first()

    if channel_id == "public-chat":
        channel = await Channel.filter(type=ChannelType.PUBLIC_CHAT.value).first()
        message_obj = await Message.create(content=message_text, author_id=user.id, channel=channel,
                                           id=uuid.uuid4().int % (2 ** 63 - 1))
        # pre-fetch the author and channel to avoid additional queries
        await message_obj.fetch_related('author', 'channel')

        await broadcast_message(message_obj)
        return response.json({'state': 'message-sent', 'message_id': message_obj.id})
    else:
        channel_id = int(channel_id)

    if not await user_has_access_to_channel(username, channel_id):
        return response.json({'state': 'no-access'}, status=403)

    message_obj = await Message.create(content=message_text, author_id=username, channel_id=channel_id)
    await broadcast_message(message_obj)
    return response.json({'state': 'message-sent', 'message_id': message_obj.id})


async def broadcast_message(message: Message):
    print("Broadcasting message")
    for client in connected_clients:
        if await user_has_access_to_channel(client.id, message.channel.id) and client.id != message.author.id:
            data = message.json()
            print(data)
            data['state'] = 'new-message'
            await client.send(json.dumps(data))


connected_clients = set()

typing_clients = set()


@app.websocket("/ws")
async def ws(request, client: Websocket):
    client_credentials = {}
    while True:
        data = await client.recv()
        # if the client_credentials is not set that means it is the first message
        # if the user doesn't authenticate on first message, we will close the connection

        if not client_credentials:
            client_credentials = json.loads(data)
            if not await verify_credentials(client_credentials['username'], client_credentials['password']):
                await client.send('{"state": "wrong-credentials"}')
                await client.close()
                break
            else:
                # get client name
                user = await User.filter(username=client_credentials['username']).first()
                await client.send(json.dumps({'state': 'authenticated', 'user_id': user.id, "name": user.name}))
                # set id of client in clients
                user = await User.filter(username=client_credentials['username']).first()
                client.id = user.id
                client.name = user.name
                connected_clients.add(client)

        data = json.loads(data)

        # user is typing
        if data['type'] == 'typing':
            for client in connected_clients:
                if (await user_has_access_to_channel(client.id, data['channel_id'])
                        or data['channel_id'] == 'public-chat'):
                    data['state'] = 'typing'

                    message = {'state': 'typing',
                               'user_id': client.id,
                               'channel_id': data['channel_id'],
                               'name': client.name}

                    typing_clients.add(client)

                    await client.send(json.dumps(message))

                    await asyncio.sleep(30)
                    if client in typing_clients:
                        await send_stop_typing_message(client.id, data['channel_id'], client.name)
                        typing_clients.remove(client)

        if data['type'] == 'stop-typing':
            if client in typing_clients:
                typing_clients.remove(client)

            await send_stop_typing_message(client.id, data['channel_id'], client.name)


async def send_stop_typing_message(user_id, channel_id, name):
    for client in connected_clients:
        if (await user_has_access_to_channel(client.id, channel_id)
                or channel_id == 'public-chat'):
            message = {'state': 'stop-typing',
                       'user_id': user_id,
                       'channel_id': channel_id,
                       'name': name}

            await client.send(json.dumps(message))


register_tortoise(
    app,
    db_url='sqlite://database.db',  # Adjust the database URL as needed
    modules={"models": ["models"]},  # Adjust the path to your model module
    generate_schemas=True
)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=0)
