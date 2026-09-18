
# ------- One-to-one chat ----------------
import flet as ft
import asyncio
import json
import base64
import io
import mimetypes
import os
import uuid
import websockets
from PIL import Image
from database.db import Database
from screens.home import Home
from datetime import timedelta
# --- naya: apne 4 screens import kiye (path apne project ke hisaab se badal lena) ---
from screens.camera_screen import CameraScreen
from screens.mic_screen import MicScreen
from screens.file_screen import FileScreen
from screens.gallery_screen import GalleryScreen

WS_SERVER_URL = "wss://indsapp-websocket.onrender.com"  # abhi live server -- asli server deploy hone pe "wss://tumhara-domain.com" daalna

MEDIA_DIR = "assets"
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")

# Render/Cloudflare ka WebSocket proxy bade messages pe connection reset
# kar deta hai (ConnectionClosedError) -- isse bachne ke liye images
# compress karte hain aur bahut badi files ko bhejne se pehle hi rok dete hain.
MAX_SEND_BYTES = 900 * 1024  # ~900 KB


def compress_image_b64(b64_data, max_dimension=1280, quality=75):
    """Bada image chhota karke wapas base64 deta hai, taaki WebSocket
    proxy ke message-size limit se connection na tute. Camera se aayi
    full-resolution photo aksar isi wajah se fail hoti hai."""
    try:
        raw = base64.b64decode(b64_data)
        img = Image.open(io.BytesIO(raw))
        img = img.convert("RGB")
        img.thumbnail((max_dimension, max_dimension))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as ex:
        print("Image compression failed:", repr(ex), flush=True)
        return b64_data  # fallback: jo mila wahi bhej do

# InteractiveViewer har Flet version me nahi hota -- agar available hai to
# pinch/scroll se zoom milega, warna bina crash kiye plain image dikhegi.
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


