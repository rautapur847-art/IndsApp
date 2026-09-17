import flet as ft
from database.db import Database
from datetime import timedelta


def format_india_time(value):
    if not value:
        return ""

    india_time = value + timedelta(hours=5, minutes=30)

    return india_time.strftime("%I:%M %p").lstrip("0")


def get_chat_list(my_id: int):
    """Logged-in user ke saare ADDED CONTACTS dikhata hai, saath me
    unka latest message agar hai to. Naya add kiya gaya contact bhi
    turant dikhega, chahe abhi tak koi message na bhejo gaya ho."""

    db = Database()

    db.cur.execute(
        """
        SELECT
            c.id AS contact_id,
            other.id,
            c.name AS name,
            other.phone,
            grouped.message AS message,
            grouped.sent_at AS sent_at,

            (
                SELECT COUNT(*)
                FROM message unread
                WHERE unread.sender_id = other.id
                AND unread.receiver_id = %s
                AND unread.message_status IN ('sent', 'delivered')
            ) AS unread_count

        FROM contacts c
        JOIN user other ON other.id = c.contact_id

        LEFT JOIN (
            SELECT
                mx.other_id,
                m.message,
                m.sent_at
            FROM (
                SELECT
                    CASE
                        WHEN sender_id = %s
                        THEN receiver_id
                        ELSE sender_id
                    END AS other_id,
                    MAX(message_id) AS last_id
                FROM message
                WHERE sender_id = %s OR receiver_id = %s
                GROUP BY other_id
            ) AS mx
            JOIN message m
                ON m.message_id = mx.last_id
        ) AS grouped

        ON grouped.other_id = other.id

        WHERE c.owner_id = %s

        ORDER BY grouped.sent_at DESC
        """,
        (
            my_id,
            my_id,
            my_id,
            my_id,
            my_id
        ),
    )

    rows = db.cur.fetchall()

    result = []

    for row in rows:

        contact_id = row["contact_id"]
        name = row["name"]

        initials = "".join(
            part[0].upper()
            for part in name.split()[:2]
        ) or "?"

        result.append({
            "contact_id": contact_id,
            "id": row["id"],
            "phone": row["phone"],
            "name": name,
            "initials": initials,
            "message": row["message"] or "No messages yet",
            "time": format_india_time(row["sent_at"]),
            "unread_count": row["unread_count"] or 0,
        })

    return result


