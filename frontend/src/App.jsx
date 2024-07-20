import React, { useState } from "react";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";

import Chat from "./Chat";
import "./App.scss";

const API_URL = "http://localhost:8000";
import { createTheme, ThemeProvider } from "@mui/material/styles";

const darkTheme = createTheme({
  palette: {
    mode: "dark",
  },
});

const sx_textfield = {
  color: "lightgrey",
  "& label": {
    color: "lightgrey",
  },

  "& label.Mui-focused": {
    color: "lightgrey",
  },

  "& .MuiOutlinedInput-root": {
    "& fieldset": {
      borderColor: "lightgrey", // Style for the outline
    },
    "&:hover fieldset": {
      borderColor: "lightgrey", // Style for hover state
    },
    "&:hover .MuiInputLabel-root": {
      color: "lightgrey",
    },
    "&.Mui-focused fieldset": {
      borderColor: "lightgrey", // Style when the input is focused
    },
    "& input": {
      // Targeting the input element directly
      color: "lightgrey", // Set the text color
    },
  },
};

function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [messages, setMessages] = useState([]);

  const onUsernameChange = (event) => {
    console.log(event.target.value);
    setUsername(event.target.value);
  };

  const onPasswordChange = (event) => {
    setPassword(event.target.value);
  };

  const login = () => {
    return console.log(username, password);
    // check if user and pass not empty
    if (username && password) {
      fetch(`${API_URL}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      })
        .then((response) => response.json())
        .then((data) => {});
    }
  };

  const singUp = () => {
    alert("fuck you");
  };

  if (!authenticated) {
    return (
      <ThemeProvider theme={darkTheme}>
        <div id="login-container">
          <h1>Welcome</h1>
          <div id="login-form">
            <TextField
              label="Username"
              variant="outlined"
              value={username}
              onChange={onUsernameChange}
              fullWidth
              margin="normal"
              className="username text-field"
              sx={sx_textfield}
            />
            <TextField
              label="Password"
              type="password"
              variant="outlined"
              value={password}
              onChange={onPasswordChange}
              fullWidth
              margin="normal"
              className="password text-field"
              sx={sx_textfield}
            />

            <div className="buttons">
              <Button
                className="mui-button"
                variant="contained"
                color="primary"
                onClick={login}
              >
                Log In
              </Button>
              <Button
                className="mui-button"
                variant="contained"
                color="primary"
                onClick={singUp}
              >
                Sign Up
              </Button>
            </div>
          </div>
        </div>
      </ThemeProvider>
    );
  }

  return <h1>asdf</h1>;
}

export default App;