def Chat(page: ft.Page, my_id: int, contact_id: int, contact_name: str, contact_phone: str,  refresh_notification):
    page.clean()

    from screens.addthis import Addthis

    # page.vertical_alignment = ft.MainAxisAlignment.CENTER
    # page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 360
    page.window.height = 700
    page.navigation_bar = None
    page.padding = 0

    db = Database()

    # ---- Apna phone number nikalo (WebSocket register karne ke liye) ----
    db.cur.execute("SELECT phone FROM user WHERE id = %s", (my_id,))
    my_row = db.cur.fetchone()
    my_phone = str(my_row["phone"]) if my_row else ""

    # ---- Websocket connection ka reference (send karte waqt use hoga) ----
    ws_state = {"connection": None}

    # mid -> {"row": control, "tick": Text control}  -- delete + tick update ke liye
    msg_index = {}

    # ab ek nahi, kayi attachments ek saath attach ho sakte hain
    # har item: {"id","type","path","name","b64"}
    pending_attachments = []

    # File download/save picker. In web mode this downloads the file.
    download_picker = ft.FilePicker()
    page.services.append(download_picker)

    # ==================================================================
    # CHHOTI HELPER FUNCTIONS
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
            banner.height = 0
            banner.opacity = 0
            page.update()

    def db_save(mid, sender_id, receiver_id, body, message_type="text"):
        """Save message using the existing message table.
        The table uses message_id as its primary key; it does not require a mid column.
        """
        try:
            db.cur.execute(
                """
                INSERT INTO message
                    (sender_id, receiver_id, message, message_type, message_status, sent_at)
                VALUES
                    (%s, %s, %s, %s, 'sent', NOW())
                """,
                (sender_id, receiver_id, body, message_type),
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
                (message_id,),
            )
            db.conn.commit()
        except Exception as ex:
            print("DB delete failed:", ex)

    def save_incoming_media(name, b64_data):
        os.makedirs(MEDIA_DIR, exist_ok=True)
        try:
            raw = base64.b64decode(b64_data)
        except Exception:
            return None
        path = os.path.join(MEDIA_DIR, f"{uuid.uuid4().hex[:8]}_{name}")
        with open(path, "wb") as f:
            f.write(raw)
        return path

    def to_data_uri(b64_data, mime="image/jpeg"):
        # Jab base64 pehle se memory me hai (abhi-abhi camera/gallery/file
        # se aaya), to disk se dobara padhne ki zaroorat nahi
        if not b64_data:
            return None
        if b64_data.startswith("data:"):
            return b64_data
        return f"data:{mime};base64,{b64_data}"

    def img_src(path):
        # Browser (web) mode me server ka raw file path seedha kaam nahi
        # karta -- isliye file ko yahin base64 me badal ke bhejte hain,
        # jo web aur desktop dono me chalta hai
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                raw = f.read()
            mime, _ = mimetypes.guess_type(path)
            mime = mime or "image/jpeg"
            return f"data:{mime};base64,{base64.b64encode(raw).decode('utf-8')}"
        except Exception:
            return None

    # ==================================================================
    # BADA VIEWER BOX  (image/file pe tap karke khulta hai)
    # Ek hi dialog reuse hota hai (HomeScreen jaisa), taaki har tap pe
    # naya AlertDialog na banana pade -- yahi pattern tumhare working
    # HomeScreen me use hota hai.
    # ==================================================================

    viewer_body = ft.Container(alignment=ft.Alignment.CENTER, expand=True)

    viewer_filename_text = ft.Text("", color="white", weight=ft.FontWeight.BOLD, size=14)

    viewer_content = ft.Container(
        content=ft.Column(
            controls=[viewer_body, viewer_filename_text],
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
                        ft.IconButton(icon=ft.Icons.CLOSE, icon_color="white", tooltip="Close", on_click=close_viewer),
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

        if HAS_INTERACTIVE_VIEWER:
            # pinch/scroll se zoom in-out
            viewer_body.content = ft.InteractiveViewer(
                min_scale=1,
                max_scale=5,
                boundary_margin=ft.Margin(0, 0, 0, 0),
                content=ft.Image(src=img_src(path), fit=ft.BoxFit.CONTAIN),
            )
        else:
            viewer_body.content = ft.Image(src=img_src(path), fit=ft.BoxFit.CONTAIN)

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
            toast("File ab available nahi hai", "red")
            return

        try:
            with open(path, "rb") as f:
                file_bytes = f.read()

            # Flet web: browser downloads the bytes.
            # Desktop: user selects a location and the bytes are saved there.
            await download_picker.save_file(
                dialog_title="Save file",
                file_name=name or "file",
                src_bytes=file_bytes,
            )
        except Exception as ex:
            print("File save/open error:", repr(ex))
            toast(f"File open nahi hua: {ex}", "red")

    async def open_file_viewer(path, name):
        viewer_body.content = ft.Column(
            controls=[
                ft.Icon(ft.Icons.INSERT_DRIVE_FILE, size=80, color="blue"),
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
                        save_file_to_device, path, name
                    ),
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        )
        viewer_filename_text.value = ""

        viewer_content.width = (page.window.width or 360) - 20
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
            toast("File ab available nahi hai", "red")
            return

        if path.lower().endswith(IMAGE_EXT):
            page.run_task(open_image_viewer, path)
        else:
            page.run_task(open_file_viewer, path, name)

    # ==================================================================
    # DELETE (long press pe menu)
    # ==================================================================

    def remove_bubble(mid):
        item = msg_index.pop(mid, None)
        if not item:
            return
        if item["row"] in chat_area.controls:
            chat_area.controls.remove(item["row"])
        page.update()

    def delete_for_me(mid, dlg):
        page.pop_dialog()
        item = msg_index.get(mid)
        db_id = item.get("db_id") if item else None
        remove_bubble(mid)
        db_delete(db_id)

    def delete_for_everyone(mid, dlg):
        page.pop_dialog()
        item = msg_index.get(mid)
        db_id = item.get("db_id") if item else None
        remove_bubble(mid)
        db_delete(db_id)
        if ws_state["connection"]:
            page.run_task(
                ws_state["connection"].send,
                json.dumps({
                    "type": "delete",
                    "to": contact_phone,
                    "mid": mid,
                }),
            )

    def open_msg_menu(mid, is_mine):
        actions = []
        if is_mine:
            actions.append(
                ft.TextButton(
                    "Delete for everyone",
                    style=ft.ButtonStyle(color="red"),
                    on_click=lambda e: delete_for_everyone(mid, dlg),
                )
            )
        actions.append(
            ft.TextButton(
                "Delete for me",
                on_click=lambda e: delete_for_me(mid, dlg),
            )
        )
        actions.append(
            ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog())
        )

        dlg = ft.AlertDialog(title=ft.Text("Message"), actions=actions)
        page.show_dialog(dlg)

    # ==================================================================
    # BUBBLE  (text + media dono handle karta hai)
    # ==================================================================

    def make_bubble(mid, text, is_mine, time_str="", status_ticks="",
                     media_kind=None, media_path=None, media_name=None, db_id=None):

        inner_controls = []

        if media_kind in ("image", "camera") and media_path and os.path.exists(media_path):
            inner_controls.append(
                ft.Container(
                    content=ft.Image(src=img_src(media_path), width=200, height=200,
                                      fit=ft.BoxFit.COVER, border_radius=10),
                    on_click=lambda e: open_viewer(media_path, media_name or "Image"),
                )
            )
        elif media_kind == "file" and media_path:
            inner_controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color="blue"),
                            ft.Text(media_name or "File", color="white", size=13,
                                     max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=180),
                        ],
                    ),
                    on_click=lambda e: open_viewer(media_path, media_name or "File"),
                    padding=6, border_radius=8, bgcolor=ft.Colors.WHITE_10,
                )
            )

        if text:
            inner_controls.append(ft.Text(text, color="white"))

        tick_text = ft.Text(status_ticks, size=13, color="blue") if is_mine else ft.Text("")

        inner_controls.append(
            ft.Row(
                controls=[ft.Text(time_str, size=11, color="white70"), tick_text],
                alignment=ft.MainAxisAlignment.END,
                spacing=5,
            )
        )

        row_content = ft.Container(
            content=ft.Column(controls=inner_controls, tight=True, spacing=4),
            bgcolor=ft.Colors.BLUE_900 if is_mine else ft.Colors.BLACK_12,
            border_radius=12,
            padding=ft.Padding(left=10, right=10, top=6, bottom=6),
            width=None,
        )
        wrapped = ft.GestureDetector(
            content=row_content,
            on_long_press_start=lambda e, m=mid, mine=is_mine: open_msg_menu(m, mine),
            on_secondary_tap=lambda e, m=mid, mine=is_mine: open_msg_menu(m, mine),
        )

        row = ft.Row(
            controls=[wrapped],
            alignment=ft.MainAxisAlignment.END if is_mine else ft.MainAxisAlignment.START,
        )

        msg_index[mid] = {"row": row, "tick": tick_text, "db_id": db_id}

        return row

    # ---------------------------------------------------------------
    # CHAT SCROLL
    # ---------------------------------------------------------------
    # Normal ListView rakha gaya hai. auto_scroll=True ka matlab:
    # - chat chhota ho to latest message bottom/input ke paas rahega
    # - chat bada ho to latest message bottom par rahega aur purane
    #   messages upar scroll honge
    # Isliye reverse=True aur manual scroll_to ki zaroorat nahi hai.
    chat_area = ft.ListView(
        controls=[],
        expand=True,
        spacing=2,
        padding=ft.Padding(left=10, right=10, top=10, bottom=5),
        auto_scroll=True,
    )
    # ---- Purani messages DB se load karo ----
    db.cur.execute(
        """
        SELECT message_id, sender_id, message, message_type, message_status, sent_at
        FROM message
        WHERE (sender_id = %s AND receiver_id = %s)
           OR (sender_id = %s AND receiver_id = %s)
        ORDER BY sent_at ASC
        """,
        (my_id, contact_id, contact_id, my_id),
    )
    history = db.cur.fetchall()
    for row in history:
        is_mine = row["sender_id"] == my_id
        time_str = format_india_time(row["sent_at"])
        row_mid = str(uuid.uuid4())
        db_id = row.get("message_id")
        body = row["message"] or ""

        if body.startswith("[media]"):
            try:
                m_path, m_name, m_kind = body[7:].split("|", 2)
            except ValueError:
                m_path, m_name, m_kind = None, "File", "file"
            chat_area.controls.append(
                make_bubble(row_mid, None, is_mine, time_str, "✓✓" if is_mine else "",
                             media_kind=m_kind, media_path=m_path, media_name=m_name,
                             db_id=db_id)
            )
        else:
            chat_area.controls.append(
                make_bubble(row_mid, body, is_mine, time_str, "✓✓" if is_mine else "",
                             db_id=db_id)
            )

    # Chat open hote hi saamne wale ke unread messages seen ho jaate hain.
    try:
        db.cur.execute(
            """
            UPDATE message
            SET message_status = 'seen'
            WHERE sender_id = %s
              AND receiver_id = %s
              AND message_status IN ('sent', 'delivered')
            """,
            (contact_id, my_id),
        )
        db.conn.commit()
    except Exception as ex:
        print("Seen update failed:", ex)

    def clear_chat(e):
        chat_area.controls.clear()
        msg_index.clear()
        page.update()
   
        try:
            db.cur.execute(
                """
                DELETE FROM message
                WHERE (sender_id = %s AND receiver_id = %s)
                   OR (sender_id = %s AND receiver_id = %s)
                """,
                (my_id, contact_id, contact_id, my_id),
            )
            db.conn.commit()
        except Exception as ex:
         toast(f"Delete failed: {ex}", "red")

    menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        tooltip="menu",
        margin=5,
        style=ft.ButtonStyle(bgcolor="black"),
        items=[
            ft.PopupMenuItem(
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.PERSON_ADD, color="blue"),
                    ft.Text("Add conatct", font_family="arial")
                ]),
                on_click=lambda e: Addthis(page, my_id, contact_name, contact_phone)
            ),
            ft.PopupMenuItem(
                content=ft.Row(controls=[
                    ft.Icon(ft.Icons.DELETE, color="red"),
                    ft.Text("Delete all chats", font_family="arial")
                ]),
                on_click=clear_chat
            )
        ]
    )

    status_text = ft.Text(
        spans=[ft.TextSpan("offline", style=ft.TextStyle(color="grey"))],
        font_family="arial",
    )
    dot = ft.Container(content=status_text)

    def update_contact_status(online):

        if online:

            status_text.spans = [
                ft.TextSpan(
                    "online",
                    style=ft.TextStyle(color="green")
                )
            ]

        else:

            status_text.spans = [
                ft.TextSpan(
                    "offline",
                    style=ft.TextStyle(color="grey")
                )
            ]

        page.update()

    from screens.contact_profile import ContactProfile

    appbar = ft.AppBar(
        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Chats",
            bgcolor=ft.Colors.BLACK_26,
            icon_size=18,
            padding=5,
            margin=5,
            on_click=lambda e: Home(page, my_id)
        ),
        title=ft.Container(
            content=ft.ListTile(
                leading=ft.CircleAvatar(
                    content=ft.Text(get_initials(contact_name)),
                    bgcolor="black",
                    tooltip="profile"
                ),
                title=ft.Column(controls=[ft.Text(contact_name), dot])
            ),
            on_click=lambda e: ContactProfile(page, my_id, contact_id, contact_name, contact_phone),
        ),
        actions=[menu],
        bgcolor=ft.Colors.WHITE_10,
    )

    # ==================================================================
    # ATTACHMENT PREVIEW BOX  (text field ke UPAR)
    # ==================================================================

    attachment_box = ft.Container(
        # Default me bilkul hidden. Attachment select hote hi
        # sirf chhota preview area dikhega.
        height=0,
        opacity=0,
        animate_opacity=200,
        animate_size=200,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        margin=ft.Margin(left=8, right=8, top=0, bottom=0),
    )

    # chhota status banner -- SnackBar ki jagah, kyunki is Flet version me
    # page.open() available nahi hai
    banner_text = ft.Text(
        "",
        size=12,
        visible=False,
        text_align=ft.TextAlign.CENTER,
    )
    banner = ft.Container(
        content=banner_text,
        height=0,
        opacity=0,
        padding=0,
        alignment=ft.Alignment.CENTER,
        animate_size=200,
        animate_opacity=200,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    def render_attachment_bar():
        if not pending_attachments:
            attachment_box.height = 0
            attachment_box.opacity = 0
            attachment_box.content = None
            page.update()
            return

        chips = []

        for item in pending_attachments:
            aid = item["id"]
            kind = item["type"]
            path = item["path"]
            name = item["name"] or "file"

            if kind in ("image", "camera") and item.get("b64"):
                thumb = ft.Image(src=to_data_uri(item["b64"]), width=56, height=56,
                                  fit=ft.BoxFit.COVER, border_radius=8)
            elif kind in ("image", "camera") and path and os.path.exists(path):
                thumb = ft.Image(src=img_src(path), width=56, height=56,
                                  fit=ft.BoxFit.COVER, border_radius=8)
            else:
                thumb = ft.Container(
                    content=ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color="blue", size=26),
                    width=56, height=56, alignment=ft.Alignment.CENTER,
                    border_radius=8, bgcolor=ft.Colors.WHITE_10,
                )

            chips.append(
                ft.Container(
                    width=76,
                    content=ft.Column(
                        controls=[
                            ft.Stack(
                                controls=[
                                    ft.GestureDetector(
                                        content=thumb,
                                        on_tap=lambda e, p=path, n=name: open_viewer(p, n),
                                    ),
                                    ft.Container(
                                        content=ft.IconButton(
                                            icon=ft.Icons.CLOSE,
                                            icon_color="white",
                                            icon_size=14,
                                            bgcolor=ft.Colors.BLACK_54,
                                            on_click=lambda e, a=aid: remove_attachment(a),
                                        ),
                                        alignment=ft.Alignment.TOP_RIGHT,
                                        width=56, height=56,
                                    ),
                                ],
                            ),
                            ft.Text(
                                name, size=10, color=ft.Colors.WHITE_70,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=70,
                            ),
                        ],
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )

        attachment_box.content = ft.Row(
            controls=chips,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        )
        # 56px thumbnail + filename ke liye chhota extra space.
        # TextField ke bilkul upar rahega, extra blank height nahi lega.
        attachment_box.height = 72
        attachment_box.opacity = 1
        page.update()

    def remove_attachment(aid):
        for i, item in enumerate(pending_attachments):
            if item["id"] == aid:
                pending_attachments.pop(i)
                break
        render_attachment_bar()

    def clear_attachment(e=None):
        pending_attachments.clear()
        render_attachment_bar()

    def show_attachment(kind, path, name, b64_data):
        # Image/camera ko yahin chhota kar do -- camera ki full-resolution
        # photo aksar 3-8 MB ki hoti hai, jo WebSocket proxy tod deta hai
        if kind in ("image", "camera") and b64_data:
            b64_data = compress_image_b64(b64_data)

        # naya attachment list me JUD jaata hai -- purana nahi hatta,
        # isliye camera + image + file sab ek saath rakh sakte ho
        pending_attachments.append({
            "id": str(uuid.uuid4()),
            "type": kind,
            "path": path,
            "name": name,
            "b64": b64_data,
        })
        render_attachment_bar()

    # ==================================================================
    # CAMERA / MIC / FILE / GALLERY  -- teri classes yahan wire ho rahi hain
    # ==================================================================

    def camera_status(text, color="white"):
        toast(text, color)

    def camera_captured(path, b64_jpeg):
        show_attachment("camera", path, os.path.basename(path), b64_jpeg)

    camera_screen = CameraScreen(page, on_status=camera_status, on_captured=camera_captured)

    # open_camera khud dialog kholta hai aur status apne aap update karta hai
    # (isi tarah jaise HomeScreen me hota hai), isliye ek chhota async
    # wrapper se call karo, seedhe method reference se nahi
    async def handle_camera_click(e):
        await camera_screen.open_camera(e)

    def gallery_status(text, color="white"):
        toast(text, color)

    def gallery_picked(path, b64_jpeg):
        name = os.path.basename(path) if path else "image.jpg"
        show_attachment("image", path, name, b64_jpeg)

    gallery_screen = GalleryScreen(page, on_status=gallery_status, on_picked=gallery_picked)

    def file_status(text, color="white"):
        toast(text, color)

    def file_picked(path, filename, file_bytes):
        b64_data = base64.b64encode(file_bytes).decode("utf-8")
        show_attachment("file", path, filename, b64_data)

    file_screen = FileScreen(page, on_status=file_status, on_picked=file_picked)

    def mic_status(text, color="white"):
        if text:
            toast(text, color)

    def mic_result(text):
        user_msg.value = ((user_msg.value or "") + " " + text).strip()
        page.update()

    def mic_recording_change(is_recording):
        mic_btn.icon_color = "red" if is_recording else "blue"
        page.update()

    mic_screen = MicScreen(
        page,
        on_status=mic_status,
        on_result=mic_result,
        on_recording_change=mic_recording_change,
    )

    # ==================================================================
    # SEND
    # ==================================================================

    def send_click(e):
        text = user_msg.value.strip()

        if not text and not pending_attachments:
            return

        if ws_state["connection"] is None:
            toast("Offline hai, message nahi gaya", "red")
            return

        # ---------- ATTACHMENTS (ek ya kayi, jitne bhi lage hon) ----------
        for item in list(pending_attachments):
            mid = str(uuid.uuid4())
            kind = item["type"]
            path = item["path"]
            name = item["name"] or "file"
            b64_data = item["b64"]

            if b64_data and len(b64_data) > MAX_SEND_BYTES:
                toast(f"{name} bahut badi hai, chhoti file/image bhejo", "red")
                remove_attachment(item["id"])
                continue

            page.run_task(
                ws_state["connection"].send,
                json.dumps({
                    "type": "attachment",
                    "mid": mid,
                    "to": contact_phone,
                    "kind": kind,
                    "name": name,
                    "data": b64_data,
                }),
            )

            chat_area.controls.append(
                make_bubble(mid, None, True, "now", "✓",
                             media_kind=kind, media_path=path, media_name=name)
            )

            db_id = db_save(
                mid,
                my_id,
                contact_id,
                text,
                message_type="text",
            )
            
            msg_index[mid]["db_id"] = db_id
            refresh_notification()

        if pending_attachments:
            clear_attachment()

        # ---------- TEXT ----------
        if text:
            mid = str(uuid.uuid4())

            page.run_task(
                ws_state["connection"].send,
                json.dumps({"type": "message", "mid": mid, "to": contact_phone, "text": text}),
            )

            chat_area.controls.append( make_bubble(mid, text, True, "now", "✓"))

            db_id = db_save(mid, my_id, contact_id, text, message_type="text")
            msg_index[mid]["db_id"] = db_id

        user_msg.value = ""
        page.update()

    # ==================================================================
    # INPUT BAR
    # ==================================================================

    mic_btn = ft.IconButton(icon=ft.Icons.MIC, icon_color="blue", margin=5, on_click=mic_screen.toggle_mic)

    user_msg = ft.TextField(
        hint_text="typing...",
        hint_style=ft.TextStyle(color="white"),
        value="",
        autofocus=True,
        expand=True,
        align=ft.Alignment.BOTTOM_CENTER,
        prefix_icon=ft.PopupMenuButton(
            icon=ft.Icon(ft.Icons.ADD, color="blue", margin=6),
            tooltip="menu",
            items=[
                ft.PopupMenuItem(
                    content=ft.Row(controls=[ft.Icon(ft.Icons.CAMERA, color="blue"), ft.Text("Camera")]),
                    on_click=handle_camera_click,
                ),
                ft.PopupMenuItem(
                    content=ft.Row(controls=[ft.Icon(ft.Icons.IMAGE, color="blue"), ft.Text("Image")]),
                    on_click=gallery_screen.open_gallery,
                ),
                ft.PopupMenuItem(
                    content=ft.Row(controls=[ft.Icon(ft.Icons.FILE_UPLOAD, color="blue"), ft.Text("File")]),
                    on_click=file_screen.open_file_picker,
                ),
            ]
        ),
        suffix_icon=ft.Row(
            controls=[
                mic_btn,
                ft.IconButton(icon=ft.Icons.SEND_OUTLINED, icon_color="blue", margin=5, on_click=send_click),
            ],
            tight=True,
            spacing=0
        ),
        height=60,
        margin=5,
        border_color=ft.Colors.WHITE_24,
        border_radius=20,
        width=520,
        color="white",
        tooltip="typing....."
    )

    # ---- WebSocket se connect karo aur live messages sunte raho ----
    # NOTE: pura function ab ek while True loop me hai. Pehle sirf ek
    # baar try hota tha -- fail hone pe hamesha "offline" pe atka rehta
    # tha jab tak Chat screen dobara na khule. Ab agar connect fail ho
    # ya connection beech me toot jaaye, ye khud har 3 second me dobara
    # try karta rahega.
    async def connect_and_listen():

        while True:

            try:
                print("Connecting to WebSocket:", WS_SERVER_URL, flush=True)

                async with websockets.connect(
                    WS_SERVER_URL,
                    max_size=None,
                    open_timeout=30,
                    ping_interval=20,
                    ping_timeout=20,
                ) as ws:

                    print("WebSocket CONNECTED", flush=True)

                    ws_state["connection"] = ws

                    status_text.spans = [
                        ft.TextSpan(
                            "online",
                            style=ft.TextStyle(color="green")
                        )
                    ]
                    page.update()

                    print("Registering phone:", my_phone, flush=True)

                    await ws.send(
                        json.dumps({
                            "type": "register",
                            "phone": my_phone
                        })
                    )

                    print("Phone registered:", my_phone, flush=True)

                    async for raw in ws:
                        print("Received:", raw, flush=True)

                        data = json.loads(raw)
                        mtype = data.get("type")
                        sender = data.get("from")

                        # =================================================
                        # CONTACT ONLINE
                        # =================================================

                        if mtype == "online":

                            phone = str(
                                data.get("phone", "")
                            ).strip()

                            if phone == str(contact_phone):

                                update_contact_status(True)

                            continue

                        # =================================================
                        # CONTACT OFFLINE
                        # =================================================

                        if mtype == "offline":

                            phone = str(
                                data.get("phone", "")
                            ).strip()

                            if phone == str(contact_phone):

                                update_contact_status(False)

                            continue

                        if mtype == "ack":
                            item = msg_index.get(data.get("mid"))
                            if item:
                                item["tick"].value = "✓✓"
                                page.update()
                            continue

                        if mtype == "delete":
                            remove_bubble(data.get("mid"))
                            continue

                        if sender != str(contact_phone):
                            continue

                        mid = data.get("mid") or str(uuid.uuid4())

                        if mtype == "message":
                            row_control = make_bubble(
                                mid,
                                data["text"],
                                False
                            )

                            chat_area.controls.append(row_control)

                            db_id = db_save(
                                mid,
                                contact_id,
                                my_id,
                                data["text"],
                                message_type="text",
                            )

                            msg_index[mid]["db_id"] = db_id

                            page.update()

                        elif mtype == "attachment":
                            kind = data.get("kind", "file")
                            name = data.get("name", "file")

                            path = save_incoming_media(
                                name,
                                data.get("data", "")
                            )

                            chat_area.controls.append(
                                make_bubble(
                                    mid,
                                    None,
                                    False,
                                    media_kind=kind,
                                    media_path=path,
                                    media_name=name,
                                )
                            )

                            db_id = db_save(
                                mid,
                                contact_id,
                                my_id,
                                f"[media]{path}|{name}|{kind}",
                                message_type=kind,
                            )

                            msg_index[mid]["db_id"] = db_id

                            page.update()

                        else:
                            continue

                        await ws.send(
                            json.dumps({
                                "type": "ack",
                                "to": sender,
                                "mid": mid
                            })
                        )

                # Yahan pahunchna matlab connection normally band ho gaya
                # (exception ke bina) -- fir bhi reconnect try karna chahiye.
                print("WebSocket connection closed, reconnecting...", flush=True)

            except Exception as ex:
                print("====================================", flush=True)
                print("WebSocket connect FAILED", flush=True)
                print("URL:", WS_SERVER_URL, flush=True)
                print("ERROR TYPE:", type(ex).__name__, flush=True)
                print("ERROR:", repr(ex), flush=True)
                print("====================================", flush=True)

            ws_state["connection"] = None
            update_contact_status(False)

            page.update()

            # thodi der ruk ke dobara try karo -- pehli baar fail hua ho
            # ya connection beech me toot gaya ho, dono cases cover ho jaate hain
            await asyncio.sleep(3)

    old_task = getattr(page, "_ws_task", None)
    if old_task and not old_task.done():
        old_task.cancel()
    page._ws_task = page.run_task(connect_and_listen)

    page.appbar = appbar

    # ---------------------------------------------------------------
    # FIXED BOTTOM AREA
    # Banner + attachment preview + TextField ek hi bottom section
    # me hain. Isliye "Opening gallery..." / "Opening file..."
    # hamesha TextField ke just upar rahega.
    # ---------------------------------------------------------------
    bottom_area = ft.Column(
        controls=[
            banner,
            attachment_box,
            ft.Row(
                controls=[user_msg],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ],
        spacing=0,
        tight=True,
    )

    # Sirf chat_area scroll karega; bottom_area fixed rahega.
    page.add(
        chat_area,
        bottom_area,
    )

    page.update()
