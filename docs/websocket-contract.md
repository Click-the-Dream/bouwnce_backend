# BOUNWCE Realtime (WebSocket) Contract

**Audience:** Frontend / mobile clients.

**Status:** Current for clients using the single events WebSocket.

All frames are **JSON objects**. Every server frame has a string `type`; almost all
carry a `data` object. Some frames add a top-level field (`client_id`, `sender`).

---

## 1. Endpoint

Use one WebSocket for direct messages, group chat, and live notifications.
Authenticate by passing your access token as a query parameter (browsers cannot
set an `Authorization` header on a WebSocket handshake).

| URL                             | Required query params |
| ------------------------------- | --------------------- |
| `wss://<host>/api/v1/events/ws` | `token`               |

- `token` — the same access token used by the app’s REST requests.
- Include `group_id` in each group action; it is not a connection query
  parameter.

> **Token lifetime:** the token is verified **only at connect time**. Get a fresh
> access token when reconnecting. An expired token fails the handshake (see
> §2.3); it does not drop an already-open socket.

### Connection-efficient delivery

- Keep one `/api/v1/events/ws` socket open per signed-in app/device session for
  DMs, group messages, typing indicators, and notifications.
- Do not open or subscribe to a separate connection for each group. Messages
  from your active groups arrive on this same socket.
- Include `group_id` with each group action. Keep the same socket open while the
  user switches between conversations and groups.
- Use push notifications while the app is offline; `GET /api/v1/events/mobile`
  is available as a fallback.

Example:

