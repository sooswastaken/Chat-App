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


async def check_user_exists(username) -> bool:
    return await User.filter(username=username).exists()


async def verify_credentials(username: str, password: str) -> bool:
    user = await User.filter(username=username).first()
    if not user:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8'))


async def get_user_id(username):
    user = await User.filter(username=username).first()
    return user.id


async def user_has_access_to_channel(user_id, channel_id) -> bool:
    # Retrieve the channel type and members
    channel = await Channel.filter(id=channel_id).first()

    print("CHECKING ACCESS")
    print("Channel type", channel.type)
    print("Channel id", channel.id)
    print("User id", user_id)

    if not channel:
        print("Channel not found")
        return False  # Channel not found

    if channel.type == ChannelType.PUBLIC_CHAT:
        return True  # All users have access to public chats

    if channel.type in (ChannelType.DM, ChannelType.GROUP_CHAT):
        # Check if user is in the list of members
        return await ChannelMember.filter(user=await User.filter(id=user_id).first(),
                                          channel=await Channel.filter(id=channel_id).first()).exists()
    # print debug, all members of channel and their ids as well as the user id
    print(
        f"User {user_id} (username: {await User.filter(id=user_id).first().name}) trying to access channel {channel_id}")
    print("All members of channel", channel_id)
    all_members = await ChannelMember.filter(channel=await Channel.filter(id=channel_id).first()).all()
    for member in all_members:
        print(member.user.id, member.user.name)

    return False


def create_id():
    return str(uuid.uuid4().int % (2 ** 63 - 1))


async def init_db():
    # Ensure at least one public chat exists
    if not await Channel.filter(type=ChannelType.PUBLIC_CHAT.value).exists():
        await Channel.create(name="Public Chat", type=ChannelType.PUBLIC_CHAT, id=create_id())
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
    return await response.file("index.html")


app.static("/", "./")


@app.post('/sign-up')
async def sign_up(request):
    data = request.json
    if not all(key in data for key in ('username', 'password', 'name')):
        return response.json({'state': 'missing-fields'}, status=400)
    if await User.filter(username=data["username"]).exists():
        return response.json({'state': 'user-already-exists'}, status=400)
    data["password"] = hash_password(data["password"])
    user_obj = await User.create(id=create_id(), **data)
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
    if not await user_has_access_to_channel(await get_user_id(username), channel_id):
        return response.json({'state': 'no-access'}, status=403)

    messages = await Message.filter(channel=await Channel.filter(id=channel_id).first()).order_by('created_at')
    return response.json({'messages': [msg.to_dict() for msg in messages]})


@app.post('/get-channels')
async def get_channels(request):
    # returns channels that the user is a member of
    username = request.json.get('username')
    password = request.json.get('password')
    if not await verify_credentials(username, password):
        return response.json({'state': 'wrong-credentials'}, status=403)

    user = await User.filter(username=username).first()
    channels = await ChannelMember.filter(user=user).prefetch_related('channel').all()
    # pre-fetch the members to avoid additional queries
    for channel in channels:
        await channel.fetch_related('user')
    return response.json({'channels': [channel.json() for channel in channels]})


@app.post('/create-channel')
async def create_channel(request):
    username = request.json.get('username')
    password = request.json.get('password')
    channel_name = request.json.get('channel_name')

    member_ids = request.json.get('members')
    if not await verify_credentials(username, password):
        return response.json({'state': 'wrong-credentials'}, status=403)

    if not member_ids:
        return response.json({'state': 'no-members'}, status=400)

    for member_id in member_ids:
        user = await User.filter(id=member_id).first()
        if not user:
            # print list of all user ids
            print("User not found", member_id)
            # print all users and all their data
            all_users = await User.all()
            for user in all_users:
                print(user.id, user.username, user.name)

            return response.json({'state': 'contains-invalid-user'}, status=400)

    user = await User.filter(username=username).first()

    channel = await Channel.create(name=channel_name, type=ChannelType.GROUP_CHAT.value,
                                   id=uuid.uuid4().int % (2 ** 63 - 1))
    await ChannelMember.create(user=user, channel=channel)
    for member_id in member_ids:
        user = await User.filter(id=member_id).first()
        await ChannelMember.create(user=user, channel=channel)

    return response.json({'state': 'channel-created', 'channel_id': channel.id})


