# ------- One-to-one chat ----------------
import flet as ft
import asyncio
import json
import base64
import mimetypes
import os
import uuid
import websockets
from database.db import Database
from screens.home import Home
from datetime import timedelta

from screens.camera_screen import CameraScreen
from screens.mic_screen import MicScreen
from screens.file_screen import FileScreen
from screens.gallery_screen import GalleryScreen


WS_SERVER_URL = "wss://indsapp-websocket.onrender.com"

MEDIA_DIR = "assets"
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")


HAS_INTERACTIVE_VIEWER = hasattr(ft, "InteractiveViewer")


def format_india_time(value):
    if not value:
        return ""

    india_time = value + timedelta(hours=5, minutes=30)

    return india_time.strftime("%I:%M %p").lstrip("0")


def get_initials(full_name):
    words = full_name.strip().split()

    if not words:
        return "?"

    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()

    return words[0][0].upper()


def Chat(
    page: ft.Page,
    my_id: int,
    contact_id: int,
    contact_name: str,
    contact_phone: str,
    refresh_notification
):

    page.clean()

    from screens.addthis import Addthis

    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 360
    page.window.height = 700
    page.navigation_bar = None
    page.padding = 0

    db = Database()

    # ---------------------------------------------------------------
    # MY PHONE
    # ---------------------------------------------------------------

    db.cur.execute(
        "SELECT phone FROM user WHERE id = %s",
        (my_id,)
    )

    my_row = db.cur.fetchone()

    my_phone = str(my_row["phone"]) if my_row else ""

    # ---------------------------------------------------------------
    # WEBSOCKET STATE
    # ---------------------------------------------------------------

    ws_state = {
        "connection": None,
        "connected": False,
        "running": True,
    }

    # mid -> message information
    msg_index = {}

    pending_attachments = []

    # ---------------------------------------------------------------
    # DOWNLOAD PICKER
    # ---------------------------------------------------------------

    download_picker = ft.FilePicker()

    page.services.append(download_picker)

    # ==================================================================
    # SMALL HELPER FUNCTIONS
    # ==================================================================

    def toast(text, color="white"):

        if not text:
            return

        banner_text.value = text
        banner_text.color = color
        banner_text.visible = True

        banner.height = 28
        banner.opacity = 1

        page.update()

        page.run_task(_clear_banner, text)


    async def _clear_banner(text):

        await asyncio.sleep(3)

        if banner_text.value == text:

            banner_text.visible = False
            banner_text.height = 0
            banner_text.opacity = 0

            page.update()


    # ==================================================================
    # DATABASE SAVE
    # ==================================================================

    def db_save(
        mid,
        sender_id,
        receiver_id,
        body,
        message_type="text"
    ):

        try:

            db.cur.execute(
                """
                INSERT INTO message
                    (
                        sender_id,
                        receiver_id,
                        message,
                        message_type,
                        message_status,
                        sent_at
                    )
                VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        'sent',
                        NOW()
                    )
                """,
                (
                    sender_id,
                    receiver_id,
                    body,
                    message_type
                )
            )

            db.conn.commit()

            return db.cur.lastrowid

        except Exception as ex:

            print("DB insert failed:", ex)

            return None


    def db_delete(message_id):

        if not message_id:
            return

        try:

            db.cur.execute(
                "DELETE FROM message WHERE message_id = %s",
                (message_id,)
            )

            db.conn.commit()

        except Exception as ex:

            print("DB delete failed:", ex)


    # ==================================================================
    # MEDIA
    # ==================================================================

    def save_incoming_media(name, b64_data):

        os.makedirs(MEDIA_DIR, exist_ok=True)

        try:

            raw = base64.b64decode(b64_data)

        except Exception:

            return None

        path = os.path.join(
            MEDIA_DIR,
            f"{uuid.uuid4().hex[:8]}_{name}"
        )

        with open(path, "wb") as f:
            f.write(raw)

        return path


    def to_data_uri(
        b64_data,
        mime="image/jpeg"
    ):

        if not b64_data:
            return None

        if b64_data.startswith("data:"):
            return b64_data

        return f"data:{mime};base64,{b64_data}"


    def img_src(path):

        if not path or not os.path.exists(path):
            return None

        try:

            with open(path, "rb") as f:
                raw = f.read()

            mime, _ = mimetypes.guess_type(path)

            mime = mime or "image/jpeg"

            return (
                f"data:{mime};base64,"
                f"{base64.b64encode(raw).decode('utf-8')}"
            )

        except Exception:

            return None


    # ==================================================================
    # VIEWER
    # ==================================================================

    viewer_body = ft.Container(
        alignment=ft.Alignment.CENTER,
        expand=True
    )

    viewer_filename_text = ft.Text(
        "",
        color="white",
        weight=ft.FontWeight.BOLD,
        size=14
    )


    viewer_content = ft.Container(
        content=ft.Column(
            controls=[
                viewer_body,
                viewer_filename_text
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        ),
        width=320,
        height=320,
        alignment=ft.Alignment(0, 0),
        scale=0.3,
        opacity=0,
        animate_scale=250,
        animate_opacity=250,
        bgcolor="black",
    )


    async def close_viewer(e=None):

        viewer_content.scale = 0.3
        viewer_content.opacity = 0

        page.update()

        await asyncio.sleep(0.22)

        if viewer_dialog.open:
            page.pop_dialog()


    viewer_dialog = ft.AlertDialog(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            icon_color="white",
                            tooltip="Close",
                            on_click=close_viewer
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                ),

                viewer_content,
            ],
            tight=True,
        ),

        on_dismiss=lambda e: None,
    )


    async def open_image_viewer(path):

        view_w = (page.window.width or 360) - 20
        view_h = (page.window.height or 700) - 140

        image_source = img_src(path)

        if HAS_INTERACTIVE_VIEWER:

            viewer_body.content = ft.InteractiveViewer(
                min_scale=1,
                max_scale=5,
                boundary_margin=ft.Margin(
                    0, 0, 0, 0
                ),
                content=ft.Image(
                    src=image_source,
                    fit=ft.BoxFit.CONTAIN
                ),
            )

        else:

            viewer_body.content = ft.Image(
                src=image_source,
                fit=ft.BoxFit.CONTAIN
            )

        viewer_filename_text.value = ""

        viewer_content.width = view_w
        viewer_content.height = view_h

        viewer_content.scale = 0.3
        viewer_content.opacity = 0

        page.show_dialog(viewer_dialog)

        await asyncio.sleep(0.03)

        viewer_content.scale = 1
        viewer_content.opacity = 1

        page.update()


    async def save_file_to_device(path, name):

        if not path or not os.path.exists(path):

            toast(
                "File ab available nahi hai",
                "red"
            )

            return

        try:

            with open(path, "rb") as f:
                file_bytes = f.read()

            await download_picker.save_file(
                dialog_title="Save file",
                file_name=name or "file",
                src_bytes=file_bytes,
            )

        except Exception as ex:

            print(
                "File save/open error:",
                repr(ex)
            )

            toast(
                f"File open nahi hua: {ex}",
                "red"
            )


    async def open_file_viewer(
        path,
        name
    ):

        viewer_body.content = ft.Column(
            controls=[
                ft.Icon(
                    ft.Icons.INSERT_DRIVE_FILE,
                    size=80,
                    color="blue"
                ),

                ft.Text(
                    name or "File",
                    color="white",
                    size=14,
                    text_align=ft.TextAlign.CENTER,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),

                ft.ElevatedButton(
                    "Download / Save File",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=lambda e: page.run_task(
                        save_file_to_device,
                        path,
                        name
                    ),
                ),
            ],

            alignment=ft.MainAxisAlignment.CENTER,

            horizontal_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),

            spacing=12,
        )

        viewer_filename_text.value = ""

        viewer_content.width = (
            page.window.width or 360
        ) - 20

        viewer_content.height = 280

        viewer_content.scale = 0.3
        viewer_content.opacity = 0

        page.show_dialog(viewer_dialog)

        await asyncio.sleep(0.03)

        viewer_content.scale = 1
        viewer_content.opacity = 1

        page.update()


    def open_viewer(path, name):

        if not path or not os.path.exists(path):

            toast(
                "File ab available nahi hai",
                "red"
            )

            return

        if path.lower().endswith(IMAGE_EXT):

            page.run_task(
                open_image_viewer,
                path
            )

        else:

            page.run_task(
                open_file_viewer,
                path,
                name
            )


    # ==================================================================
    # DELETE
    # ==================================================================

    def remove_bubble(mid):

        item = msg_index.pop(mid, None)

        if not item:
            return

        if item["row"] in chat_area.controls:

            chat_area.controls.remove(
                item["row"]
            )

        page.update()


    def delete_for_me(mid, dlg):

        page.pop_dialog()

        item = msg_index.get(mid)

        db_id = (
            item.get("db_id")
            if item
            else None
        )

        remove_bubble(mid)

        db_delete(db_id)


    def delete_for_everyone(mid, dlg):

        page.pop_dialog()

        item = msg_index.get(mid)

        db_id = (
            item.get("db_id")
            if item
            else None
        )

        remove_bubble(mid)

        db_delete(db_id)

        if ws_state["connection"]:

            page.run_task(
                send_json,
                {
                    "type": "delete",
                    "to": contact_phone,
                    "mid": mid,
                }
            )


    def open_msg_menu(mid, is_mine):

        actions = []

        if is_mine:

            actions.append(
                ft.TextButton(
                    "Delete for everyone",
                    style=ft.ButtonStyle(
                        color="red"
                    ),
                    on_click=lambda e:
                        delete_for_everyone(
                            mid,
                            dlg
                        ),
                )
            )

        actions.append(
            ft.TextButton(
                "Delete for me",
                on_click=lambda e:
                    delete_for_me(
                        mid,
                        dlg
                    ),
            )
        )

        actions.append(
            ft.TextButton(
                "Cancel",
                on_click=lambda e:
                    page.pop_dialog()
            )
        )

        dlg = ft.AlertDialog(
            title=ft.Text("Message"),
            actions=actions
        )

        page.show_dialog(dlg)


    # ==================================================================
    # MESSAGE BUBBLE
    # ==================================================================

    def make_bubble(
        mid,
        text,
        is_mine,
        time_str="",
        status_ticks="",
        media_kind=None,
        media_path=None,
        media_name=None,
        db_id=None
    ):

        inner_controls = []

        # IMAGE
        if (
            media_kind in ("image", "camera")
            and media_path
            and os.path.exists(media_path)
        ):

            inner_controls.append(
                ft.Container(
                    content=ft.Image(
                        src=img_src(media_path),
                        width=200,
                        height=200,
                        fit=ft.BoxFit.COVER,
                        border_radius=10,
                    ),

                    on_click=lambda e:
                        open_viewer(
                            media_path,
                            media_name or "Image"
                        ),
                )
            )

        # FILE
        elif media_kind == "file" and media_path:

            inner_controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.INSERT_DRIVE_FILE,
                                color="blue"
                            ),

                            ft.Text(
                                media_name or "File",
                                color="white",
                                size=13,
                                max_lines=1,
                                overflow=(
                                    ft.TextOverflow.ELLIPSIS
                                ),
                                width=180,
                            ),
                        ],
                    ),

                    on_click=lambda e:
                        open_viewer(
                            media_path,
                            media_name or "File"
                        ),

                    padding=6,
                    border_radius=8,
                    bgcolor=ft.Colors.WHITE_10,
                )
            )

        # TEXT
        if text:

            inner_controls.append(
                ft.Text(
                    text,
                    color="white"
                )
            )

        tick_text = (
            ft.Text(
                status_ticks,
                size=13,
                color="blue"
            )
            if is_mine
            else ft.Text("")
        )

        inner_controls.append(
            ft.Row(
                controls=[
                    ft.Text(
                        time_str,
                        size=11,
                        color="white70"
                    ),

                    tick_text
                ],

                alignment=(
                    ft.MainAxisAlignment.END
                ),

                spacing=5,
            )
        )

        row_content = ft.Container(
            content=ft.Column(
                controls=inner_controls,
                tight=True,
                spacing=4
            ),

            bgcolor=(
                ft.Colors.BLUE_900
                if is_mine
                else ft.Colors.BLACK_12
            ),

            border_radius=12,

            padding=ft.Padding(
                left=10,
                right=10,
                top=6,
                bottom=6
            ),
        )

        wrapped = ft.GestureDetector(
            content=row_content,

            on_long_press_start=lambda e, m=mid, mine=is_mine:
                open_msg_menu(
                    m,
                    mine
                ),

            on_secondary_tap=lambda e, m=mid, mine=is_mine:
                open_msg_menu(
                    m,
                    mine
                ),
        )

        row = ft.Row(
            controls=[wrapped],

            alignment=(
                ft.MainAxisAlignment.END
                if is_mine
                else ft.MainAxisAlignment.START
            ),
        )

        msg_index[mid] = {
            "row": row,
            "tick": tick_text,
            "db_id": db_id,
        }

        return row


    # ==================================================================
    # CHAT AREA
    # ==================================================================

    chat_area = ft.ListView(
        controls=[],
        expand=True,
        spacing=2,

        padding=ft.Padding(
            left=10,
            right=10,
            top=10,
            bottom=5
        ),

        auto_scroll=True,
    )


    # ==================================================================
    # LOAD OLD MESSAGES
    # ==================================================================

    db.cur.execute(
        """
        SELECT
            message_id,
            sender_id,
            message,
            message_type,
            message_status,
            sent_at
        FROM message
        WHERE
            (
                sender_id = %s
                AND receiver_id = %s
            )
            OR
            (
                sender_id = %s
                AND receiver_id = %s
            )
        ORDER BY sent_at ASC
        """,

        (
            my_id,
            contact_id,
            contact_id,
            my_id
        ),
    )

    history = db.cur.fetchall()

    for row in history:

        is_mine = (
            row["sender_id"] == my_id
        )

        time_str = format_india_time(
            row["sent_at"]
        )

        row_mid = str(
            uuid.uuid4()
        )

        db_id = row.get(
            "message_id"
        )

        body = row["message"] or ""

        if body.startswith("[media]"):

            try:

                m_path, m_name, m_kind = (
                    body[7:].split("|", 2)
                )

            except ValueError:

                m_path = None
                m_name = "File"
                m_kind = "file"

            chat_area.controls.append(
                make_bubble(
                    row_mid,
                    None,
                    is_mine,
                    time_str,
                    "✓✓" if is_mine else "",
                    media_kind=m_kind,
                    media_path=m_path,
                    media_name=m_name,
                    db_id=db_id
                )
            )

        else:

            chat_area.controls.append(
                make_bubble(
                    row_mid,
                    body,
                    is_mine,
                    time_str,
                    "✓✓" if is_mine else "",
                    db_id=db_id
                )
            )


    # ==================================================================
    # SEEN
    # ==================================================================

    try:

        db.cur.execute(
            """
            UPDATE message
            SET message_status = 'seen'
            WHERE
                sender_id = %s
                AND receiver_id = %s
                AND message_status IN
                    ('sent', 'delivered')
            """,

            (
                contact_id,
                my_id
            ),
        )

        db.conn.commit()

    except Exception as ex:

        print(
            "Seen update failed:",
            ex
        )


    # ==================================================================
    # CLEAR CHAT
    # ==================================================================

    def clear_chat(e):

        chat_area.controls.clear()

        msg_index.clear()

        page.update()

        try:

            db.cur.execute(
                """
                DELETE FROM message
                WHERE
                    (
                        sender_id = %s
                        AND receiver_id = %s
                    )
                    OR
                    (
                        sender_id = %s
                        AND receiver_id = %s
                    )
                """,

                (
                    my_id,
                    contact_id,
                    contact_id,
                    my_id
                ),
            )

            db.conn.commit()

        except Exception as ex:

            toast(
                f"Delete failed: {ex}",
                "red"
            )


    # ==================================================================
    # MENU
    # ==================================================================

    menu = ft.PopupMenuButton(

        icon=ft.Icons.MORE_VERT,

        tooltip="menu",

        margin=5,

        style=ft.ButtonStyle(
            bgcolor="black"
        ),

        items=[

            ft.PopupMenuItem(

                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.PERSON_ADD,
                            color="blue"
                        ),

                        ft.Text(
                            "Add conatct",
                            font_family="arial"
                        )
                    ]
                ),

                on_click=lambda e:
                    Addthis(
                        page,
                        my_id,
                        contact_name,
                        contact_phone
                    )
            ),

            ft.PopupMenuItem(

                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.DELETE,
                            color="red"
                        ),

                        ft.Text(
                            "Delete all chats",
                            font_family="arial"
                        )
                    ]
                ),

                on_click=clear_chat
            )
        ]
    )


    # ==================================================================
    # ONLINE / OFFLINE STATUS
    # ==================================================================

    status_text = ft.Text(
        spans=[
            ft.TextSpan(
                "offline",
                style=ft.TextStyle(
                    color="grey"
                )
            )
        ],

        font_family="arial",
    )


    def update_contact_status(online):

        if online:

            status_text.spans = [
                ft.TextSpan(
                    "online",
                    style=ft.TextStyle(
                        color="green"
                    )
                )
            ]

        else:

            status_text.spans = [
                ft.TextSpan(
                    "offline",
                    style=ft.TextStyle(
                        color="grey"
                    )
                )
            ]

        page.update()


    dot = ft.Container(
        content=status_text
    )


    # ==================================================================
    # CONTACT PROFILE
    # ==================================================================

    from screens.contact_profile import ContactProfile


    # ==================================================================
    # APP BAR
    # ==================================================================

    appbar = ft.AppBar(

        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Chats",
            bgcolor=ft.Colors.BLACK_26,
            icon_size=18,
            padding=5,
            margin=5,
            on_click=lambda e:
                Home(
                    page,
                    my_id
                )
        ),

        title=ft.Container(

            content=ft.ListTile(

                leading=ft.CircleAvatar(
                    content=ft.Text(
                        get_initials(
                            contact_name
                        )
                    ),

                    bgcolor="black",

                    tooltip="profile"
                ),

                title=ft.Column(
                    controls=[
                        ft.Text(
                            contact_name
                        ),

                        dot
                    ]
                )
            ),

            on_click=lambda e:
                ContactProfile(
                    page,
                    my_id,
                    contact_id,
                    contact_name,
                    contact_phone
                ),
        ),

        actions=[
            menu
        ],

        bgcolor=ft.Colors.WHITE_10,
    )


    # ==================================================================
    # SEND JSON
    # ==================================================================

    async def send_json(data):

        ws = ws_state.get(
            "connection"
        )

        if not ws:

            print(
                "WebSocket not connected"
            )

            return False

        try:

            payload = json.dumps(
                data
            )

            print(
                "WEBSOCKET SEND:",
                payload
            )

            await ws.send(
                payload
            )

            return True

        except Exception as ex:

            print(
                "WebSocket send error:",
                repr(ex)
            )

            ws_state["connection"] = None
            ws_state["connected"] = False

            update_contact_status(
                False
            )

            return False


    # ==================================================================
    # RECEIVE MESSAGE
    # ==================================================================

    async def handle_websocket_message(
        data
    ):

        print(
            "WEBSOCKET RECEIVED:",
            data
        )

        message_type = str(
            data.get("type")
            or data.get("event")
            or data.get("action")
            or ""
        ).lower()


        # ---------------------------------------------------------------
        # ONLINE
        # ---------------------------------------------------------------

        if message_type in (
            "online",
            "connected",
            "user_online"
        ):

            phone = str(
                data.get("phone")
                or data.get("user_phone")
                or data.get("from")
                or ""
            )

            user_id = data.get(
                "user_id"
            )

            if (
                phone == str(contact_phone)
                or str(user_id) == str(contact_id)
            ):

                update_contact_status(
                    True
                )

            return


        # ---------------------------------------------------------------
        # OFFLINE
        # ---------------------------------------------------------------

        if message_type in (
            "offline",
            "disconnected",
            "user_offline"
        ):

            phone = str(
                data.get("phone")
                or data.get("user_phone")
                or data.get("from")
                or ""
            )

            user_id = data.get(
                "user_id"
            )

            if (
                phone == str(contact_phone)
                or str(user_id) == str(contact_id)
            ):

                update_contact_status(
                    False
                )

            return


        # ---------------------------------------------------------------
        # PRESENCE
        # ---------------------------------------------------------------

        if message_type in (
            "presence",
            "status",
            "user_status"
        ):

            phone = str(
                data.get("phone")
                or data.get("user_phone")
                or data.get("from")
                or ""
            )

            user_id = data.get(
                "user_id"
            )

            is_contact = (
                phone == str(contact_phone)
                or str(user_id) == str(contact_id)
            )

            if not is_contact:
                return

            status = str(
                data.get("status")
                or data.get("presence")
                or ""
            ).lower()

            if status in (
                "online",
                "connected",
                "active"
            ):

                update_contact_status(
                    True
                )

            elif status in (
                "offline",
                "disconnected",
                "inactive"
            ):

                update_contact_status(
                    False
                )

            return


        # ---------------------------------------------------------------
        # DELETE
        # ---------------------------------------------------------------

        if message_type == "delete":

            mid = data.get(
                "mid"
            )

            if mid:

                remove_bubble(
                    mid
                )

            return


        # ---------------------------------------------------------------
        # MESSAGE
        # ---------------------------------------------------------------

        if message_type in (
            "message",
            "chat",
            "text"
        ):

            sender_phone = str(
                data.get("from")
                or data.get("sender_phone")
                or data.get("phone")
                or ""
            )

            sender_id = data.get(
                "sender_id"
            )

            if (
                sender_phone
                and sender_phone != str(contact_phone)
                and str(sender_id) != str(contact_id)
            ):
                return


            body = (
                data.get("message")
                or data.get("text")
                or ""
            )

            message_id = str(
                data.get("mid")
                or uuid.uuid4()
            )

            # -----------------------------------------------------------
            # MEDIA MESSAGE
            # -----------------------------------------------------------

            if data.get("media"):

                media_data = data.get(
                    "media"
                )

                media_name = (
                    data.get("file_name")
                    or data.get("name")
                    or "file"
                )

                media_kind = (
                    data.get("media_type")
                    or data.get("kind")
                    or "file"
                )

                media_path = save_incoming_media(
                    media_name,
                    media_data
                )

                db_body = (
                    f"[media]{media_path}|"
                    f"{media_name}|"
                    f"{media_kind}"
                )

                db_id = db_save(
                    message_id,
                    contact_id,
                    my_id,
                    db_body,
                    media_kind
                )

                row = make_bubble(
                    message_id,
                    body,
                    False,
                    "",
                    "",
                    media_kind=media_kind,
                    media_path=media_path,
                    media_name=media_name,
                    db_id=db_id
                )

            else:

                db_id = db_save(
                    message_id,
                    contact_id,
                    my_id,
                    body,
                    "text"
                )

                row = make_bubble(
                    message_id,
                    body,
                    False,
                    "",
                    "",
                    db_id=db_id
                )

            chat_area.controls.append(
                row
            )

            page.update()

            # Message ko seen mark karne ke liye
            await send_json(
                {
                    "type": "seen",
                    "mid": message_id,
                    "to": contact_phone
                }
            )

            return


        # ---------------------------------------------------------------
        # DELIVERED
        # ---------------------------------------------------------------

        if message_type in (
            "delivered",
            "delivery"
        ):

            mid = data.get(
                "mid"
            )

            item = msg_index.get(
                mid
            )

            if item:

                item["tick"].value = "✓✓"

                page.update()

            return


        # ---------------------------------------------------------------
        # SEEN
        # ---------------------------------------------------------------

        if message_type == "seen":

            mid = data.get(
                "mid"
            )

            item = msg_index.get(
                mid
            )

            if item:

                item["tick"].value = "✓✓"

                item["tick"].color = "blue"

                page.update()

            return


    # ==================================================================
    # WEBSOCKET CONNECTION LOOP
    # ==================================================================

    async def websocket_loop():

        while ws_state["running"]:

            try:

                print(
                    "Connecting WebSocket..."
                )

                async with websockets.connect(
                    WS_SERVER_URL,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                ) as ws:

                    ws_state["connection"] = ws
                    ws_state["connected"] = True

                    print(
                        "WebSocket CONNECTED"
                    )

                    # --------------------------------------------------
                    # REGISTER
                    # --------------------------------------------------

                    register_data = {
                        "type": "register",
                        "phone": my_phone,
                        "user_id": my_id,
                    }

                    await ws.send(
                        json.dumps(
                            register_data
                        )
                    )

                    print(
                        "REGISTER SENT:",
                        register_data
                    )

                    # --------------------------------------------------
                    # IMPORTANT:
                    # Connection means OUR websocket is online.
                    #
                    # Contact status will be changed only when server
                    # sends presence/status for that contact.
                    # --------------------------------------------------

                    # --------------------------------------------------
                    # RECEIVE LOOP
                    # --------------------------------------------------

                    async for raw_message in ws:

                        try:

                            data = json.loads(
                                raw_message
                            )

                        except Exception as ex:

                            print(
                                "Invalid JSON:",
                                raw_message,
                                ex
                            )

                            continue

                        await handle_websocket_message(
                            data
                        )


            except asyncio.CancelledError:

                break


            except Exception as ex:

                print(
                    "WebSocket connection error:",
                    repr(ex)
                )


            finally:

                ws_state["connection"] = None
                ws_state["connected"] = False

                update_contact_status(
                    False
                )


            # -----------------------------------------------------------
            # RECONNECT
            # -----------------------------------------------------------

            if ws_state["running"]:

                print(
                    "Reconnecting in 3 seconds..."
                )

                await asyncio.sleep(
                    3
                )


    # ==================================================================
    # SEND TEXT MESSAGE
    # ==================================================================

    async def send_message():

        text = message_field.value.strip()

        if not text:

            return

        if not ws_state["connected"]:

            toast(
                "Connecting...",
                "orange"
            )

            return


        mid = str(
            uuid.uuid4()
        )


        # ---------------------------------------------------------------
        # SAVE DB
        # ---------------------------------------------------------------

        db_id = db_save(
            mid,
            my_id,
            contact_id,
            text,
            "text"
        )


        # ---------------------------------------------------------------
        # SHOW MESSAGE
        # ---------------------------------------------------------------

        time_str = format_india_time(
            None
        )

        row = make_bubble(
            mid,
            text,
            True,
            time_str,
            "✓",
            db_id=db_id
        )

        chat_area.controls.append(
            row
        )


        # ---------------------------------------------------------------
        # SEND JSON
        # ---------------------------------------------------------------

        success = await send_json(
            {
                "type": "message",
                "mid": mid,
                "from": my_phone,
                "to": contact_phone,
                "sender_id": my_id,
                "receiver_id": contact_id,
                "message": text,
                "message_type": "text",
            }
        )


        if not success:

            item = msg_index.get(
                mid
            )

            if item:

                item["tick"].value = "!"

                item["tick"].color = "red"

        else:

            item = msg_index.get(
                mid
            )

            if item:

                item["tick"].value = "✓"


        message_field.value = ""

        page.update()


    # ==================================================================
    # MESSAGE INPUT
    # ==================================================================

    async def on_submit(e):

        await send_message()


    message_field = ft.TextField(

        hint_text="typing...",

        hint_style=ft.TextStyle(
            color="white70"
        ),

        border=ft.InputBorder.NONE,

        expand=True,

        text_size=18,

        multiline=False,

        on_submit=on_submit,
    )


    # ==================================================================
    # SEND BUTTON
    # ==================================================================

    send_button = ft.IconButton(

        icon=ft.Icons.SEND,

        icon_color="blue",

        icon_size=30,

        on_click=lambda e:
            page.run_task(
                send_message
            )
    )


    # ==================================================================
    # BANNER
    # ==================================================================

    banner_text = ft.Text(
        "",
        size=13,
        color="white"
    )

    banner = ft.Container(
        content=banner_text,
        height=0,
        opacity=0,
        animate_opacity=200,
        alignment=ft.Alignment.CENTER,
    )


    # ==================================================================
    # INPUT BOX
    # ==================================================================

    input_box = ft.Container(

        content=ft.Row(
            controls=[

                ft.IconButton(
                    icon=ft.Icons.ADD,
                    icon_color="blue",
                    icon_size=30,
                ),

                message_field,

                ft.IconButton(
                    icon=ft.Icons.MIC,
                    icon_color="blue",
                    icon_size=30,
                ),

                send_button,
            ],

            vertical_alignment=(
                ft.CrossAxisAlignment.CENTER
            ),
        ),

        border=ft.Border.all(
            3,
            ft.Colors.WHITE_24
        ),

        border_radius=35,

        padding=ft.Padding(
            left=8,
            right=8,
            top=2,
            bottom=2
        ),

        margin=ft.Margin(
            left=10,
            right=10,
            top=5,
            bottom=10
        ),

        height=110,
    )


    # ==================================================================
    # MAIN BODY
    # ==================================================================

    page.add(

        ft.Column(

            controls=[

                appbar,

                banner,

                chat_area,

                input_box,

            ],

            expand=True,

            spacing=0,
        )
    )


    # ==================================================================
    # START WEBSOCKET
    # ==================================================================

    page.run_task(
        websocket_loop
    )