```js
const ws = new WebSocket(
  `wss://api.example.com/api/v1/events/ws?token=${accessToken}`,
);
```

---

## 2. Connection lifecycle

### 2.1 Open

1. Open the socket with your access token.
2. Wait for `chat.ready`.
3. Include `group_id` with each group action. You must be an active member of
   that group.

Treat `chat.ready` as the signal that the connection is live. Frames that arrive
before it (presence snapshot, `bouwnce.system`) may arrive in either order.

### 2.2 Heartbeat

Clients should send a ping on an idle interval and watch for the pong:

```json
{ "type": "ping" }
```

```json
{ "type": "pong" }
```

Send a ping periodically while idle. After an abrupt disconnect, online status
may take up to about 75 seconds to update.

### 2.3 Rejection / close codes

If the connection is rejected before it opens, browsers commonly report close
code `1006` rather than the server's `1008` policy code.

| Close code          | Cause                                                                      |
| ------------------- | -------------------------------------------------------------------------- |
| `1008` (pre-accept) | Missing or invalid access token.                                           |
| `1000`              | Normal closure (either side).                                              |
| `1006`              | Abnormal network closure or a rejected connection surfaced to the browser. |

**Client rule of thumb:** if the socket fails to open, refresh the access token
when needed, then retry with backoff.

---

## 3. Shared objects

### 3.1 `UserLite` (DM frames)

```jsonc
{
  "id": "3f1c…", // uuid string
  "username": "jane", // string | null
  "full_name": "Jane Doe", // string | null
  "profile_pic": { "url": "https://…" }, // object | null
}
```

### 3.2 `sender` (group message)

Group message frames include a top-level `sender` object. Use `id` to identify
the sender and `full_name`, `username`, and `profile_pic` to display them. Treat
other fields as optional and do not rely on them.

### 3.3 `GroupMessage` (group `data`)

```jsonc
{
  "id": "uuid",
  "group_id": "uuid",
  "sender_id": "uuid",
  "body": "hello team",
  "created_at": "2026-10-11T12:00:00+00:00", // ISO-8601
  "updated_at": "2026-10-11T12:00:00+00:00",
  "edited_at": null, // ISO-8601 | null
  "is_edited": false,
  "media_type": null, // "image" | "video" | "file" | "audio" | null
  "media_urls": null, // string[] | null
  "media_names": null, // string[] | null
  "reply_to_message_id": null, // uuid | null
  "mentioned_user_ids": null, // uuid string[] | null
  "read_count": 0,
}
```

### 3.4 `ChatMessageData` (DM `data`)

```jsonc
{
  "id": "uuid",
  "conversation_id": "uuid",
  "sender_id": "uuid",
  "recipient_id": "uuid",
  "body": "hi", // string | null
  "read_at": null, // ISO-8601 | null
  "media_type": null, // "image" | "video" | "file" | null
  "media_urls": null, // string[] | null
  "media_name": null, // string | null
  "reply_to_message_id": null, // uuid | null
  "created_at": "2026-10-11T12:00:00+00:00",
  "updated_at": "2026-10-11T12:00:00+00:00",
  "sender": {/* UserLite */},
  "recipient": {/* UserLite */},
  "reply_to_message": false, // false, or a ChatMessageReplyData object
}
```

---

## 4. Direct messages — `/api/v1/events/ws`

### 4.1 Client → Server

| `type`              | Purpose                                     | Required fields                                         |
| --------------------- | ------------------------------------------- | ------------------------------------------------------- |
| `ping`              | Liveness                                    | —                                                      |
| `chat.send`         | Send a text message                         | `recipient_id`, `body`                              |
| `chat.edit`         | Edit one of your DM messages                | `message_id`, `body`                               |
| `chat.delete`       | Delete one of your DM messages              | `message_id`                                        |
| `chat.upload_media` | Send media (already uploaded to Cloudinary) | `recipient_id`, `media_urls`, `media_type`        |
| `chat.read`         | Mark conversation / message read            | `recipient_id` (+ `message_id` unless `mark_all`) |
| `chat.typing`       | Typing indicator                            | `user_id` (the _other_ user), `is_typing`         |

`type` is matched case-insensitively after trimming.

#### `chat.send`

```json
{
  "type": "chat.send",
  "recipient_id": "9b2…",
  "body": "hello!",
  "client_id": "local-42",
  "reply_to_message_id": null
}
```

| Field                   | Type                 | Notes                           |
| ----------------------- | -------------------- | ------------------------------- |
| `recipient_id`        | uuid                 | other user                      |
| `body`                | string               | 1–4000 chars                   |
| `client_id`           | string ≤ 64 \| null | your optimistic id; echoed back |
| `reply_to_message_id` | uuid \| null         | message being replied to        |

#### `chat.edit` and `chat.delete`

```json
{ "type": "chat.edit", "message_id": "message-uuid", "body": "corrected text" }
{ "type": "chat.delete", "message_id": "message-uuid" }
```

The body must contain 1–4000 characters after trimming. Only the original
sender can edit or permanently delete a message. An edit updates the message's
`updated_at`. On success, the server sends `chat.message.updated` or
`chat.message.deleted` to both participants' connected devices, including the
sender's other signed-in devices. Disconnected clients should reload message
history after reconnecting.

#### `chat.upload_media`

```json
{
  "type": "chat.upload_media",
  "recipient_id": "9b2…",
  "client_id": "local-43",
  "media_urls": ["https://res.cloudinary.com/<cloud>/image/upload/v1/abc.jpg"],
  "media_type": "image",
  "file_name": "photo.jpg",
  "body": "look at this",
  "reply_to_message_id": null
}
```

| Field          | Type                  | Notes                                                                             |
| -------------- | --------------------- | --------------------------------------------------------------------------------- |
| `media_type` | string                | `image` \| `video` \| `file` (rejected otherwise)                           |
| `media_urls` | string[]              | **must** be `https://res.cloudinary.com/<CLOUDINARY_NAME>/…` secure URLs |
| `file_name`  | string ≤ 255 \| null | original file name                                                                |
| `body`       | string \| null        | optional caption, ≤ 4000 chars                                                   |

Get a signed upload target first via `POST /api/v1/uploads/chat/sign`
(`{"upload_type":"image|video|file","count":1,"file_name":"…"}`), upload to
Cloudinary, then send the returned secure URL here.

#### `chat.read`

```json
{ "type": "chat.read", "recipient_id": "9b2…", "mark_all": true }
```

