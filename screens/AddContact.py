import flet as ft
from database.db import Database


def AddContact(page: ft.Page, my_id: int):
    page.clean()
    from screens.home import Home
    from screens.chat import Chat


    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.navigation_bar = None

    status = ft.Text("", size=13)

    # --------------------------------
    # Save status
    # --------------------------------
    is_saved = False

    # --------------------------------
    # Get initials from entered name
    # --------------------------------
    def get_initials(full_name):
        words = full_name.strip().split()

        if not words:
            return "?"

        if len(words) >= 2:
            return (words[0][0] + words[1][0]).upper()

        return words[0][0].upper()

    # --------------------------------
    # Message
    # --------------------------------
    message = ft.Text("", size=14)

    # --------------------------------
    # Avatar
    # --------------------------------
    avatar = ft.CircleAvatar(
        content=ft.Text(
            "?",
            size=30,
            weight=ft.FontWeight.BOLD,
        ),
        radius=50,
        margin=60,
    )

    # --------------------------------
    # Name
    # --------------------------------
    name = ft.TextField(
        hint_text="Name...",
        prefix_icon=ft.Icons.PERSON_ADD,
        border_color="white",
        border_radius=5,
        width=320,
    )

    # --------------------------------
    # Phone
    # --------------------------------
    phone = ft.TextField(
        hint_text="Enter mobile number...",
        prefix_icon=ft.Icons.PHONE,
        border_color="white",
        border_radius=5,
        width=320,
        keyboard_type=ft.KeyboardType.PHONE,
    )

    # --------------------------------
    # Profile Chat
    # --------------------------------
    def Profile_chat(e):
        user_name = name.value.strip()
        user_phone = phone.value.strip()

        if not user_name:
            message.value = "Name is required."
            message.color = "red"
            page.update()
            return

        if (
            not user_phone
            or not user_phone.isdigit()
            or len(user_phone) != 10
        ):
            message.value = "Enter a valid 10-digit mobile number."
            message.color = "red"
            page.update()
            return

        # --------------------------------
        # Add button must be clicked first
        # --------------------------------
        if not is_saved:
            message.value = "Save required"
            message.color = "red"
            page.update()
            return

        # --------------------------------
        # Open Chat
        # --------------------------------
        Chat(page)
        page.update()

    # --------------------------------
    # Profile Avatar
    # --------------------------------
    profile_avatar = ft.Container(
        content=ft.CircleAvatar(
            content=ft.Text(
                "?",
                weight=ft.FontWeight.BOLD,
                size=20,
            ),
            radius=20,
            bgcolor="black",
        ),
        tooltip="Profile",
        margin=10,
        on_click=Profile_chat,
    )

    # --------------------------------
    # AppBar
    # --------------------------------
    page.appbar = ft.AppBar(
        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Chats",
            bgcolor=ft.Colors.BLACK_26,
            icon_size=18,
            padding=5,
            margin=5,
            on_click=lambda e: Home(page, my_id),
        ),
        title=ft.Text("Add new contact.",  weight=ft.FontWeight.BOLD,),
        actions=[profile_avatar],
        bgcolor=ft.Colors.WHITE_10,
    )

    # --------------------------------
    # Change avatar when name changes
    # --------------------------------
    def name_change(e):
        initials = get_initials(name.value)

        avatar.content = ft.Text(
            initials,
            size=30,
            weight=ft.FontWeight.BOLD,
        )

        profile_avatar.content = ft.CircleAvatar(
            content=ft.Text(
                initials,
                size=15,
                weight=ft.FontWeight.BOLD,
            ),
            radius=20,
            bgcolor="black",
        )

        page.update()

    name.on_change = name_change

    # --------------------------------
    # Add Contact
    # --------------------------------
    def add_click(e):
        nonlocal is_saved

        contact_name = name.value.strip()
        target_phone = phone.value.strip()

        # --------------------------------
        # Name validation
        # --------------------------------
        if not contact_name:
            status.value = "Enter contact name."
            status.color = "red"
            page.update()
            return

        # --------------------------------
        # Phone validation
        # --------------------------------
        if (
            not target_phone
            or not target_phone.isdigit()
            or len(target_phone) != 10
        ):
            status.value = "Enter a valid 10-digit mobile number."
            status.color = "red"
            page.update()
            return

        try:
            db = Database()

            # --------------------------------
            # Find user by phone
            # --------------------------------
            db.cur.execute(
                """
                SELECT id, phone, name
                FROM user
                WHERE phone = %s
                """,
                (target_phone,),
            )

            found = db.cur.fetchone()

            # --------------------------------
            # User not found
            # --------------------------------
            if found is None:
                status.value = "No IndsApp user found with this number."
                status.color = "red"
                page.update()
                return

            # --------------------------------
            # Don't add yourself
            # --------------------------------
            if found["id"] == my_id:
                status.value = "You can't add yourself as a contact."
                status.color = "red"
                page.update()
                return

            # --------------------------------
            # Add contact
            # --------------------------------
            db.cur.execute(
                """
                INSERT INTO contacts
                (owner_id, contact_id, name)
                VALUES (%s, %s, %s)
                """,
                (
                    my_id,
                    found["id"],
                    contact_name,
                ),
            )

            db.conn.commit()

            # --------------------------------
            # Save successful
            # --------------------------------
            is_saved = True

            status.value = f"{contact_name} added successfully!"
            status.color = "green"

            message.value = ""

            page.update()

        except Exception as ex:
            status.value = f"Error: {ex}"
            status.color = "red"
            page.update()

    # --------------------------------
    # Add Button
    # --------------------------------
    button = ft.ElevatedButton(
        "Add",
        on_click=add_click,
        width=320,
    )

    # --------------------------------
    # UI
    # --------------------------------
    page.add(
        ft.Column(
            controls=[

                avatar,

                name,

                phone,

                status,

                button,

                message,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15,
            expand=True,
            scroll = ft.ScrollMode.HIDDEN
        )
    )

    page.update()