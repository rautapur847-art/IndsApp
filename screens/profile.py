import flet as ft


def Profile(page: ft.Page, my_id:int):

    page.clean()

    from screens.home import Home
    from database.db import Database

    # ---------------- DATABASE ----------------

    db = Database()

    user = db.get_user_by_id(my_id)

    if user is None:
        page.add(
            ft.Text(
                "User not found",
                color="red",
                size=18,
            )
        )
        page.update()
        return

    # ---------------- PAGE ----------------

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.navigation_bar = None

    page.appbar = ft.AppBar(
        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Chats",
            bgcolor=ft.Colors.BLACK_26,
            icon_size=18,
            padding=5,
            margin=5,
            on_click=lambda e: Home(page,my_id),
        ),
        title=ft.Text(
            "Profile",
            weight=ft.FontWeight.BOLD,
        ),
    )

    # ---------------- EDIT STATE ----------------

    is_editing = False

    def fields(e):
        nonlocal is_editing
    
        if not is_editing:
            # Edit mode
            is_editing = True
    
            country.disabled = False
            name.disabled = False
            phone.disabled = False
            password.disabled = False
    
            edit_save_button.text = "Save"
            edit_save_button.icon = ft.Icons.SAVE
    
        else:
            # Save mode
            new_name = name.value.strip()
            new_phone = phone.value.strip()
            new_password = password.value.strip()
    
            if not new_name:
                return
    
            if not new_phone:
                return
    
            if not new_password:
                return
    
            try:
                sql = """
                UPDATE user
                SET name = %s,
                    phone = %s,
                    password = %s
                WHERE id = %s
                """
    
                db.cur.execute(
                    sql,
                    (
                        new_name,
                        new_phone,
                        new_password,
                        my_id
                    )
                )
    
                db.conn.commit()
    
                # Update avatar initials
                initials = "".join(
                    word[0].upper()
                    for word in new_name.split()
                    if word
                )[:2]
    
                avatar.content = ft.Text(
                    initials,
                    size=30,
                    weight=ft.FontWeight.BOLD,
                )
    
                # Save complete
                is_editing = False
    
                country.disabled = True
                name.disabled = True
                phone.disabled = True
                password.disabled = True
    
                edit_save_button.text = "Edit"
                edit_save_button.icon = ft.Icons.EDIT
    
                page.update()
    
            except Exception as ex:
                print("Profile update error:", ex)
    
        # ---------------- AVATAR ----------------
    
    initials = "".join(
        word[0].upper()
        for word in user["name"].split()
        if word
    )[:2]
    
    avatar = ft.CircleAvatar(
        content=ft.Text(
            initials,
            size=30,
            weight=ft.FontWeight.BOLD,
        ),
        radius=50,
        margin=60,
    )

    # ---------------- NAME ----------------

    name = ft.TextField(
        border_color="white",
        hint_text="name..",
        prefix_icon=ft.Icons.PERSON,
        border_radius=5,
        margin=10,
        width=320,
        disabled=True,
    )

    # ---------------- COUNTRY ----------------

    country = ft.Dropdown(
        width=110,
        value="+91",
        disabled=True,
        border_color="white",
        options=[
            ft.dropdown.Option("+91", "IN +91"),
        ],
    )

    # ---------------- PHONE ----------------

    phone = ft.TextField(
        border_color="white",
        hint_text="phone..",
        prefix_icon=ft.Icons.PHONE,
        border_radius=5,
        expand=True,
        width=320,
        disabled=True,
    )

    phone_row = ft.Row(
        controls=[
            country,
            phone,
        ],
        width=320,
    )

    # ---------------- PASSWORD ----------------

    password = ft.TextField(
        border_color="white",
        hint_text="password..",
        prefix_icon=ft.Icons.PASSWORD,
        password=True,
        can_reveal_password=True,
        border_radius=5,
        margin=10,
        width=320,
        disabled=True,
    )

    # ---------------- DATABASE DATA ----------------

    name.value = user["name"]
    phone.value = str(user["phone"])
    password.value = user["password"]

    # ---------------- EDIT BUTTON ----------------

    edit_save_button = ft.ElevatedButton(
        "Edit",
        icon=ft.Icons.EDIT,
        bgcolor=ft.Colors.BLUE,
        color=ft.Colors.WHITE,
        width=320,
        on_click=fields,
    )

    # ---------------- COLUMN ----------------

    column = ft.Column(
        controls=[
            avatar,
            name,
            phone_row,
            password,
            edit_save_button,
        ],
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.HIDDEN,
    )

    page.add(column)

    page.update()