```json
{
  "type": "chat.read",
  "recipient_id": "9b2…",
  "mark_all": false,
  "message_id": "aa1…"
}
```

| Field            | Type         | Notes                                                                  |
| ---------------- | ------------ | ---------------------------------------------------------------------- |
| `recipient_id` | uuid         | the other participant                                                  |
| `mark_all`     | bool         | default `true`; when `false`, `message_id` is **required** |
| `message_id`   | uuid \| null | last read message                                                      |

#### `chat.typing`

```json
{ "type": "chat.typing", "user_id": "9b2…", "is_typing": true }
```

`user_id` is the **other** participant. The frame may be sent to both
participants; display it as the other person's typing only when `data.user`
identifies someone other than the signed-in user.

### 4.2 Server → Client

| `type`                 | When                                                            | `data`                                                                              |
| ------------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| `chat.ready`           | once after connect                                              | `{ "user_id": uuid }`                                                               |
| `pong`                 | reply to `ping`                                               | —                                                                                    |
| `bouwnce.system`       | once after connect                                              | `{ "user": { id, email, username, full_name, profile_pic } }`                       |
| `user.online.snapshot` | once after connect                                              | `{ "items": [ { "user": UserLite, "online": bool } ] }`                             |
| `user.online`          | partner connects/disconnects (and for you)                      | `{ "user": UserLite, "online": bool }`                                              |
| `chat.send.ack`        | immediately after a valid `chat.send` / `chat.upload_media` | `{ sender_id, recipient_id, client_id }`                                            |
| `chat.sent`            | after your message is accepted                                  | `{ "conversation_id": uuid, "message": ChatMessageData }` (top-level `client_id`) |
| `chat.message`         | incoming message from the other user                            | `ChatMessageData`                                                                   |
| `chat.message.updated` | a DM message was edited by its sender                           | `ChatMessageData`                                                                   |
| `chat.message.deleted` | a DM message was deleted by its sender                          | `{ conversation_id, message_id, sender_id, recipient_id }`                          |
| `chat.read.ack`        | reply to your `chat.read`                                     | `{ conversation_id, reader_id, read, updated }`                                     |
| `chat.read.updated`    | when either side marks messages read                            | `{ conversation_id, message_id, reader_id, read, updated }`                         |
| `chat.typing`          | other user's typing state                                       | `{ conversation_id, user: UserLite, is_typing }`                                    |
| `group_message`        | a message arrives in a group you belong to                      | message data includes `group_id`                                                    |
| `group_typing`         | a member of a group you belong to is typing                     | `{ "group_id": uuid, "user_id": uuid, "username": string \| null, "is_typing": bool }` |
| `error`                | validation / handler failure                                    | `{ error, message }` (see §8)                                                      |

Notes:

- `chat.send.ack` is optimistic — it arrives before the final message result.
  Use it to mark the bubble "sending" and match it to your local `client_id`.
- `chat.sent` is the server-confirmed copy of **your own** message on the
  connection that sent it; it echoes your `client_id` at the top level. Render
  from this to confirm the optimistic message.
- `chat.message` delivers incoming messages to the recipient and synchronizes
  your other connected devices. The sending connection does not receive its own
  message as `chat.message`.
- `chat.read.updated` is published to **both** participants (including the reader),
  so apply it idempotently using `updated`.

### 4.3 Example DM session

