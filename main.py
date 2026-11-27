import base64
import os
import tempfile
import flet as ft

# Opsional: Tempel string Base64 logo_orado_ok.png di sini jika tidak memakai folder assets/
ASSETS_B64 = {
    "logo_orado_ok.png": "",
}

TARGET_SKOR = 101
PENALTY_VALUES = [11, 15, 20, 25]
QUICK_SCORES = [5, 10, 15, 20, 25, 30]

# Palet warna Dark Emerald & Gold (Hex langsung agar aman di semua versi Flet)
BG_DARK = "#0B0F14"
CARD_BG = "#151C24"
CARD_ACTIVE = "#1C2632"
BORDER_COLOR = "#263241"
GOLD = "#F5B82E"
EMERALD = "#10B981"
RED_ALERT = "#EF4444"
AMBER = "#F59E0B"
PURPLE_SPECIAL = "#8B5CF6"
TEXT_PRIMARY = "#F8FAFC"
TEXT_MUTED = "#94A3B8"


def get_icon(name: str):
    """Ambil ikon secara aman untuk Flet versi lama maupun terbaru."""
    icons_mod = getattr(ft, "Icons", None) or getattr(ft, "icons", None)
    return getattr(icons_mod, name, None) if icons_mod else None


def extract_embedded_logo() -> str | None:
    """Ekstrak logo dari ASSETS_B64 ke file sementara jika tersedia."""
    b64_data = ASSETS_B64.get("logo_orado_ok.png", "").strip()
    if not b64_data:
        return None
    try:
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        temp_path = os.path.join(tempfile.gettempdir(), "logo_orado_ok.png")
        with open(temp_path, "wb") as f:
            f.write(base64.b64decode(b64_data))
        return temp_path
    except Exception:
        return None


