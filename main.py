import asyncio
import base64
from datetime import datetime
import math
import os
import random
import struct
import tempfile
import traceback
import wave
import flet as ft

try:
    import flet_audio as fta
except ImportError:
    fta = None

ASSETS_B64 = {
    "logo_orado_ok.png": "",
}

TARGET_SKOR = 101
QUICK_SCORES = [5, 10, 15, 20, 25, 30]
TURN_LIMIT_SECONDS = 30

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


def make_button(
    label: str,
    bgcolor: str,
    color: str,
    on_click,
    expand: bool = False,
    height: float = 44,
    font_size: float = 12,
):
    btn_cls = getattr(ft, "Button", None) or getattr(ft, "ElevatedButton", None)
    text_ctrl = ft.Text(
        label,
        size=font_size,
        weight=ft.FontWeight.BOLD,
        color=color,
        max_lines=1,
        no_wrap=True,
        overflow=ft.TextOverflow.ELLIPSIS,
        text_align=ft.TextAlign.CENTER,
    )
    return btn_cls(
        content=text_ctrl,
        bgcolor=bgcolor,
        color=color,
        expand=expand,
        height=height,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=10),
            padding=pad_sym(8, 4),
        ),
        on_click=on_click,
    )


def set_button_label(btn, new_label: str):
    content = getattr(btn, "content", None)
    if isinstance(content, ft.Text):
        content.value = new_label
    if hasattr(btn, "text"):
        try:
            btn.text = new_label
        except Exception:
            pass


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


def _brass_wave(freq: float, t: float) -> float:
    return (
        math.sin(2 * math.pi * freq * t) * 0.55
        + math.sin(2 * math.pi * freq * 2.0 * t) * 0.28
        + math.sin(2 * math.pi * freq * 3.0 * t) * 0.12
        + math.sin(2 * math.pi * freq * 4.0 * t) * 0.05
    )


def build_chime_sfx() -> dict[str, str]:
    sfx_dir = os.path.join(tempfile.gettempdir(), "orado_domino_mobile_chimes_v1")
    os.makedirs(sfx_dir, exist_ok=True)
    sr = 44100
    rng = random.Random(101)

    click_path = os.path.join(sfx_dir, "orado_click.wav")
    _write_wav(
        click_path,
        [
            int((math.sin(2 * math.pi * 920 * (i / sr)) * 0.65 + math.sin(2 * math.pi * 2150 * (i / sr)) * 0.35) * math.exp(-(i / sr) * 85.0) * 25000)
            for i in range(int(sr * 0.055))
        ],
        sr,
    )

    beep_path = os.path.join(sfx_dir, "orado_beep.wav")
    _write_wav(
        beep_path,
        [int(math.sin(2 * math.pi * 1320 * (i / sr)) * math.exp(-(i / sr) * 32.0) * 26000) for i in range(int(sr * 0.09))],
        sr,
    )

    shake_path = os.path.join(sfx_dir, "orado_shake.wav")
    shake_samples = []
    for i in range(int(sr * 0.22)):
        t = i / sr
        pulse = 1.0 if (t < 0.085 or t > 0.115) else 0.15
        env = math.exp(-t * 9.0) * pulse
        freq = 210 if t < 0.10 else 165
        val = (math.sin(2 * math.pi * freq * t) * 0.75 + math.sin(2 * math.pi * (freq * 2) * t) * 0.25) * env
        shake_samples.append(int(val * 25000))
    _write_wav(shake_path, shake_samples, sr)

    win_path = os.path.join(sfx_dir, "orado_win_grand.wav")
    win_samples = []
    for freq, dur in [(523.25, 0.11), (659.25, 0.11), (783.99, 0.11), (1046.50, 0.16), (783.99, 0.11)]:
        for i in range(int(sr * dur)):
            t = i / sr
            att = min(1.0, t / 0.012)
            win_samples.append(int(_brass_wave(freq, t) * att * math.exp(-t * 5.0) * 26000))
    for i in range(int(sr * 0.75)):
        t = i / sr
        att = min(1.0, t / 0.02)
        env = att * math.exp(-t * 2.6)
        chord = _brass_wave(523.25, t) * 0.32 + _brass_wave(659.25, t) * 0.28 + _brass_wave(783.99, t) * 0.28 + _brass_wave(1046.50, t) * 0.35
        sparkle = (rng.uniform(-1.0, 1.0) * 0.14) * math.exp(-t * 3.2)
        win_samples.append(int((chord * env + sparkle) * 26500))
    _write_wav(win_path, win_samples, sr)

    apollo_path = os.path.join(sfx_dir, "orado_apollo_fanfare.wav")
    apollo_samples = []
    for freq, dur in [(392.00, 0.08), (523.25, 0.08), (659.25, 0.08), (783.99, 0.09), (1046.50, 0.12), (1318.51, 0.14)]:
        for i in range(int(sr * dur)):
            t = i / sr
            att = min(1.0, t / 0.01)
            apollo_samples.append(int(_brass_wave(freq, t) * att * math.exp(-t * 6.0) * 27000))
    for i in range(int(sr * 0.85)):
        t = i / sr
        att = min(1.0, t / 0.018)
        env = att * math.exp(-t * 2.3)
        chord = _brass_wave(523.25, t) * 0.28 + _brass_wave(783.99, t) * 0.30 + _brass_wave(1046.50, t) * 0.34 + _brass_wave(1567.98, t) * 0.24
        shimmer = math.sin(2 * math.pi * 2637.0 * t) * 0.08 * math.exp(-t * 3.5)
        cheer = rng.uniform(-1.0, 1.0) * 0.16 * math.exp(-t * 2.8)
        apollo_samples.append(int((chord * env + shimmer + cheer) * 27500))
    _write_wav(apollo_path, apollo_samples, sr)

    gong_path = os.path.join(sfx_dir, "orado_7balak_gong.wav")
    gong_samples = []
    for i in range(int(sr * 1.15)):
        t = i / sr
        att = min(1.0, t / 0.015)
        gong_env = att * math.exp(-t * 2.2)
        gong = (
            math.sin(2 * math.pi * 196.0 * t) * 0.45
            + math.sin(2 * math.pi * 293.66 * t) * 0.28
            + math.sin(2 * math.pi * 440.0 * t) * 0.20
            + math.sin(2 * math.pi * 587.33 * t) * 0.14
        ) * gong_env
        spark = 0.0
        for idx_c, cf in enumerate([1046.5, 1318.5, 1568.0, 2093.0, 2637.0]):
            t_start = idx_c * 0.09
            if t >= t_start:
                dt = t - t_start
                spark += math.sin(2 * math.pi * cf * dt) * 0.18 * math.exp(-dt * 7.5)
        gong_samples.append(int((gong + spark) * 27000))
    _write_wav(gong_path, gong_samples, sr)

    combo_path = os.path.join(sfx_dir, "orado_combo_powerup.wav")
    combo_samples = []
    for idx_n, freq in enumerate([587.33, 783.99, 987.77, 1174.66, 1567.98]):
        dur = 0.075 if idx_n < 4 else 0.24
        for i in range(int(sr * dur)):
            t = i / sr
            att = min(1.0, t / 0.008)
            env = att * math.exp(-t * (11.0 if idx_n < 4 else 5.5))
            combo_samples.append(int((math.sin(2 * math.pi * freq * t) * 0.7 + math.sin(2 * math.pi * freq * 2 * t) * 0.3) * env * 26500))
    _write_wav(combo_path, combo_samples, sr)

    cekih_path = os.path.join(sfx_dir, "orado_cekih_heartbeat.wav")
    cekih_samples = []
    for i in range(int(sr * 0.55)):
        t = i / sr
        val = 0.0
        if t < 0.16:
            val = math.sin(2 * math.pi * 78.0 * t) * math.exp(-t * 24.0) * 0.95
        elif 0.22 <= t < 0.45:
            dt = t - 0.22
            val = math.sin(2 * math.pi * 64.0 * dt) * math.exp(-dt * 20.0) * 0.85
        cekih_samples.append(int(val * 29000))
    _write_wav(cekih_path, cekih_samples, sr)

    drum_path = os.path.join(sfx_dir, "orado_beradu_drum.wav")
    drum_samples = []
    for i in range(int(sr * 0.65)):
        t = i / sr
        roll_mod = 0.55 + 0.45 * math.sin(2 * math.pi * 24.0 * t)
        crescendo = min(1.0, (t / 0.50) ** 1.4)
        snare = rng.uniform(-1.0, 1.0) * 0.55 * roll_mod * crescendo
        low = math.sin(2 * math.pi * 130.0 * t) * 0.35 * roll_mod * crescendo
        if t > 0.52:
            dt = t - 0.52
            hit = math.sin(2 * math.pi * 92.0 * dt) * math.exp(-dt * 14.0) * 0.95
            drum_samples.append(int(hit * 28000))
        else:
            drum_samples.append(int((snare + low) * 25000))
    _write_wav(drum_path, drum_samples, sr)

    whistle_path = os.path.join(sfx_dir, "orado_whistle_foul.wav")
    whistle_samples = []
    for i in range(int(sr * 0.48)):
        t = i / sr
        trill = 1.0 + 0.035 * math.sin(2 * math.pi * 38.0 * t)
        env = min(1.0, t / 0.015) * (1.0 if t < 0.38 else math.exp(-(t - 0.38) * 18.0))
        w = (math.sin(2 * math.pi * 2750.0 * trill * t) * 0.65 + math.sin(2 * math.pi * 2920.0 * trill * t) * 0.35) * env
        whistle_samples.append(int(w * 25500))
    _write_wav(whistle_path, whistle_samples, sr)

    return {
        "click": click_path,
        "beep": beep_path,
        "shake": shake_path,
        "intro": win_path,
        "sfx_apollo": apollo_path,
        "sfx_7balak": gong_path,
        "sfx_combo": combo_path,
        "sfx_cekih": cekih_path,
        "sfx_beradu": drum_path,
        "sfx_whistle": whistle_path,
    }


def _export_report_file(fname: str, content_str: str) -> str:
    candidate_dirs = [
        "/storage/emulated/0/Download",
        "/storage/emulated/0/Documents",
        os.path.join(os.path.expanduser("~"), "Download"),
        os.path.join(os.path.expanduser("~"), "Documents", "BeritaAcara_ORADO"),
        tempfile.gettempdir(),
    ]
    for d in candidate_dirs:
        try:
            if not d:
                continue
            os.makedirs(d, exist_ok=True)
            full_p = os.path.join(d, fname)
            with open(full_p, "w", encoding="utf-8") as f:
                f.write(content_str)
            return full_p
        except Exception:
            continue
    raise OSError("Tidak dapat menulis file ke penyimpanan perangkat.")


