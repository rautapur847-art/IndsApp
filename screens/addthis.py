
import flet as ft
from database.db import Database


def get_initials(full_name):
    words = str(full_name).strip().split()

    if not words:
        return "?"

    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()

    return words[0][0].upper()


def Addthis(
        page: ft.Page,
        my_id: int,
        prefill_name: str = "",
        prefill_phone: str = "",
        contact_id: int = None
    ):

    page.clean()

    from screens.home import Home

    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.DARK
    page.navigation_bar = None
    page.window.width = 360
    page.window.height = 700

    status = ft.Text("", size=13)

    # ---------------- DATABASE ----------------

    db = Database()

    # ---------------- AVATAR ----------------

    avatar = ft.CircleAvatar(
        content=ft.Text(
            get_initials(prefill_name) if prefill_name else "?",
            size=30,
            weight=ft.FontWeight.BOLD,
        ),
        radius=50,
        margin=60,
    )

    # ---------------- NAME ----------------
    page.appbar = ft.AppBar(
        ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            tooltip="Chats",
            bgcolor=ft.Colors.BLACK_26,
            icon_size=18,
            padding=5,
            margin=5,
            on_click=lambda e: Home(page,1)
            
        ),
        title=ft.Text("Add contact.",  weight=ft.FontWeight.BOLD,)
    )
    name = ft.TextField(
        border_color="white",
        hint_text="Contact name...",
        prefix_icon=ft.Icons.PERSON,
        border_radius=5,
        margin=10,
        width=320,
        value=prefill_name,
    )

    # Dynamic avatar
    def name_change(e):
        avatar.content = ft.Text(
            get_initials(name.value),
            size=30,
            weight=ft.FontWeight.BOLD,
        )

        page.update()

    name.on_change = name_change

    # ---------------- PHONE ----------------

    phone = ft.TextField(
        border_color="white",
        hint_text="Phone number...",
        prefix_icon=ft.Icons.PHONE,
        border_radius=5,
        margin=10,
        width=320,
        value=str(prefill_phone),
        keyboard_type=ft.KeyboardType.PHONE,
        read_only=True,
    )

    # ---------------- SAVE ----------------

    def save_click(e):

        contact_name = str(name.value).strip()
        target_phone = str(phone.value).strip()

        # ---------------- NAME VALIDATION ----------------

        if not contact_name:
            status.value = "Enter a contact name."
            status.color = "red"
            page.update()
            return

        # ---------------- PHONE VALIDATION ----------------

        if (
            not target_phone
            or not target_phone.isdigit()
            or len(target_phone) != 10
        ):
            status.value = "Invalid phone number."
            status.color = "red"
            page.update()
            return

        try:

            # ==================================================
            # EXISTING CONTACT -> UPDATE NAME
            # ==================================================

            if contact_id is not None:

                db.cur.execute(
                    """
                    UPDATE contacts
                    SET name = %s
                    WHERE id = %s
                    AND owner_id = %s
                    """,
                    (
                        contact_name,
                        contact_id,
                        my_id
                    )
                )

                db.conn.commit()

                # Check whether row was actually updated
                if db.cur.rowcount == 0:

                    status.value = "Contact not found."
                    status.color = "red"

                    page.update()
                    return

                status.value = "Contact name updated!"
                status.color = "green"

                page.update()

                Home(page, my_id)
                return

            # ==================================================
            # NEW CONTACT -> FIND USER
            # ==================================================

            db.cur.execute(
                """
                SELECT id, name, phone
                FROM user
                WHERE phone = %s
                """,
                (target_phone,)
            )

            found = db.cur.fetchone()

            if found is None:

                status.value = "No IndsApp user found with this number."
                status.color = "red"

                page.update()
                return

            # ---------------- SELF CHECK ----------------

            if found["id"] == my_id:

                status.value = "You can't add yourself."
                status.color = "red"

                page.update()
                return

            # ---------------- CHECK EXISTING ----------------

            db.cur.execute(
                """
                SELECT id
                FROM contacts
                WHERE owner_id = %s
                AND contact_id = %s
                """,
                (
                    my_id,
                    found["id"]
                )
            )

            existing_contact = db.cur.fetchone()

            # ==================================================
            # ALREADY EXISTS -> UPDATE NAME
            # ==================================================

            if existing_contact:

                db.cur.execute(
                    """
                    UPDATE contacts
                    SET name = %s
                    WHERE id = %s
                    AND owner_id = %s
                    """,
                    (
                        contact_name,
                        existing_contact["id"],
                        my_id
                    )
                )

                status.value = "Contact name updated!"
                status.color = "green"

            # ==================================================
            # NEW CONTACT -> INSERT
            # ==================================================

            else:

                db.cur.execute(
                    """
                    INSERT INTO contacts
                    (
                        owner_id,
                        contact_id,
                        name
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        my_id,
                        found["id"],
                        contact_name
                    )
                )

                status.value = "Contact saved!"
                status.color = "green"

            # ---------------- COMMIT ----------------

            db.conn.commit()

            page.update()

            Home(page, my_id)

        except Exception as ex:

            status.value = f"Database Error: {ex}"
            status.color = "red"

            page.update()

    # ---------------- BUTTON ----------------

    save_button = ft.ElevatedButton(
        "Save",
        icon=ft.Icons.SAVE,
        bgcolor=ft.Colors.BLUE,
        color=ft.Colors.WHITE,
        width=320,
        on_click=save_click,
    )

    # ---------------- UI ----------------

    column = ft.Column(
        controls=[
            avatar,
            name,
            phone,
            status,
            save_button,
        ],
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.HIDDEN,
    )

    page.add(column)

    page.update()