def main(page: ft.Page):
    page.title = "ORADO Domino 101"
    page.bgcolor = BG_DARK
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 14
    page.scroll = ft.ScrollMode.AUTO

    # --- STATE PERTANDINGAN ---
    state = {
        "team_a": "TIM A",
        "team_b": "TIM B",
        "score_a": 0,
        "score_b": 0,
        "sets_a": 0,
        "sets_b": 0,
        "set_num": 1,
        "selected_team": "A",
        "history": [],  # list of dict: {"team": "A"/"B", "points": int, "label": str}
    }

    STORAGE_KEY = "orado_domino_101_state_v1"

    def load_state():
        try:
            saved = page.client_storage.get(STORAGE_KEY)
            if isinstance(saved, dict):
                state.update(saved)
        except Exception:
            pass

    def save_state():
        try:
            page.client_storage.set(STORAGE_KEY, state)
        except Exception:
            pass

    load_state()

    # --- AUDIO & HAPTIC ANDROID SAFE ---
    AudioClass = getattr(ft, "Audio", None)
    HapticClass = getattr(ft, "HapticFeedback", None)

    haptic = HapticClass() if HapticClass else None
    if haptic:
        page.overlay.append(haptic)

    audio_players = {}
    for sound_key, filename in [
        ("intro", "intro_mlbb.wav"),
        ("click", "ui_click.wav"),
        ("shake", "ui_shake.wav"),
    ]:
        asset_file = os.path.join("assets", filename)
        if AudioClass and os.path.exists(asset_file):
            try:
                player = AudioClass(src=filename, autoplay=(sound_key == "intro"))
                page.overlay.append(player)
                audio_players[sound_key] = player
            except Exception:
                pass

    def trigger_feedback(kind: str = "click"):
        try:
            if kind in audio_players:
                audio_players[kind].play()
        except Exception:
            pass

        try:
            if haptic:
                if kind in ("shake", "intro"):
                    haptic.heavy_impact()
                else:
                    haptic.light_impact()
        except Exception:
            pass

    # --- HELPER DIALOG LINTAS VERSI FLET ---
    def open_dialog(dlg: ft.AlertDialog):
        try:
            page.open(dlg)
        except Exception:
            page.dialog = dlg
            dlg.open = True
            page.update()

    def close_dialog(dlg: ft.AlertDialog):
        try:
            page.close(dlg)
        except Exception:
            dlg.open = False
            page.update()

    # --- KOMPONEN LOGO HEADER ---
    embedded_logo_path = extract_embedded_logo()
    if embedded_logo_path:
        logo_widget = ft.Image(src=embedded_logo_path, width=42, height=42, fit=ft.ImageFit.CONTAIN)
    elif os.path.exists(os.path.join("assets", "logo_orado_ok.png")):
        logo_widget = ft.Image(src="logo_orado_ok.png", width=42, height=42, fit=ft.ImageFit.CONTAIN)
    else:
        logo_widget = ft.Container(
            content=ft.Text("OR", weight=ft.FontWeight.BOLD, size=16, color=BG_DARK),
            bgcolor=GOLD,
            width=40,
            height=40,
            border_radius=10,
            alignment=ft.alignment.center,
        )

    # --- UI WIDGETS DINAMIS ---
    set_badge_text = ft.Text(
        f"SET {state['set_num']}  •  {state['sets_a']} - {state['sets_b']}",
        size=12,
        weight=ft.FontWeight.BOLD,
        color=GOLD,
    )

    team_a_name_text = ft.Text(state["team_a"], size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
    team_b_name_text = ft.Text(state["team_b"], size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)

    score_a_text = ft.Text(str(state["score_a"]), size=46, weight=ft.FontWeight.W_900, color=TEXT_PRIMARY)
    score_b_text = ft.Text(str(state["score_b"]), size=46, weight=ft.FontWeight.W_900, color=TEXT_PRIMARY)

    status_a_text = ft.Text("", size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED)
    status_b_text = ft.Text("", size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED)

    manual_score_input = ft.TextField(
        label="Poin Manual",
        hint_text="Contoh: 18",
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.CENTER,
        border_color=BORDER_COLOR,
        focused_border_color=GOLD,
        height=48,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        expand=True,
    )

    history_column = ft.Column(spacing=6)

    # --- LOGIKA PERMAINAN & UPDATE UI ---
    def get_status_info(score: int):
        sisa = max(0, TARGET_SKOR - score)
        if score >= TARGET_SKOR:
            return "MENANG (101+)", EMERALD
        if score >= 85:
            return f"CEKIH! Kurang {sisa}", RED_ALERT
        return f"Kurang {sisa} ke 101", TEXT_MUTED

    def select_team(team_code: str):
        state["selected_team"] = team_code
        trigger_feedback("click")
        save_state()
        refresh_ui()

    def show_winner_modal(winner_code: str, win_reason: str):
        trigger_feedback("intro")
        winner_name = state["team_a"] if winner_code == "A" else state["team_b"]
        loser_name = state["team_b"] if winner_code == "A" else state["team_a"]
        winner_score = state["score_a"] if winner_code == "A" else state["score_b"]
        loser_score = state["score_b"] if winner_code == "A" else state["score_a"]

        def next_set(e):
            if winner_code == "A":
                state["sets_a"] += 1
            else:
                state["sets_b"] += 1
            state["set_num"] += 1
            state["score_a"] = 0
            state["score_b"] = 0
            state["history"] = []
            save_state()
            close_dialog(dlg)
            refresh_ui()

        def reset_all(e):
            state["score_a"] = 0
            state["score_b"] = 0
            state["sets_a"] = 0
            state["sets_b"] = 0
            state["set_num"] = 1
            state["history"] = []
            save_state()
            close_dialog(dlg)
            refresh_ui()

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(f"🏆 {winner_name} MENANG!", color=GOLD, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text(f"Metode: {win_reason}", size=14, weight=ft.FontWeight.W_600, color=EMERALD),
                    ft.Text(
                        f"Skor Akhir: {winner_name} ({winner_score}) vs {loser_name} ({loser_score})",
                        size=13,
                        color=TEXT_PRIMARY,
                    ),
                ],
            ),
            actions=[
                ft.TextButton("Reset Match", on_click=reset_all),
                ft.ElevatedButton(
                    "Lanjut Set Berikutnya",
                    bgcolor=GOLD,
                    color=BG_DARK,
                    on_click=next_set,
                ),
            ],
        )
        open_dialog(dlg)

    def add_points(points: int, label: str = "Skor Ronde", is_penalty: bool = False):
        if points <= 0:
            return
        team = state["selected_team"]
        if team == "A":
            state["score_a"] += points
        else:
            state["score_b"] += points

        state["history"].append({
            "team": team,
            "points": points,
            "label": label,
        })

        trigger_feedback("shake" if is_penalty else "click")
        save_state()
        refresh_ui()

        if state["score_a"] >= TARGET_SKOR:
            show_winner_modal("A", f"Mencapai {state['score_a']} Poin (Domino 101)")
        elif state["score_b"] >= TARGET_SKOR:
            show_winner_modal("B", f"Mencapai {state['score_b']} Poin (Domino 101)")

    def trigger_special_win(special_type: str):
        team = state["selected_team"]
        team_name = state["team_a"] if team == "A" else state["team_b"]

        def confirm_special(e):
            state["history"].append({
                "team": team,
                "points": 0,
                "label": f"KEMENANGAN {special_type}",
            })
            save_state()
            close_dialog(confirm_dlg)
            refresh_ui()
            show_winner_modal(team, f"Kemenangan Spesial {special_type}")

        confirm_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(f"Konfirmasi {special_type}", color=GOLD, weight=ft.FontWeight.BOLD),
            content=ft.Text(
                f"Tetapkan {team_name} menang langsung dengan {special_type}?",
                color=TEXT_PRIMARY,
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda e: close_dialog(confirm_dlg)),
                ft.ElevatedButton(
                    f"Ya, {special_type}!",
                    bgcolor=PURPLE_SPECIAL,
                    color=TEXT_PRIMARY,
                    on_click=confirm_special,
                ),
            ],
        )
        open_dialog(confirm_dlg)

    def undo_last(e):
        if not state["history"]:
            return
        last = state["history"].pop()
        if last["team"] == "A":
            state["score_a"] = max(0, state["score_a"] - last["points"])
        else:
            state["score_b"] = max(0, state["score_b"] - last["points"])
        trigger_feedback("shake")
        save_state()
        refresh_ui()

    def open_edit_teams_dialog(e):
        tf_a = ft.TextField(label="Nama Tim A", value=state["team_a"], border_color=GOLD)
        tf_b = ft.TextField(label="Nama Tim B", value=state["team_b"], border_color=GOLD)

        def save_names(ev):
            state["team_a"] = (tf_a.value or "TIM A").strip().upper()
            state["team_b"] = (tf_b.value or "TIM B").strip().upper()
            save_state()
            close_dialog(edit_dlg)
            refresh_ui()

        edit_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("Ubah Nama Tim", color=GOLD, weight=ft.FontWeight.BOLD),
            content=ft.Column(tight=True, spacing=10, controls=[tf_a, tf_b]),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(edit_dlg)),
                ft.ElevatedButton("Simpan", bgcolor=GOLD, color=BG_DARK, on_click=save_names),
            ],
        )
        open_dialog(edit_dlg)

    def confirm_reset_round(e):
        def do_reset(ev):
            state["score_a"] = 0
            state["score_b"] = 0
            state["history"] = []
            trigger_feedback("shake")
            save_state()
            close_dialog(rst_dlg)
            refresh_ui()

        rst_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("Reset Skor Set Ini?", color=RED_ALERT, weight=ft.FontWeight.BOLD),
            content=ft.Text("Skor kedua tim pada set berjalan akan dikembalikan ke 0.", color=TEXT_PRIMARY),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(rst_dlg)),
                ft.ElevatedButton("Reset 0 - 0", bgcolor=RED_ALERT, color=TEXT_PRIMARY, on_click=do_reset),
            ],
        )
        open_dialog(rst_dlg)

    # --- KARTU SKOR TIM ---
    team_a_card = ft.Container(
        expand=True,
        padding=14,
        border_radius=14,
        bgcolor=CARD_ACTIVE,
        border=ft.border.all(2, GOLD),
        on_click=lambda e: select_team("A"),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
            controls=[
                team_a_name_text,
                score_a_text,
                status_a_text,
            ],
        ),
    )

    team_b_card = ft.Container(
        expand=True,
        padding=14,
        border_radius=14,
        bgcolor=CARD_BG,
        border=ft.border.all(1, BORDER_COLOR),
        on_click=lambda e: select_team("B"),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
            controls=[
                team_b_name_text,
                score_b_text,
                status_b_text,
            ],
        ),
    )

    active_team_banner = ft.Text(
        f"Target Input: {state['team_a']}",
        size=13,
        weight=ft.FontWeight.BOLD,
        color=GOLD,
    )

    def refresh_ui():
        set_badge_text.value = f"SET {state['set_num']}  •  {state['sets_a']} - {state['sets_b']}"
        team_a_name_text.value = state["team_a"]
        team_b_name_text.value = state["team_b"]
        score_a_text.value = str(state["score_a"])
        score_b_text.value = str(state["score_b"])

        st_a_txt, st_a_col = get_status_info(state["score_a"])
        st_b_txt, st_b_col = get_status_info(state["score_b"])
        status_a_text.value = st_a_txt
        status_a_text.color = st_a_col
        status_b_text.value = st_b_txt
        status_b_text.color = st_b_col

        is_a = state["selected_team"] == "A"
        team_a_card.bgcolor = CARD_ACTIVE if is_a else CARD_BG
        team_a_card.border = ft.border.all(2, GOLD if is_a else BORDER_COLOR)
        team_b_card.bgcolor = CARD_ACTIVE if not is_a else CARD_BG
        team_b_card.border = ft.border.all(2, GOLD if not is_a else BORDER_COLOR)

        active_name = state["team_a"] if is_a else state["team_b"]
        active_team_banner.value = f"Input Aktif untuk: {active_name} (Ketuk kartu skor untuk ganti tim)"

        # Bangun ulang daftar riwayat (terbaru di atas)
        history_column.controls.clear()
        if not state["history"]:
            history_column.controls.append(
                ft.Text("Belum ada poin masuk di set ini.", size=12, color=TEXT_MUTED)
            )
        else:
            total_rounds = len(state["history"])
            for idx, item in enumerate(reversed(state["history"])):
                round_no = total_rounds - idx
                t_name = state["team_a"] if item["team"] == "A" else state["team_b"]
                pts_str = f"+{item['points']}" if item["points"] > 0 else "WIN"
                badge_col = RED_ALERT if "PENALTI" in item["label"] else (
                    PURPLE_SPECIAL if "KEMENANGAN" in item["label"] else EMERALD
                )
                history_column.controls.append(
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=10, vertical=8),
                        border_radius=8,
                        bgcolor=BG_DARK,
                        border=ft.border.all(1, BORDER_COLOR),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    f"#{round_no}  {t_name} • {item['label']}",
                                    size=12,
                                    color=TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    pts_str,
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color=badge_col,
                                ),
                            ],
                        ),
                    )
                )

        page.update()

    # --- TOMBOL AKSI CEPAT ---
    def handle_manual_submit(e):
        raw = (manual_score_input.value or "").strip()
        if raw.isdigit() and int(raw) > 0:
            val = int(raw)
            manual_score_input.value = ""
            add_points(val, "Skor Ronde")

    quick_buttons = [
        ft.ElevatedButton(
            text=f"+{val}",
            bgcolor=CARD_ACTIVE,
            color=TEXT_PRIMARY,
            expand=True,
            height=44,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=lambda e, v=val: add_points(v, "Skor Cepat"),
        )
        for val in QUICK_SCORES
    ]

    penalty_buttons = [
        ft.ElevatedButton(
            text=f"+{p}",
            bgcolor="#3B181E",
            color=RED_ALERT,
            expand=True,
            height=44,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            on_click=lambda e, v=p: add_points(v, f"PENALTI (+{v})", is_penalty=True),
        )
        for p in PENALTY_VALUES
    ]

    # --- SUSUNAN HALAMAN UTAMA ---
    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Row(
                spacing=10,
                controls=[
                    logo_widget,
                    ft.Column(
                        spacing=1,
                        controls=[
                            ft.Text("ORADO DOMINO 101", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            set_badge_text,
                        ],
                    ),
                ],
            ),
            ft.Row(
                spacing=4,
                controls=[
                    ft.IconButton(
                        icon=get_icon("EDIT"),
                        tooltip="Ubah Nama Tim",
                        icon_color=GOLD,
                        on_click=open_edit_teams_dialog,
                    ),
                    ft.IconButton(
                        icon=get_icon("REFRESH"),
                        tooltip="Reset Skor Set",
                        icon_color=RED_ALERT,
                        on_click=confirm_reset_round,
                    ),
                ],
            ),
        ],
    )

    score_section = ft.Row(spacing=10, controls=[team_a_card, team_b_card])

    input_panel = ft.Container(
        padding=12,
        border_radius=14,
        bgcolor=CARD_BG,
        border=ft.border.all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=10,
            controls=[
                active_team_banner,
                ft.Row(spacing=6, controls=quick_buttons[:3]),
                ft.Row(spacing=6, controls=quick_buttons[3:]),
                ft.Row(
                    spacing=8,
                    controls=[
                        manual_score_input,
                        ft.ElevatedButton(
                            "TAMBAH",
                            bgcolor=EMERALD,
                            color=BG_DARK,
                            height=48,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                            on_click=handle_manual_submit,
                        ),
                    ],
                ),
            ],
        ),
    )

    penalty_panel = ft.Container(
        padding=12,
        border_radius=14,
        bgcolor=CARD_BG,
        border=ft.border.all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text("PENALTI RESMI ORADO (POIN KE TIM AKTIF)", size=11, weight=ft.FontWeight.BOLD, color=AMBER),
                ft.Row(spacing=6, controls=penalty_buttons),
            ],
        ),
    )

    special_panel = ft.Container(
        padding=12,
        border_radius=14,
        bgcolor=CARD_BG,
        border=ft.border.all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text("KEMENANGAN SPESIAL LANGSUNG", size=11, weight=ft.FontWeight.BOLD, color=PURPLE_SPECIAL),
                ft.Row(
                    spacing=8,
                    controls=[
                        ft.ElevatedButton(
                            "🏆 APOLLO",
                            bgcolor=PURPLE_SPECIAL,
                            color=TEXT_PRIMARY,
                            expand=True,
                            height=44,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                            on_click=lambda e: trigger_special_win("APOLLO"),
                        ),
                        ft.ElevatedButton(
                            "🀄 7 BALAK",
                            bgcolor=GOLD,
                            color=BG_DARK,
                            expand=True,
                            height=44,
                            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                            on_click=lambda e: trigger_special_win("7 BALAK"),
                        ),
                    ],
                ),
            ],
        ),
    )

    history_panel = ft.Container(
        padding=12,
        border_radius=14,
        bgcolor=CARD_BG,
        border=ft.border.all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("RIWAYAT RONDE", size=12, weight=ft