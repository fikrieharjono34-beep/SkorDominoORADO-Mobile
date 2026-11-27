import base64
from datetime import datetime
import math
import os
import struct
import tempfile
import wave
import flet as ft

try:
    import flet_audio as fta
except ImportError:
    fta = None

# Opsional: Tempel string Base64 logo_orado_ok.png di sini jika tidak memakai folder assets/
ASSETS_B64 = {
    "logo_orado_ok.png": "",
}

TARGET_SKOR = 101
QUICK_SCORES = [5, 10, 15, 20, 25, 30]

# Palet warna Dark Emerald & Gold
BG_DARK = "#0B0F14"
CARD_BG = "#151C24"
CARD_ACTIVE = "#1C2632"
BORDER_COLOR = "#263241"
GOLD = "#F5B82E"
EMERALD = "#10B981"
RED_ALERT = "#EF4444"
BLUE_TEAM = "#3B82F6"
AMBER = "#F59E0B"
PURPLE_SPECIAL = "#8B5CF6"
TEXT_PRIMARY = "#F8FAFC"
TEXT_MUTED = "#94A3B8"


# --- HELPER KOMPATIBILITAS LINTAS VERSI FLET ---
def get_icon(name: str):
    icons_mod = getattr(ft, "Icons", None) or getattr(ft, "icons", None)
    return getattr(icons_mod, name, None) if icons_mod else None


def border_all(width: float, color: str):
    border_mod = getattr(ft, "Border", None) or getattr(ft, "border", None)
    return border_mod.all(width, color) if border_mod else None


def pad_sym(horizontal: float, vertical: float):
    padding_mod = getattr(ft, "Padding", None) or getattr(ft, "padding", None)
    return padding_mod.symmetric(horizontal=horizontal, vertical=vertical) if padding_mod else None


def align_center():
    align_mod = getattr(ft, "Alignment", None) or getattr(ft, "alignment", None)
    if align_mod and hasattr(align_mod, "CENTER"):
        return align_mod.CENTER
    if align_mod and hasattr(align_mod, "center"):
        return align_mod.center
    return None


def make_button(label: str, bgcolor: str, color: str, on_click, expand: bool = False, height: float = 42):
    btn_cls = getattr(ft, "Button", None) or getattr(ft, "ElevatedButton", None)
    return btn_cls(
        label,
        bgcolor=bgcolor,
        color=color,
        expand=expand,
        height=height,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        on_click=on_click,
    )


def set_button_label(btn, new_label: str):
    if hasattr(btn, "text"):
        try:
            btn.text = new_label
        except Exception:
            pass
    content = getattr(btn, "content", None)
    if isinstance(content, ft.Text):
        content.value = new_label


def extract_embedded_logo() -> str | None:
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


