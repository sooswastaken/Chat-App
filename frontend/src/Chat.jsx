import React, { useEffect } from "react";

const Chat = ({ messages, chatRef }) => {
  return (
    <div className="chat" ref={chatRef}>
      <ul>
        {messages.map((message, index) => (
          <li key={index}>
            {message.author_name}: {message.content}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Chat;