def main(page: ft.Page):
    page.title = "ORADO Domino 101 — Mobile Referee"
    page.bgcolor = BG_DARK
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    state = {
        "table_no": "MEJA 01",
        "stage_name": "PENYISIHAN",
        "team_a": "TIM MERAH",
        "team_b": "TIM BIRU",
        "players_a": "",
        "players_b": "",
        "match_format": "BO3",
        "swap_sides": False,
        "score_a": 0,
        "score_b": 0,
        "sets_a": 0,
        "sets_b": 0,
        "set_num": 1,
        "round_num": 1,
        "opener_team": "A",
        "awaiting_next_set": False,
        "minor_a": 0,
        "minor_b": 0,
        "major_a": 0,
        "major_b": 0,
        "selected_team": "A",
        "bonus_mode": "1x",
        "sound_mode": "all",
        "sound_on": True,
        "dispute_active": False,
        "dispute_info": "",
        "set_records": [],
        "history": [],
        "referee_notes": [],
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

    timer_state = {
        "seconds": TURN_LIMIT_SECONDS,
        "running": False,
        "task_started": False,
    }

    typing_active = [False]
    is_landscape_mode = [False]
    saved_matches: list[dict] = []

    STORAGE_KEY = "orado_domino_101_mobile_state_v1"
    ARCHIVE_KEY = "orado_domino_101_mobile_archive_v1"

    def get_target_sets() -> int:
        return 3 if state.get("match_format") == "BO5" else 2

    def get_opening_balak(round_num: int) -> str:
        idx = (max(1, round_num) - 1) % 7
        return f"Balak {idx}-{idx}"

    def normalize_match_bounds():
        target = get_target_sets()
        if state.get("match_finished"):
            state["sets_a"] = min(state.get("sets_a", 0), target)
            state["sets_b"] = min(state.get("sets_b", 0), target)
            if state["sets_a"] >= target and state["sets_b"] >= target:
                state["sets_b"] = target - 1
            elif state["sets_a"] >= target:
                state["sets_b"] = min(state["sets_b"], target - 1)
            elif state["sets_b"] >= target:
                state["sets_a"] = min(state["sets_a"], target - 1)
            state["awaiting_next_set"] = False
        else:
            state["sets_a"] = min(state.get("sets_a", 0), target - 1)
            state["sets_b"] = min(state.get("sets_b", 0), target - 1)

    def load_state():
        try:
            cs = getattr(page, "client_storage", None)
            if not cs:
                return
            saved = cs.get(STORAGE_KEY)
            if isinstance(saved, dict):
                state.update(saved)
            arch = cs.get(ARCHIVE_KEY)
            if isinstance(arch, list):
                saved_matches.clear()
                saved_matches.extend(arch)
        except Exception:
            pass
        normalize_match_bounds()

    def save_state():
        normalize_match_bounds()
        try:
            cs = getattr(page, "client_storage", None)
            if cs:
                cs.set(STORAGE_KEY, state)
        except Exception:
            pass

    def save_archive():
        try:
            cs = getattr(page, "client_storage", None)
            if cs:
                cs.set(ARCHIVE_KEY, saved_matches[:30])
        except Exception:
            pass

    def bind_typing_guard(tf: ft.TextField):
        orig_focus = tf.on_focus
        orig_blur = tf.on_blur

        def _on_focus(ev):
            typing_active[0] = True
            if orig_focus:
                orig_focus(ev)

        def _on_blur(ev):
            typing_active[0] = False
            if orig_blur:
                orig_blur(ev)

        tf.on_focus = _on_focus
        tf.on_blur = _on_blur
        return tf

    def is_match_locked() -> bool:
        return (
            state.get("referee_decision") == "setuju"
            and state.get("red_decision") == "setuju"
            and state.get("blue_decision") == "setuju"
        )

    def check_locked_guard() -> bool:
        if is_match_locked():
            play_sfx("sfx_whistle")
            show_toast("🔒 Hasil sudah SAH (3/3 Setuju) & terkunci! Klik 'Match Baru (0-0)'.")
            return True
        if state.get("match_finished"):
            play_sfx("sfx_whistle")
            show_toast("🏆 Pertandingan sudah selesai! Silakan konfirmasi TTD atau 'Match Baru (0-0)'.")
            return True
        return False

    def check_awaiting_next_set_guard() -> bool:
        if state.get("awaiting_next_set"):
            play_sfx("click")
            show_toast(f"⏸ Menunggu wasit klik '▶ Mulai Set {state['set_num']}'.")
            return True
        return False

    def reset_approval_flags():
        state["match_finished"] = False
        state["awaiting_next_set"] = False
        state["referee_decision"] = ""
        state["red_decision"] = ""
        state["blue_decision"] = ""
        state["referee_reject_reason"] = ""
        state["red_reject_reason"] = ""
        state["blue_reject_reason"] = ""
        state["approve_referee_time"] = ""
        state["approve_red_time"] = ""
        state["approve_blue_time"] = ""

    audio_players = {}

    def init_audio_players():
        AudioClass = getattr(fta, "Audio", None) if fta else None
        ReleaseMode = getattr(fta, "ReleaseMode", None) if fta else None
        if not AudioClass:
            return

        def _attach_audio(key: str, src_path: str):
            try:
                kwargs = {
                    "src": src_path,
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
                audio_players[key] = player
            except Exception:
                pass

        chime_paths = build_chime_sfx()
        for sound_key, wav_path in chime_paths.items():
            if os.path.exists(wav_path):
                _attach_audio(sound_key, wav_path)

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
            "v_waktu_habis": "voice_waktu_habis.mp3",
            "v_wo": "voice_wo.mp3",
        }
        for v_key, asset_name in voice_assets.items():
            _attach_audio(v_key, asset_name)

    async def _play_sound_async(player):
        try:
            res_play = player.play()
            if hasattr(res_play, "__await__"):
                await res_play
        except Exception:
            pass

    async def _play_combo_sequence_async(sfx_player, voice_player, delay_sec: float):
        try:
            if sfx_player:
                r1 = sfx_player.play()
                if hasattr(r1, "__await__"):
                    await r1
                await asyncio.sleep(delay_sec)
            if voice_player:
                r2 = voice_player.play()
                if hasattr(r2, "__await__"):
                    await r2
        except Exception:
            pass

    def play_sfx(kind: str = "click"):
        mode = state.get("sound_mode", "all")
        if mode == "mute":
            return
        is_voice = kind.startswith("v_")
        if mode == "voice" and not is_voice and kind != "beep":
            return
        player = audio_players.get(kind) or (audio_players.get("click") if not is_voice else None)
        if not player:
            return
        try:
            if hasattr(page, "run_task"):
                page.run_task(_play_sound_async, player)
            else:
                player.play()
        except Exception:
            pass

    def play_festive_with_voice(sfx_key: str, voice_key: str, delay_sec: float = 1.05):
        mode = state.get("sound_mode", "all")
        if mode == "mute":
            return
        if mode == "voice":
            play_sfx(voice_key)
            return
        sfx_player = audio_players.get(sfx_key)
        voice_player = audio_players.get(voice_key)
        try:
            if hasattr(page, "run_task"):
                page.run_task(_play_combo_sequence_async, sfx_player, voice_player, delay_sec)
            else:
                if sfx_player:
                    sfx_player.play()
                elif voice_player:
                    voice_player.play()
        except Exception:
            pass

    def open_dialog(dlg: ft.AlertDialog):
        typing_active[0] = False
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
        typing_active[0] = False
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

    def show_toast(msg: str, duration_ms: int = 3200):
        try:
            sb = ft.SnackBar(content=ft.Text(msg, color=TEXT_PRIMARY, size=12), bgcolor=CARD_ACTIVE, duration=duration_ms)
            if hasattr(page, "show_snack_bar"):
                page.show_snack_bar(sb)
            else:
                page.snack_bar = sb
                sb.open = True
                page.update()
        except Exception:
            pass

    def announce_balak_opener(prefix_note: str = ""):
        balak_label = get_opening_balak(state["round_num"])
        holder_name = state["team_a"] if state.get("opener_team", "A") == "A" else state["team_b"]
        msg = f"🀄 Silakan yang punya {balak_label} ({holder_name}) agar diturunkan batunya!"
        if prefix_note:
            msg = f"{prefix_note} • {msg}"
        show_toast(msg, duration_ms=4200)

    async def _copy_clipboard_async(txt: str):
        try:
            if hasattr(page, "set_clipboard"):
                res = page.set_clipboard(txt)
                if hasattr(res, "__await__"):
                    await res
            elif hasattr(page, "clipboard") and hasattr(page.clipboard, "set"):
                res = page.clipboard.set(txt)
                if hasattr(res, "__await__"):
                    await res
        except Exception:
            pass

    def copy_to_clipboard(txt: str):
        try:
            if hasattr(page, "run_task"):
                page.run_task(_copy_clipboard_async, txt)
            elif hasattr(page, "set_clipboard"):
                page.set_clipboard(txt)
        except Exception:
            pass

    def open_rules_dialog(e):
        play_sfx("click")
        rules_items = [
            ("Pasal 1b • Pergantian Pemain", "Pergantian pemain cadangan hanya sah dilakukan di antara pergantian Set dan wajib dicatat wasit."),
            ("Pasal 7b • Tukar Tempat Duduk", "Tim dapat meminta tukar posisi duduk pada pergantian Set atas persetujuan wasit."),
            ("Pasal 8c • Shuffle Ulang (5 / 6 Balak)", "Jika pemain memegang 5 atau 6 kartu balak saat pembagian awal, berhak mengajukan kocok ulang sebelum batu pertama turun."),
            ("Pasal 8e • 7 Balak / 1 Seri Lengkap", "Pemain yang memegang 7 balak lengkap langsung memenangkan Set dengan skor digenapkan ke 101 (+1 Set normal; TIDAK berlaku bonus Apollo)."),
            ("Pasal 10 & 14 • Pelanggaran Ringan & Berat", "• Ringan (2x = 1 Berat / +11 ke lawan): Batu jatuh/terbuka, kode/bicara ke partner, salah susun.\n• Berat (+11 ke lawan): Melewati batas waktu 30 detik.\n• Berat (+25 ke lawan): Salah buang batu / mendahului giliran.\n• Akumulasi 3x Pelanggaran Berat = DISKUALIFIKASI (Lawan Menang Match)."),
            ("Pasal 10e.2 • Pass Palsu (Sisa Batu)", "• Sisa ≥ 4 batu: Penalti +50 poin untuk lawan & ronde berakhir.\n• Sisa ≤ 3 batu: Lawan langsung menang Set (skor <51 digenapkan 101, atau skor ≥51 ditambah +75)."),
            ("Pasal 11 • Format Pertandingan", "Babak penyisihan menggunakan sistem Best of 3 (BO3 / 2 Set menang), babak Final menggunakan Best of 5 (BO5 / 3 Set menang)."),
            ("Pasal 12d • Kemenangan APOLLO (+2 Set)", "Berlaku HANYA jika sebuah tim mencapai 101+ poin sementara skor lawan masih 0 (dan bukan dari 7 Balak / Ronde 1), sehingga tim pemenang memperoleh +2 Set sekaligus."),
            ("Aturan Batu Beradu (Gaple / Macet)", "• Menang Adu: Semua sisa mata (sendiri + lawan) menjadi poin pemenang.\n• Kalah Adu: Semua sisa mata (sendiri + lawan) dikali 2 untuk lawan.\n• Seri Adu: Semua sisa mata diberikan kepada lawan."),
        ]

        rules_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=340)
        for title_r, desc_r in rules_items:
            rules_col.controls.append(
                ft.Container(
                    padding=10,
                    border_radius=8,
                    bgcolor=BG_DARK,
                    border=border_all(1, BORDER_COLOR),
                    content=ft.Column(
                        spacing=3,
                        controls=[
                            ft.Text(title_r, size=12, weight=ft.FontWeight.BOLD, color=GOLD),
                            ft.Text(desc_r, size=11, color=TEXT_PRIMARY),
                        ],
                    ),
                )
            )

        rules_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("📖 Pasal Resmi ORADO", color=GOLD, weight=ft.FontWeight.BOLD, size=15),
            content=rules_col,
            actions=[
                make_button("Tutup", EMERALD, BG_DARK, lambda ev: close_dialog(rules_dlg)),
            ],
        )
        open_dialog(rules_dlg)

    dispute_banner_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY, expand=True)
    dispute_banner = ft.Container(
        visible=state.get("dispute_active", False),
        padding=pad_sym(10, 6),
        bgcolor="#451218",
        border=border_all(1, RED_ALERT),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=8,
            controls=[
                dispute_banner_text,
                make_button("✓ Selesai", EMERALD, BG_DARK, None, height=34),
            ],
        ),
    )

    def resolve_dispute(e):
        now_hms = datetime.now().strftime("%H:%M:%S")
        prev_info = state.get("dispute_info", "Sengketa")
        state["dispute_active"] = False
        state["dispute_info"] = ""
        timer_state["running"] = False
        note_str = f"[{now_hms} • Set {state['set_num']} R{state['round_num']}] SENGKETA SELESAI ({prev_info}) — Laga dilanjutkan"
        state.setdefault("referee_notes", []).insert(0, note_str)
        play_sfx("click")
        save_state()
        refresh_ui()
        show_toast("Sengketa ditutup & dicatat ke kronologi.")

    dispute_banner.content.controls[1].on_click = resolve_dispute

    def open_dispute_dialog(e):
        if state.get("dispute_active"):
            resolve_dispute(e)
            return
        play_sfx("sfx_whistle")
        timer_state["running"] = False
        update_timer_ui()

        protester_choice = [state["selected_team"]]
        btn_p_a = make_button(
            f"Merah ({state['team_a']})",
            RED_ALERT if protester_choice[0] == "A" else CARD_ACTIVE,
            TEXT_PRIMARY,
            None,
            expand=True,
            height=42,
        )
        btn_p_b = make_button(
            f"Biru ({state['team_b']})",
            BLUE_TEAM if protester_choice[0] == "B" else CARD_ACTIVE,
            TEXT_PRIMARY,
            None,
            expand=True,
            height=42,
        )
        tf_dispute_reason = bind_typing_guard(
            ft.TextField(
                label="Pokok Keberatan / Protes Tim",
                hint_text="Contoh: Protes batu jatuh / giliran",
                border_color=RED_ALERT,
                focused_border_color=GOLD,
            )
        )

        def pick_protester(tc: str):
            play_sfx("click")
            protester_choice[0] = tc
            btn_p_a.bgcolor = RED_ALERT if tc == "A" else CARD_ACTIVE
            btn_p_b.bgcolor = BLUE_TEAM if tc == "B" else CARD_ACTIVE
            page.update()

        btn_p_a.on_click = lambda ev: pick_protester("A")
        btn_p_b.on_click = lambda ev: pick_protester("B")

        def activate_dispute(ev):
            p_name = state["team_a"] if protester_choice[0] == "A" else state["team_b"]
            reason_txt = (tf_dispute_reason.value or "Keberatan Teknis Lapangan").strip()
            now_hms = datetime.now().strftime("%H:%M:%S")
            info_full = f"Pemohon: {p_name} • {reason_txt} (Pukul {now_hms})"
            timer_state["running"] = False
            state["dispute_active"] = True
            state["dispute_info"] = info_full
            stamp = f"[{now_hms} • Set {state['set_num']} R{state['round_num']}] ⚖️ PROTES / PENDING: {p_name} — {reason_txt}"
            state.setdefault("referee_notes", []).insert(0, stamp)
            record_snapshot(protester_choice[0], "PENDING", f"PROTES / SENGKETA ({p_name}): {reason_txt}", "Timer Dikunci")
            save_state()
            close_dialog(disp_dlg)
            refresh_ui()
            show_toast(f"⚖️ PENDING SENGKETA ({p_name}). Timer dikunci.")

        disp_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("⚖️ Pending / Catat Protes", color=RED_ALERT, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Column(
                tight=True,
                spacing=10,
                controls=[
                    ft.Text("Timer 30 detik dikunci selama status sengketa aktif.", size=11, color=TEXT_MUTED),
                    ft.Row(spacing=8, controls=[btn_p_a, btn_p_b]),
                    tf_dispute_reason,
                ],
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(disp_dlg)),
                make_button("Aktifkan Pending", RED_ALERT, TEXT_PRIMARY, activate_dispute),
            ],
        )
        open_dialog(disp_dlg)

    embedded_logo_path = extract_embedded_logo()
    if embedded_logo_path:
        logo_widget = ft.Image(src=embedded_logo_path, width=32, height=32)
    elif os.path.exists(os.path.join("assets", "logo_orado_ok.png")):
        logo_widget = ft.Image(src="logo_orado_ok.png", width=32, height=32)
    else:
        logo_widget = ft.Container(
            content=ft.Text("OR", weight=ft.FontWeight.BOLD, size=13, color=BG_DARK),
            bgcolor=GOLD,
            width=32,
            height=32,
            border_radius=8,
            alignment=align_center(),
        )

    match_meta_badge = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=GOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    round_balak_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=EMERALD)
    opener_badge_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY, max_lines=1)

    team_a_name_text = ft.Text(
        state["team_a"],
        size=16,
        weight=ft.FontWeight.BOLD,
        color=TEXT_PRIMARY,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        text_align=ft.TextAlign.CENTER,
    )
    team_b_name_text = ft.Text(
        state["team_b"],
        size=16,
        weight=ft.FontWeight.BOLD,
        color=TEXT_PRIMARY,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        text_align=ft.TextAlign.CENTER,
    )
    players_a_subtext = ft.Text("", size=11, color=TEXT_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER)
    players_b_subtext = ft.Text("", size=11, color=TEXT_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, text_align=ft.TextAlign.CENTER)

    score_a_text = ft.Text(
        str(state["score_a"]),
        size=56,
        weight=ft.FontWeight.BOLD,
        color=TEXT_PRIMARY,
        max_lines=1,
        no_wrap=True,
        text_align=ft.TextAlign.CENTER,
    )
    score_b_text = ft.Text(
        str(state["score_b"]),
        size=56,
        weight=ft.FontWeight.BOLD,
        color=TEXT_PRIMARY,
        max_lines=1,
        no_wrap=True,
        text_align=ft.TextAlign.CENTER,
    )

    score_a_box = ft.Container(
        padding=pad_sym(8, 8),
        border_radius=12,
        bgcolor=BG_DARK,
        border=border_all(1, BORDER_COLOR),
        alignment=align_center(),
        content=score_a_text,
    )

    score_b_box = ft.Container(
        padding=pad_sym(8, 8),
        border_radius=12,
        bgcolor=BG_DARK,
        border=border_all(1, BORDER_COLOR),
        alignment=align_center(),
        content=score_b_text,
    )

    status_a_text = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)
    status_b_text = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=TEXT_MUTED, text_align=ft.TextAlign.CENTER)

    foul_a_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=AMBER, text_align=ft.TextAlign.CENTER)
    foul_b_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=AMBER, text_align=ft.TextAlign.CENTER)

    sound_mode_btn = make_button("🔊 Meriah", CARD_ACTIVE, EMERALD, None, expand=True, height=34, font_size=11)
    dispute_header_btn = make_button("⚖️ Protes", CARD_ACTIVE, AMBER, open_dispute_dialog, expand=True, height=34, font_size=11)
    rules_header_btn = make_button("📖 Pasal", CARD_ACTIVE, TEXT_PRIMARY, open_rules_dialog, expand=True, height=34, font_size=11)

    def cycle_sound_mode(e):
        cur = state.get("sound_mode", "all")
        if cur == "all":
            state["sound_mode"] = "voice"
            state["sound_on"] = True
            show_toast("Mode Audio: Suara Wasit Saja")
        elif cur == "voice":
            state["sound_mode"] = "mute"
            state["sound_on"] = False
            show_toast("Mode Audio: Hening / Mute")
        else:
            state["sound_mode"] = "all"
            state["sound_on"] = True
            play_sfx("sfx_combo")
            show_toast("Mode Audio: Efek Meriah + Suara Wasit")
        save_state()
        refresh_ui()

    sound_mode_btn.on_click = cycle_sound_mode

    timer_display_text = ft.Text("30s", size=24, weight=ft.FontWeight.BOLD, color=EMERALD)
    timer_status_text = ft.Text("Siap • 30 Detik", size=10, color=TEXT_MUTED)
    btn_timer_next = make_button("▶ Mulai 30s", EMERALD, BG_DARK, None, expand=True, height=40, font_size=11)
    btn_timer_pause = make_button("⏸", CARD_ACTIVE, GOLD, None, height=40, font_size=12)
    btn_timer_stop = make_button("⏹", CARD_ACTIVE, TEXT_PRIMARY, None, height=40, font_size=12)
    btn_timer_pen11 = make_button("+11 Habis", "#3B181E", RED_ALERT, None, height=40, font_size=11)

    def reset_turn_timer(silent: bool = False):
        timer_state["running"] = False
        timer_state["seconds"] = TURN_LIMIT_SECONDS
        if not silent:
            play_sfx("click")
        update_timer_ui()

    def update_timer_ui():
        sec = timer_state["seconds"]
        running = timer_state["running"]
        timer_display_text.value = f"{sec:02d}s"

        if state.get("dispute_active"):
            timer_display_text.color = RED_ALERT
            timer_status_text.value = "⚖️ DIKUNCI (Sengketa Aktif)"
            timer_status_text.color = RED_ALERT
            set_button_label(btn_timer_next, "🔒 Pending")
            btn_timer_next.bgcolor = CARD_ACTIVE
            btn_timer_next.color = RED_ALERT
            return

        if state.get("awaiting_next_set"):
            timer_display_text.color = GOLD
            timer_status_text.value = f"⏸ Klik Mulai Set {state['set_num']}"
            timer_status_text.color = GOLD
            set_button_label(btn_timer_next, f"▶ Mulai Set {state['set_num']}")
            btn_timer_next.bgcolor = GOLD
            btn_timer_next.color = BG_DARK
            return

        if sec == 0:
            timer_display_text.color = RED_ALERT
            timer_status_text.value = "⏰ HABIS! (+11 ke Lawan)"
            timer_status_text.color = RED_ALERT
            set_button_label(btn_timer_next, "⏭ Giliran Baru")
            btn_timer_next.bgcolor = EMERALD
            btn_timer_next.color = BG_DARK
        elif sec <= 5:
            timer_display_text.color = RED_ALERT
            timer_status_text.value = "⚠️ 5 DETIK TERAKHIR!"
            timer_status_text.color = RED_ALERT
            set_button_label(btn_timer_next, "⏭ Ganti (30s)")
            btn_timer_next.bgcolor = AMBER
            btn_timer_next.color = BG_DARK
        elif running:
            timer_display_text.color = GOLD
            timer_status_text.value = "⏳ Timer 30s berjalan"
            timer_status_text.color = GOLD
            set_button_label(btn_timer_next, "⏭ Ganti (30s)")
            btn_timer_next.bgcolor = GOLD
            btn_timer_next.color = BG_DARK
        else:
            timer_display_text.color = EMERALD
            timer_status_text.value = "Dijeda" if sec < TURN_LIMIT_SECONDS else "Siap • 30 Detik"
            timer_status_text.color = AMBER if sec < TURN_LIMIT_SECONDS else TEXT_MUTED
            set_button_label(btn_timer_next, "▶ Lanjut" if sec < TURN_LIMIT_SECONDS else "▶ Mulai 30s")
            btn_timer_next.bgcolor = EMERALD
            btn_timer_next.color = BG_DARK

    async def timer_background_loop():
        while True:
            await asyncio.sleep(1.0)
            if state.get("dispute_active") or state.get("awaiting_next_set") or state.get("match_finished"):
                if timer_state["running"]:
                    timer_state["running"] = False
                    update_timer_ui()
                    try:
                        page.update()
                    except Exception:
                        pass
                continue
            if timer_state["running"] and timer_state["seconds"] > 0:
                timer_state["seconds"] -= 1
                sec_now = timer_state["seconds"]
                if 1 <= sec_now <= 5:
                    play_sfx("beep")
                elif sec_now == 0:
                    timer_state["running"] = False
                    play_festive_with_voice("sfx_whistle", "v_waktu_habis", delay_sec=0.55)
                    show_toast("⏰ Waktu 30 detik habis! Klik '+11 Habis' bila terlambat jalan.")
                update_timer_ui()
                try:
                    page.update()
                except Exception:
                    pass

    def ensure_timer_loop():
        if not timer_state["task_started"] and hasattr(page, "run_task"):
            timer_state["task_started"] = True
            page.run_task(timer_background_loop)

    def start_awaited_set(e=None):
        if is_match_locked():
            check_locked_guard()
            return
        if not state.get("awaiting_next_set"):
            return
        state["awaiting_next_set"] = False
        state["round_num"] = 1
        reset_turn_timer(silent=True)
        play_sfx("click")
        save_state()
        refresh_ui()
        announce_balak_opener(f"Set {state['set_num']} Dimulai")

    def handle_timer_next_turn(e=None):
        if state.get("dispute_active"):
            timer_state["running"] = False
            play_sfx("sfx_whistle")
            update_timer_ui()
            page.update()
            show_toast("⚖️ Timer dikunci karena PENDING SENGKETA aktif!")
            return
        if state.get("awaiting_next_set"):
            start_awaited_set(e)
            return
        if state.get("match_finished"):
            show_toast("🏆 Pertandingan sudah selesai.")
            return
        ensure_timer_loop()
        if not timer_state["running"] and 0 < timer_state["seconds"] < TURN_LIMIT_SECONDS:
            timer_state["running"] = True
        else:
            timer_state["seconds"] = TURN_LIMIT_SECONDS
            timer_state["running"] = True
        play_sfx("click")
        update_timer_ui()
        page.update()

    def handle_timer_pause(e):
        if timer_state["running"]:
            timer_state["running"] = False
            play_sfx("click")
            update_timer_ui()
            page.update()

    btn_timer_next.on_click = handle_timer_next_turn
    btn_timer_pause.on_click = handle_timer_pause
    btn_timer_stop.on_click = lambda e: (reset_turn_timer(silent=False), page.update())

    manual_score_input = bind_typing_guard(
        ft.TextField(
            label="Poin Sisa Batu",
            hint_text="Contoh: 18",
            border_color=BORDER_COLOR,
            focused_border_color=GOLD,
        )
    )

    ref_note_input = bind_typing_guard(
        ft.TextField(
            label="Catatan Wasit",
            hint_text="Contoh: Shuffle ulang 5 balak",
            border_color=BORDER_COLOR,
            focused_border_color=GOLD,
        )
    )

    set_records_column = ft.Column(spacing=4)
    ref_notes_column = ft.Column(spacing=5)
    history_column = ft.Column(spacing=5)
    archive_btn_label = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=GOLD, text_align=ft.TextAlign.CENTER)

    next_set_banner_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=GOLD, expand=True)
    btn_start_next_set_banner = make_button("▶ Mulai Set", EMERALD, BG_DARK, start_awaited_set, height=36, font_size=11)
    next_set_banner = ft.Container(
        visible=state.get("awaiting_next_set", False),
        padding=pad_sym(10, 8),
        border_radius=12,
        bgcolor="#251F10",
        border=border_all(1, GOLD),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=8,
            controls=[
                next_set_banner_text,
                btn_start_next_set_banner,
            ],
        ),
    )

    approval_summary_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED)
    approval_status_banner = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=AMBER)

    def on_approval_text_change(field_key: str):
        def _handler(e):
            state[field_key] = e.control.value or ""
            save_state()
        return _handler

    ref_name_field = bind_typing_guard(
        ft.TextField(
            label="Nama Wasit",
            hint_text="Isi nama wasit",
            value=state.get("referee_name", ""),
            border_color=BORDER_COLOR,
            focused_border_color=GOLD,
            on_change=on_approval_text_change("referee_name"),
        )
    )

    red_rep_field = bind_typing_guard(
        ft.TextField(
            label="Perwakilan Tim Merah",
            hint_text="Kapten / Pemain Merah",
            value=state.get("red_rep_name", ""),
            border_color=BORDER_COLOR,
            focused_border_color=RED_ALERT,
            on_change=on_approval_text_change("red_rep_name"),
        )
    )

    blue_rep_field = bind_typing_guard(
        ft.TextField(
            label="Perwakilan Tim Biru",
            hint_text="Kapten / Pemain Biru",
            value=state.get("blue_rep_name", ""),
            border_color=BORDER_COLOR,
            focused_border_color=BLUE_TEAM,
            on_change=on_approval_text_change("blue_rep_name"),
        )
    )

    ref_reject_reason_field = bind_typing_guard(
        ft.TextField(
            label="Alasan Wasit Tidak Setuju",
            hint_text="Tuliskan alasan keberatan wasit...",
            value=state.get("referee_reject_reason", ""),
            multiline=True,
            min_lines=1,
            max_lines=2,
            border_color=RED_ALERT,
            focused_border_color=GOLD,
            visible=(state.get("referee_decision") == "tidak_setuju"),
            on_change=on_approval_text_change("referee_reject_reason"),
        )
    )

    red_reject_reason_field = bind_typing_guard(
        ft.TextField(
            label="Alasan Tim Merah Tidak Setuju",
            hint_text="Tuliskan alasan keberatan Tim Merah...",
            value=state.get("red_reject_reason", ""),
            multiline=True,
            min_lines=1,
            max_lines=2,
            border_color=RED_ALERT,
            focused_border_color=GOLD,
            visible=(state.get("red_decision") == "tidak_setuju"),
            on_change=on_approval_text_change("red_reject_reason"),
        )
    )

    blue_reject_reason_field = bind_typing_guard(
        ft.TextField(
            label="Alasan Tim Biru Tidak Setuju",
            hint_text="Tuliskan alasan keberatan Tim Biru...",
            value=state.get("blue_reject_reason", ""),
            multiline=True,
            min_lines=1,
            max_lines=2,
            border_color=RED_ALERT,
            focused_border_color=GOLD,
            visible=(state.get("blue_decision") == "tidak_setuju"),
            on_change=on_approval_text_change("blue_reject_reason"),
        )
    )

    ref_approve_subtext = ft.Text("", size=10, color=TEXT_MUTED)
    red_approve_subtext = ft.Text("", size=10, color=TEXT_MUTED)
    blue_approve_subtext = ft.Text("", size=10, color=TEXT_MUTED)

    red_team_label_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=RED_ALERT)
    blue_team_label_text = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=BLUE_TEAM)

    btn_approve_ref = make_button("Setujui", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38, font_size=11)
    btn_reject_ref = make_button("Tidak Setuju", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38, font_size=11)

    btn_approve_red = make_button("Setujui", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38, font_size=11)
    btn_reject_red = make_button("Tidak Setuju", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38, font_size=11)

    btn_approve_blue = make_button("Setujui", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38, font_size=11)
    btn_reject_blue = make_button("Tidak Setuju", CARD_ACTIVE, TEXT_PRIMARY, None, expand=True, height=38, font_size=11)

    def set_party_decision(party: str, choice: str):
        now_str = datetime.now().strftime("%H:%M:%S WIB")
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
                play_sfx("sfx_whistle")
                show_toast(f"{label_party} memilih TIDAK SETUJU. Isi alasan keberatan di kolom merah.")
            else:
                all_ok = (
                    state.get("referee_decision") == "setuju"
                    and state.get("red_decision") == "setuju"
                    and state.get("blue_decision") == "setuju"
                )
                if all_ok:
                    play_sfx("intro")
                    show_toast("🔒 SAH! 3/3 Pihak menyetujui hasil akhir (Skor Terkunci)!")
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

    def switch_opener_team(e):
        if is_match_locked():
            check_locked_guard()
            return
        state["opener_team"] = "B" if state.get("opener_team", "A") == "A" else "A"
        play_sfx("click")
        save_state()
        refresh_ui()
        announce_balak_opener()

    def toggle_swap_sides(e):
        state["swap_sides"] = not state.get("swap_sides", False)
        play_sfx("click")
        save_state()
        refresh_ui()
        show_toast("Posisi visual kartu Tim Merah & Tim Biru ditukar.")

    def get_status_info(score: int):
        sisa = max(0, TARGET_SKOR - score)
        if score >= TARGET_SKOR:
            return "MENANG SET (101+)", EMERALD
        if score >= 85:
            return f"CEKIH! Kurang {sisa}", RED_ALERT
        return f"Kurang {sisa} ke 101", TEXT_MUTED

    def record_snapshot(team: str, points_str: str, label: str, score_transition: str = ""):
        now_hms = datetime.now().strftime("%H:%M:%S")
        state["history"].append({
            "time": now_hms,
            "team": team,
            "points_str": points_str,
            "label": label,
            "transition": score_transition,
            "snap": {
                "score_a": state["score_a"],
                "score_b": state["score_b"],
                "round_num": state["round_num"],
                "opener_team": state.get("opener_team", "A"),
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

    def archive_current_match(status_summary: str = "Disimpan Manual", sets_a_override: int | None = None, sets_b_override: int | None = None):
        target = get_target_sets()
        raw_a = state["sets_a"] if sets_a_override is None else sets_a_override
        raw_b = state["sets_b"] if sets_b_override is None else sets_b_override
        if state.get("match_finished") or sets_a_override is not None or sets_b_override is not None:
            sa = min(raw_a, target)
            sb = min(raw_b, target)
            if sa >= target and sb >= target:
                sb = target - 1
            elif sa >= target:
                sb = min(sb, target - 1)
            elif sb >= target:
                sa = min(sa, target - 1)
        else:
            sa = min(raw_a, target - 1)
            sb = min(raw_b, target - 1)

        entry = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "timestamp": datetime.now().strftime("%d/%m/%Y • %H:%M:%S WIB"),
            "table_no": state.get("table_no", "MEJA 01"),
            "stage_name": state.get("stage_name", "PENYISIHAN"),
            "format": state["match_format"],
            "team_a": state["team_a"],
            "team_b": state["team_b"],
            "players_a": state.get("players_a", ""),
            "players_b": state.get("players_b", ""),
            "sets_a": sa,
            "sets_b": sb,
            "score_a": state["score_a"],
            "score_b": state["score_b"],
            "set_num": state["set_num"],
            "set_records": list(state.get("set_records", [])),
            "status": status_summary,
            "approvals": get_approval_snapshot(),
            "notes": list(state.get("referee_notes", [])),
            "logs": [
                {
                    "time": h.get("time", "-"),
                    "team": state["team_a"] if h["team"] == "A" else state["team_b"],
                    "points_str": h.get("points_str", ""),
                    "label": h.get("label", ""),
                    "transition": h.get("transition", ""),
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
            status_summary=f"Set {state['set_num']} (Set {state['sets_a']}-{state['sets_b']} | Poin {state['score_a']}-{state['score_b']}){sah_note}"
        )
        refresh_ui()
        show_toast("Berita Acara tersimpan ke Arsip HP!")

    def start_fresh_match(e=None):
        typing_active[0] = False
        play_sfx("shake")
        reset_turn_timer(silent=True)
        state["score_a"] = 0
        state["score_b"] = 0
        state["sets_a"] = 0
        state["sets_b"] = 0
        state["set_num"] = 1
        state["round_num"] = 1
        state["opener_team"] = "A"
        state["awaiting_next_set"] = False
        state["minor_a"] = 0
        state["minor_b"] = 0
        state["major_a"] = 0
        state["major_b"] = 0
        state["dispute_active"] = False
        state["dispute_info"] = ""
        state["set_records"] = []
        state["history"] = []
        state["referee_notes"] = []
        reset_approval_flags()
        save_state()
        refresh_ui()
        announce_balak_opener("Match Baru (0-0)")

    def _format_party_decision_line(dec: str, t_str: str, reason_str: str) -> str:
        if dec == "setuju":
            return f"DISETUJUI ({t_str or '-'})"
        if dec == "tidak_setuju":
            alasan_txt = reason_str if reason_str else "(Alasan belum diisi)"
            return f"TIDAK SETUJU ({t_str or '-'}) — Alasan: {alasan_txt}"
        return "Belum dikonfirmasi"

    def open_match_detail_dialog(match_item: dict):
        appr = match_item.get("approvals") or {}
        ref_line = _format_party_decision_line(appr.get("ref_dec", ""), appr.get("ref_time", ""), appr.get("ref_reason", ""))
        red_line = _format_party_decision_line(appr.get("red_dec", ""), appr.get("red_time", ""), appr.get("red_reason", ""))
        blue_line = _format_party_decision_line(appr.get("blue_dec", ""), appr.get("blue_time", ""), appr.get("blue_reason", ""))

        if appr.get("all_approved"):
            pengesahan_status = "SAH & DISETUJUI SEMUA PIHAK (3/3)"
        elif appr.get("any_rejected"):
            pengesahan_status = "TIDAK SAH / ADA PIHAK TIDAK SETUJU"
        else:
            pengesahan_status = "MENUNGGU KONFIRMASI LENGKAP"

        pa_str = f" ({match_item.get('players_a')})" if (match_item.get("players_a") or "").strip() else ""
        pb_str = f" ({match_item.get('players_b')})" if (match_item.get("players_b") or "").strip() else ""

        lines = [
            "BERITA ACARA RESMI ORADO DOMINO 101",
            f"Lokasi/Meja: {match_item.get('table_no', 'MEJA 01')} | Babak: {match_item.get('stage_name', 'PENYISIHAN')} ({match_item.get('format', 'BO3')})",
            f"Waktu Arsip: {match_item.get('timestamp', '-')}",
            f"Tim Merah: {match_item.get('team_a')}{pa_str}",
            f"Tim Biru: {match_item.get('team_b')}{pb_str}",
            f"Skor Set Akhir: {match_item.get('sets_a', 0)} - {match_item.get('sets_b', 0)}",
            f"Skor Poin Set Terakhir: {match_item.get('score_a', 0)} - {match_item.get('score_b', 0)}",
            f"Status: {match_item.get('status', '-')}",
            "",
            "--- REKAP SKOR PER SET ---",
        ]
        s_recs = match_item.get("set_records", [])
        if s_recs:
            for sr_item in s_recs:
                lines.append(
                    f"• Set {sr_item.get('set')}: {match_item.get('team_a')} {sr_item.get('score_a')} - {sr_item.get('score_b')} {match_item.get('team_b')} ({sr_item.get('note', '-')})"
                )
        else:
            lines.append("• (Belum ada rincian set tersimpan)")

        lines.extend([
            "",
            "--- KONFIRMASI TTD HASIL AKHIR ---",
            f"• Wasit ({appr.get('ref_name', 'Wasit')}): {ref_line}",
            f"• Tim Merah ({appr.get('red_name', 'Kapten Merah')}): {red_line}",
            f"• Tim Biru ({appr.get('blue_name', 'Kapten Biru')}): {blue_line}",
            f"Pengesahan: {pengesahan_status}",
            "",
            "--- CATATAN WASIT ---",
        ])
        notes = match_item.get("notes", [])
        if notes:
            lines.extend([f"• {n}" for n in notes])
        else:
            lines.append("• (Tidak ada catatan wasit)")

        lines.append("")
        lines.append("--- KRONOLOGI LOG RONDE & SANKSI (AUDIT TRAIL) ---")
        logs = match_item.get("logs", [])
        if logs:
            for idx, lg in enumerate(logs, start=1):
                t_hms = f"[{lg.get('time')}] " if lg.get("time") else ""
                tr_str = f" | {lg.get('transition')}" if lg.get("transition") else ""
                lines.append(f"{idx}. {t_hms}{lg.get('team')} | {lg.get('label')} ({lg.get('points_str')}){tr_str}")
        else:
            lines.append("• (Belum ada log poin)")

        rekap_text = "\n".join(lines)
        rekap_field = ft.TextField(
            value=rekap_text,
            multiline=True,
            min_lines=8,
            max_lines=14,
            read_only=True,
            border_color=BORDER_COLOR,
        )

        def handle_copy_rekap(ev):
            copy_to_clipboard(rekap_text)
            play_sfx("click")
            show_toast("Berita Acara disalin ke Clipboard!")

        def handle_export_txt(ev):
            try:
                safe_a = "".join(c if c.isalnum() else "_" for c in match_item.get("team_a", "Merah"))
                safe_b = "".join(c if c.isalnum() else "_" for c in match_item.get("team_b", "Biru"))
                fname = f"ORADO_{match_item.get('table_no', 'M01').replace(' ', '')}_{safe_a}_vs_{safe_b}_{match_item.get('id', '')[-6:]}.txt"
                saved_path = _export_report_file(fname, rekap_text)
                play_sfx("click")
                show_toast(f"Tersimpan: {saved_path}", duration_ms=4200)
            except Exception as ex:
                show_toast(f"Gagal ekspor file: {ex}")

        detail_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(f"{match_item.get('team_a')} vs {match_item.get('team_b')}", color=GOLD, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Column(tight=True, spacing=8, controls=[rekap_field]),
            actions=[
                ft.TextButton("Tutup", on_click=lambda ev: close_dialog(detail_dlg)),
                make_button("💾 .txt", CARD_ACTIVE, GOLD, handle_export_txt, font_size=11),
                make_button("📋 Salin", EMERALD, BG_DARK, handle_copy_rekap, font_size=11),
            ],
        )
        open_dialog(detail_dlg)

    def open_archive_dialog(e):
        play_sfx("click")
        archive_list_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=340)

        def rebuild_archive_list():
            archive_list_col.controls.clear()
            if not saved_matches:
                archive_list_col.controls.append(ft.Text("Belum ada riwayat pertandingan tersimpan.", size=12, color=TEXT_MUTED))
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
                        sah_badge = " • ❌ KEBERATAN"
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
                                            ft.Text(f"{m.get('team_a')} vs {m.get('team_b')}", size=13, weight=ft.FontWeight.BOLD, color=GOLD, expand=True),
                                            ft.Text(f"SET {m.get('sets_a', 0)}-{m.get('sets_b', 0)}", size=12, weight=ft.FontWeight.BOLD, color=EMERALD),
                                        ],
                                    ),
                                    ft.Text(f"{m.get('table_no', 'MEJA 01')} • {m.get('timestamp')} ({m.get('format')}){sah_badge}", size=10, color=sub_col),
                                    ft.Text(f"{m.get('status')}", size=11, color=TEXT_MUTED),
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.END,
                                        spacing=4,
                                        controls=[
                                            ft.TextButton("Berita Acara", on_click=make_view(m)),
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
            title=ft.Text(f"Arsip ({len(saved_matches)})", color=GOLD, weight=ft.FontWeight.BOLD, size=15),
            content=archive_list_col,
            actions=[ft.TextButton("Tutup", on_click=lambda ev: close_dialog(arch_dlg))],
        )
        open_dialog(arch_dlg)

    def add_referee_note(text_val: str):
        cleaned = (text_val or "").strip()
        if not cleaned:
            return
        now_hms = datetime.now().strftime("%H:%M:%S")
        stamp = f"[{now_hms} • Set {state['set_num']} R{state['round_num']}] {cleaned}"
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
        if check_locked_guard():
            return
        state["selected_team"] = team_code
        play_sfx("click")
        save_state()
        refresh_ui()

    def set_bonus_mode(mode: str):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        state["bonus_mode"] = mode
        if mode == "2x":
            play_sfx("v_2x")
        elif mode == "+50":
            play_sfx("v_balak50")
        else:
            play_sfx("click")
        refresh_ui()

    def _compute_capped_match_sets(winner_code: str, sets_earned: int) -> tuple[int, int, bool]:
        target_sets = get_target_sets()
        raw_a = state["sets_a"] + (sets_earned if winner_code == "A" else 0)
        raw_b = state["sets_b"] + (sets_earned if winner_code == "B" else 0)
        is_match_over = (raw_a >= target_sets) or (raw_b >= target_sets)
        if is_match_over:
            if winner_code == "A":
                final_a = target_sets
                final_b = min(raw_b, target_sets - 1)
            else:
                final_b = target_sets
                final_a = min(raw_a, target_sets - 1)
        else:
            final_a = min(raw_a, target_sets - 1)
            final_b = min(raw_b, target_sets - 1)
        return final_a, final_b, is_match_over

    def handle_disqualification_victory(winner_code: str, offender_code: str, reason: str):
        play_sfx("sfx_whistle")
        reset_turn_timer(silent=True)
        winner_name = state["team_a"] if winner_code == "A" else state["team_b"]
        offender_name = state["team_a"] if offender_code == "A" else state["team_b"]
        target_sets = get_target_sets()
        projected_sets_a, projected_sets_b, _ = _compute_capped_match_sets(winner_code, target_sets)

        state.setdefault("set_records", []).append({
            "set": state["set_num"],
            "score_a": state["score_a"],
            "score_b": state["score_b"],
            "winner": winner_name,
            "note": f"Diskualifikasi {offender_name} (3x Berat)",
        })

        record_snapshot(
            winner_code,
            "MENANG DQ",
            f"DISKUALIFIKASI: {offender_name} (3x Pelanggaran Berat) → {winner_name} MENANG",
            f"Set {state['sets_a']}-{state['sets_b']} → {projected_sets_a}-{projected_sets_b}",
        )
        now_hms = datetime.now().strftime("%H:%M:%S")
        state.setdefault("referee_notes", []).insert(
            0,
            f"[{now_hms} • Set {state['set_num']} R{state['round_num']}] DISKUALIFIKASI: {offender_name} → {winner_name} Menang",
        )
        save_state()
        refresh_ui()

        def go_to_approval_dq(e):
            play_sfx("click")
            state["sets_a"] = projected_sets_a
            state["sets_b"] = projected_sets_b
            state["match_finished"] = True
            state["awaiting_next_set"] = False
            save_state()
            close_dialog(dq_dlg)
            refresh_ui()
            show_toast(f"{offender_name} DISKUALIFIKASI! Silakan konfirmasi TTD.")

        def save_and_new_dq(e):
            play_sfx("click")
            state["sets_a"] = projected_sets_a
            state["sets_b"] = projected_sets_b
            state["match_finished"] = True
            archive_current_match(
                status_summary=f"Selesai (DISKUALIFIKASI) • Juara: {winner_name} ({projected_sets_a}-{projected_sets_b})",
                sets_a_override=projected_sets_a,
                sets_b_override=projected_sets_b,
            )
            close_dialog(dq_dlg)
            start_fresh_match()
            show_toast(f"Hasil Diskualifikasi ({winner_name} Menang) tersimpan ke Arsip!")

        dq_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(f"🚫 DISKUALIFIKASI! {winner_name} MENANG!", color=RED_ALERT, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text(f"Tim Terdiskualifikasi: {offender_name} (3/3 Berat)", size=12, weight=ft.FontWeight.BOLD, color=RED_ALERT),
                    ft.Text(f"Pemenang: {winner_name} (Set {projected_sets_a} - {projected_sets_b})", size=12, weight=ft.FontWeight.BOLD, color=EMERALD),
                    ft.Text(reason, size=11, color=TEXT_PRIMARY),
                ],
            ),
            actions=[
                ft.TextButton("Simpan & Baru", on_click=save_and_new_dq),
                make_button("Konfirmasi TTD", EMERALD, BG_DARK, go_to_approval_dq, font_size=11),
            ],
        )
        open_dialog(dq_dlg)

    def trigger_wo_victory(e):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        play_festive_with_voice("intro", "v_wo", delay_sec=1.15)
        wo_offender_code = state["selected_team"]
        winner_code = "B" if wo_offender_code == "A" else "A"
        wo_offender_name = state["team_a"] if wo_offender_code == "A" else state["team_b"]
        winner_name = state["team_a"] if winner_code == "A" else state["team_b"]
        target_sets = get_target_sets()
        projected_sets_a, projected_sets_b, _ = _compute_capped_match_sets(winner_code, target_sets)

        def confirm_wo(ev):
            reset_turn_timer(silent=True)
            state.setdefault("set_records", []).append({
                "set": state["set_num"],
                "score_a": state["score_a"],
                "score_b": state["score_b"],
                "winner": winner_name,
                "note": f"Menang WO ({wo_offender_name} WO)",
            })
            record_snapshot(
                winner_code,
                "MENANG WO",
                f"WO ({wo_offender_name}) → {winner_name} MENANG",
                f"Set {state['sets_a']}-{state['sets_b']} → {projected_sets_a}-{projected_sets_b}",
            )
            now_hms = datetime.now().strftime("%H:%M:%S")
            state.setdefault("referee_notes", []).insert(
                0,
                f"[{now_hms} • Set {state['set_num']} R{state['round_num']}] WO: {wo_offender_name} → {winner_name} Menang",
            )
            state["sets_a"] = projected_sets_a
            state["sets_b"] = projected_sets_b
            state["match_finished"] = True
            state["awaiting_next_set"] = False
            save_state()
            close_dialog(wo_dlg)
            refresh_ui()
            show_toast(f"{wo_offender_name} WO → {winner_name} MENANG!")

        wo_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(f"🏳️ WO: {wo_offender_name} → {winner_name}", color=GOLD, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Text(
                f"{wo_offender_name} dinyatakan WO/gugur. Kemenangan diberikan kepada {winner_name} (Set {projected_sets_a} - {projected_sets_b}).",
                color=TEXT_PRIMARY,
                size=12,
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(wo_dlg)),
                make_button(f"Sahkan {winner_name}", GOLD, BG_DARK, confirm_wo, font_size=11),
            ],
        )
        open_dialog(wo_dlg)

    def handle_set_victory(
        winner_code: str,
        win_reason: str,
        allow_apollo: bool = True,
        force_apollo: bool = False,
        is_seven_balak: bool = False,
        play_default_fanfare: bool = True,
    ):
        if state.get("match_finished"):
            return
        reset_turn_timer(silent=True)

        winner_name = state["team_a"] if winner_code == "A" else state["team_b"]
        loser_name = state["team_b"] if winner_code == "A" else state["team_a"]
        winner_score = state["score_a"] if winner_code == "A" else state["score_b"]
        loser_score = state["score_b"] if winner_code == "A" else state["score_a"]

        rounds_completed = len([h for h in state["history"] if "Ronde" in h["label"] or "Pass Palsu" in h["label"]])
        if is_seven_balak:
            is_apollo = False
        elif force_apollo:
            is_apollo = (loser_score == 0)
        else:
            is_apollo = bool(allow_apollo and winner_score >= TARGET_SKOR and loser_score == 0 and rounds_completed > 0)

        if is_apollo and not force_apollo:
            play_festive_with_voice("sfx_apollo", "v_apollo", delay_sec=1.25)
        elif play_default_fanfare:
            play_sfx("intro")

        sets_earned = 2 if is_apollo else 1
        projected_sets_a, projected_sets_b, is_match_over = _compute_capped_match_sets(winner_code, sets_earned)
        completed_set_no = state["set_num"]

        set_summary_rec = {
            "set": completed_set_no,
            "score_a": state["score_a"],
            "score_b": state["score_b"],
            "winner": winner_name,
            "note": "APOLLO (+2 Set)" if is_apollo else win_reason,
        }

        def go_to_approval_bottom(e):
            play_sfx("click")
            state.setdefault("set_records", []).append(set_summary_rec)
            state["sets_a"] = projected_sets_a
            state["sets_b"] = projected_sets_b
            state["match_finished"] = True
            state["awaiting_next_set"] = False
            save_state()
            close_dialog(dlg)
            refresh_ui()
            show_toast("Silakan konfirmasi TTD hasil akhir di bagian Pengesahan TTD.")

        def proceed_next(e):
            play_sfx("click")
            state.setdefault("set_records", []).append(set_summary_rec)
            state["sets_a"] = projected_sets_a
            state["sets_b"] = projected_sets_b
            if is_match_over:
                state["match_finished"] = True
                state["awaiting_next_set"] = False
                archive_current_match(
                    status_summary=f"Selesai • Juara: {winner_name} ({projected_sets_a}-{projected_sets_b})",
                    sets_a_override=projected_sets_a,
                    sets_b_override=projected_sets_b,
                )
                close_dialog(dlg)
                start_fresh_match()
                show_toast(f"Match {winner_name} tersimpan ke Arsip!")
            else:
                next_s = completed_set_no + 1
                state["set_num"] = next_s
                state["score_a"] = 0
                state["score_b"] = 0
                state["round_num"] = 1
                state["awaiting_next_set"] = True
                state["minor_a"] = 0
                state["minor_b"] = 0
                state["major_a"] = 0
                state["major_b"] = 0
                state["history"] = []
                save_state()
                close_dialog(dlg)
                refresh_ui()
                show_toast(f"Set {completed_set_no} selesai. Klik '▶ Mulai Set {next_s}' jika siap.")

        def reset_match_now(e):
            close_dialog(dlg)
            start_fresh_match()

        title_text = (
            f"🏆 {winner_name} JUARA MATCH!"
            if is_match_over
            else (f"🔥 APOLLO! {winner_name} (+2 SET)" if is_apollo else f"🏆 {winner_name} MENANG SET {completed_set_no}!")
        )

        apollo_note = (
            "Bonus APOLLO Aktif (Lawan 0 poin) → +2 Set!"
            if is_apollo
            else f"Perolehan Set: +{sets_earned} Set (Set: {projected_sets_a} - {projected_sets_b})"
        )

        dialog_actions = (
            [
                ft.TextButton("Simpan & Baru", on_click=proceed_next),
                make_button("Konfirmasi TTD", EMERALD, BG_DARK, go_to_approval_bottom, font_size=11),
            ]
            if is_match_over
            else [
                ft.TextButton("Reset 0-0", on_click=reset_match_now),
                make_button(f"Siapkan Set {completed_set_no + 1}", GOLD, BG_DARK, proceed_next, font_size=11),
            ]
        )

        dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(title_text, color=GOLD, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text(f"Keterangan: {win_reason}", size=12, weight=ft.FontWeight.BOLD, color=EMERALD),
                    ft.Text(f"Skor Akhir Set: {winner_name} ({winner_score}) vs {loser_name} ({loser_score})", size=12, color=TEXT_PRIMARY),
                    ft.Text(apollo_note, size=11, weight=ft.FontWeight.BOLD, color=PURPLE_SPECIAL if is_apollo else GOLD),
                ],
            ),
            actions=dialog_actions,
        )
        open_dialog(dlg)

    def add_round_score(base_points: int, custom_breakdown: str = ""):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        if base_points <= 0:
            return
        team = state["selected_team"]
        mode = state["bonus_mode"]
        prev_score = state["score_a"] if team == "A" else state["score_b"]
        detail_suffix = f" [{custom_breakdown}]" if custom_breakdown else ""

        if mode == "2x":
            final_pts = base_points * 2
            label = f"Ronde {state['round_num']} • 2x Ujung/Sama ({base_points}×2){detail_suffix}"
        elif mode == "+50":
            final_pts = base_points + 50
            label = f"Ronde {state['round_num']} • Balak Sempurna ({base_points}+50){detail_suffix}"
        else:
            final_pts = base_points
            label = f"Ronde {state['round_num']} • Normal{detail_suffix}"

        new_score = prev_score + final_pts
        record_snapshot(team, f"+{final_pts}", label, f"Skor: {prev_score} → {new_score}")

        if team == "A":
            state["score_a"] = new_score
        else:
            state["score_b"] = new_score

        state["round_num"] += 1
        state["bonus_mode"] = "1x"
        reset_turn_timer(silent=True)

        reached_victory = new_score >= TARGET_SKOR
        if not reached_victory:
            if mode in ("2x", "+50"):
                play_sfx("sfx_combo")
            elif prev_score < 85 <= new_score:
                play_sfx("sfx_cekih")
                t_cekih = state["team_a"] if team == "A" else state["team_b"]
                show_toast(f"🔥 {t_cekih} masuk zona CEKIH ({new_score} poin)!")
            else:
                play_sfx("click")

        save_state()
        refresh_ui()

        if not reached_victory:
            announce_balak_opener()
        elif state["score_a"] >= TARGET_SKOR:
            handle_set_victory("A", f"Mencapai {state['score_a']} Poin (Domino 101)", allow_apollo=True)
        elif state["score_b"] >= TARGET_SKOR:
            handle_set_victory("B", f"Mencapai {state['score_b']} Poin (Domino 101)", allow_apollo=True)

    def open_tile_calculator_dialog(e):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        play_sfx("click")
        tiles_list: list[int] = []
        winner_name = state["team_a"] if state["selected_team"] == "A" else state["team_b"]

        expr_text = ft.Text("Batu terpilih: (Belum ada)", size=12, color=TEXT_PRIMARY)
        total_calc_text = ft.Text("Total Sisa Mata = 0 Poin", size=16, weight=ft.FontWeight.BOLD, color=GOLD)

        def update_calc_view():
            if not tiles_list:
                expr_text.value = "Batu terpilih: (Belum ada)"
                total_calc_text.value = "Total Sisa Mata = 0 Poin"
            else:
                joined = " + ".join(str(x) for x in tiles_list)
                expr_text.value = f"Rincian Batu: {joined}"
                total_calc_text.value = f"Total Sisa Mata = {sum(tiles_list)} Poin"
            page.update()

        def push_tile_val(val_dot: int):
            def _h(ev):
                play_sfx("click")
                tiles_list.append(val_dot)
                update_calc_view()
            return _h

        def pop_tile_val(ev):
            if tiles_list:
                play_sfx("shake")
                tiles_list.pop()
                update_calc_view()

        def clear_tile_val(ev):
            play_sfx("shake")
            tiles_list.clear()
            update_calc_view()

        def apply_calc_total(ev):
            tot = sum(tiles_list)
            if tot <= 0:
                show_toast("Pilih minimal satu nilai kartu terlebih dahulu!")
                return
            breakdown = "+".join(str(x) for x in tiles_list) + f"={tot}"
            close_dialog(calc_dlg)
            add_round_score(tot, custom_breakdown=f"Batu: {breakdown}")

        grid_rows = []
        for r_i in range(0, 12, 4):
            row_btns = [
                make_button(f"+{v}", CARD_ACTIVE, TEXT_PRIMARY, push_tile_val(v), expand=True, height=40)
                for v in range(r_i + 1, r_i + 5)
            ]
            grid_rows.append(ft.Row(spacing=6, controls=row_btns))

        calc_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(f"🧮 Hitung Batu → {winner_name}", color=GOLD, weight=ft.FontWeight.BOLD, size=14),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    *grid_rows,
                    ft.Row(
                        spacing=6,
                        controls=[
                            make_button("⌫ Hapus", "#2B2416", AMBER, pop_tile_val, expand=True, height=38, font_size=11),
                            make_button("Reset", "#3B181E", RED_ALERT, clear_tile_val, expand=True, height=38, font_size=11),
                        ],
                    ),
                    ft.Container(
                        padding=10,
                        border_radius=8,
                        bgcolor=BG_DARK,
                        border=border_all(1, GOLD),
                        content=ft.Column(spacing=4, controls=[expr_text, total_calc_text]),
                    ),
                ],
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(calc_dlg)),
                make_button("Sahkan Poin", EMERALD, BG_DARK, apply_calc_total, font_size=11),
            ],
        )
        open_dialog(calc_dlg)

    def open_batu_beradu_dialog(e):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        play_festive_with_voice("sfx_beradu", "v_beradu", delay_sec=0.70)
        closer_team = [state.get("selected_team", "A")]

        btn_closer_a = make_button(
            f"Merah ({state['team_a']})",
            RED_ALERT if closer_team[0] == "A" else CARD_ACTIVE,
            TEXT_PRIMARY,
            None,
            expand=True,
            height=40,
            font_size=11,
        )
        btn_closer_b = make_button(
            f"Biru ({state['team_b']})",
            BLUE_TEAM if closer_team[0] == "B" else CARD_ACTIVE,
            TEXT_PRIMARY,
            None,
            expand=True,
            height=40,
            font_size=11,
        )

        tf_sisa_a = bind_typing_guard(
            ft.TextField(
                label=f"Sisa Mata {state['team_a']}",
                hint_text="Contoh: 11",
                border_color=RED_ALERT,
                focused_border_color=GOLD,
            )
        )
        tf_sisa_b = bind_typing_guard(
            ft.TextField(
                label=f"Sisa Mata {state['team_b']}",
                hint_text="Contoh: 24",
                border_color=BLUE_TEAM,
                focused_border_color=GOLD,
            )
        )

        preview_text = ft.Text(
            "Isi sisa mata kedua tim untuk melihat hasil otomatis.",
            size=11,
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
                    f"{closer_name} MENANG Adu ({s_own} < {s_opp}) → +{total_semua} Poin",
                    f"Ronde {state['round_num']} • Beradu Menang (Merah {va} + Biru {vb})",
                    "v_beradu_menang",
                )
            elif s_own > s_opp:
                pts_x2 = total_semua * 2
                return (
                    "kalah",
                    opp_code,
                    opp_name,
                    pts_x2,
                    f"{closer_name} KALAH Adu ({s_own} > {s_opp}) → +{pts_x2} ke {opp_name}",
                    f"Ronde {state['round_num']} • Beradu Kalah (Merah {va} + Biru {vb})×2",
                    "v_beradu_kalah",
                )
            else:
                return (
                    "seri",
                    opp_code,
                    opp_name,
                    total_semua,
                    f"SERI Adu ({va} = {vb}) → +{total_semua} ke {opp_name}",
                    f"Ronde {state['round_num']} • Beradu Seri (Merah {va} + Biru {vb} ke Lawan)",
                    "v_beradu_seri",
                )

        def compute_preview(ev=None):
            raw_a = (tf_sisa_a.value or "").strip()
            raw_b = (tf_sisa_b.value or "").strip()
            if not (raw_a.isdigit() and raw_b.isdigit()):
                preview_text.value = "Isi angka sisa mata kedua tim."
                preview_text.color = TEXT_MUTED
                if ev is not None:
                    page.update()
                return
            va, vb = int(raw_a), int(raw_b)
            if va == 0 and vb == 0:
                preview_text.value = "Total sisa mata tidak boleh 0."
                preview_text.color = RED_ALERT
                if ev is not None:
                    page.update()
                return
            outcome, _, _, _, summary_msg, _, _ = evaluate_beradu(va, vb, closer_team[0])
            preview_text.value = summary_msg
            preview_text.color = EMERALD if outcome == "menang" else (RED_ALERT if outcome == "kalah" else AMBER)
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
            va, vb = int(raw_a), int(raw_b)
            if va == 0 and vb == 0:
                show_toast("Total sisa mata tidak boleh 0!")
                return

            outcome, win_code, win_name, pts, _, log_label, voice_k = evaluate_beradu(va, vb, closer_team[0])
            prev_w = state["score_a"] if win_code == "A" else state["score_b"]
            new_w = prev_w + pts

            record_snapshot(win_code, f"+{pts}", log_label, f"Skor: {prev_w} → {new_w}")
            if win_code == "A":
                state["score_a"] = new_w
            else:
                state["score_b"] = new_w

            state["round_num"] += 1
            state["bonus_mode"] = "1x"
            reset_turn_timer(silent=True)
            reached_victory = new_w >= TARGET_SKOR
            if not reached_victory:
                if outcome in ("menang", "kalah"):
                    play_festive_with_voice("sfx_combo", voice_k, delay_sec=0.58)
                else:
                    play_sfx(voice_k)
            save_state()
            close_dialog(beradu_dlg)
            refresh_ui()

            if not reached_victory:
                announce_balak_opener(f"Batu Beradu: +{pts} ke {win_name}")
            elif state["score_a"] >= TARGET_SKOR:
                handle_set_victory("A", f"Mencapai {state['score_a']} Poin via Batu Beradu", allow_apollo=True, play_default_fanfare=False)
            elif state["score_b"] >= TARGET_SKOR:
                handle_set_victory("B", f"Mencapai {state['score_b']} Poin via Batu Beradu", allow_apollo=True, play_default_fanfare=False)

        beradu_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("⚔️ Batu Beradu", color=GOLD, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    ft.Text("Tim yang Menutup / Membuat Beradu:", size=11, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Row(spacing=6, controls=[btn_closer_a, btn_closer_b]),
                    tf_sisa_a,
                    tf_sisa_b,
                    ft.Container(
                        padding=8,
                        border_radius=8,
                        bgcolor=BG_DARK,
                        border=border_all(1, BORDER_COLOR),
                        content=preview_text,
                    ),
                ],
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(beradu_dlg)),
                make_button("Sahkan", EMERALD, BG_DARK, confirm_batu_beradu, font_size=11),
            ],
        )
        open_dialog(beradu_dlg)

    def apply_penalty(points: int, reason: str, voice_key: str, ends_round: bool = False):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        offender_team = state["selected_team"]
        beneficiary_team = "B" if offender_team == "A" else "A"
        offender_name = state["team_a"] if offender_team == "A" else state["team_b"]
        beneficiary_name = state["team_a"] if beneficiary_team == "A" else state["team_b"]

        prev_b = state["score_a"] if beneficiary_team == "A" else state["score_b"]
        new_b = prev_b + points

        record_snapshot(
            beneficiary_team,
            f"+{points}",
            f"PELANGGARAN {offender_name}: {reason} → Poin ke {beneficiary_name}",
            f"Skor {beneficiary_name}: {prev_b} → {new_b}",
        )

        if offender_team == "A":
            state["major_a"] += 1
            state["score_b"] = new_b
        else:
            state["major_b"] += 1
            state["score_a"] = new_b

        if ends_round:
            state["round_num"] += 1

        reset_turn_timer(silent=True)
        play_festive_with_voice("sfx_whistle", voice_key, delay_sec=0.52)
        save_state()
        refresh_ui()

        offender_majors = state["major_a"] if offender_team == "A" else state["major_b"]
        beneficiary_score = state["score_a"] if beneficiary_team == "A" else state["score_b"]

        if offender_majors >= 3:
            handle_disqualification_victory(beneficiary_team, offender_team, f"Akumulasi 3x Pelanggaran Berat {offender_name} ({reason})")
        elif beneficiary_score >= TARGET_SKOR:
            handle_set_victory(beneficiary_team, f"Mencapai {beneficiary_score} Poin via Penalti {offender_name}", allow_apollo=True, play_default_fanfare=False)
        else:
            if ends_round:
                announce_balak_opener(f"Pelanggaran {offender_name}: +{points} ke {beneficiary_name}")
            else:
                show_toast(f"Pelanggaran {offender_name}: +{points} Poin ke {beneficiary_name}!")

    btn_timer_pen11.on_click = lambda e: apply_penalty(11, "Waktu 30dtk Habis / Terlambat Jalan (+11)", "v_pen11")

    def execute_minor_foul(foul_detail: str):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        offender_team = state["selected_team"]
        beneficiary_team = "B" if offender_team == "A" else "A"
        offender_name = state["team_a"] if offender_team == "A" else state["team_b"]
        beneficiary_name = state["team_a"] if beneficiary_team == "A" else state["team_b"]
        current_minor = state["minor_a"] if offender_team == "A" else state["minor_b"]

        if current_minor + 1 >= 2:
            prev_b = state["score_a"] if beneficiary_team == "A" else state["score_b"]
            new_b = prev_b + 11
            record_snapshot(
                beneficiary_team,
                "+11",
                f"2x Ringan {offender_name} ({foul_detail}) → 1 Berat (+11 ke {beneficiary_name})",
                f"Skor {beneficiary_name}: {prev_b} → {new_b}",
            )
            if offender_team == "A":
                state["minor_a"] = 0
                state["major_a"] += 1
                state["score_b"] = new_b
            else:
                state["minor_b"] = 0
                state["major_b"] += 1
                state["score_a"] = new_b
            play_festive_with_voice("sfx_whistle", "v_pen11", delay_sec=0.52)
            save_state()
            refresh_ui()

            offender_majors = state["major_a"] if offender_team == "A" else state["major_b"]
            beneficiary_score = state["score_a"] if beneficiary_team == "A" else state["score_b"]

            if offender_majors >= 3:
                handle_disqualification_victory(beneficiary_team, offender_team, f"Akumulasi 3x Pelanggaran Berat {offender_name} (2x Ringan)")
            elif beneficiary_score >= TARGET_SKOR:
                handle_set_victory(beneficiary_team, f"Mencapai 101 Poin dari 2x Ringan {offender_name}", allow_apollo=True, play_default_fanfare=False)
            else:
                show_toast(f"2x Ringan {offender_name} → +11 ke {beneficiary_name}!")
        else:
            record_snapshot(offender_team, "WARN 1/2", f"Ringan 1/2 oleh {offender_name} ({foul_detail})", f"Ringan 1/2 ({offender_name})")
            if offender_team == "A":
                state["minor_a"] += 1
            else:
                state["minor_b"] += 1
            play_sfx("v_ringan")
            save_state()
            refresh_ui()
            show_toast(f"Ringan 1/2 dicatat untuk {offender_name}.")

    def open_minor_foul_dialog(e):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        play_sfx("click")
        offender_name = state["team_a"] if state["selected_team"] == "A" else state["team_b"]
        beneficiary_name = state["team_b"] if state["selected_team"] == "A" else state["team_a"]

        def pick_minor(detail_str: str):
            def _h(ev):
                close_dialog(minor_dlg)
                execute_minor_foul(detail_str)
            return _h

        minor_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(f"⚠️ Pelanggar: {offender_name} → {beneficiary_name}", color=AMBER, weight=ft.FontWeight.BOLD, size=14),
            content=ft.Column(
                tight=True,
                spacing=8,
                controls=[
                    make_button("1. Batu Jatuh / Terbuka", "#2B2416", AMBER, pick_minor("Batu Jatuh / Terbuka"), height=42, font_size=11),
                    make_button("2. Bicara / Kode ke Partner", "#2B2416", AMBER, pick_minor("Berbicara / Kode Partner"), height=42, font_size=11),
                    make_button("3. Salah Susun / Ulur Tempo", "#2B2416", AMBER, pick_minor("Salah Susun / Mengulur Waktu"), height=42, font_size=11),
                ],
            ),
            actions=[ft.TextButton("Batal", on_click=lambda ev: close_dialog(minor_dlg))],
        )
        open_dialog(minor_dlg)

    def trigger_apollo_win(e):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        team = state["selected_team"]
        team_name = state["team_a"] if team == "A" else state["team_b"]
        opp_name = state["team_b"] if team == "A" else state["team_a"]
        opp_score = state["score_b"] if team == "A" else state["score_a"]
        prev_w = state["score_a"] if team == "A" else state["score_b"]
        new_w = max(TARGET_SKOR, prev_w)

        if opp_score > 0:
            play_sfx("sfx_whistle")
            show_toast(f"❌ APOLLO ditolak (Pasal 12d): Skor {opp_name} sudah {opp_score} (harus 0 poin)!")
            return

        play_festive_with_voice("sfx_apollo", "v_apollo", delay_sec=1.35)

        def confirm_apollo(ev):
            record_snapshot(team, "APOLLO", "KEMENANGAN APOLLO (+2 SET)", f"Skor: {prev_w} → {new_w} (+2 Set)")
            if team == "A":
                state["score_a"] = new_w
            else:
                state["score_b"] = new_w
            save_state()
            close_dialog(confirm_dlg)
            refresh_ui()
            handle_set_victory(team, "Kemenangan Spesial APOLLO (+2 Set • Lawan 0 Poin)", allow_apollo=True, force_apollo=True, is_seven_balak=False, play_default_fanfare=False)

        confirm_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("🔥 Konfirmasi APOLLO (+2 Set)", color=PURPLE_SPECIAL, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Text(f"Tetapkan {team_name} menang APOLLO (+2 Set)? Skor {opp_name} saat ini 0 poin.", color=TEXT_PRIMARY, size=12),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(confirm_dlg)),
                make_button("Ya, APOLLO!", PURPLE_SPECIAL, TEXT_PRIMARY, confirm_apollo, font_size=11),
            ],
        )
        open_dialog(confirm_dlg)

    def trigger_seven_balak_win(e):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        play_festive_with_voice("sfx_7balak", "v_7balak", delay_sec=1.20)
        team = state["selected_team"]
        team_name = state["team_a"] if team == "A" else state["team_b"]
        prev_w = state["score_a"] if team == "A" else state["score_b"]
        new_w = max(TARGET_SKOR, prev_w)

        def confirm_7balak(ev):
            record_snapshot(team, "→ 101", "7 BALAK / 1 SERI LENGKAP (Pasal 8e • Tanpa Apollo)", f"Skor: {prev_w} → {new_w}")
            if team == "A":
                state["score_a"] = new_w
            else:
                state["score_b"] = new_w
            save_state()
            close_dialog(confirm_dlg)
            refresh_ui()
            handle_set_victory(team, "7 Balak / 1 Seri Lengkap (Skor 101 • Tanpa Bonus Apollo)", allow_apollo=False, force_apollo=False, is_seven_balak=True, play_default_fanfare=False)

        confirm_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("Konfirmasi 7 Balak / 1 Seri", color=GOLD, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Text(f"Tetapkan {team_name} menang Set dengan 7 Balak? Skor 101 (+1 Set normal, tanpa Apollo).", color=TEXT_PRIMARY, size=12),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(confirm_dlg)),
                make_button("Ya, Sah 101!", GOLD, BG_DARK, confirm_7balak, font_size=11),
            ],
        )
        open_dialog(confirm_dlg)

    def trigger_false_pass_under_3(e):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        play_festive_with_voice("sfx_whistle", "v_pass_kalah", delay_sec=0.55)
        offender_team = state["selected_team"]
        beneficiary_team = "B" if offender_team == "A" else "A"
        offender_name = state["team_a"] if offender_team == "A" else state["team_b"]
        beneficiary_name = state["team_a"] if beneficiary_team == "A" else state["team_b"]
        cur_score = state["score_a"] if beneficiary_team == "A" else state["score_b"]

        new_score = TARGET_SKOR if cur_score < 51 else (cur_score + 75)
        rule_desc = "Skor < 51 digenapkan ke 101" if cur_score < 51 else f"Skor {cur_score} + 75 = {new_score}"

        def confirm_fp3(ev):
            record_snapshot(beneficiary_team, f"→ {new_score}", f"Pass Palsu ≤3 Batu oleh {offender_name} → {beneficiary_name} Menang", f"Skor {beneficiary_name}: {cur_score} → {new_score}")
            if offender_team == "A":
                state["major_a"] += 1
                state["score_b"] = new_score
            else:
                state["major_b"] += 1
                state["score_a"] = new_score
            save_state()
            close_dialog(fp_dlg)
            refresh_ui()

            offender_majors = state["major_a"] if offender_team == "A" else state["major_b"]
            if offender_majors >= 3:
                handle_disqualification_victory(beneficiary_team, offender_team, f"Akumulasi 3x Pelanggaran Berat {offender_name} (Pass Palsu ≤ 3)")
            else:
                handle_set_victory(beneficiary_team, f"{offender_name} Pass Palsu ≤3 Batu ({rule_desc})", allow_apollo=True, play_default_fanfare=False)

        fp_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text(f"Pass Palsu ≤ 3 ({offender_name})", color=RED_ALERT, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Text(f"{offender_name} Pass Palsu sisa ≤3 batu? {beneficiary_name} menang Set ({rule_desc}).", color=TEXT_PRIMARY, size=12),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(fp_dlg)),
                make_button("Sahkan", RED_ALERT, TEXT_PRIMARY, confirm_fp3, font_size=11),
            ],
        )
        open_dialog(fp_dlg)

    def undo_last(e=None):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        if not state["history"]:
            return
        last = state["history"].pop()
        snap = last.get("snap")
        if snap:
            state["score_a"] = snap["score_a"]
            state["score_b"] = snap["score_b"]
            state["round_num"] = snap["round_num"]
            state["opener_team"] = snap.get("opener_team", state.get("opener_team", "A"))
            state["minor_a"] = snap["minor_a"]
            state["minor_b"] = snap["minor_b"]
            state["major_a"] = snap["major_a"]
            state["major_b"] = snap["major_b"]
        play_sfx("shake")
        save_state()
        refresh_ui()
        show_toast("Aksi terakhir dibatalkan (Undo).")

    def open_settings_dialog(e):
        play_sfx("click")
        tf_table = bind_typing_guard(ft.TextField(label="Nomor Meja", value=state.get("table_no", "MEJA 01"), border_color=GOLD))
        tf_stage = bind_typing_guard(ft.TextField(label="Babak", value=state.get("stage_name", "PENYISIHAN"), border_color=GOLD))
        tf_a = bind_typing_guard(ft.TextField(label="Nama Tim Merah", value=state["team_a"], border_color=RED_ALERT))
        tf_pa = bind_typing_guard(ft.TextField(label="Pemain Merah", hint_text="Contoh: Andi & Muslim", value=state.get("players_a", ""), border_color=BORDER_COLOR))
        tf_b = bind_typing_guard(ft.TextField(label="Nama Tim Biru", value=state["team_b"], border_color=BLUE_TEAM))
        tf_pb = bind_typing_guard(ft.TextField(label="Pemain Biru", hint_text="Contoh: Eko & Eka", value=state.get("players_b", ""), border_color=BORDER_COLOR))
        selected_fmt = [state["match_format"]]

        btn_bo3 = make_button("BO3", GOLD if selected_fmt[0] == "BO3" else CARD_ACTIVE, BG_DARK if selected_fmt[0] == "BO3" else TEXT_PRIMARY, None, expand=True, height=40)
        btn_bo5 = make_button("BO5", GOLD if selected_fmt[0] == "BO5" else CARD_ACTIVE, BG_DARK if selected_fmt[0] == "BO5" else TEXT_PRIMARY, None, expand=True, height=40)

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
            state["table_no"] = (tf_table.value or "MEJA 01").strip().upper()
            state["stage_name"] = (tf_stage.value or "PENYISIHAN").strip().upper()
            state["team_a"] = (tf_a.value or "TIM MERAH").strip().upper()
            state["players_a"] = (tf_pa.value or "").strip()
            state["team_b"] = (tf_b.value or "TIM BIRU").strip().upper()
            state["players_b"] = (tf_pb.value or "").strip()
            state["match_format"] = selected_fmt[0]
            play_sfx("click")
            save_state()
            close_dialog(edit_dlg)
            refresh_ui()

        edit_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("Meja, Tim & Pemain", color=GOLD, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Column(
                tight=True,
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Row(spacing=8, controls=[ft.Container(expand=True, content=tf_table), ft.Container(expand=True, content=tf_stage)]),
                    tf_a,
                    tf_pa,
                    tf_b,
                    tf_pb,
                    ft.Row(spacing=8, controls=[btn_bo3, btn_bo5]),
                ],
            ),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(edit_dlg)),
                make_button("Simpan", GOLD, BG_DARK, save_settings, font_size=11),
            ],
        )
        open_dialog(edit_dlg)

    settings_header_btn = make_button("⚙️ Meja", CARD_ACTIVE, GOLD, open_settings_dialog, expand=True, height=34, font_size=11)

    def confirm_reset_round(e):
        play_sfx("shake")

        def do_reset_set(ev):
            if is_match_locked():
                check_locked_guard()
                close_dialog(rst_dlg)
                return
            reset_turn_timer(silent=True)
            state["score_a"] = 0
            state["score_b"] = 0
            state["round_num"] = 1
            state["awaiting_next_set"] = False
            state["match_finished"] = False
            state["minor_a"] = 0
            state["minor_b"] = 0
            state["major_a"] = 0
            state["major_b"] = 0
            state["history"] = []
            play_sfx("shake")
            save_state()
            close_dialog(rst_dlg)
            refresh_ui()
            announce_balak_opener(f"Set {state['set_num']} Direset")

        def do_reset_match(ev):
            close_dialog(rst_dlg)
            start_fresh_match()

        rst_dlg = ft.AlertDialog(
            modal=True,
            bgcolor=CARD_BG,
            title=ft.Text("Reset Skor?", color=RED_ALERT, weight=ft.FontWeight.BOLD, size=15),
            content=ft.Text("Reset skor Set berjalan atau reset seluruh Match (0-0)?", color=TEXT_PRIMARY, size=12),
            actions=[
                ft.TextButton("Batal", on_click=lambda ev: close_dialog(rst_dlg)),
                make_button("Reset Set", AMBER, BG_DARK, do_reset_set, font_size=11),
                make_button("Reset Match", RED_ALERT, TEXT_PRIMARY, do_reset_match, font_size=11),
            ],
        )
        open_dialog(rst_dlg)

    team_a_card = ft.Container(
        expand=True,
        padding=12,
        border_radius=14,
        bgcolor=CARD_ACTIVE,
        border=border_all(2, GOLD),
        on_click=lambda e: select_team("A"),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
            controls=[
                ft.Text("● TIM MERAH", size=11, weight=ft.FontWeight.BOLD, color=RED_ALERT, text_align=ft.TextAlign.CENTER),
                team_a_name_text,
                players_a_subtext,
                score_a_box,
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
            spacing=4,
            controls=[
                ft.Text("● TIM BIRU", size=11, weight=ft.FontWeight.BOLD, color=BLUE_TEAM, text_align=ft.TextAlign.CENTER),
                team_b_name_text,
                players_b_subtext,
                score_b_box,
                status_b_text,
                foul_b_text,
            ],
        ),
    )

    score_cards_row = ft.Row(spacing=8, controls=[team_a_card, team_b_card])

    active_team_banner = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=GOLD)
    penalty_target_banner = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color=AMBER)

    btn_bonus_1x = make_button("1x Normal", EMERALD, BG_DARK, lambda e: set_bonus_mode("1x"), expand=True, height=42, font_size=11)
    btn_bonus_2x = make_button("2x Ujung/Sama", CARD_ACTIVE, TEXT_PRIMARY, lambda e: set_bonus_mode("2x"), expand=True, height=42, font_size=11)
    btn_bonus_50 = make_button("+50 Balak", CARD_ACTIVE, TEXT_PRIMARY, lambda e: set_bonus_mode("+50"), expand=True, height=42, font_size=11)
    btn_batu_beradu = make_button("⚔️ Batu Beradu", "#242B38", GOLD, open_batu_beradu_dialog, expand=True, height=42, font_size=11)
    btn_tile_calc = make_button("🧮 Hitung Batu", "#1E293B", EMERALD, open_tile_calculator_dialog, expand=True, height=42, font_size=11)

    def _update_party_buttons(dec: str, t_str: str, btn_yes, btn_no, reason_field: ft.TextField, sub_txt: ft.Text, label_role: str):
        if dec == "setuju":
            set_button_label(btn_yes, "✓ Setuju")
            btn_yes.bgcolor = EMERALD
            btn_yes.color = BG_DARK
            set_button_label(btn_no, "Tidak Setuju")
            btn_no.bgcolor = CARD_ACTIVE
            btn_no.color = TEXT_MUTED
            reason_field.visible = False
            sub_txt.value = f"Disetujui {label_role} ({t_str})"
            sub_txt.color = EMERALD
        elif dec == "tidak_setuju":
            set_button_label(btn_yes, "Setujui")
            btn_yes.bgcolor = CARD_ACTIVE
            btn_yes.color = TEXT_MUTED
            set_button_label(btn_no, "✗ Tidak Setuju")
            btn_no.bgcolor = RED_ALERT
            btn_no.color = TEXT_PRIMARY
            reason_field.visible = True
            sub_txt.value = f"Tidak Setuju ({t_str})"
            sub_txt.color = RED_ALERT
        else:
            set_button_label(btn_yes, "Setujui")
            btn_yes.bgcolor = CARD_ACTIVE
            btn_yes.color = TEXT_PRIMARY
            set_button_label(btn_no, "Tidak Setuju")
            btn_no.bgcolor = CARD_ACTIVE
            btn_no.color = TEXT_PRIMARY
            reason_field.visible = False
            sub_txt.value = f"Menunggu {label_role}"
            sub_txt.color = TEXT_MUTED

    def refresh_ui():
        try:
            normalize_match_bounds()
            locked = is_match_locked()
            awaiting_set = bool(state.get("awaiting_next_set")) and not state.get("match_finished")
            fmt_label = "FINAL BO5" if state["match_format"] == "BO5" else "REGULER BO3"
            tbl = state.get("table_no", "MEJA 01")
            stg = state.get("stage_name", "PENYISIHAN")
            lock_tag = " • 🔒 SAH" if locked else (" • ⏸ TUNGGU SET" if awaiting_set else "")
            match_meta_badge.value = f"{tbl} • {stg} • {fmt_label} • SET {state['set_num']} ({state['sets_a']}-{state['sets_b']}){lock_tag}"

            balak_str = get_opening_balak(state["round_num"])
            round_balak_text.value = f"Ronde {state['round_num']} • {balak_str}"

            holder_name = state["team_a"] if state.get("opener_team", "A") == "A" else state["team_b"]
            opener_badge_text.value = f"🀄 {balak_str}: {holder_name}"
            opener_badge_text.color = RED_ALERT if state.get("opener_team", "A") == "A" else BLUE_TEAM

            next_set_banner.visible = awaiting_set
            set_button_label(btn_start_next_set_banner, f"▶ Mulai Set {state['set_num']}")
            next_set_banner_text.value = (
                f"⏸ Set {state['set_num']} siap • {balak_str}: {holder_name}. "
                f"Klik mulai, lalu yang punya {balak_str} turunkan batunya."
            )

            score_cards_row.controls = [team_b_card, team_a_card] if state.get("swap_sides") else [team_a_card, team_b_card]

            if state.get("dispute_active"):
                timer_state["running"] = False
                dispute_banner.visible = True
                dispute_banner_text.value = f"⚖️ SENGKETA AKTIF — {state.get('dispute_info', '')}"
                set_button_label(dispute_header_btn, "⚖️ Pending!")
                dispute_header_btn.bgcolor = RED_ALERT
                dispute_header_btn.color = TEXT_PRIMARY
            else:
                dispute_banner.visible = False
                set_button_label(dispute_header_btn, "⚖️ Protes")
                dispute_header_btn.bgcolor = CARD_ACTIVE
                dispute_header_btn.color = AMBER

            sm = state.get("sound_mode", "all")
            if sm == "all":
                set_button_label(sound_mode_btn, "🔊 Meriah")
                sound_mode_btn.color = EMERALD
            elif sm == "voice":
                set_button_label(sound_mode_btn, "🎙️ Wasit")
                sound_mode_btn.color = GOLD
            else:
                set_button_label(sound_mode_btn, "🔇 Hening")
                sound_mode_btn.color = TEXT_MUTED

            team_a_name_text.value = state["team_a"]
            team_b_name_text.value = state["team_b"]
            pa = (state.get("players_a") or "").strip()
            pb = (state.get("players_b") or "").strip()
            players_a_subtext.value = f"Pemain: {pa}" if pa else "Pasangan: -"
            players_b_subtext.value = f"Pemain: {pb}" if pb else "Pasangan: -"

            score_a_text.value = str(state["score_a"])
            score_b_text.value = str(state["score_b"])

            st_a_txt, st_a_col = get_status_info(state["score_a"])
            st_b_txt, st_b_col = get_status_info(state["score_b"])
            status_a_text.value = st_a_txt
            status_a_text.color = st_a_col
            status_b_text.value = st_b_txt
            status_b_text.color = st_b_col

            foul_a_text.value = f"Ringan {state['minor_a']}/2 • Berat {state['major_a']}/3"
            foul_a_text.color = RED_ALERT if state["major_a"] >= 3 else AMBER
            foul_b_text.value = f"Ringan {state['minor_b']}/2 • Berat {state['major_b']}/3"
            foul_b_text.color = RED_ALERT if state["major_b"] >= 3 else AMBER

            is_a = state["selected_team"] == "A"
            team_a_card.bgcolor = CARD_ACTIVE if is_a else CARD_BG
            team_a_card.border = border_all(2, GOLD if is_a else BORDER_COLOR)
            score_a_box.border = border_all(1, GOLD if is_a else BORDER_COLOR)

            team_b_card.bgcolor = CARD_ACTIVE if not is_a else CARD_BG
            team_b_card.border = border_all(2, GOLD if not is_a else BORDER_COLOR)
            score_b_box.border = border_all(1, GOLD if not is_a else BORDER_COLOR)

            active_name = state["team_a"] if is_a else state["team_b"]
            opp_name = state["team_b"] if is_a else state["team_a"]

            if locked:
                active_team_banner.value = "🔒 TERKUNCI (SAH 3/3) — Klik 'Match Baru (0-0)'"
                active_team_banner.color = EMERALD
            elif awaiting_set:
                active_team_banner.value = f"⏸ MENUNGGU MULAI SET {state['set_num']}"
                active_team_banner.color = GOLD
            else:
                active_team_banner.value = f"Tim Aktif: {active_name}"
                active_team_banner.color = GOLD

            penalty_target_banner.value = f"⚠️ PELANGGAR / WO: {active_name} → POIN KE {opp_name}"

            bm = state["bonus_mode"]
            btn_bonus_1x.bgcolor = EMERALD if bm == "1x" else CARD_ACTIVE
            btn_bonus_1x.color = BG_DARK if bm == "1x" else TEXT_PRIMARY
            btn_bonus_2x.bgcolor = GOLD if bm == "2x" else CARD_ACTIVE
            btn_bonus_2x.color = BG_DARK if bm == "2x" else TEXT_PRIMARY
            btn_bonus_50.bgcolor = PURPLE_SPECIAL if bm == "+50" else CARD_ACTIVE
            btn_bonus_50.color = TEXT_PRIMARY

            update_timer_ui()

            set_records_column.controls.clear()
            s_recs = state.get("set_records", [])
            if not s_recs:
                set_records_column.controls.append(ft.Text(f"Set {state['set_num']} berjalan ({state['score_a']} - {state['score_b']}).", size=11, color=TEXT_MUTED))
            else:
                for sr_item in s_recs:
                    set_records_column.controls.append(
                        ft.Container(
                            padding=pad_sym(10, 5),
                            border_radius=7,
                            bgcolor=BG_DARK,
                            border=border_all(1, BORDER_COLOR),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(f"Set {sr_item.get('set')}: {sr_item.get('score_a')} - {sr_item.get('score_b')}", size=11, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                    ft.Text(f"🏆 {sr_item.get('winner')}", size=11, weight=ft.FontWeight.BOLD, color=EMERALD),
                                ],
                            ),
                        )
                    )

            ref_notes_column.controls.clear()
            notes = state.get("referee_notes", [])
            if not notes:
                ref_notes_column.controls.append(ft.Text("Belum ada catatan wasit.", size=11, color=TEXT_MUTED))
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
                            padding=pad_sym(8, 4),
                            border_radius=8,
                            bgcolor=BG_DARK,
                            border=border_all(1, BORDER_COLOR),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(note_txt, size=11, color=TEXT_PRIMARY, expand=True),
                                    make_button("✕", CARD_ACTIVE, TEXT_MUTED, make_remove_note(n_idx), height=28, font_size=10),
                                ],
                            ),
                        )
                    )

            history_column.controls.clear()
            if not state["history"]:
                history_column.controls.append(ft.Text("Belum ada catatan poin di set ini.", size=11, color=TEXT_MUTED))
            else:
                total_items = len(state["history"])
                for idx, item in enumerate(reversed(state["history"])):
                    item_no = total_items - idx
                    t_hms = f"[{item.get('time')}] " if item.get("time") else ""
                    t_name = state["team_a"] if item["team"] == "A" else state["team_b"]
                    pts_str = item.get("points_str", "")
                    lbl = item.get("label", "")
                    tr_txt = f" ({item.get('transition')})" if item.get("transition") else ""
                    if any(k in lbl for k in ("PELANGGARAN", "Pass Palsu", "Ringan", "DISKUALIFIKASI", "PROTES", "WO (")):
                        badge_col = RED_ALERT
                    elif any(k in lbl for k in ("APOLLO", "BALAK", "Sempurna")):
                        badge_col = PURPLE_SPECIAL
                    elif "Beradu" in lbl:
                        badge_col = GOLD
                    else:
                        badge_col = EMERALD

                    history_column.controls.append(
                        ft.Container(
                            padding=pad_sym(8, 5),
                            border_radius=8,
                            bgcolor=BG_DARK,
                            border=border_all(1, BORDER_COLOR),
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(f"#{item_no} {t_hms}{t_name} • {lbl}{tr_txt}", size=11, color=TEXT_PRIMARY, expand=True),
                                    ft.Text(pts_str, size=11, weight=ft.FontWeight.BOLD, color=badge_col),
                                ],
                            ),
                        )
                    )

            archive_btn_label.value = f"📂 Arsip ({len(saved_matches)})"

            ref_name_field.value = state.get("referee_name", "")
            red_rep_field.value = state.get("red_rep_name", "")
            blue_rep_field.value = state.get("blue_rep_name", "")

            ref_reject_reason_field.value = state.get("referee_reject_reason", "")
            red_reject_reason_field.value = state.get("red_reject_reason", "")
            blue_reject_reason_field.value = state.get("blue_reject_reason", "")

            red_team_label_text.value = f"● MERAH ({state['team_a']})"
            blue_team_label_text.value = f"● BIRU ({state['team_b']})"

            finish_tag = " [SELESAI]" if state.get("match_finished") else ""
            approval_summary_text.value = (
                f"Hasil{finish_tag}: {state['team_a']} vs {state['team_b']} • "
                f"Set ({state['sets_a']}-{state['sets_b']}) • Poin ({state['score_a']}-{state['score_b']})"
            )

            ref_dec = state.get("referee_decision", "")
            red_dec = state.get("red_decision", "")
            blue_dec = state.get("blue_decision", "")

            _update_party_buttons(ref_dec, state.get("approve_referee_time", ""), btn_approve_ref, btn_reject_ref, ref_reject_reason_field, ref_approve_subtext, "Wasit")
            _update_party_buttons(red_dec, state.get("approve_red_time", ""), btn_approve_red, btn_reject_red, red_reject_reason_field, red_approve_subtext, "Merah")
            _update_party_buttons(blue_dec, state.get("approve_blue_time", ""), btn_approve_blue, btn_reject_blue, blue_reject_reason_field, blue_approve_subtext, "Biru")

            decisions = [ref_dec, red_dec, blue_dec]
            approved_count = decisions.count("setuju")
            rejected_count = decisions.count("tidak_setuju")

            if approved_count == 3:
                approval_status_banner.value = "🔒 SAH & TERKUNCI (3/3 Setuju)"
                approval_status_banner.color = EMERALD
                approval_panel.border = border_all(2, EMERALD)
            elif rejected_count > 0:
                approval_status_banner.value = f"⚠️ KEBERATAN (Setuju {approved_count}/3 • Tolak {rejected_count}/3)"
                approval_status_banner.color = RED_ALERT
                approval_panel.border = border_all(2, RED_ALERT)
            else:
                approval_status_banner.value = f"⏳ Pengesahan: {approved_count}/3 Setuju"
                approval_status_banner.color = AMBER
                approval_panel.border = border_all(1, GOLD if state.get("match_finished") else BORDER_COLOR)

            page.update()
        except Exception as exc:
            try:
                err_box = ft.Container(
                    padding=12,
                    bgcolor="#451218",
                    border=border_all(1, RED_ALERT),
                    content=ft.Text(f"UI Error: {exc}\n{traceback.format_exc()[-400:]}", size=11, color=TEXT_PRIMARY),
                )
                body_host.content = err_box
                page.update()
            except Exception:
                pass

    def handle_manual_submit(e):
        if check_locked_guard() or check_awaiting_next_set_guard():
            return
        raw = (manual_score_input.value or "").strip()
        if raw.isdigit() and int(raw) > 0:
            val = int(raw)
            manual_score_input.value = ""
            add_round_score(val)

    manual_score_input.on_submit = handle_manual_submit
    ref_note_input.on_submit = handle_submit_ref_note

    quick_buttons = [
        make_button(f"+{val}", CARD_ACTIVE, TEXT_PRIMARY, lambda e, v=val: add_round_score(v), expand=True, height=42, font_size=12)
        for val in QUICK_SCORES
    ]

    header_col = ft.Column(spacing=6, controls=[])
    header = ft.Container(
        padding=pad_sym(10, 6),
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=header_col,
    )

    timer_panel = ft.Container(
        padding=pad_sym(10, 8),
        border_radius=12,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                timer_display_text,
                                ft.Column(
                                    spacing=1,
                                    controls=[
                                        ft.Text("TIMER 30 DETIK (PASAL 14)", size=10, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                        timer_status_text,
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(spacing=4, controls=[btn_timer_pause, btn_timer_stop, btn_timer_pen11]),
                    ],
                ),
                ft.Row(controls=[btn_timer_next]),
            ],
        ),
    )

    input_panel = ft.Container(
        padding=10,
        border_radius=12,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                active_team_banner,
                ft.Row(spacing=6, controls=[btn_bonus_1x, btn_bonus_2x, btn_bonus_50]),
                ft.Row(spacing=4, controls=quick_buttons),
                ft.Row(
                    spacing=6,
                    controls=[
                        ft.Container(expand=True, content=manual_score_input),
                        make_button("TAMBAH", EMERALD, BG_DARK, handle_manual_submit, height=46, font_size=11),
                    ],
                ),
                ft.Row(spacing=6, controls=[btn_tile_calc, btn_batu_beradu]),
            ],
        ),
    )

    penalty_panel = ft.Container(
        padding=10,
        border_radius=12,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                penalty_target_banner,
                ft.Row(
                    spacing=6,
                    controls=[
                        make_button("Ringan 2x=+11", "#2B2416", AMBER, open_minor_foul_dialog, expand=True, height=42, font_size=11),
                        make_button("+11 (30s/Berat)", "#3B181E", RED_ALERT, lambda e: apply_penalty(11, "Waktu 30dtk / Pelanggaran Berat (+11)", "v_pen11"), expand=True, height=42, font_size=11),
                    ],
                ),
                ft.Row(
                    spacing=6,
                    controls=[
                        make_button("+25 (Salah/Dahulu)", "#3B181E", RED_ALERT, lambda e: apply_penalty(25, "Batu Salah / Mendahului Giliran (+25)", "v_pen25"), expand=True, height=42, font_size=11),
                        make_button("+50 (Pass ≥4)", "#3B181E", RED_ALERT, lambda e: apply_penalty(50, "Pass Palsu Sisa ≥4 Batu (+50)", "v_pass50", ends_round=True), expand=True, height=42, font_size=11),
                    ],
                ),
            ],
        ),
    )

    special_panel = ft.Container(
        padding=10,
        border_radius=12,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text("KEPUTUSAN SET & KHUSUS", size=11, weight=ft.FontWeight.BOLD, color=PURPLE_SPECIAL),
                ft.Row(
                    spacing=6,
                    controls=[
                        make_button("🔥 APOLLO +2 Set", PURPLE_SPECIAL, TEXT_PRIMARY, trigger_apollo_win, expand=True, height=42, font_size=11),
                        make_button("🀄 7 Balak (101)", GOLD, BG_DARK, trigger_seven_balak_win, expand=True, height=42, font_size=11),
                    ],
                ),
                ft.Row(
                    spacing=6,
                    controls=[
                        make_button("🚫 Pass ≤3 Batu", "#3B181E", RED_ALERT, trigger_false_pass_under_3, expand=True, height=42, font_size=11),
                        make_button("🏳️ WO Lawan Menang", CARD_ACTIVE, GOLD, trigger_wo_victory, expand=True, height=42, font_size=11),
                    ],
                ),
            ],
        ),
    )

    set_recap_panel = ft.Container(
        padding=10,
        border_radius=12,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text("📊 REKAP ANTAR-SET", size=11, weight=ft.FontWeight.BOLD, color=EMERALD),
                set_records_column,
            ],
        ),
    )

    referee_panel = ft.Container(
        padding=10,
        border_radius=12,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Text("📋 CATATAN WASIT", size=11, weight=ft.FontWeight.BOLD, color=GOLD),
                ft.Row(
                    spacing=6,
                    controls=[
                        make_button("Shuffle", CARD_ACTIVE, TEXT_PRIMARY, lambda e: handle_quick_ref_tag("Shuffle Ulang (5/6 Balak • Pasal 8c)"), expand=True, height=40, font_size=11),
                        make_button("Tukar Kursi", CARD_ACTIVE, TEXT_PRIMARY, lambda e: handle_quick_ref_tag("Tukar Tempat Duduk (Pasal 7b)"), expand=True, height=40, font_size=11),
                        make_button("Ganti Pemain", CARD_ACTIVE, TEXT_PRIMARY, lambda e: handle_quick_ref_tag("Pergantian Pemain (Pasal 1b)"), expand=True, height=40, font_size=11),
                    ],
                ),
                ft.Row(
                    spacing=6,
                    controls=[
                        ft.Container(expand=True, content=ref_note_input),
                        make_button("CATAT", GOLD, BG_DARK, handle_submit_ref_note, height=46, font_size=11),
                    ],
                ),
                ref_notes_column,
            ],
        ),
    )

    def build_party_approval_box(title_widget: ft.Control, name_field: ft.TextField, approve_btn, reject_btn, reason_field: ft.TextField, sub_text: ft.Text):
        return ft.Container(
            padding=8,
            border_radius=10,
            bgcolor=BG_DARK,
            border=border_all(1, BORDER_COLOR),
            content=ft.Column(
                spacing=5,
                controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[title_widget, sub_text]),
                    name_field,
                    ft.Row(spacing=6, controls=[approve_btn, reject_btn]),
                    reason_field,
                ],
            ),
        )

    approval_panel = ft.Container(
        padding=10,
        border_radius=12,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=7,
            controls=[
                ft.Text("✍️ PENGESAHAN TTD HASIL AKHIR", size=11, weight=ft.FontWeight.BOLD, color=GOLD),
                approval_summary_text,
                approval_status_banner,
                build_party_approval_box(ft.Text("● WASIT", size=11, weight=ft.FontWeight.BOLD, color=GOLD), ref_name_field, btn_approve_ref, btn_reject_ref, ref_reject_reason_field, ref_approve_subtext),
                build_party_approval_box(red_team_label_text, red_rep_field, btn_approve_red, btn_reject_red, red_reject_reason_field, red_approve_subtext),
                build_party_approval_box(blue_team_label_text, blue_rep_field, btn_approve_blue, btn_reject_blue, blue_reject_reason_field, blue_approve_subtext),
                ft.Row(
                    spacing=6,
                    controls=[
                        make_button("Simpan Arsip", EMERALD, BG_DARK, handle_manual_save_match, expand=True, height=40, font_size=11),
                        make_button("Match Baru (0-0)", CARD_ACTIVE, TEXT_PRIMARY, start_fresh_match, expand=True, height=40, font_size=11),
                    ],
                ),
            ],
        ),
    )

    archive_bar = ft.Container(
        padding=pad_sym(10, 10),
        border_radius=10,
        bgcolor=CARD_ACTIVE,
        border=border_all(1, GOLD),
        alignment=align_center(),
        on_click=open_archive_dialog,
        content=archive_btn_label,
    )

    history_panel = ft.Container(
        padding=10,
        border_radius=12,
        bgcolor=CARD_BG,
        border=border_all(1, BORDER_COLOR),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("AUDIT TRAIL RONDE & SANKSI", size=11, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        make_button("↩ Undo", CARD_ACTIVE, GOLD, undo_last, height=34, font_size=11),
                    ],
                ),
                history_column,
                archive_bar,
            ],
        ),
    )

    portrait_list = ft.ListView(
        expand=True,
        spacing=10,
        padding=pad_sym(8, 6),
        controls=[],
    )

    landscape_left_list = ft.ListView(
        expand=True,
        spacing=8,
        padding=pad_sym(6, 4),
        controls=[],
    )

    landscape_right_list = ft.ListView(
        expand=True,
        spacing=8,
        padding=pad_sym(6, 4),
        controls=[],
    )

    landscape_row = ft.Row(
        expand=True,
        spacing=4,
        controls=[
            ft.Container(expand=5, content=landscape_left_list),
            ft.Container(expand=6, content=landscape_right_list),
        ],
    )

    body_host = ft.Container(
        expand=True,
        content=portrait_list,
    )

    def detect_landscape() -> bool:
        w = getattr(page, "width", None) or 0
        h = getattr(page, "height", None) or 0
        return bool(w > h and w >= 550)

    def apply_responsive_layout(force: bool = False):
        if typing_active[0] and not force:
            return
        new_land = detect_landscape()
        if not force and new_land == is_landscape_mode[0]:
            return
        is_landscape_mode[0] = new_land

        portrait_list.controls.clear()
        landscape_left_list.controls.clear()
        landscape_right_list.controls.clear()
        header_col.controls.clear()

        title_brand_row = ft.Row(
            spacing=8,
            expand=True,
            controls=[
                logo_widget,
                ft.Column(
                    spacing=1,
                    expand=True,
                    controls=[
                        ft.Text(
                            "ORADO DOMINO 101",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        match_meta_badge,
                    ],
                ),
            ],
        )

        action_btns_row = ft.Row(
            spacing=4,
            controls=[
                sound_mode_btn,
                dispute_header_btn,
                rules_header_btn,
                settings_header_btn,
            ],
        )

        opener_tools_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=4,
            controls=[
                round_balak_text,
                ft.Container(
                    padding=pad_sym(8, 4),
                    border_radius=6,
                    bgcolor=BG_DARK,
                    border=border_all(1, BORDER_COLOR),
                    on_click=switch_opener_team,
                    content=opener_badge_text,
                ),
                ft.Row(
                    spacing=4,
                    controls=[
                        make_button("⇄ Sisi", CARD_ACTIVE, TEXT_PRIMARY, toggle_swap_sides, height=30, font_size=10),
                        make_button("Reset", "#3B181E", RED_ALERT, confirm_reset_round, height=30, font_size=10),
                    ],
                ),
            ],
        )

        if new_land:
            score_a_text.size = 52
            score_b_text.size = 52
            score_a_box.padding = pad_sym(6, 6)
            score_b_box.padding = pad_sym(6, 6)
            team_a_card.padding = 10
            team_b_card.padding = 10
            header.padding = pad_sym(10, 5)
            header_col.spacing = 4
            header_col.controls.extend([
                ft.Row(
                    spacing=8,
                    controls=[
                        title_brand_row,
                        ft.Container(width=310, content=action_btns_row),
                    ],
                ),
                opener_tools_row,
            ])

            landscape_left_list.controls.extend([
                score_cards_row,
                next_set_banner,
                timer_panel,
            ])
            landscape_right_list.controls.extend([
                input_panel,
                penalty_panel,
                special_panel,
                set_recap_panel,
                referee_panel,
                approval_panel,
                history_panel,
            ])
            body_host.content = landscape_row
        else:
            score_a_text.size = 56
            score_b_text.size = 56
            score_a_box.padding = pad_sym(8, 8)
            score_b_box.padding = pad_sym(8, 8)
            team_a_card.padding = 12
            team_b_card.padding = 12
            header.padding = pad_sym(10, 7)
            header_col.spacing = 6
            header_col.controls.extend([
                title_brand_row,
                action_btns_row,
                opener_tools_row,
            ])

            portrait_list.controls.extend([
                score_cards_row,
                next_set_banner,
                timer_panel,
                input_panel,
                penalty_panel,
                special_panel,
                set_recap_panel,
                referee_panel,
                approval_panel,
                history_panel,
            ])
            body_host.content = portrait_list

    def on_page_resized(e):
        before = is_landscape_mode[0]
        apply_responsive_layout(force=False)
        if before != is_landscape_mode[0]:
            try:
                page.update()
            except Exception:
                pass

    if hasattr(page, "on_resized"):
        page.on_resized = on_page_resized
    if hasattr(page, "on_resize"):
        page.on_resize = on_page_resized

    root_layout = ft.Column(
        expand=True,
        spacing=4,
        controls=[
            header,
            dispute_banner,
            body_host,
        ],
    )

    SafeAreaCls = getattr(ft, "SafeArea", None)
    if SafeAreaCls:
        page.add(SafeAreaCls(expand=True, content=root_layout))
    else:
        page.add(root_layout)

    load_state()
    if "sound_mode" not in state:
        state["sound_mode"] = "all" if state.get("sound_on", True) else "mute"
    apply_responsive_layout(force=True)
    refresh_ui()
    init_audio_players()


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main, assets_dir="assets")
    else:
        ft.app(target=main, assets_dir="assets")
