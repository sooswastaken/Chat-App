const appDiv = document.getElementById("app");
const messagesDiv = document.getElementById("messages");
const messageInput = document.getElementById("messageInput");
const loginForm = document.getElementById("loginForm");
let currentChannelId = "public-chat";
let userCredentials = {};

let socket;
let messages = [];


async function fetchChannels() {
    const response = await fetch("/get-channels", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(userCredentials)
    });

    const data = await response.json();
    if (data.channels) {
        const channelList = document.getElementById('channelList');
        channelList.innerHTML = "";
        // add public chat
        const publicChat = document.createElement('button');
        publicChat.textContent = "Public Chat";
        publicChat.onclick = () => switchChannel("public-chat");
        channelList.appendChild(publicChat);
        // disable public chat button
        if (currentChannelId === "public-chat") {
            publicChat.disabled = true;
        }

        // add br
        const br = document.createElement('br');
        channelList.appendChild(br);
        const br2 = document.createElement('br');
        channelList.appendChild(br2);


        data.channels.forEach(channel => {
            const div = document.createElement('button')
            div.textContent = channel.channel_name;
            div.onclick = () => switchChannel(channel.channel_id, channel.channel_name);
            channelList.appendChild(div);
            // add br
            let br = document.createElement('br');
            channelList.appendChild(br);
            let br2 = document.createElement('br');
            channelList.appendChild(br2);
        });
    }
}

function switchChannel(channelId, channelName) {
    // enable button for current channel
    const buttons = document.getElementsByTagName('button');
    for (let i = 0; i < buttons.length; i++) {
        if (buttons[i].textContent === channelName) {
            buttons[i].disabled = false;
        }
    }

    currentChannelId = channelId; // store current channel ID globally
    console.log("Switching to channel:", currentChannelId);
    fetchAndClearMessages().then(() => {
        console.log("Messages fetched successfully.");
    }).catch(error => {
        console.error("Failed to fetch messages:", error);
    });

    // disable button for current channel

    for (let i = 0; i < buttons.length; i++) {
        if (buttons[i].textContent === currentChannelId) {
            buttons[i].disabled = true;
        }
    }

    // change channelName label
    document.getElementById('channelName').textContent = channelName;
}


async function fetchAndClearMessages() {
    await fetchMessages();
    messagesDiv.innerHTML = "";
    await fetchMessages();
}

async function fetchMessages() {
    const response = await fetch(`/get-messages/${currentChannelId}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(userCredentials)
    });

    const data = await response.json();
    if (data.messages) {
        messagesDiv.innerHTML = ""; // clear existing messages
        data.messages.forEach(message => {
            displayMessage(message);
        });
    }
}

function showCreateGroupChatForm() {
    document.getElementById('createGroupChatForm').style.display = 'block';
}

function showStartDMForm() {
    return alert("This feature is not yet implemented.");
    document.getElementById('startDMForm').style.display = 'block';
}

async function createGroupChat() {
    const name = document.getElementById('gcName').value.trim();
    const members = document.getElementById('gcMembers').value.trim().split(',');

    const response = await fetch("/create-channel", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            username: userCredentials.username,
            password: userCredentials.password,
            channel_name: name,
            members: members
        })
    });

    const data = await response.json();
    if (data.state === "channel-created") {
        alert("Group chat created!");
        await fetchChannels();
    } else {
        alert("Failed to create group chat: " + data.state);
    }
}

async function startDM() {
    const userId = document.getElementById('dmUserId').value.trim();

    const response = await fetch(`/start-dm/${userId}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(userCredentials)
    });

    const data = await response.json();
    if (data.state === "dm-started") {
        alert("DM started!");
        await fetchChannels();
    } else {
        alert("Failed to start DM: " + data.state);
    }
}


