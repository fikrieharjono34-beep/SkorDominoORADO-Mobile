import base64
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


# --- GENERATOR EFEK SUARA LOKAL (16-BIT PCM WAV UNTUK ANDROID) ---
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


def build_builtin_sfx() -> dict[str, str]:
    sfx_dir = os.path.join(tempfile.gettempdir(), "orado_domino_sfx")
    os.makedirs(sfx_dir, exist_ok=True)
    sr = 44100

    # 1. Ketukan batu domino (55 ms)
    click_path = os.path.join(sfx_dir, "orado_click.wav")
    click_len = int(sr * 0.055)
    click_samples = []
    for i in range(click_len):
        t = i / sr
        env = math.exp(-t * 85.0)
        val = (math.sin(2 * math.pi * 920 * t) * 0.65 + math.sin(2 * math.pi * 2150 * t) * 0.35) * env
        click_samples.append(int(val * 26000))
    _write_wav(click_path, click_samples, sr)

    # 2. Nada peringatan penalti / undo / reset (220 ms)
    shake_path = os.path.join(sfx_dir, "orado_shake.wav")
    shake_len = int(sr * 0.22)
    shake_samples = []
    for i in range(shake_len):
        t = i / sr
        pulse = 1.0 if (t < 0.085 or t > 0.115) else 0.15
        env = math.exp(-t * 9.0) * pulse
        freq = 210 if t < 0.10 else 165
        val = (math.sin(2 * math.pi * freq * t) * 0.75 + math.sin(2 * math.pi * (freq * 2) * t) * 0.25) * env
        shake_samples.append(int(val * 26000))
    _write_wav(shake_path, shake_samples, sr)

    # 3. Fanfare kemenangan / pembuka (480 ms)
    win_path = os.path.join(sfx_dir, "orado_win.wav")
    notes = [(523.25, 0.10), (659.25, 0.10), (783.99, 0.10), (1046.50, 0.18)]
    win_samples = []
    for freq, dur in notes:
        n_len = int(sr * dur)
        for i in range(n_len):
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
        "team_a": "TIM A",
        "team_b": "TIM B",
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
    }

    STORAGE_KEY = "orado_domino_101_state_v2"

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

    # --- SISTEM AUDIO FLET 1.x (flet-audio) ---
    builtin_sfx = build_builtin_sfx()
    audio_players = {}
    AudioClass = getattr(fta, "Audio", None) if fta else None
    ReleaseMode = getattr(fta, "ReleaseMode", None) if fta else None

    if AudioClass:
        for sound_key, asset_filename in [
            ("intro", "intro_mlbb.wav"),
            ("click", "ui_click.wav"),
            ("shake", "ui_shake.wav"),
        ]:
            asset_disk_path = os.path.join("assets", asset_filename)
            audio_src = asset_filename if os.path.exists(asset_disk_path) else builtin_sfx.get(sound_key, "")
            if audio_src:
                try:
                    kwargs = {
                        "src": audio_src,
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
        tooltip="Suara On/Off",
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

    history_column = ft.Column(spacing=6)

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

    def select_team(team_code: str):
        state["selected_team"] = team_code
        play_sfx("click")
        save_state()
        refresh_ui()

    def set_bonus_mode(mode: str):
        state["bonus_mode"] = mode
        play_sfx("click")
        refresh_ui()

    def handle_set_victory(
        winner_code: str,
        win_reason: str,
        allow_apollo: bool = True,
        force_apollo: bool = False,
    ):
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

        sets_earned = 2 if is_apollo else 1
        target_sets = get_target_sets()

        projected_sets_a = state["sets_a"] + (sets_earned if winner_code == "A" else 0)
        projected_sets_b = state["sets_b"] + (sets_earned if winner_code == "B" else 0)
        is_match_over = (projected_sets_a >= target_sets) or (projected_sets_b >= target_sets)

        def proceed_next(e):
            play_sfx("click")
            state["sets_a"] = projected_sets_a
            state["sets_b"] = projected_sets_b
            if is_match_over:
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
            actions=[
                ft.TextButton("Reset 0-0", on_click=reset_match_now),
                make_button(
                    "Mulai Match Baru" if is_match_over else "Lanjut Set Berikutnya",
                    GOLD,
                    BG_DARK,
                    proceed_next,
                ),
            ],
        )
        open_dialog(dlg)

    def add_round_score(base_points: int):
        if base_points <= 0:
            return
        team = state["selected_team"]
        mode = state["bonus_mode"]

        if mode == "2x":
            final_pts = base_points * 2
            label = f"Ronde {state['round_num']} • 2x Ujung/Beradu ({base_points}×2)"
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

    def apply_penalty(points: int, reason: str, ends_round: bool = False):
        winner_team = state["selected_team"]

        record_snapshot(winner_team, f"+{points}", f"PENALTI: {reason}")

        if winner_team == "A":
            state["score_a"] += points
            state["major_b"] += 1
        else:
            state["score_b"] += points
            state["major_a"] += 1

        if ends_round:
            state["round_num"] += 1

        play_sfx("shake")
        save_state()
        refresh_ui()

        offender_majors = state["major_b"] if winner_team == "A" else state["major_a"]
        winner_score = state["score_a"] if winner_team == "A" else state["score_b"]

        if offender_majors >= 3:
            if winner_score < TARGET_SKOR:
                if winner_team == "A":
                    state["score_a"] = TARGET_SKOR
                else:
                    state["score_b"] = TARGET_SKOR
                save_state()
                refresh_ui()
            handle_set_victory(winner_team, "Lawan Akumulasi 3x Pelanggaran Berat (Pasal 14b.3)", allow_apollo=True)
        elif winner_score >= TARGET_SKOR:
            handle_set_victory(winner_team, f"Mencapai {winner_score} Poin via Penalti ({reason})", allow_apollo=True)

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
            play_sfx("shake")
            save_state()
            refresh_ui()

            offender_majors = state["major_b"] if winner_team == "A" else state["major_a"]
            winner_score = state["score_a"] if winner_team == "A" else state["score_b"]
            if offender_majors >= 3:
                if winner_score < TARGET_SKOR:
                    if winner_team == "A":
                        state["score_a"] = TARGET_SKOR
                    else:
                        state["score_b"] = TARGET_SKOR
                    save_state()
                    refresh_ui()
                handle_set_victory(winner_team, "Lawan Akumulasi 3x Pelanggaran Berat", allow_apollo=True)
            elif winner_score >= TARGET_SKOR:
                handle_set_victory(winner_team, "Mencapai 101 Poin dari Penalti 2x Ringan", allow_apollo=True)
        else:
            record_snapshot(offender_team, "WARN", f"Pelanggaran Ringan 1/2 ({offender_name})")
            if winner_team == "A":
                state["minor_b"] += 1
            else:
                state["minor_a"] += 1
            play_sfx("shake")
            save_state()
            refresh_ui()

    def trigger_apollo_win(e):
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
            handle_set_victory(team, "Kemenangan Spesial APOLLO (+2 Set)", allow_apollo=True, force_apollo=True)

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
            handle_set_victory(team, "7 Balak / 1 Seri Lengkap (Skor Digenapkan 101, Tanpa Apollo)", allow_apollo=False)

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
        winner_team = state["selected_team"]
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
            handle_set_victory(winner_team, f"Lawan Pass Palsu Sisa ≤3 Batu ({rule_desc})", allow_apollo=True)

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
        tf_a = ft.TextField(label="Nama Tim A", value=state["team_a"], border_color=GOLD)
        tf_b = ft.TextField(label="Nama Tim B", value=state["team_b"], border_color=GOLD)
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
            state["team_a"] = (tf_a.value or "TIM A").strip().upper()
            state["team_b"] = (tf_b.value or "TIM B").strip().upper()
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
            play_sfx("shake")
            save_state()
            close_dialog(rst_dlg)
            refresh_ui()

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
                team_b_name_text,
                score_b_text,
                status_b_text,
                foul_b_text,
            ],
        ),
    )

    active_team_banner = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=GOLD)

    btn_bonus_1x = make_button("1x Normal", EMERALD, BG_DARK, lambda e: set_bonus_mode("1x"), expand=True, height=36)
    btn_bonus_2x = make_button("2x Ujung/Beradu", CARD_ACTIVE, TEXT_PRIMARY, lambda e: set_bonus_mode("2x"), expand=True, height=36)
    btn_bonus_50 = make_button("+50 Balak Semp.", CARD_ACTIVE, TEXT_PRIMARY, lambda e: set_bonus_mode("+50"), expand=True, height=36)

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
        foul_b_text.value = f"Ringan: {state['minor_b']}/2 • Berat: {state['major_b']}/3"

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
                badge_col = RED_ALERT if ("PENALTI" in lbl or "Pass Palsu" in lbl or "Ringan" in lbl) else (
                    PURPLE_SPECIAL if ("APOLLO" in lbl or "BALAK" in lbl or "Sempurna" in lbl) else EMERALD
                )
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
                ft.Text("PENALTI & PELANGGARAN LAWAN (PASAL 10 & 14)", size=11, weight=ft.FontWeight.BOLD, color=AMBER),
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
                            lambda e: apply_penalty(11, "Waktu 30dtk / Pelanggaran Berat (+11)"),
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
                            lambda e: apply_penalty(25, "Batu Salah / Mendahului Giliran (+25)"),
                            expand=True,
                            height=40,
                        ),
                        make_button(
                            "+50 (Pass Palsu ≥4)",
                            "#3B181E",
                            RED_ALERT,
                            lambda e: apply_penalty(50, "Pass Palsu Sisa ≥4 Batu (+50)", ends_round=True),
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
                        ft.TextButton(
                            "Undo Terakhir",
                            icon=get_icon("UNDO"),
                            on_click=undo_last,
                        ),
                    ],
                ),
                history_column,
            ],
        ),
    )

    main_body = ft.Container(
        padding=14,
        content=ft.Column(
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                header,
                score_section,
                input_panel,
                penalty_panel,
                special_panel,
                history_panel,
            ],
        ),
    )

    page.add(ft.SafeArea(expand=True, content=main_body))
    refresh_ui()


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main, assets_dir="assets")
    else:
        ft.app(target=main, assets_dir="assets")
        
