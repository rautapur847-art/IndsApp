import flet as ft
import threading
import random
import string
import time
import os
import re
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import bcrypt
from database.db import Database  # apna Database class jahan bhi ho, wahan se import karo
from screens.home import Home  # apna Home screen jahan bhi ho, wahan se import karo

load_dotenv()  # .env file me se variables ko environment me load karta hai

OTP_EXPIRY_SECONDS = 300      # OTP kitni der tak valid rahega
RESEND_COOLDOWN_SECONDS = 60  # Resend button kitni der disable rahega

GMAIL_ADDRESS = os.getenv("SMTP_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("SMTP_PASSWORD")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def send_email_otp(to_email: str, otp_code: str):
    """Gmail SMTP se email par OTP bhejta hai — kisi bhi email address
    par bhej sakta hai, koi domain verification nahi chahiye.
    Returns (success: bool, detail: str)."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_ADDRESS ya GMAIL_APP_PASSWORD environment variable set nahi hai.")

    body = (
        f"Your OTP for IndsApp sign up is: {otp_code}\n"
        "It expires in 5 minutes.\n"
        "Do not share this code with anyone."
    )
    msg = MIMEText(body)
    msg["Subject"] = "IndsApp — Your verification code"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, [to_email], msg.as_string())
        return True, "sent"
    except Exception as ex:
        return False, str(ex)


def Sign(page: ft.Page):

    page.clean()
    from screens.login import LoginScreen
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # OTP se juda saara state ek jagah — closure ke andar,
    # taaki global variable ki zaroorat na pade
    otp_state = {
        "code": None,
        "sent_at": 0,
        "locked_email": None,
        "seconds_left": 0,
    }

    def generate_otp():
        return "".join(random.choices(string.digits, k=6))

    # ---------------- OTP send ----------------

    def send_otp(e):
        user_email = email.value.strip()

        if not user_email or not EMAIL_REGEX.match(user_email):
            otp_status.value = "Enter a valid email address."
            otp_status.color = "red"
            page.update()
            return

        code = generate_otp()

        try:
            sent, detail = send_email_otp(user_email, code)
        except Exception as ex:
            otp_status.value = f"Failed to send OTP: {ex}"
            otp_status.color = "red"
            page.update()
            return

        if not sent:
            otp_status.value = f"Failed to send OTP: {detail}"
            otp_status.color = "red"
            page.update()
            return

        otp_state["code"] = code
        otp_state["sent_at"] = time.time()
        otp_state["locked_email"] = user_email
        otp_state["seconds_left"] = RESEND_COOLDOWN_SECONDS

        otp.visible = True
        otp.value = ""
        otp_status.value = f"OTP sent to {user_email}."
        otp_status.color = "green"

        # Email lock — taaki verify hamesha usi email ke against ho
        # jispe OTP bheja gaya tha
        email.disabled = True
        send_otp_button.disabled = True

        page.update()
        countdown()

    def countdown():
        if otp_state["seconds_left"] > 0:
            timer_text.value = f"Resend OTP in {otp_state['seconds_left']}s"
            otp_state["seconds_left"] -= 1
            page.update()
            threading.Timer(1, countdown).start()
        else:
            timer_text.value = ""
            send_otp_button.disabled = False
            email.disabled = False
            page.update()

    # ---------------- OTP verify + full-form validation (Sign button par) ----------------

    def sign_in(e):
        user_name = name.value.strip()
        user_phone = phone.value.strip()
        user_email = email.value.strip()
        user_password = password.value
        entered_otp = otp.value.strip()

        # Koi bhi field empty nahi honi chahiye
        if not user_name:
            message.value = "Name is required."
            message.color = "red"
            page.update()
            return

        if not user_phone or not user_phone.isdigit() or len(user_phone) < 10:
            message.value = "Enter a valid 10-digit mobile number."
            message.color = "red"
            page.update()
            return

        if not user_email or not EMAIL_REGEX.match(user_email):
            message.value = "Enter a valid email address."
            message.color = "red"
            page.update()
            return

        if not user_password:
            message.value = "Password is required."
            message.color = "red"
            page.update()
            return

        if not entered_otp:
            message.value = "Enter the OTP sent to your email."
            message.color = "red"
            page.update()
            return

        # OTP verification
        if otp_state["code"] is None:
            message.value = "Click 'Send OTP' and verify your email first."
            message.color = "red"
            page.update()
            return

        if user_email != otp_state["locked_email"]:
            message.value = "Email changed after OTP was sent — resend OTP."
            message.color = "red"
            page.update()
            return

        if time.time() - otp_state["sent_at"] > OTP_EXPIRY_SECONDS:
            message.value = "OTP expired — click Send OTP again."
            message.color = "red"
            otp_state["code"] = None
            otp.visible = False
            email.disabled = False
            page.update()
            return

        if entered_otp != otp_state["code"]:
            message.value = "Incorrect OTP."
            message.color = "red"
            page.update()
            return

        # ───────────────────────────────────────────────
        # Sab kuch valid hai aur OTP verify ho chuka hai —
        # ab yahi DB me save karna hai (koi alag function nahi chahiye)
        # ───────────────────────────────────────────────
        try:
            hashed_password = bcrypt.hashpw(user_password.encode(), bcrypt.gensalt()).decode()

            user_db.UserRegister(
                user_name,
                user_phone,
                user_email,
                hashed_password,
            )
            # Abhi-abhi insert hue naye user ka ID — Home() ko chahiye
            # taaki wo isi user ke apne chats fetch kar sake
            new_user_id = user_db.cur.lastrowid

            message.value = "Registration successful!"
            message.color = "green"
            page.update()
            Home(page, new_user_id)

        except Exception as ex:
            if "Duplicate entry" in str(ex) and "email" in str(ex):
                message.value = "This email is already registered. Try logging in instead."
            elif "Duplicate entry" in str(ex) and "phone" in str(ex):
                message.value = "This phone number is already registered. Try logging in instead."
            else:
                message.value = f"Registration error: {ex}"
            message.color = "red"
            message.selectable = True
            page.update()

    # ---------------- UI controls ----------------

    user_db = Database()
    timer_text = ft.Text("", size=12)
    otp_status = ft.Text("", size=12)
    message = ft.Text("", size=14)

    def get_initials(full_name):
        words = full_name.strip().split()

        if not words:
            return "?"

        if len(words) >= 2:
            return (words[0][0] + words[1][0]).upper()

        return words[0][0].upper()
        
    avatar = ft.CircleAvatar(
        content=ft.Text(
            "?",
            size=30,
            weight=ft.FontWeight.BOLD,
        ),
        radius=40,
        margin=60
    )

    name = ft.TextField(
        border_color="white",
        hint_text="name..",
        prefix_icon=ft.Icons.PERSON,
        border_radius=5,
        margin=10,
        width=320
    )


    def name_change(e):
        initials = get_initials(name.value)

        avatar.content = ft.Text(
            initials,
            size=30,
            weight=ft.FontWeight.BOLD,
        )

        page.update()

    name.on_change = name_change

    phone = ft.TextField(
        border_color="white",
        hint_text="Phone...",
        prefix_icon=ft.Icons.PHONE,
        border_radius=5,
        margin=10,
        width=320,
        keyboard_type=ft.KeyboardType.PHONE,
    )

    email = ft.TextField(
        border_color="white",
        hint_text="Email...",
        prefix_icon=ft.Icons.EMAIL,
        border_radius=5,
        width=230,
        keyboard_type=ft.KeyboardType.EMAIL,
    )

    send_otp_button = ft.TextButton(
        "Send OTP",
        on_click=send_otp,
    )

    email_row = ft.Row(
        controls=[
            email, send_otp_button,
        ],
        width=320
    )

    otp = ft.TextField(
        border_color="white",
        hint_text="Enter OTP...",
        prefix_icon=ft.Icons.LOCK,
        border_radius=5,
        width=320,
        visible=False,
        max_length=6,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    password = ft.TextField(
        border_color="white",
        hint_text="password..",
        prefix_icon=ft.Icons.PASSWORD,
        password=True,
        can_reveal_password=True,
        border_radius=5,
        margin=10,
        width=320
    )

    column = ft.Column(
        controls=[
            avatar,
            name,
            phone,
            email_row,
            otp,
            timer_text,
            otp_status,
            password,
            message,
             ft.ElevatedButton(
                "Sign with IndsApp",
                width=320,
                height=40,
                on_click=sign_in,
            ),

            ft.TextButton(
                "Already an account login.",
                on_click=lambda e: LoginScreen(page),
            ),
        ],

        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.HIDDEN,
    )

    page.add(column)
    page.update()