def Home(page: ft.Page, my_id: int):

    page.clean()

    from screens.setting import Setting
    from screens.chat import Chat
    from screens.profile import Profile
    from screens.AddContact import AddContact

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 360
    page.window.height = 700

    menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        tooltip="menu",
        margin=5,
        style=ft.ButtonStyle(
            bgcolor="black",
        ),
        items=[
            ft.PopupMenuItem(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.PERSON_ADD,
                            color="blue"
                        ),
                        ft.Text("New cantact.")
                    ]
                ),
                on_click=lambda e: AddContact(page, my_id)
            ),

            ft.PopupMenuItem(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.SETTINGS,
                            color="green"
                        ),
                        ft.Text("Setting"),
                    ]
                ),
                on_click=lambda e: Setting(page)
            )
        ]
    )

    data = Database()
    user = data.get_user_by_id(my_id)

    if user:
        user_name = user["name"]

        initials = "".join(
            word[0].upper()
            for word in user_name.split()
            if word
        )[:2]
    else:
        initials = "?"

    profile_avatar = ft.Container(
        content=ft.CircleAvatar(
            content=ft.Text(
                initials,
                weight=ft.FontWeight.BOLD,
                size=15,
            ),
            radius=20,
            bgcolor="black",
        ),
        tooltip="Profile",
        margin=5,
        on_click=lambda e: Profile(page, my_id),
    )

    appbar = ft.AppBar(
        title=ft.Text(
            "IndsApp",
            weight=ft.FontWeight.BOLD,
        ),
        actions=[
            profile_avatar,
            menu,
        ],
        bgcolor=ft.Colors.WHITE_10,
    )

    # ------------------------------------------------
    # GET CHAT DATA
    # ------------------------------------------------

    users = get_chat_list(my_id)

    unseen_users = [
        user for user in users
        if user["unread_count"] > 0
    ]

    # ------------------------------------------------
    # CHATS
    # ------------------------------------------------

    chats = ft.ListView(
        expand=True,
        spacing=0,
        padding=10,
        scroll=ft.ScrollMode.HIDDEN,
    )

    def show_chats(user_list):

        chats.controls.clear()

        for user in user_list:

            chats.controls.append(
                ft.ListTile(
                    leading=ft.CircleAvatar(
                        content=ft.Text(
                            user["initials"]
                        )
                    ),

                    title=ft.Text(
                        user["name"]
                    ),

                    subtitle=ft.Text(
                        user["message"]
                    ),

                    trailing=ft.Text(
                        user["time"]
                    ),

                    on_click=lambda e, u=user: Chat(
                        page,
                        my_id,
                        u["id"],
                        u["name"],
                        u["phone"],
                        refresh_notification
                    )
                )
            )

            chats.controls.append(
                ft.Divider()
            )

        page.update()

    def clear_search(e):

        search.value = ""
        search.suffix_icon = None

        show_chats(users)

        page.update()

    def search_chat(e):

        query = search.value.lower().strip()

        if query:

            search.suffix_icon = ft.IconButton(
                icon=ft.Icons.CLOSE,
                icon_color="white",
                on_click=clear_search,
                margin=5,
                icon_size=18
            )

        else:

            search.suffix_icon = None

        filtered_users = [
            user
            for user in users
            if query in user["name"].lower()
        ]

        show_chats(filtered_users)

    search = ft.TextField(
        hint_text="Search chats....",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=25,
        height=45,
        expand=True,
        border_color=ft.Colors.WHITE_30,
        margin=5,
        tooltip="Search chats....",
        on_change=search_chat
    )

    search_bar = ft.Container(
        content=search,
    )

    show_chats(users)

    # ------------------------------------------------
    # NOTIFICATION
    # ------------------------------------------------

    notification_dot = ft.Container(
        width=8,
        height=8,
        bgcolor="blue",
        border_radius=50,
        right=2,
        top=1,
        visible=len(unseen_users) > 0,
    )

    notifacation = ft.Stack(
        controls=[
            ft.Icon(
                ft.Icons.NOTIFICATIONS,
                size=24,
            ),

            notification_dot,
        ],
        width=32,
        height=32,
    )

    # ------------------------------------------------
    # REFRESH NOTIFICATION
    # ------------------------------------------------

    def refresh_notification():

        nonlocal users

        users = get_chat_list(my_id)

        unseen_users = [
            user
            for user in users
            if user["unread_count"] > 0
        ]

        notification_dot.visible = len(unseen_users) > 0

        page.update()

    # ------------------------------------------------
    # NAVIGATION
    # ------------------------------------------------

    def navigation_change(e):

        refresh_notification()

        if e.control.selected_index == 0:

            show_chats(users)

        else:

            unseen_users = [
                user
                for user in users
                if user["unread_count"] > 0
            ]

            show_chats(unseen_users)

    navigation = ft.NavigationBar(
        bgcolor=ft.Colors.BLACK_12,

        on_change=navigation_change,

        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.CHAT_ROUNDED,
                label="Chats",
                bgcolor="black",
            ),

            ft.NavigationBarDestination(
                notifacation,
                label="Unseen",
                bgcolor="black",
            )
        ]
    )

    # ------------------------------------------------
    # PAGE
    # ------------------------------------------------

    page.appbar = appbar

    page.add(
        search_bar,
        chats
    )

    page.navigation_bar = navigation

    page.update()