```text
client → { "type": "ping" }
server → { "type": "pong" }

server → { "type": "bouwnce.system", "data": { "user": { "id": "…", "username": "bouwnce", … } } }
server → { "type": "user.online.snapshot", "data": { "items": [ … ] } }
server → { "type": "chat.ready", "data": { "user_id": "…" } }

client → { "type": "chat.send", "recipient_id": "9b2…", "body": "hey", "client_id": "c1" }
server → { "type": "chat.send.ack", "data": { "sender_id": "…", "recipient_id": "9b2…", "client_id": "c1" } }
server → { "type": "chat.sent", "client_id": "c1", "data": { "conversation_id": "…", "message": { … } } }

client → { "type": "chat.typing", "user_id": "9b2…", "is_typing": true }
server → (to 9b2…) { "type": "chat.typing", "data": { "conversation_id": "…", "user": { … }, "is_typing": true } }

# edit or delete one of your messages; the message_id comes from its message data
client → { "type": "chat.edit", "message_id": "m1", "body": "updated text" }
server → (to both participants and your other devices) { "type": "chat.message.updated", "data": { "id": "m1", "body": "updated text", … } }
client → { "type": "chat.delete", "message_id": "m1" }
server → (to both participants and your other devices) { "type": "chat.message.deleted", "data": { "conversation_id": "…", "message_id": "m1", … } }

# other user replies
server → { "type": "chat.message", "data": { "id": "…", "sender_id": "9b2…", "recipient_id": "…", "body": "hi", … } }
```

---

## 5. Group chat — same events socket

Use the same `/api/v1/events/ws` connection as direct messages. Include the
group UUID as `group_id` in each group action. Only active group members may
send group actions.

### 5.1 Client → Server

| `type`          | Aliases           | Purpose                         |
| ----------------- | ----------------- | ------------------------------- |
| `ping`          | —                | Liveness (`pong` reply)       |
| `group_message` | `group.message` | Send a message (`group_id`)   |
| `group_typing`  | `group.typing`  | Typing indicator (`group_id`) |
| `group_message_edit` | — | Edit one of your messages (`group_id`, `message_id`) |
| `group_message_delete` | — | Delete one of your messages (`group_id`, `message_id`) |

`type` is matched case-insensitively after trimming. Any other value yields an
`error` frame (§8).

#### `group_message` / `group.message`

```json
{
  "type": "group_message",
  "group_id": "group-uuid",
  "body": "standup in 5",
  "client_id": "local-7",
  "media_type": "image",
  "media_urls": ["https://res.cloudinary.com/<cloud>/image/upload/v1/abc.jpg"],
  "media_names": ["photo.jpg"],
  "reply_to_message_id": "aa1…",
  "mentioned_user_ids": ["9b2…", "7c4…"]
}
```

| Field                   | Type             | Notes                                                     |
| ----------------------- | ---------------- | --------------------------------------------------------- |
| `group_id`            | uuid             | group to send the message to                              |
| `body`                | string           | **required, non-empty**. Keep to ≤4000 characters. |
| `client_id`           | string \| null   | echoed on the ack                                         |
| `media_type`          | string \| null   | `image` \| `video` \| `file` \| `audio`           |
| `media_urls`          | string[] \| null | media URLs                                                |
| `media_names`         | string[] \| null | original file names                                       |
| `reply_to_message_id` | uuid \| null     | message being replied to                                  |
| `mentioned_user_ids`  | uuid[] \| null   | every id must be an active member                         |

An empty body returns an `error` frame and sends nothing.

#### `group_typing` / `group.typing`

```json
{ "type": "group_typing", "group_id": "group-uuid", "is_typing": true }
```

Broadcast to **all other members only** — the sender never receives its own
typing event.

#### `group_message_edit`

```json
{
  "type": "group_message_edit",
  "group_id": "group-uuid",
  "message_id": "message-uuid",
  "body": "updated text"
}
```

You may update `body`, `media_type`, `media_urls`, and/or `media_names`.
Include at least one non-null field. The message must belong to this group, and
only its sender may edit it. Edits are sent to connected devices of active
group members, including your other signed-in devices.

#### `group_message_delete`

```json
{
  "type": "group_message_delete",
  "group_id": "group-uuid",
  "message_id": "message-uuid"
}
```

Only the message sender may delete it. Deletion is permanent and is broadcast
to connected devices of active group members, including your other signed-in
devices. Disconnected clients should reload group history after reconnecting.

### 5.2 Server → Client

