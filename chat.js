const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('messageInput');
const loginForm = document.getElementById('loginForm');
let userCredentials = {};

let socket;


async function signUp() {
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();


    // get name from input
    name = prompt('Enter your name:');

    if (!username || !password || !name) {
        alert('Please fill in all fields.');
        return;
    }

    // Sign-up POST request
    fetch('http://localhost:8000/sign-up', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: username,
            password: password,
            name: name
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.state === 'user-created') {
            alert('Sign up successful!');
            login(); // Automatically log the user in after registration
        } else {
            alert('Sign up failed: ' + data.state);
        }
    })
    .catch(error => {
        console.error('Error during sign up:', error);
    });
}


async function login() {
    userCredentials.username = document.getElementById('username').value.trim();
    userCredentials.password = document.getElementById('password').value.trim();

    if (userCredentials.username && userCredentials.password) {
        // Initialize WebSocket connection

        // fetch /get-messages/public-chat with body of username and password

        fetch('http://localhost:8000/get-messages/public-chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(userCredentials)
        })
            .then(response => response.json())
            .then(data => {
                if (data.state === 'wrong-credentials') {
                    alert('Login failed! Please check your credentials and try again.');
                } else {
                    loginForm.style.display = 'none'; // Hide login form
                    messagesDiv.style.visibility = 'visible';
                    document.getElementById('input').style.visibility = 'visible';
                    data.messages.forEach(message => {
                        displayMessage(message);
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });

        initializeWebSocket();
    } else {
        alert('Please enter both username and password.');
    }
}

function initializeWebSocket() {
    socket = new WebSocket('ws://localhost:8000/ws');

    socket.onopen = () => {
        socket.send(JSON.stringify(userCredentials));
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        if (data.state === 'wrong-credentials') {
            alert('Login failed! Please check your credentials and try again.');
            socket.close();
        } else if (data.state === 'authenticated') {
            loginForm.style.display = 'none'; // Hide login form
            messagesDiv.style.visibility = 'visible';
            document.getElementById('input').style.visibility = 'visible';
            userCredentials['id'] = data.id;
            userCredentials['name'] = data.name;
        } else if (data.state === 'new-message') {
            displayMessage(data);
        }
    };

    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    socket.onclose = () => {
        console.log('WebSocket closed');
    };
}

function displayMessage(message) {
    const messageElement = document.createElement('div');
    messageElement.textContent = `${message.author_name}: ${message.content}`;
    messagesDiv.appendChild(messageElement);

    // scroll to bottom of chat
    setTimeout(() => {
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }, 0);
}

async function sendMessage() {
    const content = messageInput.value.trim();

    // send to /send-message/public-chat with body of username, password, and content
    await fetch('http://localhost:8000/send-message/public-chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: userCredentials.username,
            password: userCredentials.password,
            message: content
        })
    });


    let message = {
        content: content,
        author_name: userCredentials.name
    };

    displayMessage(message);
    // clear input
    messageInput.value = '';

}