# --- GENERATOR EFEK NADA KETUKAN & FANFARE ---
def _write_wav(filepath: str, samples: list[int], sample_rate: int = 44100):
    if os.path.exists(filepath):
        return
    try:
        with wave.open(filepath, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            raw = struct.pack(f"<{len(samples)}h", *[max(-32767, min(32767, s)) for s in samples])
            wf.writeframes(raw)
    except Exception:
        pass


def build_chime_sfx() -> dict[str, str]:
    sfx_dir = os.path.join(tempfile.gettempdir(), "orado_domino_chimes_v4")
    os.makedirs(sfx_dir, exist_ok=True)
    sr = 44100

    # 1. Ketukan batu domino (55 ms)
    click_path = os.path.join(sfx_dir, "orado_click.wav")
    click_samples = []
    for i in range(int(sr * 0.055)):
        t = i / sr
        env = math.exp(-t * 85.0)
        val = (math.sin(2 * math.pi * 920 * t) * 0.65 + math.sin(2 * math.pi * 2150 * t) * 0.35) * env
        click_samples.append(int(val * 26000))
    _write_wav(click_path, click_samples, sr)

    # 2. Nada undo / reset / diskualifikasi (220 ms)
    shake_path = os.path.join(sfx_dir, "orado_shake.wav")
    shake_samples = []
    for i in range(int(sr * 0.22)):
        t = i / sr
        pulse = 1.0 if (t < 0.085 or t > 0.115) else 0.15
        env = math.exp(-t * 9.0) * pulse
        freq = 210 if t < 0.10 else 165
        val = (math.sin(2 * math.pi * freq * t) * 0.75 + math.sin(2 * math.pi * (freq * 2) * t) * 0.25) * env
        shake_samples.append(int(val * 26000))
    _write_wav(shake_path, shake_samples, sr)

    # 3. Fanfare pembuka / kemenangan set normal (480 ms)
    win_path = os.path.join(sfx_dir, "orado_win.wav")
    win_samples = []
    for freq, dur in [(523.25, 0.10), (659.25, 0.10), (783.99, 0.10), (1046.50, 0.18)]:
        for i in range(int(sr * dur)):
            t = i / sr
            env = math.exp(-t * 7.5)
            val = (math.sin(2 * math.pi * freq * t) * 0.75 + math.sin(2 * math.pi * (freq * 1.5) * t) * 0.25) * env
            win_samples.append(int(val * 25000))
    _write_wav(win_path, win_samples, sr)

    return {
        "click": click_path,
        "shake": shake_path,
        "intro": win_path,
    }


def main(page: ft.Page):
    page.title = "ORADO Domino 101"
    page.bgcolor = BG_DARK
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    # --- STATE PERTANDINGAN RESMI ORADO 2026 ---
    state = {
        "team_a": "TIM MERAH",
        "team_b": "TIM BIRU",
        "match_format": "BO3",  # "BO3" = Reguler (Menang 2 Set), "BO5" = Final (Menang 3 Set)
        "score_a": 0,
        "score_b": 0,
        "sets_a": 0,
        "sets_b": 0,
        "set_num": 1,
        "round_num": 1,
        "minor_a": 0,
        "minor_b": 0,
        "major_a": 0,
        "major_b": 0,
        "selected_team": "A",
        "bonus_mode": "1x",  # "1x", "2x", "+50"
        "sound_on": True,
        "history": [],
        "referee_notes": [],
        # State Persetujuan / Keberatan Hasil Akhir Pertandingan ("", "setuju", "tidak_setuju")
        "match_finished": False,
        "referee_name": "",
        "red_rep_name": "",
        "blue_rep_name": "",
        "referee_decision": "",
        "red_decision": "",
        "blue_decision": "",
        "referee_reject_reason": "",
        "red_reject_reason": "",
        "blue_reject_reason": "",
        "approve_referee_time": "",
        "approve_red_time": "",
        "approve_blue_time": "",
    }

    saved_matches: list[dict] = []

    STORAGE_KEY = "orado_domino_101_state_v2"
    ARCHIVE_KEY = "orado_domino_101_saved_matches_v1"

    def load_state():
        try:
            saved = page.client_storage.get(STORAGE_KEY)
            if isinstance(saved, dict):
                state.update(saved)
                if not state.get("referee_decision") and saved.get("approve_referee"):
                    state["referee_decision"] = "setuju"
                if not state.get("red_decision") and saved.get("approve_red"):
                    state["red_decision"] = "setuju"
                if not state.get("blue_decision") and saved.get("approve_blue"):
                    state["blue_decision"] = "setuju"
            arch = page.client_storage.get(ARCHIVE_KEY)
            if isinstance(arch, list):
                saved_matches.clear()
                saved_matches.extend(arch)
        except Exception:
            pass

    def save_state():
        try:
            page.client_storage.set(STORAGE_KEY, state)
        except Exception:
            pass

    def save_archive():
        try:
            page.client_storage.set(ARCHIVE_KEY, saved_matches[:30])
        except Exception:
            pass

    load_state()

    def reset_approval_flags():
        state["match_finished"] = False
        state["referee_decision"] = ""
        state["red_decision"] = ""
        state["blue_decision"] = ""
        state["referee_reject_reason"] = ""
        state["red_reject_reason"] = ""
        state["blue_reject_reason"] = ""
        state["approve_referee_time"] = ""
        state["approve_red_time"] = ""
        state["approve_blue_time"] = ""

    # --- SISTEM AUDIO & SUARA WASIT INDONESIA (flet-audio) ---
    chime_paths = build_chime_sfx()
    audio_players = {}
    AudioClass = getattr(fta, "Audio", None) if fta else None
    ReleaseMode = getattr(fta, "ReleaseMode", None) if fta else None

    if AudioClass:
        for sound_key, wav_path in chime_paths.items():
            try:
                kwargs = {
                    "src": wav_path,
                    "autoplay": (sound_key == "intro" and state.get("sound_on", True)),
                    "volume": 1.0,
                }
                if ReleaseMode and hasattr(ReleaseMode, "STOP"):
                    kwargs["release_mode"] = ReleaseMode.STOP
                player = AudioClass(**kwargs)
                if hasattr(page, "services"):
                    page.services.append(player)
                else:
                    page.overlay.append(player)
                audio_players[sound_key] = player
            except Exception:
                pass

        voice_assets = {
            "v_ringan": "voice_ringan.mp3",
            "v_pen11": "voice_penalti_11.mp3",
            "v_pen25": "voice_penalti_25.mp3",
            "v_pass50": "voice_pass_palsu_50.mp3",
            "v_pass_kalah": "voice_pass_palsu_kalah.mp3",
            "v_apollo": "voice_apollo.mp3",
            "v_7balak": "voice_7balak.mp3",
            "v_2x": "voice_2x.mp3",
            "v_balak50": "voice_balak50.mp3",
            "v_beradu": "voice_beradu.mp3",
            "v_beradu_menang": "voice_beradu_menang.mp3",
            "v_beradu_kalah": "voice_beradu_kalah.mp3",
            "v_beradu_seri": "voice_beradu_seri.mp3",
        }
        for v_key, asset_name in voice_assets.items():
            try:
                kwargs = {
                    "src": asset_name,
                    "autoplay": False,
                    "volume": 1.0,
                }
                if ReleaseMode and hasattr(ReleaseMode, "STOP"):
                    kwargs["release_mode"] = ReleaseMode.STOP
                player = AudioClass(**kwargs)
                if hasattr(page, "services"):
                    page.services.append(player)
                else:
                    page.overlay.append(player)
                audio_players[v_key] = player
            except Exception:
                pass

    async def _play_sound_async(player):
        try:
            res_play = player.play()
            if hasattr(res_play, "__await__"):
                await res_play
        except Exception:
            pass

    def play_sfx(kind: str = "click"):
        if not state.get("sound_on", True):
            return
        player = audio_players.get(kind) or audio_players.get("click")
        if not player:
            return
        try:
            if hasattr(page, "run_task"):
                page.run_task(_play_sound_async, player)
            else:
                player.play()
        except Exception:
            pass

    # --- HELPER DIALOG LINTAS VERSI FLET ---
    def open_dialog(dlg: ft.AlertDialog):
        try:
            if hasattr(page, "show_dialog"):
                page.show_dialog(dlg)
            elif hasattr(page, "open"):
                page.open(dlg)
            else:
                page.dialog = dlg
                dlg.open = True
                page.update()
        except Exception:
            page.dialog = dlg
            dlg.open = True
            page.update()

    def close_dialog(dlg: ft.AlertDialog):
        try:
            if hasattr(page, "pop_dialog"):
                page.pop_dialog()
            elif hasattr(page, "close"):
                page.close(dlg)
            else:
                dlg.open = False
                page.update()
        except Exception:
            dlg.open = False
            page.update()

    def show_toast(msg: str):
        try:
            sb = ft.SnackBar(content=ft.Text(msg, color=TEXT_PRIMARY), bgcolor=CARD_ACTIVE, duration=2500)
            if hasattr(page, "show_snack_bar"):
                page.show_snack_bar(sb)
            else:
                page.snack_bar = sb
                sb.open = True
                page.update()
        except Exception:
            pass

    # --- KOMPONEN LOGO HEADER ---
    embedded_logo_path = extract_embedded_logo()
    if embedded_logo_path:
        logo_widget = ft.Image(src=embedded_logo_path, width=38, height=38)
    elif os.path.exists(os.path.join("assets", "logo_orado_ok.png")):
        logo_widget = ft.Image(src="logo_orado_ok.png", width=38, height=38)
    else:
        logo_widget = ft.Container(
            content=ft.Text("OR", weight=ft.FontWeight.BOLD, size=14, color=BG_DARK),
            bgcolor=GOLD,
            width=36,
            height=36,
            border_radius=10,
            alignment=align_center(),
        )

    # --- UI WIDGETS DINAMIS ---
    set_badge_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=GOLD)
    round_balak_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=EMERALD)

    team_a_name_text = ft.Text(state["team_a"], size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)
    team_b_name_text = ft.Text(state["team_b"], size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)

    score_a_text = ft.Text(str(state["score_a"]), size=44, weight=ft.FontWeight.W_900, color=TEXT_PRIMARY)
    score_b_text = ft.Text(str(state["score_b"]), size=44, weight=ft.FontWeight.W_900, color=TEXT_PRIMARY)

    status_a_text = ft.Text("", size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED)
    status_b_text = ft.Text("", size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED)

    foul_a_text = ft.Text("", size=10, weight=ft.FontWeight.W_600, color=AMBER)
    foul_b_text = ft.Text("", size=10, weight=ft.FontWeight.W_600, color=AMBER)

    sound_btn = ft.IconButton(
        icon=get_icon("VOLUME_UP" if state.get("sound_on", True) else "VOLUME_OFF"),
        tooltip="Suara Wasit & Efek On/Off",
        icon_color=EMERALD if state.get("sound_on", True) else TEXT_MUTED,
        on_click=None,
    )

    manual_score_input = ft.TextField(
        label="Poin Sisa Batu",
        hint_text="Contoh: 18",
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.CENTER,
        border_color=BORDER_COLOR,
        focused_border_color=GOLD,
        height=46,
        content_padding=pad_sym(12, 8),
        expand=True,
    )

    ref_note_input = ft.TextField(
        label="Catatan Wasit",
        hint_text="Contoh: Meja 2 • Shuffle ulang 5 balak",
        border_color=BORDER_COLOR,
        focused_border_color=GOLD,
        height=44,
        text_size=12,
        content_padding=pad_sym(10, 8),
        expand=True,
    )

    ref_notes_column = ft.Column(spacing=5)
    history_column = ft.Column(spacing=6)
    archive_btn_label = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=GOLD)

    # --- WIDGET PERSETUJUAN HASIL AKHIR PERTANDINGAN (SETUJU & TIDAK SETUJU + ALASAN) ---
    approval_summary_text = ft.Text("", size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED)
    approval_status_banner = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=AMBER)

    def on_approval_text_change(field_key: str):
        def _handler(e):
            state[field_key] = e.control.value or ""
            save_state()
        return _handler

    ref_name_field = ft.TextField(
        label="Nama Wasit",
        hint_text="Isi nama wasit",
        value=state.get("referee_name", ""),
        border_color=BORDER_COLOR,
        focused_border_color=GOLD,
        height=42,
        text_size=12,
        content_padding=pad_sym(10, 6),
        on_change=on_approval_text_change("referee_name"),
    )

    red_rep_field = ft.TextField(
        label="Perwakilan Tim Merah",
        hint_text="Kapten / Pemain Merah",
        value=state.get("red_rep_name", ""),
        border_color=BORDER_COLOR,
        focused_border_color=RED_ALERT,
        height=42,
        text_size=12,
        content_padding=pad_sym(10, 6),
        on_change=on_approval_text_change("red_rep_name"),
    )

    blue_rep_field = ft.TextField(
        label="Perwakilan Tim Biru",
        hint_text="Kapten / Pemain Biru",
        value=state.get("blue_rep_name", ""),
        border_color=BORDER_COLOR,
        focused_border_color=BLUE_TEAM,
        height=42,
        text_size=12,
        content_padding=pad_sym(10, 6),
        on_change=on_approval_text_change("blue_rep_name"),
    )

    ref_reject_reason_field = ft.TextField(
        label="Alasan Wasit Tidak Setuju",
        hint_text="Tuliskan alasan keberatan wasit...",
        value=state.get("referee_reject_reason", ""),
        multiline=True,
        min_lines=1,
        max_lines=3,
        border_color=RED_ALERT,
        focused_border_color=GOLD,
        text_size=12,
        content_padding=pad_sym(10, 8),
        visible=(state.get("referee_decision") == "tidak_setuju"),
        on_change=on_approval_text_change("referee_reject_reason"),
    )

    red_reject_reason_field = ft.TextField(
        label="Alasan Tim Merah Tidak Setuju",
        hint_text="Tuliskan alasan keberatan Tim Merah...",
        value=state.get("red_reject_reason", ""),
        multiline=True,
        min_lines=1,
        max_lines=3,
        border_color=RED_ALERT,
        focused_border_color=GOLD,
        text_size=12,
        content_padding=pad_sym(10, 8),
        visible=(state.get("red_decision") == "tidak_setuju"),
        on_change=on_approval_text_change("red_reject_reason"),
    )

    blue_reject_reason_field = ft.TextField(
        label="Alasan Tim Biru Tidak Setuju",
        hint_text="Tuliskan alasan keberatan Tim Biru...",
        value=state.get("blue_reject_reason", ""),
        multiline=True,
        min_lines=1,
        max_lines=3,
        border_color=RED_ALERT,
        focused_border_color=GOLD,
        text_size=12,
        content_padding=pad_sym(10, 8),
        visible=(state.get("blue_decision") == "tidak_setuju"),
        on_change=on_approval_text_change("blue_reject_reason"),
    )

    ref_approve_subtext = ft.Text("", size=10, color=TEXT_MUTED)
    red_approve_subtext = ft.Text("", size=10, color=TEXT_MUTED)
    blue_approve_subtext = ft.Text("", size=10, color=TEXT_MUTED)

    red_team_label_text = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=RED_ALERT)
    blue_team_label_text = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=BLUE_TEAM)

    btn_approve_ref = make_button("Setujui", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38)
    btn_reject_ref = make_button("Tidak Setuju", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38)

    btn_approve_red = make_button("Setujui", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38)
    btn_reject_red = make_button("Tidak Setuju", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38)

    btn_approve_blue = make_button("Setujui", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38)
    btn_reject_blue = make_button("Tidak Setuju", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38)

    def set_party_decision(party: str, choice: str):
        now_str = datetime.now().strftime("%H:%M WIB")
        dec_key_map = {
            "ref": ("referee_decision", "approve_referee_time", "Wasit"),
            "red": ("red_decision", "approve_red_time", "Tim Merah"),
            "blue": ("blue_decision", "approve_blue_time", "Tim Biru"),
        }
        dec_key, time_key, label_party = dec_key_map[party]
        current = state.get(dec_key, "")

        if current == choice:
            state[dec_key] = ""
            state[time_key] = ""
            play_sfx("click")
        else:
            state[dec_key] = choice
            state[time_key] = now_str
            if choice == "tidak_setuju":
                play_sfx("shake")
                show_toast(f"{label_party} memilih TIDAK SETUJU. Silakan isi alasan keberatan di kolom merah.")
            else:
                all_ok = (
                    state.get("referee_decision") == "setuju"
                    and state.get("red_decision") == "setuju"
                    and state.get("blue_decision") == "setuju"
                )
                if all_ok:
                    play_sfx("intro")
                    show_toast("Sah! Wasit, Tim Merah & Tim Biru telah menyetujui hasil akhir!")
                else:
                    play_sfx("click")

        save_state()
        refresh_ui()

    btn_approve_ref.on_click = lambda e: set_party_decision("ref", "setuju")
    btn_reject_ref.on_click = lambda e: set_party_decision("ref", "tidak_setuju")
    btn_approve_red.on_click = lambda e: set_party_decision("red", "setuju")
    btn_reject_red.on_click = lambda e: set_party_decision("red", "tidak_setuju")
    btn_approve_blue.on_click = lambda e: set_party_decision("blue", "setuju")
    btn_reject_blue.on_click = lambda e: set_party_decision("blue", "tidak_setuju")

    # --- LOGIKA ATURAN RESMI ORADO ---
    def toggle_sound(e):
        state["sound_on"] = not state.get("sound_on", True)
        save_state()
        if state["sound_on"]:
            play_sfx("click")
        refresh_ui()

    sound_btn.on_click = toggle_sound

    def get_opening_balak(round_num: int) -> str:
        idx = (max(1, round_num) - 1) % 7
        return f"Balak {idx}-{idx}"

    def get_target_sets() -> int:
        return 3 if state["match_format"] == "BO5" else 2

    def get_status_info(score: int):
        sisa = max(0, TARGET_SKOR - score)
        if score >= TARGET_SKOR:
            return "MENANG SET (101+)", EMERALD
        if score >= 85:
            return f"CEKIH! Kurang {sisa}", RED_ALERT
        return f"Kurang {sisa} ke 101", TEXT_MUTED

    def record_snapshot(team: str, points_str: str, label: str):
        state["history"].append({
            "team": team,
            "points_str": points_str,
            "label": label,
            "snap": {
                "score_a": state["score_a"],
                "score_b": state["score_b"],
                "round_num": state["round_num"],
                "minor_a": state["minor_a"],
                "minor_b": state["minor_b"],
                "major_a": state["major_a"],
                "major_b": state["major_b"],
            },
        })

    def get_approval_snapshot() -> dict:
        ref_dec = state.get("referee_decision", "")
        red_dec = state.get("red_decision", "")
        blue_dec = state.get("blue_decision", "")
        all_ok = (ref_dec == "setuju") and (red_dec == "setuju") and (blue_dec == "setuju")
        any_reject = "tidak_setuju" in (ref_dec, red_dec, blue_dec)
        return {
            "all_approved": all_ok,
            "any_rejected": any_reject,
            "ref_name": (state.get("referee_name") or "").strip() or "Wasit Pertandingan",
            "ref_dec": ref_dec,
            "ref_reason": (state.get("referee_reject_reason") or "").strip(),
            "ref_time": state.get("approve_referee_time", ""),
            "red_name": (state.get("red_rep_name") or "").strip() or "Perwakilan Tim Merah",
            "red_dec": red_dec,
            "red_reason": (state.get("red_reject_reason") or "").strip(),
            "red_time": state.get("approve_red_time", ""),
            "blue_name": (state.get("blue_rep_name") or "").strip() or "Perwakilan Tim Biru",
            "blue_dec": blue_dec,
            "blue_reason": (state.get("blue_reject_reason") or "").strip(),
            "blue_time": state.get("approve_blue_time", ""),
        }

    # --- LOGIKA SIMPAN & ARSIP RIWAYAT PERTANDINGAN ---
    def archive_current_match(status_summary: str = "Disimpan Manual", sets_a_override: int | None = None, sets_b_override: int | None = None):
        sa = state["sets_a"] if sets_a_override is None else sets_a_override
        sb = state["sets_b"] if sets_b_override is None else sets_b_override
        entry = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "timestamp": datetime.now().strftime("%d/%m/%Y • %H:%M"),
            "format": state["match_format"],
            "team_a": state["team_a"],
            "team_b": state["team_b"],
            "sets_a": sa,
            "sets_b": sb,
            "score_a": state["score_a"],
            "score_b": state["score_b"],
            "set_num": state["set_num"],
            "status": status_summary,
            "approvals": get_approval_snapshot(),
            "notes": list(state.get("referee_notes", [])),
            "logs": [
                {
                    "team": state["team_a"] if h["team"] == "A" else state["team_b"],
                    "points_str": h.get("points_str", ""),
                    "label": h.get("label", ""),
                }
                for h in state.get("history", [])
            ],
        }
        saved_matches.insert(0, entry)
        if len(saved_matches) > 30:
            del saved_matches[30:]
        save_archive()

    def handle_manual_save_match(e):
        play_sfx("click")
        appr = get_approval_snapshot()
        if appr["all_approved"]:
            sah_note = " • SAH (3/3 Setuju)"
        elif appr["any_rejected"]:
            sah_note = " • ADA KEBERATAN (Tidak Setuju)"
        else:
            sah_note = ""
        archive_current_match(
            status_summary=f"Set {state['set_num']} (Skor Set {state['sets_a']}-{state['sets_b']} | Poin {state['score_a']}-{state['score_b']}){sah_note}"
        )
        refresh_ui()
        missing_reason = (
            (appr["ref_dec"] == "tidak_setuju" and not appr["ref_reason"])
            or (appr["red_dec"] == "tidak_setuju" and not appr["red_reason"])
            or (appr["blue_dec"] == "tidak_setuju" and not appr["blue_reason"])
        )
        if missing_reason:
            show_toast("Tersimpan ke Arsip! (Catatan: kolom alasan Tidak Setuju masih kosong)")
        else:
            show_toast("Hasil pertandingan & konfirmasi TTD tersimpan ke Arsip!")

    def start_fresh_match(e=None):
        play_sfx("shake")
        state["score_a"] = 0
        state["score_b"] = 0
        state["sets_a"] = 0
        state["sets_b"] = 0
        state["set_num"] = 1
        state["round_num"] = 1
        state["minor_a"] = 0
        state["minor_b"] = 0
        state["major_a"] = 0
        state["major_b"] = 0
        state["history"] = []
        state["referee_notes"] = []
        reset_approval_flags()
        save_state()
        refresh_ui()
        show_toast("Papan skor & persetujuan direset untuk pertandingan baru.")

    def _format_party_decision_line(dec: str, t_str: str, reason_str: str) -> str:
        if dec == "setuju":
            return f"DISETUJUI ({t_str or '-'})"
        if dec == "tidak_setuju":
            alasan_txt = reason_str if reason_str else "(Alasan belum diisi)"
            return f"TIDAK SETUJU ({t_str or '-'}) — Alasan: {alasan_txt}"
        return "Belum dikonfirmasi"

    def open_match_detail_dialog(match_item: dict):
        appr = match_item.get("approvals") or {}
        ref_line = _format_party_decision_line(
            appr.get("ref_dec", ""), appr.get("ref_time", ""), appr.get("ref_reason", "")
        )
        red_line = _format_party_decision_line(
            appr.get("red_dec", ""), appr.get("red_time", ""), appr.get("red_reason", "")
        )
        blue_line = _format_party_decision_line(
            appr.get("blue_dec", ""), appr.get("blue_time", ""), appr.get("blue_reason", "")
        )

        if appr.get("all_approved"):
            pengesahan_status = "SAH & DISETUJUI SEMUA PIHAK (3/3)"
        elif appr.get("any_rejected"):
            pengesahan_status = "TIDAK SAH / ADA PIHAK TIDAK SETUJU"
        else:
            pengesahan_status = "MENUNGGU KONFIRMASI LENGKAP"

        lines = [
            f"ORADO DOMINO 101 ({match_item.get('format', 'BO3')})",
            f"Waktu: {match_item.get('timestamp', '-')}",
            f"Tim Merah: {match_item.get('team_a')}",
            f"Tim Biru: {match_item.get('team_b')}",
            f"Skor Set Akhir: {match_item.get('sets_a', 0)} - {match_item.get('sets_b', 0)}",
            f"Skor Poin Set Terakhir: {match_item.get('score_a', 0)} - {match_item.get('score_b', 0)}",
            f"Status: {match_item.get('status', '-')}",
            "",
            "--- KONFIRMASI TTD HASIL AKHIR ---",
            f"• Wasit ({appr.get('ref_name', 'Wasit')}): {ref_line}",
            f"• Tim Merah ({appr.get('red_name', 'Kapten Merah')}): {red_line}",
            f"• Tim Biru ({appr.get('blue_name', 'Kapten Biru')}): {blue_line}",
            f"Pengesahan: {pengesahan_status}",
            "",
            "--- CATATAN WASIT ---",
        ]
        notes = match_item.get("notes", [])
        if notes:
            lines.extend([f"• {n}" for n in notes])
        else:
            lines.append("• (Tidak ada catatan wasit)")

        lines.append("")
        lines.append("--- LOG RONDE & SANKSI ---")
        logs = match_item.get("logs", [])
        if logs:
            for idx, lg in enumerate(logs, start=1):
                lines.append(f"{idx}. {lg.get('team')} | {lg.get('label')} ({lg.get('points_str')})")
        else:
            lines.append("• (Belum ada log poin)")

        rekap_text = "\n".join(lines)
        rekap_field = ft.TextField(
            value=rekap_text,
            multiline=True,
            min_lines=9,
            max_lines=15,
            read_only=True,
            text_size=11,
            border_color=BORDER_COLOR,
        )

        detail_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(
                f"{match_item.get('team_a')} vs {match_item.get('team_b')}",
                color=GOLD,
                weight=ft.FontWeight.BOLD,
                size=15,
            ),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text("Tahan teks di bawah untuk menyalin berita acara ke WhatsApp:", size=11, color=TEXT_MUTED),
                    rekap_field,
                ],
            ),
            actions=[
                ft.TextButton("Tutup", on_click=lambda ev: close_dialog(detail_dlg)),
            ],
        )
        open_dialog(detail_dlg)

    def open_archive_dialog(e):
        play_sfx("click")
        archive_list_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=340)

        def rebuild_archive_list():
            archive_list_col.controls.clear()
            if not saved_matches:
                archive_list_col.controls.append(
                    ft.Text("Belum ada riwayat pertandingan yang disimpan.", size=12, color=TEXT_MUTED)
                )
            else:
                for idx, m in enumerate(saved_matches):
                    def make_del(index_to_del: int):
                        def _del(ev):
                            if 0 <= index_to_del < len(saved_matches):
                                saved_matches.pop(index_to_del)
                                save_archive()
                                rebuild_archive_list()
                                refresh_ui()
                                page.update()
                        return _del

                    def make_view(item_data: dict):
                        def _view(ev):
                            close_dialog(arch_dlg)
                            open_match_detail_dialog(item_data)
                        return _view

                    appr_info = m.get("approvals") or {}
                    if appr_info.get("all_approved"):
                        sah_badge = " • ✅ SAH (3/3)"
                        card_border = EMERALD
                        sub_col = EMERALD
                    elif appr_info.get("any_rejected"):
                        sah_badge = " • ❌ ADA KEBERATAN"
                        card_border = RED_ALERT
                        sub_col = RED_ALERT
                    else:
                        sah_badge = ""
                        card_border = BORDER_COLOR
                        sub_col = TEXT_MUTED

                    archive_list_col.controls.append(
                        ft.Container(
                            padding=10,
                            border_radius=10,
                            bgcolor=BG_DARK,
                            border=border_all(1, card_border),
                            content=ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Text(
                                                f"{m.get('team_a')} vs {m.get('team_b')}",
                                                size=13,
                                                weight=ft.FontWeight.BOLD,
                                                color=GOLD,
                                                expand=True,
                                            ),
                                            ft.Text(
                                                f"SET {m.get('sets_a', 0)}-{m.get('sets_b', 0)}",
                                                size=12,
                                                weight=ft.FontWeight.BOLD,
                                                color=EMERALD,
                                            ),
                                        ],
                                    ),
                                    ft.Text(
                                        f"{m.get('timestamp')} • {m.get('format')}{sah_badge}",
                                        size=11,
                                        color=sub_col,
                                    ),
                                    ft.Text(
                                        f"{m.get('status')}",
                                        size=11,
                                        color=TEXT_MUTED,
                                    ),
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.END,
                                        spacing=6,
                                        controls=[
                                            ft.TextButton("Lihat Berita Acara", on_click=make_view(m)),
                                            ft.TextButton("Hapus", on_click=make_del(idx)),
                                        ],
                                    ),
                                ],
                            ),
                        )
                    )

        rebuild_archive_list()

        arch_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(f"Arsip Pertandingan ({len(saved_matches)})", color=GOLD, weight=ft.FontWeight.BOLD, size=16),
            content=archive_list_col,
            actions=[
                ft.TextButton("Tutup", on_click=lambda ev: close_dialog(arch_dlg)),
            ],
        )
        open_dialog(arch_dlg)

    # --- LOGIKA CATATAN WASIT ---
    def add_referee_note(text_val: str):
        cleaned = (text_val or "").strip()
        if not cleaned:
            return
        stamp = f"[Set {state['set_num']} • R{state['round_num']}] {cleaned}"
        state.setdefault("referee_notes", []).insert(0, stamp)
        play_sfx("click")
        save_state()
        refresh_ui()

    def handle_submit_ref_note(e):
        val = ref_note_input.value
        if (val or "").strip():
            ref_note_input.value = ""
            add_referee_note(val)

    def handle_quick_ref_tag(tag_text: str):
        active_name = state["team_a"] if state["selected_team"] == "A" else state["team_b"]
        add_referee_note(f"{tag_text} ({active_name})")

    def select_team(team_code: str):
        state["selected_team"] = team_code
        play_sfx("click")
        save_state()
        refresh_ui()

    def set_bonus_mode(mode: str):
        state["bonus_mode"] = mode
        if mode == "2x":
            play_sfx("v_2x")
        elif mode == "+50":
            play_sfx("v_balak50")
        else:
            play_sfx("click")
        refresh_ui()

    def scroll_to_approval_panel():
        try:
            main_scroll_col.scroll_to(key="approval_section", duration=450)
        except Exception:
            try:
                main_scroll_col.scroll_to(offset=-1, duration=450)
            except Exception:
                pass

    # --- DISKUALIFIKASI LANGSUNG (3x PELANGGARAN BERAT) -> KEMENANGAN TIM LAWAN ---
    def handle_disqualification_victory(winner_code: str, offender_code: str, reason: str):
        play_sfx("shake")
        winner_name = state["team_a"] if winner_code == "A" else state["team_b"]
        offender_name = state["team_a"] if offender_code == "A" else state["team_b"]
        target_sets = get_target_sets()

        projected_sets_a = max(state["sets_a"], target_sets) if winner_code == "A" else state["sets_a"]
        projected_sets_b = max(state["sets_b"], target_sets) if winner_code == "B" else state["sets_b"]

        record_snapshot(
            winner_code,
            "MENANG DQ",
            f"DISKUALIFIKASI: {offender_name} (3x Pelanggaran Berat) → {winner_name} MENANG",
        )
        dq_stamp = (
            f"[Set {state['set_num']} • R{state['round_num']}] "
            f"DISKUALIFIKASI: {offender_name} (3x Pelanggaran Berat) — Kemenangan Match untuk {winner_name}"
        )
        state.setdefault("referee_notes", []).insert(0, dq_stamp)
        save_state()
        refresh_ui()

        def go_to_approval_dq(e):
            play_sfx("click")
            state["sets_a"] = projected_sets_a
            state["sets_b"] = projected_sets_b
            state["match_finished"] = True
            save_state()
            close_dialog(dq_dlg)
            refresh_ui()
            scroll_to_approval_panel()
            show_toast(f"{offender_name} DISKUALIFIKASI! Silakan konfirmasi TTD hasil akhir.")

        def save_and_new_dq(e):
            play_sfx("click")
            state["sets_a"] = projected_sets_a
            state["sets_b"] = projected_sets_b
            archive_current_match(
                status_summary=f"Selesai (DISKUALIFIKASI) • Pemenang: {winner_name} ({projected_sets_a}-{projected_sets_b})",
                sets_a_override=projected_sets_a,
                sets_b_override=projected_sets_b,
            )
            state["score_a"] = 0
            state["score_b"] = 0
            state["sets_a"] = 0
            state["sets_b"] = 0
            state["set_num"] = 1
            state["round_num"] = 1
            state["minor_a"] = 0
            state["minor_b"] = 0
            state["major_a"] = 0
            state["major_b"] = 0
            state["history"] = []
            state["referee_notes"] = []
            reset_approval_flags()
            save_state()
            close_dialog(dq_dlg)
            refresh_ui()
            show_toast(f"Hasil Diskualifikasi ({winner_name} Menang) tersimpan ke Arsip!")

        dq_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(
                f"🚫 DISKUALIFIKASI! {winner_name} MENANG!",
                color=RED_ALERT,
                weight=ft.FontWeight.BOLD,
                size=16,
            ),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text(
                        f"Tim Terdiskualifikasi: {offender_name} (3/3 Pelanggaran Berat)",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=RED_ALERT,
                    ),
                    ft.Text(
                        f"Pemenang Pertandingan: {winner_name} (Skor Set {projected_sets_a} - {projected_sets_b})",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=EMERALD,
                    ),
                    ft.Text(f"Keterangan: {reason}", size=12, color=TEXT_PRIMARY),
                ],
            ),
            actions=[
                ft.TextButton("Simpan & Baru", on_click=save_and_new_dq),
                make_button("Konfirmasi TTD ↓", EMERALD, BG_DARK, go_to_approval_dq),
            ],
        )
        open_dialog(dq_dlg)

    def handle_set_victory(
        winner_code: str,
        win_reason: str,
        allow_apollo: bool = True,
        force_apollo: bool = False,
        play_default_fanfare: bool = True,
    ):
        if play_default_fanfare:
            play_sfx("intro")

        winner_name = state["team_a"] if winner_code == "A" else state["team_b"]
        loser_name = state["team_b"] if winner_code == "A" else state["team_a"]
        winner_score = state["score_a"] if winner_code == "A" else state["score_b"]
        loser_score = state["score_b"] if winner_code == "A" else state["score_a"]

        rounds_completed = len([h for h in state["history"] if "Ronde" in h["label"] or "Pass Palsu" in h["label"]])
        is_apollo = force_apollo or (
            allow_apollo
            and winner_score >= TARGET_SKOR
            and loser_score == 0
            and rounds_completed > 1
        )

        if is_apollo and not force_apollo:
            play_sfx("v_apollo")

        sets_earned = 2 if is_apollo else 1
        target_sets = get_target_sets()

        projected_sets_a = state["sets_a"] + (sets_earned if winner_code == "A" else 0)
        projected_sets_b = state["sets_b"] + (sets_earned if winner_code == "B" else 0)
        is_match_over = (projected_sets_a >= target_sets) or (projected_sets_b >= target_sets)

        def go_to_approval_bottom(e):
            play_sfx("click")
            state["sets_a"] = projected_sets_a
            state["sets_b"] = projected_sets_b
            state["match_finished"] = True
            save_state()
            close_dialog(dlg)
            refresh_ui()
            scroll_to_approval_panel()
            show_toast("Silakan Wasit, Tim Merah & Tim Biru konfirmasi hasil di bawah!")

        def proceed_next(e):
            play_sfx("click")
            state["sets_a"] = projected_sets_a
            state["sets_b"] = projected_sets_b
            if is_match_over:
                archive_current_match(
                    status_summary=f"Selesai • Juara: {winner_name} ({projected_sets_a}-{projected_sets_b})",
                    sets_a_override=projected_sets_a,
                    sets_b_override=projected_sets_b,
                )
                state["score_a"] = 0
                state["score_b"] = 0
                state["sets_a"] = 0
                state["sets_b"] = 0
                state["set_num"] = 1
                state["round_num"] = 1
                state["minor_a"] = 0
                state["minor_b"] = 0
                state["major_a"] = 0
                state["major_b"] = 0
                state["history"] = []
                state["referee_notes"] = []
                reset_approval_flags()
                show_toast(f"Match {winner_name} otomatis tersimpan ke Arsip!")
            else:
                state["set_num"] += 1
                state["score_a"] = 0
                state["score_b"] = 0
                state["round_num"] = 1
                state["minor_a"] = 0
                state["minor_b"] = 0
                state["major_a"] = 0
                state["major_b"] = 0
                state["history"] = []
            save_state()
            close_dialog(dlg)
            refresh_ui()

        def reset_match_now(e):
            play_sfx("shake")
            state["score_a"] = 0
            state["score_b"] = 0
            state["sets_a"] = 0
            state["sets_b"] = 0
            state["set_num"] = 1
            state["round_num"] = 1
            state["minor_a"] = 0
            state["minor_b"] = 0
            state["major_a"] = 0
            state["major_b"] = 0
            state["history"] = []
            state["referee_notes"] = []
            reset_approval_flags()
            save_state()
            close_dialog(dlg)
            refresh_ui()

        title_text = (
            f"🏆 {winner_name} JUARA MATCH!"
            if is_match_over
            else (f"🔥 APOLLO! {winner_name} (+2 SET)" if is_apollo else f"🏆 {winner_name} MENANG SET {state['set_num']}!")
        )

        apollo_note = (
            "Bonus APOLLO Aktif (Lawan 0 poin) → Langsung +2 Set sekaligus!"
            if is_apollo
            else f"Perolehan Set: +{sets_earned} Set (Skor Set: {projected_sets_a} - {projected_sets_b})"
        )

        dialog_actions = (
            [
                ft.TextButton("Simpan & Baru", on_click=proceed_next),
                make_button("Konfirmasi TTD ↓", EMERALD, BG_DARK, go_to_approval_bottom),
            ]
            if is_match_over
            else [
                ft.TextButton("Reset 0-0", on_click=reset_match_now),
                make_button("Lanjut Set Berikutnya", GOLD, BG_DARK, proceed_next),
            ]
        )

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(title_text, color=GOLD, weight=ft.FontWeight.BOLD, size=17),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text(f"Keterangan: {win_reason}", size=13, weight=ft.FontWeight.W_600, color=EMERALD),
                    ft.Text(
                        f"Skor Akhir Set: {winner_name} ({winner_score}) vs {loser_name} ({loser_score})",
                        size=13,
                        color=TEXT_PRIMARY,
                    ),
                    ft.Text(apollo_note, size=12, weight=ft.FontWeight.BOLD, color=PURPLE_SPECIAL if is_apollo else GOLD),
                ],
            ),
            actions=dialog_actions,
        )
        open_dialog(dlg)

    def add_round_score(base_points: int):
        if base_points <= 0:
            return
        team = state["selected_team"]
        mode = state["bonus_mode"]

        if mode == "2x":
            final_pts = base_points * 2
            label = f"Ronde {state['round_num']} • 2x Ujung/Sama ({base_points}×2)"
        elif mode == "+50":
            final_pts = base_points + 50
            label = f"Ronde {state['round_num']} • Balak Sempurna ({base_points}+50)"
        else:
            final_pts = base_points
            label = f"Ronde {state['round_num']} • Normal"

        record_snapshot(team, f"+{final_pts}", label)

        if team == "A":
            state["score_a"] += final_pts
        else:
            state["score_b"] += final_pts

        state["round_num"] += 1
        state["bonus_mode"] = "1x"
        play_sfx("click")
        save_state()
        refresh_ui()

        if state["score_a"] >= TARGET_SKOR:
            handle_set_victory("A", f"Mencapai {state['score_a']} Poin (Domino 101)", allow_apollo=True)
        elif state["score_b"] >= TARGET_SKOR:
            handle_set_victory("B", f"Mencapai {state['score_b']} Poin (Domino 101)", allow_apollo=True)

    # --- KALKULATOR POIN BATU BERADU (GAPLE / MACET) ---
    def open_batu_beradu_dialog(e):
        play_sfx("v_beradu")
        closer_team = [state.get("selected_team", "A")]

        btn_closer_a = make_button(
            f"Merah ({state['team_a']})",
            RED_ALERT if closer_team[0] == "A" else CARD_ACTIVE,
            TEXT_PRIMARY,
            None,
            expand=True,
            height=38,
        )
        btn_closer_b = make_button(
            f"Biru ({state['team_b']})",
            BLUE_TEAM if closer_team[0] == "B" else CARD_ACTIVE,
            TEXT_PRIMARY,
            None,
            expand=True,
            height=38,
        )

        tf_sisa_a = ft.TextField(
            label=f"Sisa Mata {state['team_a']} (Merah)",
            hint_text="Contoh: 11",
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            border_color=RED_ALERT,
            focused_border_color=GOLD,
            height=46,
        )
        tf_sisa_b = ft.TextField(
            label=f"Sisa Mata {state['team_b']} (Biru)",
            hint_text="Contoh: 24",
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            border_color=BLUE_TEAM,
            focused_border_color=GOLD,
            height=46,
        )

        preview_text = ft.Text(
            "Isi sisa mata kedua tim untuk melihat hasil otomatis.",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=TEXT_MUTED,
        )

        def evaluate_beradu(va: int, vb: int, closer: str):
            total_semua = va + vb
            if closer == "A":
                closer_name, opp_code, opp_name = state["team_a"], "B", state["team_b"]
                s_own, s_opp = va, vb
            else:
                closer_name, opp_code, opp_name = state["team_b"], "A", state["team_a"]
                s_own, s_opp = vb, va

            if s_own < s_opp:
                return (
                    "menang",
                    closer,
                    closer_name,
                    total_semua,
                    f"{closer_name} MENANG Adu ({s_own} < {s_opp}) → +{total_semua} Poin (Semua Batu {va}+{vb})",
                    f"Ronde {state['round_num']} • Beradu Menang ({va}+{vb})",
                    "v_beradu_menang",
                )
            elif s_own > s_opp:
                pts_x2 = total_semua * 2
                return (
                    "kalah",
                    opp_code,
                    opp_name,
                    pts_x2,
                    f"{closer_name} KALAH Adu ({s_own} > {s_opp}) → +{pts_x2} Poin untuk {opp_name} (Semua Batu {va}+{vb} × 2)",
                    f"Ronde {state['round_num']} • Beradu Kalah ({va}+{vb})×2",
                    "v_beradu_kalah",
                )
            else:
                return (
                    "seri",
                    opp_code,
                    opp_name,
                    total_semua,
                    f"SERI Adu ({va} = {vb}) → +{total_semua} Poin untuk {opp_name} (Semua Batu {va}+{vb} ke Lawan)",
                    f"Ronde {state['round_num']} • Beradu Seri ({va}+{vb} ke Lawan)",
                    "v_beradu_seri",
                )

        def compute_preview(ev=None):
            raw_a = (tf_sisa_a.value or "").strip()
            raw_b = (tf_sisa_b.value or "").strip()
            if not (raw_a.isdigit() and raw_b.isdigit()):
                preview_text.value = "Isi angka sisa mata kedua tim (contoh: 11 dan 24)."
                preview_text.color = TEXT_MUTED
                if ev is not None:
                    page.update()
                return

            va = int(raw_a)
            vb = int(raw_b)
            if va == 0 and vb == 0:
                preview_text.value = "Total sisa mata tidak boleh 0."
                preview_text.color = RED_ALERT
                if ev is not None:
                    page.update()
                return

            outcome, _, _, _, summary_msg, _, _ = evaluate_beradu(va, vb, closer_team[0])
            preview_text.value = summary_msg
            if outcome == "menang":
                preview_text.color = EMERALD
            elif outcome == "kalah":
                preview_text.color = RED_ALERT
            else:
                preview_text.color = AMBER

            if ev is not None:
                page.update()

        def set_closer(team_c: str):
            play_sfx("click")
            closer_team[0] = team_c
            btn_closer_a.bgcolor = RED_ALERT if team_c == "A" else CARD_ACTIVE
            btn_closer_b.bgcolor = BLUE_TEAM if team_c == "B" else CARD_ACTIVE
            compute_preview(True)

        btn_closer_a.on_click = lambda ev: set_closer("A")
        btn_closer_b.on_click = lambda ev: set_closer("B")
        tf_sisa_a.on_change = compute_preview
        tf_sisa_b.on_change = compute_preview

        def confirm_batu_beradu(ev):
            raw_a = (tf_sisa_a.value or "").strip()
            raw_b = (tf_sisa_b.value or "").strip()
            if not (raw_a.isdigit() and raw_b.isdigit()):
                show_toast("Isi angka sisa mata kedua tim terlebih dahulu!")
                return

            va = int(raw_a)
            vb = int(raw_b)
            if va == 0 and vb == 0:
                show_toast("Total sisa mata tidak boleh 0!")
                return

            _, win_code, win_name, pts, _, log_label, voice_k = evaluate_beradu(va, vb, closer_team[0])

            record_snapshot(win_code, f"+{pts}", log_label)
            if win_code == "A":
                state["score_a"] += pts
            else:
                state["score_b"] += pts

            state["round_num"] += 1
            state["bonus_mode"] = "1x"
            play_sfx(voice_k)
            save_state()
            close_dialog(beradu_dlg)
            refresh_ui()

            if state["score_a"] >= TARGET_SKOR:
                handle_set_victory(
                    "A",
                    f"Mencapai {state['score_a']} Poin via Batu Beradu",
                    allow_apollo=True,
                    play_default_fanfare=False,
                )
            elif state["score_b"] >= TARGET_SKOR:
                handle_set_victory(
                    "B",
                    f"Mencapai {state['score_b']} Poin via Batu Beradu",
                    allow_apollo=True,
                    play_default_fanfare=False,
                )
            else:
                show_toast(f"Batu Beradu: +{pts} Poin untuk {win_name}!")

        beradu_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("⚔️ Batu Beradu (Gaple / Macet)", color=GOLD, weight=ft.FontWeight.BOLD, size=16),
            content=ft.Column(
                tight=True,
                spacing=10,
                controls=[
                    ft.Text(
                        "• Menang: Semua batu (sendiri+lawan)\n"
                        "• Kalah: (Semua batu) × 2 untuk lawan\n"
                        "• Seri: Semua batu diberikan ke lawan",
                        size=11,
                        color=TEXT_MUTED,
                    ),
                    ft.Text("Tim yang Menutup / Membuat Beradu:", size=11, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Row(spacing=6, controls=[btn_closer_a, btn_closer_b]),
                    tf_sisa_a,
                    tf_sisa_b,
                    ft.Container(
                        padding=10,
                        border_radius=8,
                        bgcolor=BG_DARK,
                        border=border_all(1, BORDER_COLOR),
                        content=preview_text,
                    ),
                ],
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(beradu_dlg)),
                make_button("Sahkan Poin Beradu", EMERALD, BG_DARK, confirm_batu_beradu),
            ],
        )
        open_dialog(beradu_dlg)

    def apply_penalty(points: int, reason: str, voice_key: str, ends_round: bool = False):
        winner_team = state["selected_team"]
        offender_team = "B" if winner_team == "A" else "A"

        record_snapshot(winner_team, f"+{points}", f"PENALTI: {reason}")

        if winner_team == "A":
            state["score_a"] += points
            state["major_b"] += 1
        else:
            state["score_b"] += points
            state["major_a"] += 1

        if ends_round:
            state["round_num"] += 1

        play_sfx(voice_key)
        save_state()
        refresh_ui()

        offender_majors = state["major_b"] if winner_team == "A" else state["major_a"]
        winner_score = state["score_a"] if winner_team == "A" else state["score_b"]

        # 3x Pelanggaran Berat -> Langsung Diskualifikasi & Kemenangan untuk Tim Lawan
        if offender_majors >= 3:
            handle_disqualification_victory(
                winner_team,
                offender_team,
                f"Akumulasi 3x Pelanggaran Berat ({reason})",
            )
        elif winner_score >= TARGET_SKOR:
            handle_set_victory(
                winner_team,
                f"Mencapai {winner_score} Poin via Penalti ({reason})",
                allow_apollo=True,
                play_default_fanfare=False,
            )

    def apply_minor_foul_on_opponent(e):
        winner_team = state["selected_team"]
        offender_team = "B" if winner_team == "A" else "A"
        offender_name = state["team_b"] if winner_team == "A" else state["team_a"]

        current_minor = state["minor_b"] if winner_team == "A" else state["minor_a"]

        if current_minor + 1 >= 2:
            record_snapshot(winner_team, "+11", f"2x Pelanggaran Ringan {offender_name} (1 Berat)")
            if winner_team == "A":
                state["minor_b"] = 0
                state["major_b"] += 1
                state["score_a"] += 11
            else:
                state["minor_a"] = 0
                state["major_a"] += 1
                state["score_b"] += 11
            play_sfx("v_pen11")
            save_state()
            refresh_ui()

            offender_majors = state["major_b"] if winner_team == "A" else state["major_a"]
            winner_score = state["score_a"] if winner_team == "A" else state["score_b"]

            # 3x Pelanggaran Berat -> Langsung Diskualifikasi & Kemenangan untuk Tim Lawan
            if offender_majors >= 3:
                handle_disqualification_victory(
                    winner_team,
                    offender_team,
                    "Akumulasi 3x Pelanggaran Berat (dari Pelanggaran Ringan)",
                )
            elif winner_score >= TARGET_SKOR:
                handle_set_victory(
                    winner_team,
                    "Mencapai 101 Poin dari Penalti 2x Ringan",
                    allow_apollo=True,
                    play_default_fanfare=False,
                )
        else:
            record_snapshot(offender_team, "WARN", f"Pelanggaran Ringan 1/2 ({offender_name})")
            if winner_team == "A":
                state["minor_b"] += 1
            else:
                state["minor_a"] += 1
            play_sfx("v_ringan")
            save_state()
            refresh_ui()

    def trigger_apollo_win(e):
        play_sfx("v_apollo")
        team = state["selected_team"]
        team_name = state["team_a"] if team == "A" else state["team_b"]
        opp_score = state["score_b"] if team == "A" else state["score_a"]

        warn_note = (
            "\n⚠️ Catatan: Skor lawan saat ini tidak 0 (menurut Pasal 12d, Apollo sah jika lawan 0 poin & bukan Ronde 1)."
            if opp_score > 0
            else "\nSkor lawan 0 poin → Sah mendapat +2 Set sekaligus (Pasal 12d)."
        )

        def confirm_apollo(ev):
            record_snapshot(team, "APOLLO", "KEMENANGAN APOLLO (+2 SET)")
            if team == "A":
                state["score_a"] = max(TARGET_SKOR, state["score_a"])
            else:
                state["score_b"] = max(TARGET_SKOR, state["score_b"])
            save_state()
            close_dialog(confirm_dlg)
            refresh_ui()
            handle_set_victory(
                team,
                "Kemenangan Spesial APOLLO (+2 Set)",
                allow_apollo=True,
                force_apollo=True,
                play_default_fanfare=False,
            )

        confirm_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("🔥 Konfirmasi APOLLO (+2 Set)", color=PURPLE_SPECIAL, weight=ft.FontWeight.BOLD),
            content=ft.Text(
                f"Tetapkan {team_name} menang APOLLO (langsung +2 Set)?{warn_note}",
                color=TEXT_PRIMARY,
                size=13,
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(confirm_dlg)),
                make_button("Ya, APOLLO!", PURPLE_SPECIAL, TEXT_PRIMARY, confirm_apollo),
            ],
        )
        open_dialog(confirm_dlg)

    def trigger_seven_balak_win(e):
        play_sfx("v_7balak")
        team = state["selected_team"]
        team_name = state["team_a"] if team == "A" else state["team_b"]

        def confirm_7balak(ev):
            record_snapshot(team, "→ 101", "7 BALAK / 1 SERI LENGKAP (Pasal 8e)")
            if team == "A":
                state["score_a"] = max(TARGET_SKOR, state["score_a"])
            else:
                state["score_b"] = max(TARGET_SKOR, state["score_b"])
            save_state()
            close_dialog(confirm_dlg)
            refresh_ui()
            handle_set_victory(
                team,
                "7 Balak / 1 Seri Lengkap (Skor Digenapkan 101, Tanpa Apollo)",
                allow_apollo=False,
                play_default_fanfare=False,
            )

        confirm_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("Konfirmasi 7 Balak / 1 Seri", color=GOLD, weight=ft.FontWeight.BOLD),
            content=ft.Text(
                f"Tetapkan {team_name} menang Set dengan 7 Balak / 1 Seri Lengkap?\n"
                f"(Skor digenapkan ke 101 & bonus Apollo tidak berlaku sesuai Pasal 8e).",
                color=TEXT_PRIMARY,
                size=13,
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(confirm_dlg)),
                make_button("Ya, Sah 101!", GOLD, BG_DARK, confirm_7balak),
            ],
        )
        open_dialog(confirm_dlg)

    def trigger_false_pass_under_3(e):
        play_sfx("v_pass_kalah")
        winner_team = state["selected_team"]
        loser_team = "B" if winner_team == "A" else "A"
        winner_name = state["team_a"] if winner_team == "A" else state["team_b"]
        loser_name = state["team_b"] if winner_team == "A" else state["team_a"]
        cur_score = state["score_a"] if winner_team == "A" else state["score_b"]

        new_score = TARGET_SKOR if cur_score < 51 else (cur_score + 75)
        rule_desc = (
            "Skor < 51 digenapkan ke 101"
            if cur_score < 51
            else f"Skor {cur_score} + 75 = {new_score}"
        )

        def confirm_fp3(ev):
            record_snapshot(winner_team, f"→ {new_score}", f"Pass Palsu ≤3 Batu oleh {loser_name}")
            if winner_team == "A":
                state["score_a"] = new_score
                state["major_b"] += 1
            else:
                state["score_b"] = new_score
                state["major_a"] += 1
            save_state()
            close_dialog(fp_dlg)
            refresh_ui()

            offender_majors = state["major_b"] if winner_team == "A" else state["major_a"]
            if offender_majors >= 3:
                handle_disqualification_victory(
                    winner_team,
                    loser_team,
                    f"Akumulasi 3x Pelanggaran Berat (Pass Palsu ≤ 3 Batu oleh {loser_name})",
                )
            else:
                handle_set_victory(
                    winner_team,
                    f"Lawan Pass Palsu Sisa ≤3 Batu ({rule_desc})",
                    allow_apollo=True,
                    play_default_fanfare=False,
                )

        fp_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("Pass Palsu (Sisa ≤ 3 Batu)", color=RED_ALERT, weight=ft.FontWeight.BOLD),
            content=ft.Text(
                f"{loser_name} melakukan Pass Palsu saat sisa batu ≤ 3?\n"
                f"{winner_name} menang Set ({rule_desc}).",
                color=TEXT_PRIMARY,
                size=13,
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(fp_dlg)),
                make_button("Sahkan Menang Set", RED_ALERT, TEXT_PRIMARY, confirm_fp3),
            ],
        )
        open_dialog(fp_dlg)

    def undo_last(e):
        if not state["history"]:
            return
        last = state["history"].pop()
        snap = last.get("snap")
        if snap:
            state["score_a"] = snap["score_a"]
            state["score_b"] = snap["score_b"]
            state["round_num"] = snap["round_num"]
            state["minor_a"] = snap["minor_a"]
            state["minor_b"] = snap["minor_b"]
            state["major_a"] = snap["major_a"]
            state["major_b"] = snap["major_b"]
        play_sfx("shake")
        save_state()
        refresh_ui()

    def open_settings_dialog(e):
        play_sfx("click")
        tf_a = ft.TextField(label="Nama Tim Merah (Tim A)", value=state["team_a"], border_color=RED_ALERT)
        tf_b = ft.TextField(label="Nama Tim Biru (Tim B)", value=state["team_b"], border_color=BLUE_TEAM)
        selected_fmt = [state["match_format"]]

        btn_bo3 = make_button(
            "Reguler (BO3)",
            GOLD if selected_fmt[0] == "BO3" else CARD_ACTIVE,
            BG_DARK if selected_fmt[0] == "BO3" else TEXT_PRIMARY,
            None,
            expand=True,
            height=40,
        )
        btn_bo5 = make_button(
            "Final (BO5)",
            GOLD if selected_fmt[0] == "BO5" else CARD_ACTIVE,
            BG_DARK if selected_fmt[0] == "BO5" else TEXT_PRIMARY,
            None,
            expand=True,
            height=40,
        )

        def pick_fmt(fmt_code: str):
            play_sfx("click")
            selected_fmt[0] = fmt_code
            btn_bo3.bgcolor = GOLD if fmt_code == "BO3" else CARD_ACTIVE
            btn_bo3.color = BG_DARK if fmt_code == "BO3" else TEXT_PRIMARY
            btn_bo5.bgcolor = GOLD if fmt_code == "BO5" else CARD_ACTIVE
            btn_bo5.color = BG_DARK if fmt_code == "BO5" else TEXT_PRIMARY
            page.update()

        btn_bo3.on_click = lambda ev: pick_fmt("BO3")
        btn_bo5.on_click = lambda ev: pick_fmt("BO5")

        def save_settings(ev):
            state["team_a"] = (tf_a.value or "TIM MERAH").strip().upper()
            state["team_b"] = (tf_b.value or "TIM BIRU").strip().upper()
            state["match_format"] = selected_fmt[0]
            play_sfx("click")
            save_state()
            close_dialog(edit_dlg)
            refresh_ui()

        edit_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("Pengaturan Pertandingan", color=GOLD, weight=ft.FontWeight.BOLD),
            content=ft.Column(
                tight=True,
                spacing=10,
                controls=[
                    tf_a,
                    tf_b,
                    ft.Text("Format Set (Pasal 11):", size=12, color=TEXT_MUTED),
                    ft.Row(spacing=8, controls=[btn_bo3, btn_bo5]),
                ],
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(edit_dlg)),
                make_button("Simpan", GOLD, BG_DARK, save_settings),
            ],
        )
        open_dialog(edit_dlg)

    def confirm_reset_round(e):
        play_sfx("shake")

        def do_reset_set(ev):
            state["score_a"] = 0
            state["score_b"] = 0
            state["round_num"] = 1
            state["minor_a"] = 0
            state["minor_b"] = 0
            state["major_a"] = 0
            state["major_b"] = 0
            state["history"] = []
            play_sfx("shake")
            save_state()
            close_dialog(rst_dlg)
            refresh_ui()

        def do_reset_match(ev):
            close_dialog(rst_dlg)
            start_fresh_match()

        rst_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("Reset Skor?", color=RED_ALERT, weight=ft.FontWeight.BOLD),
            content=ft.Text("Pilih reset skor Set berjalan saja atau reset seluruh Match (Set 0-0).", color=TEXT_PRIMARY, size=13),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(rst_dlg)),
                make_button("Reset Set Ini", AMBER, BG_DARK, do_reset_set),
                make_button("Reset Full Match", RED_ALERT, TEXT_PRIMARY, do_reset_match),
            ],
        )
        open_dialog(rst_dlg)

    # --- KARTU SKOR TIM ---
    team_a_card = ft.Container(
        expand=True,
        padding=12,
        border_radius=14,
        bgcolor=CARD_ACTIVE,
        border=border_all(2, GOLD),
        on_click=lambda e: select_team("A"),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=3,
            controls=[
                ft.Text("● TIM MERAH", size=10, weight=ft.FontWeight.BOLD, color=RED_ALERT),
                team_a_name_text,
                score_a_text,
                status_a_text,
                foul_a_text,
            ],
        ),
    )

    team_b_card = ft.Container(
        expand=True,
        padding=12,
        border_radius=14,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        on_click=lambda e: select_team("B"),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=3,
            controls=[
                ft.Text("● TIM BIRU", size=10, weight=ft.FontWeight.BOLD, color=BLUE_TEAM),
                team_b_name_text,
                score_b_text,
                status_b_text,
                foul_b_text,
            ],
        ),
    )

    active_team_banner = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=GOLD)

    btn_bonus_1x = make_button("1x Normal", EMERALD, BG_DARK, lambda e: set_bonus_mode("1x"), expand=True, height=36)
    btn_bonus_2x = make_button("2x Ujung/Sama", CARD_ACTIVE, TEXT_PRIMARY, lambda e: set_bonus_mode("2x"), expand=True, height=36)
    btn_bonus_50 = make_button("+50 Balak Semp.", CARD_ACTIVE, TEXT_PRIMARY, lambda e: set_bonus_mode("+50"), expand=True, height=36)
    btn_batu_beradu = make_button(
        "⚔️ Batu Beradu (Hitung Sisa Mata)",
        "#242B38",
        GOLD,
        open_batu_beradu_dialog,
        expand=True,
        height=40,
    )

    def _update_party_buttons(
        dec: str,
        t_str: str,
        btn_yes,
        btn_no,
        reason_field: ft.TextField,
        sub_txt: ft.Text,
        label_role: str,
    ):
        if dec == "setuju":
            set_button_label(btn_yes, "✓ Setuju")
            btn_yes.bgcolor = EMERALD
            btn_yes.color = BG_DARK
            set_button_label(btn_no, "Tidak Setuju")
            btn_no.bgcolor = CARD_ACTIVE
            btn_no.color = TEXT_MUTED
            reason_field.visible = False
            sub_txt.value = f"Disetujui {label_role} pukul {t_str}"
            sub_txt.color = EMERALD
        elif dec == "tidak_setuju":
            set_button_label(btn_yes, "Setujui")
            btn_yes.bgcolor = CARD_ACTIVE
            btn_yes.color = TEXT_MUTED
            set_button_label(btn_no, "✗ Tidak Setuju")
            btn_no.bgcolor = RED_ALERT
            btn_no.color = TEXT_PRIMARY
            reason_field.visible = True
            sub_txt.value = f"Tidak Setuju pukul {t_str} (Isi alasan di bawah)"
            sub_txt.color = RED_ALERT
        else:
            set_button_label(btn_yes, "Setujui")
            btn_yes.bgcolor = CARD_ACTIVE
            btn_yes.color = TEXT_PRIMARY
            set_button_label(btn_no, "Tidak Setuju")
            btn_no.bgcolor = CARD_ACTIVE
            btn_no.color = TEXT_PRIMARY
            reason_field.visible = False
            sub_txt.value = f"Menunggu konfirmasi {label_role}"
            sub_txt.color = TEXT_MUTED

    def refresh_ui():
        fmt_label = "FINAL BO5" if state["match_format"] == "BO5" else "REGULER BO3"
        set_badge_text.value = f"{fmt_label} • SET {state['set_num']} ({state['sets_a']} - {state['sets_b']})"
        round_balak_text.value = f"Ronde {state['round_num']} • Pembuka: {get_opening_balak(state['round_num'])}"

        sound_btn.icon = get_icon("VOLUME_UP" if state.get("sound_on", True) else "VOLUME_OFF")
        sound_btn.icon_color = EMERALD if state.get("sound_on", True) else TEXT_MUTED

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

        foul_a_text.value = f"Ringan: {state['minor_a']}/2 • Berat: {state['major_a']}/3"
        foul_a_text.color = RED_ALERT if state["major_a"] >= 3 else AMBER
        foul_b_text.value = f"Ringan: {state['minor_b']}/2 • Berat: {state['major_b']}/3"
        foul_b_text.color = RED_ALERT if state["major_b"] >= 3 else AMBER

        is_a = state["selected_team"] == "A"
        team_a_card.bgcolor = CARD_ACTIVE if is_a else CARD_BG
        team_a_card.border = border_all(2, GOLD if is_a else BORDER_COLOR)
        team_b_card.bgcolor = CARD_ACTIVE if not is_a else CARD_BG
        team_b_card.border = border_all(2, GOLD if not is_a else BORDER_COLOR)

        active_name = state["team_a"] if is_a else state["team_b"]
        active_team_banner.value = f"Penerima Poin Aktif: {active_name} (Ketuk kartu untuk ganti)"

        bm = state["bonus_mode"]
        btn_bonus_1x.bgcolor = EMERALD if bm == "1x" else CARD_ACTIVE
        btn_bonus_1x.color = BG_DARK if bm == "1x" else TEXT_PRIMARY
        btn_bonus_2x.bgcolor = GOLD if bm == "2x" else CARD_ACTIVE
        btn_bonus_2x.color = BG_DARK if bm == "2x" else TEXT_PRIMARY
        btn_bonus_50.bgcolor = PURPLE_SPECIAL if bm == "+50" else CARD_ACTIVE
        btn_bonus_50.color = TEXT_PRIMARY

        # Render Catatan Wasit
        ref_notes_column.controls.clear()
        notes = state.get("referee_notes", [])
        if not notes:
            ref_notes_column.controls.append(
                ft.Text("Belum ada catatan wasit di pertandingan ini.", size=11, color=TEXT_MUTED)
            )
        else:
            for n_idx, note_txt in enumerate(notes):
                def make_remove_note(del_i: int):
                    def _rm(ev):
                        if 0 <= del_i < len(state.get("referee_notes", [])):
                            state["referee_notes"].pop(del_i)
                            save_state()
                            refresh_ui()
                    return _rm

                ref_notes_column.controls.append(
                    ft.Container(
                        padding=pad_sym(10, 6),
                        border_radius=8,
                        bgcolor=BG_DARK,
                        border=border_all(1, BORDER_COLOR),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(note_txt, size=11, color=TEXT_PRIMARY, expand=True),
                                ft.IconButton(
                                    icon=get_icon("CLOSE"),
                                    icon_size=15,
                                    icon_color=TEXT_MUTED,
                                    tooltip="Hapus catatan",
                                    on_click=make_remove_note(n_idx),
                                ),
                            ],
                        ),
                    )
                )

        # Render Riwayat Ronde & Sanksi
        history_column.controls.clear()
        if not state["history"]:
            history_column.controls.append(
                ft.Text("Belum ada catatan poin di set ini.", size=12, color=TEXT_MUTED)
            )
        else:
            total_items = len(state["history"])
            for idx, item in enumerate(reversed(state["history"])):
                item_no = total_items - idx
                t_name = state["team_a"] if item["team"] == "A" else state["team_b"]
                pts_str = item.get("points_str", "")
                lbl = item.get("label", "")
                if "PENALTI" in lbl or "Pass Palsu" in lbl or "Ringan" in lbl or "DISKUALIFIKASI" in lbl:
                    badge_col = RED_ALERT
                elif "APOLLO" in lbl or "BALAK" in lbl or "Sempurna" in lbl:
                    badge_col = PURPLE_SPECIAL
                elif "Beradu" in lbl:
                    badge_col = GOLD
                else:
                    badge_col = EMERALD

                history_column.controls.append(
                    ft.Container(
                        padding=pad_sym(10, 8),
                        border_radius=8,
                        bgcolor=BG_DARK,
                        border=border_all(1, BORDER_COLOR),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    f"#{item_no}  {t_name} • {lbl}",
                                    size=11,
                                    color=TEXT_PRIMARY,
                                    expand=True,
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

        archive_btn_label.value = f"📂 Arsip Riwayat Pertandingan ({len(saved_matches)} Tersimpan)"

        # Render Panel Persetujuan Hasil Akhir Pertandingan
        ref_name_field.value = state.get("referee_name", "")
        red_rep_field.value = state.get("red_rep_name", "")
        blue_rep_field.value = state.get("blue_rep_name", "")

        ref_reject_reason_field.value = state.get("referee_reject_reason", "")
        red_reject_reason_field.value = state.get("red_reject_reason", "")
        blue_reject_reason_field.value = state.get("blue_reject_reason", "")

        red_team_label_text.value = f"● TIM MERAH ({state['team_a']})"
        blue_team_label_text.value = f"● TIM BIRU ({state['team_b']})"

        finish_tag = " [PERTANDINGAN SELESAI]" if state.get("match_finished") else ""
        approval_summary_text.value = (
            f"Hasil Akhir{finish_tag}: {state['team_a']} vs {state['team_b']} • "
            f"Skor Set ({state['sets_a']} - {state['sets_b']}) • Poin Set ({state['score_a']} - {state['score_b']})"
        )

        ref_dec = state.get("referee_decision", "")
        red_dec = state.get("red_decision", "")
        blue_dec = state.get("blue_decision", "")

        _update_party_buttons(
            ref_dec,
            state.get("approve_referee_time", ""),
            btn_approve_ref,
            btn_reject_ref,
            ref_reject_reason_field,
            ref_approve_subtext,
            "Wasit",
        )
        _update_party_buttons(
            red_dec,
            state.get("approve_red_time", ""),
            btn_approve_red,
            btn_reject_red,
            red_reject_reason_field,
            red_approve_subtext,
            "Tim Merah",
        )
        _update_party_buttons(
            blue_dec,
            state.get("approve_blue_time", ""),
            btn_approve_blue,
            btn_reject_blue,
            blue_reject_reason_field,
            blue_approve_subtext,
            "Tim Biru",
        )

        decisions = [ref_dec, red_dec, blue_dec]
        approved_count = decisions.count("setuju")
        rejected_count = decisions.count("tidak_setuju")

        if approved_count == 3:
            approval_status_banner.value = "✅ SAH & DISETUJUI SEMUA PIHAK (Wasit, Tim Merah & Tim Biru)"
            approval_status_banner.color = EMERALD
            approval_panel.border = border_all(2, EMERALD)
        elif rejected_count > 0:
            approval_status_banner.value = (
                f"⚠️ BELUM SAH / ADA KEBERATAN (Setuju: {approved_count}/3 • Tidak Setuju: {rejected_count}/3)"
            )
            approval_status_banner.color = RED_ALERT
            approval_panel.border = border_all(2, RED_ALERT)
        else:
            approval_status_banner.value = f"⏳ Status Pengesahan: {approved_count}/3 Pihak Menyetujui"
            approval_status_banner.color = AMBER
            approval_panel.border = border_all(1, GOLD if state.get("match_finished") else BORDER_COLOR)

        page.update()

    # --- TOMBOL AKSI CEPAT ---
    def handle_manual_submit(e):
        raw = (manual_score_input.value or "").strip()
        if raw.isdigit() and int(raw) > 0:
            val = int(raw)
            manual_score_input.value = ""
            add_round_score(val)

    quick_buttons = [
        make_button(
            f"+{val}",
            CARD_ACTIVE,
            TEXT_PRIMARY,
            lambda e, v=val: add_round_score(v),
            expand=True,
            height=42,
        )
        for val in QUICK_SCORES
    ]

    # --- SUSUNAN HALAMAN UTAMA ---
    header = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.Row(
                spacing=8,
                controls=[
                    logo_widget,
                    ft.Column(
                        spacing=1,
                        controls=[
                            ft.Text("ORADO DOMINO 101", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            set_badge_text,
                            round_balak_text,
                        ],
                    ),
                ],
            ),
            ft.Row(
                spacing=0,
                controls=[
                    sound_btn,
                    ft.IconButton(
                        icon=get_icon("EDIT"),
                        tooltip="Pengaturan Tim & Format BO3/BO5",
                        icon_color=GOLD,
                        on_click=open_settings_dialog,
                    ),
                    ft.IconButton(
                        icon=get_icon("REFRESH"),
                        tooltip="Reset Skor",
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
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                active_team_banner,
                ft.Row(spacing=6, controls=[btn_bonus_1x, btn_bonus_2x, btn_bonus_50]),
                ft.Row(spacing=6, controls=quick_buttons[:3]),
                ft.Row(spacing=6, controls=quick_buttons[3:]),
                ft.Row(
                    spacing=8,
                    controls=[
                        manual_score_input,
                        make_button("TAMBAH", EMERALD, BG_DARK, handle_manual_submit, height=46),
                    ],
                ),
                ft.Row(controls=[btn_batu_beradu]),
            ],
        ),
    )

    penalty_panel = ft.Container(
        padding=12,
        border_radius=14,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text("PENALTI & PELANGGARAN LAWAN (3x BERAT = DISKUALIFIKASI)", size=11, weight=ft.FontWeight.BOLD, color=AMBER),
                ft.Row(
                    spacing=6,
                    controls=[
                        make_button(
                            "Ringan (2x=+11)",
                            "#2B2416",
                            AMBER,
                            apply_minor_foul_on_opponent,
                            expand=True,
                            height=40,
                        ),
                        make_button(
                            "+11 (30dtk/Berat)",
                            "#3B181E",
                            RED_ALERT,
                            lambda e: apply_penalty(11, "Waktu 30dtk / Pelanggaran Berat (+11)", "v_pen11"),
                            expand=True,
                            height=40,
                        ),
                    ],
                ),
                ft.Row(
                    spacing=6,
                    controls=[
                        make_button(
                            "+25 (Salah/Dahulu)",
                            "#3B181E",
                            RED_ALERT,
                            lambda e: apply_penalty(25, "Batu Salah / Mendahului Giliran (+25)", "v_pen25"),
                            expand=True,
                            height=40,
                        ),
                        make_button(
                            "+50 (Pass Palsu ≥4)",
                            "#3B181E",
                            RED_ALERT,
                            lambda e: apply_penalty(50, "Pass Palsu Sisa ≥4 Batu (+50)", "v_pass50", ends_round=True),
                            expand=True,
                            height=40,
                        ),
                    ],
                ),
            ],
        ),
    )

    special_panel = ft.Container(
        padding=12,
        border_radius=14,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text("KEPUTUSAN SET KHUSUS (PASAL 8e, 10e.2 & 12d)", size=11, weight=ft.FontWeight.BOLD, color=PURPLE_SPECIAL),
                ft.Row(
                    spacing=6,
                    controls=[
                        make_button(
                            "🔥 APOLLO",
                            PURPLE_SPECIAL,
                            TEXT_PRIMARY,
                            trigger_apollo_win,
                            expand=True,
                            height=42,
                        ),
                        make_button(
                            "🀄 7 Balak",
                            GOLD,
                            BG_DARK,
                            trigger_seven_balak_win,
                            expand=True,
                            height=42,
                        ),
                        make_button(
                            "🚫 Pass ≤3",
                            "#3B181E",
                            RED_ALERT,
                            trigger_false_pass_under_3,
                            expand=True,
                            height=42,
                        ),
                    ],
                ),
            ],
        ),
    )

    referee_panel = ft.Container(
        padding=12,
        border_radius=14,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text("📋 CATATAN WASIT RESMI", size=11, weight=ft.FontWeight.BOLD, color=GOLD),
                ft.Row(
                    spacing=6,
                    controls=[
                        make_button(
                            "Shuffle Ulang",
                            CARD_ACTIVE,
                            TEXT_PRIMARY,
                            lambda e: handle_quick_ref_tag("Shuffle Ulang (5/6 Balak • Pasal 8c)"),
                            expand=True,
                            height=34,
                        ),
                        make_button(
                            "Tukar Kursi",
                            CARD_ACTIVE,
                            TEXT_PRIMARY,
                            lambda e: handle_quick_ref_tag("Tukar Tempat Duduk (Pasal 7b)"),
                            expand=True,
                            height=34,
                        ),
                        make_button(
                            "Ganti Pemain",
                            CARD_ACTIVE,
                            TEXT_PRIMARY,
                            lambda e: handle_quick_ref_tag("Pergantian Pemain (Pasal 1b)"),
                            expand=True,
                            height=34,
                        ),
                    ],
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        ref_note_input,
                        make_button("CATAT", GOLD, BG_DARK, handle_submit_ref_note, height=44),
                    ],
                ),
                ref_notes_column,
            ],
        ),
    )

    # --- PANEL PERSETUJUAN / KEBERATAN HASIL AKHIR PERTANDINGAN ---
    def build_party_approval_box(
        title_widget: ft.Control,
        name_field: ft.TextField,
        approve_btn,
        reject_btn,
        reason_field: ft.TextField,
        sub_text: ft.Text,
    ):
        return ft.Container(
            padding=10,
            border_radius=10,
            bgcolor=BG_DARK,
            border=border_all(1, BORDER_COLOR),
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            title_widget,
                            sub_text,
                        ],
                    ),
                    name_field,
                    ft.Row(
                        spacing=8,
                        controls=[
                            approve_btn,
                            reject_btn,
                        ],
                    ),
                    reason_field,
                ],
            ),
        )

    approval_panel = ft.Container(
        key="approval_section",
        padding=12,
        border_radius=14,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text("✍️ KONFIRMASI TTD HASIL AKHIR PERTANDINGAN", size=12, weight=ft.FontWeight.BOLD, color=GOLD),
                approval_summary_text,
                approval_status_banner,
                build_party_approval_box(
                    ft.Text("● WASIT PERTANDINGAN", size=12, weight=ft.FontWeight.BOLD, color=GOLD),
                    ref_name_field,
                    btn_approve_ref,
                    btn_reject_ref,
                    ref_reject_reason_field,
                    ref_approve_subtext,
                ),
                build_party_approval_box(
                    red_team_label_text,
                    red_rep_field,
                    btn_approve_red,
                    btn_reject_red,
                    red_reject_reason_field,
                    red_approve_subtext,
                ),
                build_party_approval_box(
                    blue_team_label_text,
                    blue_rep_field,
                    btn_approve_blue,
                    btn_reject_blue,
                    blue_reject_reason_field,
                    blue_approve_subtext,
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        make_button(
                            "Simpan ke Arsip",
                            EMERALD,
                            BG_DARK,
                            handle_manual_save_match,
                            expand=True,
                            height=42,
                        ),
                        make_button(
                            "Match Baru (0-0)",
                            CARD_ACTIVE,
                            TEXT_PRIMARY,
                            start_fresh_match,
                            expand=True,
                            height=42,
                        ),
                    ],
                ),
            ],
        ),
    )

    # --- PANEL PALING BAWAH: RIWAYAT RONDE & SANKSI ---
    archive_bar = ft.Container(
        padding=pad_sym(12, 10),
        border_radius=10,
        bgcolor=CARD_ACTIVE,
        border=border_all(1, GOLD),
        alignment=align_center(),
        on_click=open_archive_dialog,
        content=archive_btn_label,
    )

    history_panel = ft.Container(
        padding=12,
        border_radius=14,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("RIWAYAT RONDE & SANKSI", size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ft.Row(
                            spacing=2,
                            controls=[
                                ft.TextButton(
                                    "Undo",
                                    icon=get_icon("UNDO"),
                                    on_click=undo_last,
                                ),
                                ft.TextButton(
                                    "Simpan Match",
                                    icon=get_icon("SAVE"),
                                    on_click=handle_manual_save_match,
                                ),
                            ],
                        ),
                    ],
                ),
                history_column,
                archive_bar,
            ],
        ),
    )

    main_scroll_col = ft.Column(
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            header,
            score_section,
            input_panel,
            penalty_panel,
            special_panel,
            referee_panel,
            approval_panel,
            history_panel,
        ],
    )

    main_body = ft.Container(
        padding=14,
        content=main_scroll_col,
    )

    page.add(ft.SafeArea(expand=True, content=main_body))
    refresh_ui()


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main, assets_dir="assets")
    else:
        ft.app(target=main, assets_dir="assets")