@app.route('/start-dm/<user_id>')
async def start_dm(request, user_id):
    username = request.json.get('username')
    password = request.json.get('password')
    if not await verify_credentials(username, password):
        return response.json({'state': 'wrong-credentials'}, status=403)

    user = await User.filter(username=username).first()
    if not user:
        return response.json({'state': 'user-not-found'}, status=404)

    other_user = await User.filter(id=user_id).first()
    if not other_user:
        return response.json({'state': 'other-user-not-found'}, status=404)

    # Check if a DM channel already exists between the two users
    channel = await Channel.filter(type=ChannelType.DM.value).filter(
        members__user=user).filter(members__user=other_user).first()

    if not channel:
        channel = await Channel.create(type=ChannelType.DM.value)
        await ChannelMember.create(user=user, channel=channel)
        await ChannelMember.create(user=other_user, channel=channel)

    return response.json({'state': 'dm-started', 'channel_id': channel.id})


# edit channel
@app.post('/edit-channel/<channel_id>')
async def edit_channel(request, channel_id):
    username = request.json.get('username')
    password = request.json.get('password')

    if not await verify_credentials(username, password):
        return response.json({'state': 'wrong-credentials'}, status=403)

    channel = await Channel.filter(id=channel_id).first()
    if not channel:
        return response.json({'state': 'channel-not-found'}, status=404)

    if not await user_has_access_to_channel(await get_user_id(username), channel_id):
        return response.json({'state': 'no-access'}, status=403)

    channel_name = request.json.get('channel_name')
    member_ids = request.json.get('members')

    if channel_name:
        channel.name = channel_name
        await channel.save()

    if member_ids:
        for member_id in member_ids:
            user = await User.filter(id=member_id).first()
            if not user:
                return response.json({'state': 'contains-invalid-user'}, status=400)

        # get all current members
        current_members = await ChannelMember.filter(channel=channel).all()
        current_member_ids = [member.user.id for member in current_members]

        # remove members that are not in the new list
        for member in current_members:
            if member.user.id not in member_ids:
                await member.delete()

        # add new members

        for member_id in member_ids:
            if member_id not in current_member_ids:
                user = await User.filter(id=member_id).first()
                await ChannelMember.create(user=user, channel=channel)

    return response.json({'state': 'channel-edited', 'channel_id': channel.id})


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
                                           id=create_id())
        # pre-fetch the author and channel to avoid additional queries
        await message_obj.fetch_related('author', 'channel')

        await broadcast_message(message_obj)
        return response.json({'state': 'message-sent', 'message_id': message_obj.id})
    else:
        channel_id = channel_id

    if not await user_has_access_to_channel(await get_user_id(username), channel_id):
        return response.json({'state': 'no-access'}, status=403)

    message_obj = await Message.create(content=message_text, author_id=username,
                                       channel=await Channel.filter(id=channel_id).first(), id=create_id())
    await broadcast_message(message_obj)
    return response.json({'state': 'message-sent', 'message_id': message_obj.id})


async def broadcast_message(message: Message):
    for client in connected_clients:

        if await user_has_access_to_channel(client.id, message.channel.id) and client.id != message.author.id:
            data = message.json()
            data['state'] = 'new-message'
            await client.send(json.dumps(data))


connected_clients = set()


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
                dictyionary = {'state': 'authenticated', 'user_id': user.id, "name": user.name}
                await client.send(json.dumps({'state': 'authenticated', 'user_id': user.id, "name": user.name}))
                # set id of client in clients
                user = await User.filter(username=client_credentials['username']).first()
                client.id = user.id
                client.name = user.name
                connected_clients.add(client)


register_tortoise(
    app,
    db_url='sqlite://database.db',  # Adjust the database URL as needed
    modules={"models": ["models"]},  # Adjust the path to your model module
    generate_schemas=True
)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=0)