| `type`               | When                                                    | Payload                                                                                          |
| ---------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `pong`               | reply to `ping`                                       | `{ "type": "pong" }`                                                                           |
| `group_message`      | a message is broadcast in the group                     | `{ "type": "group_message", "data": GroupMessage, "sender": User }`                            |
| `group_message_sent` | ack for **your** `group_message`                | `{ "type": "group_message_sent", "client_id": "…", "data": GroupMessage }`                    |
| `group_message_updated` | a group message was edited                 | `{ "type": "group_message_updated", "group_id": uuid, "data": GroupMessage, "sender": User }` |
| `group_message_deleted` | a group message was deleted                | `{ "type": "group_message_deleted", "data": { "group_id": uuid, "message_id": uuid, "sender_id": uuid } }` |
| `group_typing`       | another member is typing                                | `{ "type": "group_typing", "data": { "group_id": uuid, "user_id": uuid, "username": string \| null, "is_typing": bool } }` |
| `error`              | invalid JSON / unknown type / empty body / send failure | `{ "type": "error", "message": "…" }`                                                         |

Notes:

- The sender receives **both**: the broadcast `group_message` and the
  `group_message_sent` ack (which carries your `client_id`). Use the ack to
  confirm your temporary sending bubble, and do not show the broadcast as a
  second copy of the same message.
- `group_message.data` contains the message; the top-level `sender` contains the
  sender's display details (§3.2).
- Typing indicators are temporary. Do not add them to message history.

### 5.3 Example group session

```text
server → { "type": "chat.ready", "data": { "user_id": "u1" } }

client → { "type": "group_message", "group_id": "g1", "body": "hi all", "client_id": "c1" }
server → { "type": "group_message_sent", "client_id": "c1", "data": { "id": "m1", "body": "hi all", … } }
# every member (including the sender) also gets the broadcast:
server → { "type": "group_message", "data": { "id": "m1", "group_id": "g1", "sender_id": "u1", "body": "hi all", … }, "sender": { … } }

client → { "type": "group_typing", "group_id": "g1", "is_typing": true }
server → (to other members) { "type": "group_typing", "data": { "group_id": "g1", "user_id": "u1", "username": "jane", "is_typing": true } }
```

---

## 6. Showing messages

- Show each message only once. A message may arrive while loading history, after
  reconnecting, or on more than one signed-in device. If it is already in the
  conversation, update or ignore the repeat instead of adding another bubble.
- When sending a message, use the `client_id` acknowledgement described in §4.2
  to reconcile your temporary sending bubble with the confirmed message. Do not
  display the same sent message again when its group broadcast arrives.
- Sort messages by their `created_at` time; messages may arrive out of order.
- Treat typing indicators as temporary UI state, not as conversation messages.

## 7. Reconnecting

After reconnecting, wait for `chat.ready` before treating the socket as ready.
Load or refresh history through the REST endpoints in §10, then merge incoming
messages with the messages already shown so none appear twice. When opening a
group chat, load its history through REST.

---

## 8. Error frames

Error frames always have `"type": "error"`. Shape varies slightly between DM and
group.

### Direct messages

```json
{
  "type": "error",
  "error": "invalid_payload",
  "message": "Expected: {type:'chat.send', recipient_id:'<uuid>', body:'...'}"
}
```

| `error`                    | Cause                                                                                          |
| ---------------------------- | ---------------------------------------------------------------------------------------------- |
| `invalid_payload`          | `chat.send` / `chat.upload_media` / `chat.read` / `chat.typing` body failed validation |
| `self_send_not_allowed`    | `chat.upload_media` with `recipient_id` == self                                            |
| `invalid_media_type`       | media type not in `image` / `video` / `file`                                             |
| `missing_media_urls`       | empty `media_urls`                                                                           |
| `invalid_media_urls`       | a URL is not a Cloudinary secure URL for this deployment                                       |
| `chat.send.failed`         | message could not be sent (for example, you are not allowed to message the recipient)          |
| `chat.edit.failed`         | message edit failed (missing message, invalid body, or you are not its sender)                 |
| `chat.delete.failed`       | message deletion failed (missing message or you are not its sender)                             |
| `chat.message.delivery_failed` | the change was saved but could not be broadcast; reload the conversation to sync it          |
| `chat.upload_media.failed` | media message could not be sent                                                                |
| `chat.read.failed`         | read update failed (conversation not found, bad `message_id`, …)                            |
| `chat.typing.failed`       | typing publish failed                                                                          |