async function signUp() {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    // get name from input
    name = prompt("Pick a display name:");

    if (!username || !password || !name || username === "" || password === "" || name === "") {
        alert("Please fill in all fields.");
        return;
    }


    // Sign-up POST request
    fetch("/sign-up", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            username: username,
            password: password,
            name: name,
        }),
    })
        .then((response) => response.json())
        .then((data) => {
            if (data.state === "user-created") {
                alert("Sign up successful!");
                login(); // Automatically log the user in after registration
            } else {
                alert("Sign up failed: " + data.state);
            }
        })
        .catch((error) => {
            console.error("Error during sign up:", error);
        });
}

async function login() {
    userCredentials.username = document.getElementById("username").value.trim();
    userCredentials.password = document.getElementById("password").value.trim();

    if (userCredentials.username && userCredentials.password) {
        // Initialize WebSocket connection

        // fetch /get-messages/public-chat with body of username and password

        fetch("/get-messages/public-chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(userCredentials),
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.state === "wrong-credentials") {
                    alert("Login failed! Please check your credentials and try again.");
                } else {
                    loginForm.style.display = "none"; // Hide login form
                    appDiv.style.visibility = "visible";
                    document.getElementById("input").style.visibility = "visible";
                    messages = data.messages;
                    data.messages.forEach((message) => {
                        displayMessage(message);
                    });

                    fetchChannels();
                    initializeWebSocket();
                }
            })
            .catch((error) => {
                console.error("Error:", error);
            });

    } else {
        alert("Please enter both username and password.");
    }
}

function initializeWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const url = `${protocol}${window.location.host}/ws`;
    const socket = new WebSocket(url);

    socket.onopen = () => {
        socket.send(JSON.stringify(userCredentials));
    };

    socket.onmessage = (event) => {
        console.log("Raw WebSocket message:", event.data);

        const data = JSON.parse(event.data, (key, value) => {
            if (typeof value === 'number' && !Number.isSafeInteger(value)) {
                // Convert to BigInt
                return BigInt(value); // Convert the number to a string before converting to BigInt
            }
            return value;
        });

        console.log("Parsed WebSocket message:", data);
        if (data.state === "wrong-credentials") {
            alert("Login failed! Please check your credentials and try again.");
            socket.close();
        } else if (data.state === "authenticated") {
            loginForm.style.display = "none"; // Hide login form
            messagesDiv.style.visibility = "visible";
            document.getElementById("input").style.visibility = "visible";
            userCredentials["id"] = data.user_id;
            console.log("User ID:", userCredentials.id);
            userCredentials["name"] = data.name;

            // populate user-info div
            const userInfo = document.getElementById('userInfo');
            userInfo.innerHTML = "";
            const name = document.createElement('p');
            name.textContent = `Display Name: ${data.name}`;
            userInfo.appendChild(name);
            const username = document.createElement('p');
            username.textContent = `Username: ${userCredentials.username}`;
            userInfo.appendChild(username);
            const id = document.createElement('p');
            id.textContent = `ID: ${userCredentials.id}`;
            userInfo.appendChild(id);
        } else if (data.state === "new-message") {
            // check if its the current channel
            // if (data.channel_id === currentChannelId) {
                displayMessage(data);
            // }
            // could add logic for unread messages
        }
    };

    socket.onerror = (error) => {
        console.error("WebSocket error:", error);
    };

    socket.onclose = () => {
        console.log("WebSocket closed");
    };
}

function displayMessage(message) {
    const messageElement = document.createElement("div");
    messageElement.textContent = `${message.author_name}: ${message.content}`;
    messagesDiv.appendChild(messageElement);

    // scroll to bottom of chat
    setTimeout(() => {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }, 0);
}

// have typing enter in message input send message
messageInput.addEventListener("keypress", (event) => {
    if (event.key === "Enter") {
        sendMessage();
    }
});

async function sendMessage() {
    const content = messageInput.value.trim();
    if ((!content) || (content === "")) {
        return;
    }
    // send to /send-message/public-chat with body of username, password, and content
    await fetch("/send-message/" + currentChannelId, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            username: userCredentials.username,
            password: userCredentials.password,
            message: content,
        }),
    });

    let message = {
        content: content,
        author_name: userCredentials.name,
    };

    displayMessage(message);
    // clear input
    messageInput.value = "";
}