DM handler errors are non-fatal: the socket stays open.

### Group actions

Group action errors do not close the shared socket.

| Error | Cause |
| ----- | ----- |
| `invalid_group_id` | A group action is missing a valid `group_id`. |
| `group.access.denied` | The signed-in user is not an active member of the group. |
| `group.access.failed` | The server could not verify active group membership. |
| `Message body cannot be empty` | `group_message` has a blank body. |
| `group.message.failed` | The message could not be saved or validated, including an invalid mention. |
| `group_message_edit.failed` | The edit was invalid, the message is missing/not in this group, or you are not its sender. |
| `group_message_delete.failed` | The message is missing/not in this group, or you are not its sender. |
| `group.message.delivery_failed` | The change was saved but could not be broadcast; reload group history to sync it. |

---

## 9. Notifications

The `/api/v1/events/ws` socket receives incoming DM messages and group messages
for the user's active group memberships. Group frames include `group_id`, so
the client can show them in the correct chat or open that group when selected.

When the app is backgrounded or offline, use the platform push notification
flow. On tap, open the relevant conversation or group and fetch its history.
The mobile events long-poll endpoint is available as an optional fallback:
`GET /api/v1/events/mobile`.

---

## 10. Related REST endpoints

| Purpose                           | Endpoint                                                       |
| --------------------------------- | -------------------------------------------------------------- |
| DM send (fallback without socket) | `POST /api/v1/chats/messages`                                |
| DM conversations                  | `GET /api/v1/chats/conversations`                            |
| DM messages                       | `GET /api/v1/chats/conversations/{conversation_id}/messages` |
| Sign chat upload                  | `POST /api/v1/uploads/chat/sign`                             |
| Group send                        | `POST /api/v1/groups/{group_id}/messages`                    |
| Group history                     | `GET /api/v1/groups/{group_id}/messages`                     |
| Group members                     | `GET /api/v1/groups/{group_id}/members`                      |

---

## 11. Quick reference — every frame type

### Client → Server

| Endpoint     | Types                                                                                                    |
| ------------ | -------------------------------------------------------------------------------------------------------- |
| `/events/ws` | `ping`, `chat.send`, `chat.edit`, `chat.delete`, `chat.upload_media`, `chat.read`, `chat.typing`, `group_message`, `group_message_edit`, `group_message_delete`, `group_typing` |

### Server → Client

| Endpoint     | Types                                                                                                                                                                                                                                                                          |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `/events/ws` | `chat.ready`, `pong`, `bouwnce.system`, `user.online.snapshot`, `user.online`, `chat.send.ack`, `chat.sent`, `chat.message`, `chat.message.updated`, `chat.message.deleted`, `chat.read.ack`, `chat.read.updated`, `chat.typing`, `group_message`, `group_message_sent`, `group_message_updated`, `group_message_deleted`, `group_typing`, `error` |

---

## 12. Client checklist

1. Open one `/api/v1/events/ws` socket per signed-in device session.
2. Wait for `chat.ready` before enabling chat.
3. Include `group_id` in every group message and typing action.
4. Send `ping` on an idle interval; treat `pong` as liveness.
5. On send: attach a `client_id`, render an optimistic bubble, reconcile on
   `chat.sent` / `group_message_sent`.
6. For edits and deletes, send the matching `chat.*` or `group_message_*`
   action with the message id. Apply the corresponding update/delete event to
   the local conversation; only the original sender can change a message.
7. Merge incoming messages with the displayed conversation so repeated
   deliveries do not create duplicate bubbles.
8. On group reconnect, reload history via REST and then listen for new frames.
9. If the handshake is rejected, refresh the token if needed, then retry with
   backoff.
